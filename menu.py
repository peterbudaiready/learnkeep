import streamlit as st

def get_pages():
    return {
        "Main": [
            st.Page("pages/main_ui.py", title="New Course", icon=":material/add_circle:"),
            st.Page("pages/dashboard.py", title="Dashboard", icon=":material/dashboard:"),
        ],
        "Skilling": [
            st.Page("pages/database_view.py", title="My Courses", icon=":material/school:"),
            st.Page("pages/libraries.py", title="Libraries", icon=":material/folder:"),
            st.Page("pages/notes.py", title="My Notes", icon=":material/note:"),
        ],
        "Settings": [
            st.Page("pages/profile.py", title="Profile", icon=":material/settings:"),
        ],
        "Resources": [
            st.Page("pages/docu.py", title="Documentation", icon=":material/book:"),
            st.Page("pages/sup.py", title="Support Line", icon=":material/support_agent:"),
            st.Page("pages/forum.py", title="Forum", icon=":material/forum:"),
        ],
        "Actions": [
            st.Page("pages/course_view.py", title="Course View", icon=":material/play_circle:"),
        ],
    }
