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
from src.components.floating_container import render_floating_container
import pathlib
import io
from src.utils.xp_manager import xp_manager
import os

# Import PIL components separately
from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont

# Initialize OpenAI client with API key from secrets.toml
client = OpenAI(
    api_key=st.secrets["openai"]["api_key"],
    organization=st.secrets["openai"]["org_id"]
)

# ────────────────────────── UTILITIES ──────────────────────────
display_login_popup()
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
    """Update course progress status when all paragraphs are viewed"""
    try:
        # Update course progress status
        supabase.table("courses").update({"progress": True}).eq("id", course_id).execute()
        
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
        st.error(f"Could not update course progress status: {e}")

def update_course_final_completion(supabase: Client, course_id: str) -> None:
    """Update course completed status when all tests are completed"""
    try:
        # Get current completion status
        response = supabase.table("courses").select("completed").eq("id", course_id).single().execute()
        if not response.data.get("completed", False):
            # Update completed status to true
            supabase.table("courses").update({"completed": True}).eq("id", course_id).execute()
            # Add XP reward for course completion
            user_id = st.session_state["user"]["id"]
            xp_manager.reward_course_completion(user_id)
    except Exception as e:
        st.error(f"Could not update final completion status: {e}")


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
                # Get current completion status
                comp = supabase.table("courses").select("completition, course_length").eq("id", course_id).single().execute().data
                curr = int(comp.get("completition") or 0)
                course_length = int(comp.get("course_length") or 1)
                
                # Update completion value
                new_completion = curr + 1
                supabase.table("courses").update({"completition": new_completion}).eq("id", course_id).execute()
                
                # Check if course is completed
                if new_completion >= course_length:
                    supabase.table("courses").update({"completed": True}).eq("id", course_id).execute()
                
            except Exception as e:
                st.error(f"Could not update completion status: {e}")
            st.success("Passed! Moving on.")
            st.session_state.show_test = False
            st.rerun()
        else:
            st.error(f"{wrong} mistakes—max is 1.")

# main layout
subject = content.get("topic", params.get("main_subject", "Untitled Course"))
st.title(f"{subject} — Week {wk}")

# Calculate progress variables before columns
done = sum(st.session_state.get(k, False) for k in checkbox_keys)
total = len(checkbox_keys)

# Track current paragraph index for this week
para_keys = list(course_dict.get(f"Week{wk}", {}).get("paragraphs", {}).keys())
if f"current_para_{wk}" not in st.session_state:
    st.session_state[f"current_para_{wk}"] = 0
current_para_idx = st.session_state[f"current_para_{wk}"]

# Check if course is completed
try:
    course_status = supabase.table("courses").select("completed").eq("id", course_id).single().execute().data
    show_congrats = course_status.get("completed", False)
