import streamlit as st
from supabase import create_client, Client
from postgrest.exceptions import APIError
import base64
from login_popup import display_login_popup

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
for idx, course in enumerate(st.session_state.courses):
    if idx % 4 == 0:
        cols = st.columns(4, gap="large")

    with cols[idx % 4]:
        img_base64 = ""
        raw_hex = course.get("course_img")
        if raw_hex:
            try:
                clean_hex = raw_hex[2:] if raw_hex.startswith("\\x") else raw_hex
                img_bytes = bytes.fromhex(clean_hex)
                img_base64 = base64.b64encode(img_bytes).decode("utf-8")
            except Exception as e:
                st.error(f"Image decode error: {e}")

        container_style = f"""
            position: relative;
            width: 100%;
            height: 300px;
            background-image: url('data:image/png;base64,{img_base64}');
            background-size: cover;
            background-repeat: no-repeat;
            background-position: center;
            border-radius: 8px;
            overflow: hidden;
            margin-bottom: 10px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        """ if img_base64 else ""

        overlay_style = f"""
            background-color: rgba(255, 255, 255, 0.5);
            width: 100%;
            height: 100%;
            padding: 16px;
            box-sizing: border-box;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        """ if img_base64 else ""

        with st.container(border=True):
            if img_base64:
                st.markdown(
                    f"""
                    <div style="{container_style}">
                        <div style="{overlay_style}">
                            <h4 style='margin:0'>{course.get('title', 'Untitled')}</h4>
                            <div style='margin-top:auto;'>
                                <!-- Space reserved for footer or controls -->
                            </div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(f"<h4 style='margin:0'>{course.get('title', 'Untitled')}</h4>", unsafe_allow_html=True)

            st.feedback("stars", key=f"rating-{course['id']}")

            col1, col2 = st.columns([1, 1], gap="small")
            with col1:
                if st.button("Open", key=f"open-{course['id']}"):
                    st.session_state.current_course_id = course['id']
                    st.switch_page("pages/course_view.py")
            with col2:
                st.button("Save", key=f"save-{course['id']}")

# ───────────────────  Lazy Loading  ───────────────────
if st.button("Load more…", use_container_width=True):
    fetch_next_batch()
    st.rerun()
