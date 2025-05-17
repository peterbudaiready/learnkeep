from __future__ import annotations
import streamlit as st
from supabase import create_client, Client
from login_popup import display_login_popup

# Initialize Supabase client
SUPABASE_URL = "https://fcyutudqmkhrywffsjky.supabase.co"
SUPABASE_ANON_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImZjeXV0dWRxbWtocnl3ZmZzamt5Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDI0MjQ3OTAsImV4cCI6MjA1ODAwMDc5MH0."
    "IucZQwgH1CFYFCgb9E3-TV7I-NOnPq9-3lmrWc4ZE7I"
)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# Display login popup
display_login_popup()

# Get current user
user = st.session_state.get("user")
if not user:
    st.warning("Please log in to view your notes.")
    st.stop()

# Get all courses with notes for the current user
try:
    courses = supabase.table("courses").select("id, title, course_notes").eq("user_id", user["id"]).execute().data
except Exception as e:
    st.error(f"Error fetching courses: {e}")
    st.stop()

# Filter out courses without notes
courses_with_notes = [course for course in courses if course.get("course_notes")]

if not courses_with_notes:
    st.info("You don't have any notes yet. Start taking notes in your courses!")
    st.stop()

# Display notes
st.title("My Notes")

for course in courses_with_notes:
    with st.expander(f"📝 {course['title']}"):
        st.text_area("", value=course['course_notes'], height=200, key=f"notes_{course['id']}", disabled=True)