except Exception as e:
    st.error(f"Could not verify course completion status: {e}")
    show_congrats = False

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
            col1, col2, col3 = st.columns([1,1,1])
            with col1:
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
            with col2:
                if st.button("Certification", use_container_width=True):
                    # Get user's name from Supabase
                    user_id = st.session_state["user"]["id"]
                    response = supabase.table("user_profile").select("profile_name").eq("user_id", user_id).execute()
                    user_name = response.data[0].get("profile_name") if response.data else "Unnamed User"
                    
                    # Generate 9-digit course ID from UUID
                    course_id_9digits = str(abs(hash(course_id)))[:9]
                    
                    # Load the certificate template
                    try:
                        # Create a new image with white background
                        img = Image.new('RGB', (800, 600), color='white')
                        draw = ImageDraw.Draw(img)
                        
                        # Add text to the image
                        # Course name in center
                        font_large = ImageFont.load_default()
                        text_bbox = draw.textbbox((0, 0), subject, font=font_large)
                        text_width = text_bbox[2] - text_bbox[0]
                        text_height = text_bbox[3] - text_bbox[1]
                        x = (img.width - text_width) // 2
                        y = (img.height - text_height) // 2
                        draw.text((x, y), subject, font=font_large, fill="black")
                        
                        # User name in bottom left
                        font_small = ImageFont.load_default()
                        draw.text((50, img.height - 100), user_name, font=font_small, fill="black")
                        
                        # Course ID in bottom right
                        draw.text((img.width - 200, img.height - 100), f"ID: {course_id_9digits}", font=font_small, fill="black")
                        
                        # Save the modified image to a bytes buffer
                        img_byte_arr = io.BytesIO()
                        img.save(img_byte_arr, format='PNG')
                        img_byte_arr = img_byte_arr.getvalue()
                        
                        # Create download button for the certificate
                        st.download_button(
                            label="Click to download Certificate",
                            data=img_byte_arr,
                            file_name=f"{subject.replace(' ', '_')}_certificate.png",
                            mime="image/png",
                            use_container_width=True
                        )
                    except Exception as e:
                        st.error(f"Error generating certificate: {str(e)}")
                        st.stop()
            with col3:
                if st.button("Begin project", use_container_width=True):
                    st.session_state["show_project_dialog"] = True
                    st.session_state["project_loading"] = True
                    st.session_state["project_result"] = None
    else:
        # Only show one paragraph container at a time
        if para_keys:
            pid = para_keys[current_para_idx]
            para = course_dict.get(f"Week{wk}", {}).get("paragraphs", {}).get(pid, {})
            with st.container():
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
                # display resources as buttons in one row
                res = para.get("resources", [])
                if res:
                    cols = st.columns(len(res))
                    for idx, (_, url) in enumerate(res):
                        label = re.sub(r"^https?://(www\\.)?", "", url).split("/")[0]
                        with cols[idx]:
                            if st.button(f"[{label}]({url})", key=f"resource_btn_{wk}_{pid}_{idx}", use_container_width=True):
                                import webbrowser
                                webbrowser.open_new_tab(url)
                
                # Explain button in its own row
                explain_key = f"explain_para_{wk}_{pid}"
                if st.button("Explain", key=explain_key, use_container_width=True):
                    st.session_state["show_explanation_dialog"] = True
                    st.session_state["explanation_loading"] = True
                    st.session_state["explanation_result"] = None
                    st.session_state["explanation_para_text"] = para["text"]
                
                # Navigation buttons (Back and Next)
                back_disabled = current_para_idx <= 0
                next_disabled = current_para_idx >= len(para_keys) - 1
                next_key = f"next_para_{wk}"
                back_key = f"back_para_{wk}"
                btn_cols = st.columns([1, 1])
                with btn_cols[0]:
                    if st.button("Back", key=back_key, disabled=back_disabled, use_container_width=True):
                        st.session_state[f"current_para_{wk}"] -= 1
                        # Update progress in Supabase
                        try:
                            supabase.table("courses").update({"progress": current_para_idx - 1}).eq("id", course_id).execute()
                        except Exception as e:
                            st.error(f"Could not update progress: {e}")
                        st.rerun()
                with btn_cols[1]:
                    if current_para_idx == len(para_keys) - 1:  # Last paragraph of the week
                        if st.button("Take a test", key=f"test_btn_{wk}", use_container_width=True):
                            st.session_state.show_test = True
                            show_test_dialog()
                    else:
                        if st.button("Next", key=next_key, disabled=next_disabled, use_container_width=True):
                            st.session_state[f"current_para_{wk}"] += 1
                            # Update progress in Supabase
                            try:
                                supabase.table("courses").update({"progress": current_para_idx + 1}).eq("id", course_id).execute()
                            except Exception as e:
                                st.error(f"Could not update progress: {e}")
                            st.rerun()

if not show_congrats:
    with col_right:
        render_floating_container(
            done=done,
            total=total,
            wk=wk,
            show_test=st.session_state.show_test,
            show_test_dialog=show_test_dialog,
            notes=st.session_state.notes,
            notes_input_key="notes_input",
            supabase=supabase,
            course_id=course_id,
            st_session_state=st.session_state,
            duration=duration,
            max_week=max_week,
            update_course_final_completion=update_course_final_completion,
            course_dict=course_dict,
            subject=subject
        )

