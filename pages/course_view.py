from __future__ import annotations
import json, re, time
from typing import Dict, Any, List, Tuple
from uuid import UUID

import streamlit as st
from supabase import create_client, Client
from login_popup import display_login_popup
import pandas as pd
import matplotlib.pyplot as plt  # noqa: F401 chart exec
from openai import OpenAI
from pdf_generator import generate_course_pdf

# ────────────────────────── UTILITIES ──────────────────────────

def is_valid_uuid(val: str) -> bool:
    try:
        UUID(str(val))
        return True
    except Exception:
        return False


def clean_json(s: str) -> str:
    """Remove code-block fencing and whitespace around JSON strings."""
    return re.sub(r"`(?:json|python)?\n?|\n`", "", s).strip()


def fix_json(s: str) -> str:
    """Escape stray newlines inside JSON string literals so json.loads succeeds."""
    out, ins, esc = "", False, False
    for ch in s:
        if ins:
            if esc:
                out += ch; esc = False
            elif ch == "\\":
                out += ch; esc = True
            elif ch == '"':
                out += ch; ins = False
            elif ch == "\n":
                out += "\\n"
            else:
                out += ch
        else:
            out += ch
            if ch == '"':
                ins = True
    return out


def extract_links(html: str) -> List[Tuple[str, str]]:
    """Return [(text, href), …] pairs from <a href="…">text</a> snippets."""
    pattern = re.compile(r"<a\s[^>]*href=['\"](.*?)['\"][^>]*>(.*?)</a>", re.I | re.S)
    return [(m.group(2).strip(), m.group(1).strip()) for m in pattern.finditer(html)]


def parse_scheme(scheme: str, duration: int) -> Dict[str, Any]:
    """Convert raw multi-paragraph scheme string → dict[WeekX]['paragraphs']"""
    course: Dict[str, Any] = {}
    if re.search(r"Week\s+\d+:", scheme):
        blocks = re.split(r"(?=Week\s+\d+:)", scheme)
        for block in blocks:
            m = re.match(r"Week\s+(\d+):\s*(.*)", block, re.S)
            if not m:
                continue
            wk, payload = int(m.group(1)), m.group(2)
            course[f"Week{wk}"] = {"paragraphs": {}}
            paras = re.findall(
                r"Paragraph\s+\d+:\s*(.*?)(?=\nParagraph\s+\d+:|\nWeek\s+\d+:|\Z)",
                payload, re.S
            )
            for idx, p in enumerate(paras, 1):
                course[f"Week{wk}"]["paragraphs"][f"Paragraph{idx}"] = {
                    "text": p.strip(),
                    "resources": extract_links(p)
                }
    else:
        paras = re.findall(r"Paragraph\s+\d+:\s*(.*?)(?=\nParagraph\s+\d+:|\Z)", scheme, re.S) or [scheme]
        course["Week1"] = {"paragraphs": {}}
        for idx, p in enumerate(paras, 1):
            course["Week1"]["paragraphs"][f"Paragraph{idx}"] = {
                "text": p.strip(),
                "resources": extract_links(p)
            }
    for i in range(1, duration + 1):
        course.setdefault(f"Week{i}", {"paragraphs": {}})
    return course

def update_course_completion(supabase: Client, course_id: str, course_dict: Dict[str, Any]) -> None:
    """Update course checked status when all checkboxes are checked"""
    all_checkbox_keys = []
    # Collect all checkbox keys across all weeks
    for week_num in range(1, len(course_dict) + 1):
        week_key = f"Week{week_num}"
        for pid, para in course_dict.get(week_key, {}).get("paragraphs", {}).items():
            for i, _ in enumerate(para.get("resources", [])):
                all_checkbox_keys.append(f"wk{week_num}_{pid}_r{i}")
    
    # Check if all checkboxes are checked
    if all(st.session_state.get(key, False) for key in all_checkbox_keys):
        try:
            # Update course completion status
            supabase.table("courses").update({"checked": True}).eq("id", course_id).execute()
            
            # Get current user's XP
            user_id = st.session_state["user"]["id"]
            response = supabase.table("user_profile").select("xp").eq("user_id", user_id).execute()
            
            if response.data:
                current_xp = response.data[0].get("xp", 0) or 0
                # Add 100 XP for completing the course
                new_xp = current_xp + 100
                # Update user's XP
                supabase.table("user_profile").update({"xp": new_xp}).eq("user_id", user_id).execute()
                
        except Exception as e:
            st.error(f"Could not update course completion status: {e}")

