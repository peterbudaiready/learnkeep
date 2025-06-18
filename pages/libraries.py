import streamlit as st
from supabase import create_client, Client
from postgrest.exceptions import APIError
import base64
from login_popup import display_login_popup
import pathlib
from src.utils.xp_manager import xp_manager

# ─── Streamlit bootstrap ─────────────────────────────────────────────────
display_login_popup()                      # stores logged‑in user in Session


# ───────────────────  Supabase  ───────────────────
SUPABASE_URL = "https://fcyutudqmkhrywffsjky.supabase.co"
SUPABASE_ANON_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImZjeXV0dWRxbWtocnl3ZmZzamt5Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDI0MjQ3OTAsImV4cCI6MjA1ODAwMDc5MH0."
    "IucZQwgH1CFYFCgb9E3-TV7I-NOnPq9-3lmrWc4ZE7I"
)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# ───────────────────  Config  ───────────────────
PAGE_SIZE = 8  # fetch 8 public courses per request

if "offset" not in st.session_state:
    st.session_state.offset = 0
if "courses" not in st.session_state:
    st.session_state.courses: list[dict] = []

# ───────────────────  Data Access  ───────────────────

def fetch_next_batch(page_size: int = PAGE_SIZE) -> None:
    start, end = st.session_state.offset, st.session_state.offset + page_size - 1

    def _query(public_col: str):
        return (
            supabase.table("courses")
            .select(f"id, title, rating, {public_col}, course_img")
            .eq(public_col, True)
            .range(start, end)
            .execute()
        )

    try:
        response = _query("public")
    except APIError as e:
        if "column courses.public does not exist" in str(e):
            response = _query('"Public"')
        else:
            raise

    if response.data:
        st.session_state.courses.extend(response.data)
        st.session_state.offset += page_size

# ───────────────────  Bootstrap  ───────────────────
if st.session_state.offset == 0:
    fetch_next_batch()

st.title("🌐 Public Courses")

# ───────────────────  UI  ───────────────────
cols = st.columns(4, gap="large", vertical_alignment="top")
for idx, course in enumerate(st.session_state.courses):
    with cols[idx % 4]:
        with st.container(border=True):
            st.markdown(f"<h4 style='margin:0'>{course.get('title', 'Untitled')}</h4>", unsafe_allow_html=True)

            st.feedback("stars", key=f"rating-{course['id']}")

            if st.button("Save", key=f"btn-black-save-{course['id']}"):
                try:
                    # Get the original course data
                    original_course = supabase.table("courses").select("*").eq("id", course["id"]).single().execute().data
                    
                    # Create a new course entry with specific fields
                    new_course_data = {
                        # Course parameters
                        "title": original_course["title"],
                        "course_topic": original_course["course_topic"],
                        "course_length": original_course["course_length"],
                        "skill_level": original_course["skill_level"],
                        "resource_type": original_course["resource_type"],
                        "emphasis": original_course["emphasis"],
                        "knowledge": original_course["knowledge"],
                        "learning_curve": original_course["learning_curve"],
                        
                        # Content and creator info
                        "content": original_course["content"],
                        "creators_id": original_course["creators_id"],
                        "project": original_course.get("project"),
                        
                        # New user and reset fields
                        "user_id": st.session_state["user"]["id"],
                        "progress": 0,
                        "checked": False,
                        "completed": False,
                        "completition": 0,
                        "course_notes": ""
                    }
                    
                    # Insert the new course
                    response = supabase.table("courses").insert(new_course_data).execute()
                    
                    # Add XP reward to the course creator
                    creator_id = original_course["creators_id"]
                    xp_manager.reward_course_saved(creator_id)
                    
                    st.success("Course saved!")
                except Exception as e:
                    st.error(f"Failed to save course: {e}")

# ───────────────────  Lazy Loading  ───────────────────
if st.button("Load more…", key="btn-black-load-more", use_container_width=True):
    fetch_next_batch()
    st.rerun()