# Add the explanation dialog at the end of the file
if st.session_state.get("show_explanation_dialog", False):
    @st.dialog("Paragraph Explanation", width="large")
    def show_explanation_dialog():
        import time
        from streamlit import session_state as ss
        import re
        import json
        para_text = ss.get("explanation_para_text", "")
        # Identify the current paragraph uniquely
        course_id = st.session_state.get("current_course_id")
        wk = st.session_state.current_week
        para_keys = list(course_dict.get(f"Week{wk}", {}).get("paragraphs", {}).keys())
        current_para_idx = st.session_state.get(f"current_para_{wk}", 0)
        if para_keys and 0 <= current_para_idx < len(para_keys):
            paragraph_id = para_keys[current_para_idx]
        else:
            paragraph_id = "unknown"
        # --- Caching logic ---
        if ss.get("explanation_loading", True):
            with st.spinner("Checking for cached explanation..."):
                # 1. Check Supabase for cached explanation
                try:
                    resp = supabase.table("paragraph_explanations").select("explanation_json").eq("course_id", course_id).eq("week_number", wk).eq("paragraph_id", paragraph_id).maybe_single().execute()
                    cached = resp.data["explanation_json"] if resp.data and resp.data.get("explanation_json") else None
                except Exception as e:
                    cached = None
                if cached:
                    try:
                        explanation_json = cached if isinstance(cached, dict) else json.loads(cached)
                        ss["explanation_result"] = explanation_json
                        ss["explanation_loading"] = False
                        st.rerun()
                    except Exception:
                        pass
            # 2. If not cached, call OpenAI and save to Supabase
            with st.spinner("Generating explanation..."):
                try:
                    thread = client.beta.threads.create()
                    msg = client.beta.threads.messages.create(
                        thread_id=thread.id,
                        role="user",
                        content=f"Explain the following paragraph in detail using the provided JSON schema. Paragraph: {para_text}"
                    )
                    run = client.beta.threads.runs.create(
                        thread_id=thread.id,
                        assistant_id="asst_mer5PvwGviUVWm6yDO7zo3TV",
                        instructions="Return the explanation in the following JSON schema: {\n  \"name\": \"learning_explanation\",\n  \"schema\": {\n    \"type\": \"object\",\n    \"properties\": {\n      \"input_text\": {\n        \"type\": \"string\",\n        \"description\": \"The input text paragraph that needs to be explained.\"\n      },\n      \"detailed_explanation\": {\n        \"type\": \"string\",\n        \"description\": \"A comprehensive and well-analyzed explanation of the input text, structured between 500 and 700 words, presented in a storytelling format.\"\n      }\n    },\n    \"required\": [\n      \"input_text\",\n      \"detailed_explanation\"\n    ],\n    \"additionalProperties\": false\n  },\n  \"strict\": true\n}"
                    )
                    # Wait for completion
                    while True:
                        run_status = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
                        if run_status.status in ("completed", "failed", "cancelled", "expired"):
                            break
                        time.sleep(1)
                    if run_status.status == "completed":
                        messages = client.beta.threads.messages.list(thread_id=thread.id)
                        # Get the latest assistant message
                        for m in reversed(messages.data):
                            if m.role == "assistant":
                                content = m.content[0].text.value if m.content else ""
                                try:
                                    match = re.search(r'\{.*\}', content, re.S)
                                    if match:
                                        explanation_json = json.loads(match.group(0))
                                        ss["explanation_result"] = explanation_json
                                        # Save to Supabase
                                        try:
                                            supabase.table("paragraph_explanations").upsert({
                                                "course_id": course_id,
                                                "week_number": wk,
                                                "paragraph_id": paragraph_id,
                                                "explanation_json": explanation_json
                                            }).execute()
                                        except Exception:
                                            pass
                                    else:
                                        ss["explanation_result"] = {"error": "No JSON found in response.", "raw": content}
                                except Exception as e:
                                    ss["explanation_result"] = {"error": str(e), "raw": content}
                                break
                        else:
                            ss["explanation_result"] = {"error": "No assistant message found."}
                    else:
                        ss["explanation_result"] = {"error": f"Run status: {run_status.status}"}
                except Exception as e:
                    ss["explanation_result"] = {"error": str(e)}
                ss["explanation_loading"] = False
                st.rerun()
        else:
            result = ss.get("explanation_result")
            if result is None:
                st.info("No explanation available.")
            else:
                detailed = result.get("detailed_explanation")
                if detailed:
                    formatted = re.sub(r"\n{2,}", "\n\n", detailed)
                    st.markdown(formatted, unsafe_allow_html=True)
                else:
                    st.warning("No detailed explanation found in the response.")
            if st.button("Close", use_container_width=True):
                ss["show_explanation_dialog"] = False
                ss["explanation_loading"] = False
                ss["explanation_result"] = None
                ss["explanation_para_text"] = None
    show_explanation_dialog()