def update_course_final_completion(supabase: Client, course_id: str) -> None:
    """Update course completed status when all tests are completed"""
    try:
        # Get current completion status
        response = supabase.table("courses").select("completed").eq("id", course_id).single().execute()
        if not response.data.get("completed", False):
            # Update completed status to true
            supabase.table("courses").update({"completed": True}).eq("id", course_id).execute()
    except Exception as e:
        st.error(f"Could not update final completion status: {e}")

# ────────────────────────────── INIT ──────────────────────────────

st.markdown(
    """
<style>
#MainMenu, footer {visibility: hidden;}
/* floating tutor chat */
div:has( > .element-container div.floating) {
    display: flex; flex-direction: column; position: fixed;
    right: 1rem; top: 1rem; width: 26%; max-height: calc(100vh - 2rem);
    overflow-y: auto; padding: .75rem; padding-top: 80px; border: 1px solid #ccc; border-radius: 4px;
    background: var(--background-color); z-index: 999;
}
section.main > div.block-container {padding-right: 28%;}
/* Hide right container when course is completed */
div:has( > .element-container div.floating.hide-container) {
    display: none !important;
}
section.main > div.block-container.hide-right-padding {
    padding-right: 1rem !important;
}
</style>
""",
    unsafe_allow_html=True,
)

# session state init
if "current_week" not in st.session_state:
    st.session_state.current_week = 1
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "show_test" not in st.session_state:
    st.session_state.show_test = False
if "disabled_checkboxes" not in st.session_state:
    st.session_state.disabled_checkboxes = set()

# ─────────────────────── LOAD COURSE DATA ───────────────────────

display_login_popup()

course_id = st.session_state.get("current_course_id")
if not course_id:
    st.warning("No course selected."); st.stop()
if not is_valid_uuid(course_id):
    st.error("Invalid course ID."); st.stop()

SUPABASE_URL = "https://fcyutudqmkhrywffsjky.supabase.co"
SUPABASE_ANON_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImZjeXV0dWRxbWtocnl3ZmZzamt5Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDI0MjQ3OTAsImV4cCI6MjA1ODAwMDc5MH0."
    "IucZQwgH1CFYFCgb9E3-TV7I-NOnPq9-3lmrWc4ZE7I"
)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
row = supabase.table("courses").select("*").eq("id", course_id).single().execute().data
if not row:
    st.error("Course not found."); st.stop()

# Initialize notes after we have the row data
if "notes" not in st.session_state:
    st.session_state.notes = row.get("notes", "")

test_content = row.get("test")

# parse content
raw_content = row.get("content")
if isinstance(raw_content, dict):
    content = raw_content
elif isinstance(raw_content, str):
    try:
        content = json.loads(fix_json(clean_json(raw_content)))
    except json.JSONDecodeError:
        content = {}
else:
    content = {}
if not content:
    st.error("Course content is missing or malformed."); st.stop()

# build course structure
params = content.get("parameters", {})
m = re.match(r"(\d+)", params.get("duration", "1"))
if m:
    duration = int(m.group(1))
else:
    duration = int(params.get("duration", 1) or 1)
max_week = duration
course_dict: Dict[str, Any] = {}

if "course_content" in params:
    for wk_item in params["course_content"]:
        wk = int(wk_item.get("week_number", 1))
        key = f"Week{wk}"
        course_dict[key] = {
            "paragraphs": {},
            "supplemental": wk_item.get("supplemental_material", {})
        }
        for idx, para in enumerate(wk_item.get("paragraphs", []), 1):
            course_dict[key]["paragraphs"][f"Paragraph{idx}"] = {
                "title": para.get("paragraph_title", ""),
                "text": para.get("text", ""),
                "resources": [(u, u) for u in para.get("resources", [])]
            }
    for i in range(1, duration+1):
        course_dict.setdefault(f"Week{i}", {"paragraphs": {}, "supplemental": {}})
else:
    course_dict = parse_scheme(content.get("scheme", ""), duration)

# collect ordered keys for progress
wk = st.session_state.current_week
checkbox_keys: List[str] = []
# paragraph resource keys
for pid, para in course_dict.get(f"Week{wk}", {}).get("paragraphs", {}).items():
    for i, _ in enumerate(para.get("resources", [])):
        checkbox_keys.append(f"wk{wk}_{pid}_r{i}")

