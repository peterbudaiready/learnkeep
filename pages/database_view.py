import streamlit as st
from dateutil.parser import isoparse
from supabase import create_client, Client
from login_popup import display_login_popup
import pathlib

st.markdown(
    """
    <!--  Google Material Icons font  -->
    <link href="https://fonts.googleapis.com/icon?family=Material+Icons"
          rel="stylesheet">
    """,
    unsafe_allow_html=True,
)

display_login_popup()
st.title("📚 My Courses")

# ───────────────────  Supabase Client  ───────────────────
SUPABASE_URL = "https://fcyutudqmkhrywffsjky.supabase.co"
SUPABASE_ANON_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImZjeXV0dWRxbWtocnl3ZmZzamt5Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDI0MjQ3OTAsImV4cCI6MjA1ODAwMDc5MH0."
    "IucZQwgH1CFYFCgb9E3-TV7I-NOnPq9-3lmrWc4ZE7I"
)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# ───────────────────  User Validation  ───────────────────
user_id = st.session_state.get("user", {}).get("id")
if not user_id:
    st.warning("User not logged in.")
    st.stop()

# ───────────────────  Fetch User Courses  ───────────────────
courses = (
    supabase.table("courses")
    .select("*")
    .order("created_at", desc=True)
    .execute()
    .data
    or []
)
courses = [c for c in courses if c.get("user_id") == user_id]

st.subheader("Your Courses")
if not courses:
    st.info("You haven't generated any courses yet.")
    st.stop()

# ───────────────────  Helper dialogs  ───────────────────
def open_dialog(course_id: str, title: str, action: str, existing_notes: str = ""):
    @st.dialog(f'{action} for "{title}"')
    def _dlg():
        if action == "Notes":
            txt = st.text_area("Course notes:", value=existing_notes, height=400, key=f"notes-area-{course_id}")
            if st.button("save", key=f"btn-black-save-notes-{course_id}"):  # ← Material icon
                supabase.table("courses").update(
                    {"course_notes": txt}
                ).eq("id", course_id).execute()
                st.success("Notes saved. Close dialog when done.")
    _dlg()

# ───────────────────  Render each course  ───────────────────
for course in courses:
    cid   = course["id"]
    title = course.get("title", "Untitled Course")
    try:
        created = isoparse(course.get("created_at")).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        created = "Unknown Date"

    with st.container(border=True, key=f"container-{cid}"):
        info, pills_col, pub_col = st.columns([6, 3, 1])

        info.markdown(f"### {title}", unsafe_allow_html=True)
        info.markdown(f"🕒 **Created:** {created}", unsafe_allow_html=True)

        # public toggle
        now_pub = bool(course.get("Public", False))
        new_pub = pub_col.toggle("public", value=now_pub, key=f"pub-toggle-{cid}", help="Public?")
        if new_pub != now_pub:
            supabase.table("courses").update({"Public": new_pub}).eq("id", cid).execute()
            st.rerun()

        # pills replacing buttons
        option_map = {
            0: ":material/visibility:",
            1: ":material/note:",
        }
        selected_action = pills_col.pills(
            label="",
            options=option_map.keys(),
            format_func=lambda option: option_map[option],
            selection_mode="single",
            key=f"pills-{cid}",
        )

        if selected_action == 0:
            st.session_state["current_course_id"] = cid
            st.switch_page("pages/course_view.py")

        elif selected_action == 1:
            open_dialog(cid, title, "Notes", course.get("course_notes", ""))