# Add the project dialog at the end of the file
if st.session_state.get("show_project_dialog", False):
    @st.dialog("Project Details", width="large")
    def show_project_dialog():
        import json
        from streamlit import session_state as ss
        
        # Combine all paragraphs into a single text
        course_text = ""
        for week_num in range(1, len(course_dict) + 1):
            week_key = f"Week{week_num}"
            for para in course_dict.get(week_key, {}).get("paragraphs", {}).values():
                course_text += para.get("text", "") + "\n\n"
        
        if ss.get("project_loading", True):
            with st.spinner("Checking for cached project..."):
                # 1. Check Supabase for cached project
                try:
                    response = supabase.table("courses").select("project").eq("id", course_id).single().execute()
                    cached = response.data.get("project") if response.data else None
                    if cached:
                        ss["project_result"] = cached
                        ss["project_loading"] = False
                        st.rerun()
                except Exception as e:
                    cached = None
            
            # 2. If not cached, call OpenAI and save to Supabase
            with st.spinner("Generating project details..."):
                try:
                    thread = client.beta.threads.create()
                    msg = client.beta.threads.messages.create(
                        thread_id=thread.id,
                        role="user",
                        content=f"Based on this course content, generate a portfolio project following the specified JSON schema. Course content: {course_text}"
                    )
                    
                    run = client.beta.threads.runs.create(
                        thread_id=thread.id,
                        assistant_id="asst_VhOwZxM8nnwrbZpADOGzTLa6"
                    )
                    
                    # Wait for completion
                    while True:
                        run_status = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
                        if run_status.status in ("completed", "failed", "cancelled", "expired"):
                            break
                        time.sleep(1)
                    
                    if run_status.status == "completed":
                        messages = client.beta.threads.messages.list(thread_id=thread.id)
                        # Get the latest assistant message
                        for m in reversed(messages.data):
                            if m.role == "assistant":
                                content = m.content[0].text.value if m.content else ""
                                try:
                                    match = re.search(r'\{.*\}', content, re.S)
                                    if match:
                                        project_json = json.loads(match.group(0))
                                        ss["project_result"] = project_json
                                        # Save to Supabase
                                        try:
                                            supabase.table("courses").update({
                                                "project": project_json
                                            }).eq("id", course_id).execute()
                                        except Exception as e:
                                            st.error(f"Could not save project to database: {e}")
                                    else:
                                        ss["project_result"] = {"error": "No JSON found in response.", "raw": content}
                                except Exception as e:
                                    ss["project_result"] = {"error": str(e), "raw": content}
                                break
                        else:
                            ss["project_result"] = {"error": "No assistant message found."}
                    else:
                        ss["project_result"] = {"error": f"Run status: {run_status.status}"}
                except Exception as e:
                    ss["project_result"] = {"error": str(e)}
                ss["project_loading"] = False
                st.rerun()
        else:
            result = ss.get("project_result")
            if result is None:
                st.info("No project details available.")
            else:
                if "error" in result:
                    st.error(f"Error: {result['error']}")
                else:
                    # Format the JSON as markdown
                    st.markdown(f"## {result.get('project_title', 'Project Title')}")
                    st.markdown(f"### Overview\n{result.get('overview', '')}")
                    
                    st.markdown("### Implementation Steps")
                    for step in result.get('implementation_steps', []):
                        st.markdown(f"- {step}")
                    
                    st.markdown("### Required Skills")
                    for skill in result.get('required_skills', []):
                        st.markdown(f"- {skill}")
                    
                    st.markdown("### Tools and Libraries")
                    for tool in result.get('tools_and_libraries', []):
                        st.markdown(f"- {tool}")
                    
                    st.markdown("### Resources")
                    resources = result.get('resources', {})
                    
                    st.markdown("#### Websites")
                    for site in resources.get('websites', []):
                        st.markdown(f"- {site}")
                    
                    st.markdown("#### YouTube Videos")
                    for video in resources.get('youtube_videos', []):
                        st.markdown(f"- {video}")
                    
                    st.markdown("#### Charts")
                    for chart in resources.get('charts', []):
                        st.code(chart, language="python")
                    
                    st.markdown("#### Tables")
                    for table in resources.get('tables', []):
                        st.code(table, language="python")
                    
                    st.markdown("#### Articles")
                    for article in resources.get('articles', []):
                        st.markdown(f"- {article}")
                    
                    st.markdown("### Optional Enhancements")
                    for enhancement in result.get('optional_enhancements', []):
                        st.markdown(f"- {enhancement}")
            
            if st.button("Close", use_container_width=True):
                ss["show_project_dialog"] = False
                ss["project_loading"] = False
                ss["project_result"] = None
    show_project_dialog()