# init saved progress
init_flag = f"initialized_{course_id}_{wk}"
if init_flag not in st.session_state:
    stored = 0
    try:
        stored = int(row.get("progress") or 0)
    except Exception:
        pass
    for i, key in enumerate(checkbox_keys):
        st.session_state[key] = i < stored
        if i < stored:
            st.session_state.disabled_checkboxes.add(key)
    st.session_state[init_flag] = True

# callback for checkbox order and saving
def on_checkbox_change(changed_key):
    idx = checkbox_keys.index(changed_key)
    # ensure previous is checked
    if idx > 0 and not st.session_state.get(checkbox_keys[idx-1], False):
        st.session_state[changed_key] = False
        st.toast("Please check items in order.", icon="⚠️")
        return
    
    # If checkbox was checked, disable it
    if st.session_state[changed_key]:
        st.session_state.disabled_checkboxes.add(changed_key)
    else:
        st.session_state.disabled_checkboxes.discard(changed_key)
    
    # count done
    done = sum(st.session_state.get(k, False) for k in checkbox_keys)
    try:
        supabase.table("courses").update({"progress": done}).eq("id", course_id).execute()
        # Check if all checkboxes across all weeks are checked
        update_course_completion(supabase, course_id, course_dict)
    except Exception as e:
        st.error(f"Could not update progress: {e}")

# dialog for test
@st.dialog("Knowledge Check", width="large")
def show_test_dialog():
    data = {}
    if isinstance(test_content, str):
        try:
            data = json.loads(fix_json(clean_json(test_content)))
        except Exception:
            data = {}
    else:
        data = test_content or {}
    st.header("Knowledge Check")
    answers: Dict[int, str] = {}
    for i, q in enumerate(data.get("questions", [])):
        st.subheader(f"Question {i+1}")
        st.write(q.get("question", ""))
        opts = q.get("options", {})
        answers[i] = st.radio("", options=list(opts.keys()), format_func=lambda x,o=opts: o.get(x, ""), key=f"q{i}")
    if st.button("Submit"):
        wrong = sum(1 for i, q in enumerate(data.get("questions", [])) if answers.get(i) != q.get("correct_answer"))
        if wrong <= 1:
            try:
                comp = supabase.table("courses").select("completition").eq("id", course_id).single().execute().data
                curr = int(comp.get("completition") or 0)
                supabase.table("courses").update({"completition": curr+1}).eq("id", course_id).execute()
            except Exception as e:
                st.error(f"Could not update completition: {e}")
            st.success("Passed! Moving on.")
            st.session_state.show_test = False
            st.session_state.current_week += 1
            st.rerun()
        else:
            st.error(f"{wrong} mistakes—max is 1.")

# main layout
subject = content.get("topic", params.get("main_subject", "Untitled Course"))
st.title(f"{subject} — Week {wk}")

# Calculate progress variables before columns
done = sum(st.session_state.get(k, False) for k in checkbox_keys)
total = len(checkbox_keys)

# Check if we should show congratulations
show_congrats = False
if total and done == total and wk >= max_week:
    try:
        comp = supabase.table("courses").select("completition, completed").eq("id", course_id).single().execute().data
        tests_completed = int(comp.get("completition") or 0)
        if tests_completed >= duration:  # All tests completed
            # Update final completion status
            update_course_final_completion(supabase, course_id)
            show_congrats = True
    except Exception as e:
        st.error(f"Could not verify test completion: {e}")

# Create columns based on whether congratulations should be shown
if show_congrats:
    col_left = st.container()
else:
    col_left, col_right = st.columns([7, 3])

with col_left:
    if show_congrats:
        with st.container():
            st.markdown("""
            <div style='text-align: center; padding: 2rem; border: 1px solid #ccc; border-radius: 8px; margin-bottom: 2rem;'>
                <h1 style='text-align: center;'>✅</h1>
                <h3 style='text-align: center;'>Congratulations!</h3>
                <p style='text-align: center;'>You successfully completed a {subject} course.</p>
            </div>
            """, unsafe_allow_html=True)
            col1, col2, col3 = st.columns([1,2,1])
            with col2:
                if st.button("Download course", use_container_width=True):
                    # Generate PDF
                    pdf_bytes = generate_course_pdf(course_dict, subject)
                    # Create download button
                    st.download_button(
                        label="Click to download PDF",
                        data=pdf_bytes,
                        file_name=f"{subject.replace(' ', '_')}_course.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
    else:
        # paragraphs and resources
        for pid, para in course_dict.get(f"Week{wk}", {}).get("paragraphs", {}).items():
            # Display paragraph title as subheading
            if para.get("title"):
                st.subheader(para["title"])
                
            sk = f"wk{wk}_{pid}_stream"
            if not st.session_state.get(sk):
                def gen(txt):
                    for w in txt.split():
                        yield w + " "; time.sleep(0.004)
                st.write_stream(gen(para["text"]))
                st.session_state[sk] = True
            else:
                st.markdown(para["text"], unsafe_allow_html=True)
            # display resources as checkboxes in one row
            res = para.get("resources", [])
            if res:
                cols = st.columns(len(res))
                for idx, (_, url) in enumerate(res):
                    label = re.sub(r"^https?://(www\\.)?", "", url).split("/")[0]
                    with cols[idx]:
                        key = f"wk{wk}_{pid}_r{idx}"
                        st.checkbox(f"[{label}]({url})", key=key, on_change=on_checkbox_change, args=(key,), disabled=st.session_state.get(key, False))

        # supplemental materials for this week
        supp = course_dict.get(f"Week{wk}", {}).get("supplemental", {})
        # bulletpoints list
        if supp.get("bulletpoints"):
            st.markdown("**Key takeaways:**")
            for bp in supp.get("bulletpoints", []):
                st.markdown(f"- {bp}")
        # images
        for img in supp.get("images", []):
            try:
                st.image(img, width=200)
            except Exception:
                st.error(f"Could not load image: {img}")
        # charts and tables side by side
        chart_col, table_col = st.columns(2)
        with chart_col:
            for ch in supp.get("charts", []):
                ch_mod = re.sub(r"figsize=\([^)]*\)", "figsize=(5,3)", ch)
                try:
                    exec(ch_mod, globals())
                except Exception:
                    st.code(ch, language="python")
        with table_col:
            for tb in supp.get("tables", []):
                try:
                    exec(tb, globals())
                except Exception:
                    st.code(tb, language="python")

if not show_congrats:
    with col_right:
        st.markdown('<div class="floating"></div>', unsafe_allow_html=True)
        st.header("Progress")
        st.progress(done / (total or 1), text=f"Week {wk}: {done}/{total}")
        
        if st.session_state.show_test:
            show_test_dialog()
        elif done == total and total > 0:  # Only show test button when all checkboxes are checked
            if st.button("Take a test"):
                st.session_state.show_test = True
                st.rerun()
            
        if total and done == total and wk >= max_week:
            st.success("Course complete!")
            # Check if all tests are completed
            try:
                comp = supabase.table("courses").select("completition, completed").eq("id", course_id).single().execute().data
                tests_completed = int(comp.get("completition") or 0)
                if tests_completed >= duration:  # All tests completed
                    # Update final completion status
                    update_course_final_completion(supabase, course_id)

            except Exception as e:
                st.error(f"Could not verify test completion: {e}")

        st.subheader("Notes")
        notes = st.text_area("", value=st.session_state.notes, height=200, key="notes_input")
        if notes != st.session_state.notes:
            try:
                supabase.table("courses").update({"course_notes": notes}).eq("id", course_id).execute()
                st.session_state.notes = notes
                st.toast("Notes saved!", icon="💾")
            except Exception as e:
                st.error(f"Could not save notes: {e}")

        st.subheader("Tutor Chat")
        client = OpenAI(api_key="sk-...", organization="org-...")
        for m in st.session_state.chat_history:
            with st.chat_message(m["role"]):
                st.markdown(m["content"], unsafe_allow_html=True)
        if prompt := st.chat_input("Ask …"):
            st.session_state.chat_history.append({"role":"user","content":prompt})
            with st.chat_message("user"):
                st.markdown(prompt)
            stream = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role":"system","content":"You are a concise, helpful teacher."}] + st.session_state.chat_history,
                stream=True
            )
            with st.chat_message("assistant"):
                reply = st.write_stream(stream)
            st.session_state.chat_history.append({"role":"assistant","content":reply})
