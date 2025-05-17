import streamlit as st
from dateutil.parser import isoparse
from supabase import create_client, Client
from login_popup import display_login_popup

# ───────────────────  UI  ───────────────────
st.markdown(
    """
    <!--  Google Material Icons font  -->
    <link href="https://fonts.googleapis.com/icon?family=Material+Icons"
          rel="stylesheet">
    <style>
        #MainMenu, footer {visibility:hidden;}
        .stButton>button, .stToggle label {font-family:"Material Icons";}
    </style>
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
def open_image_dialog(course_id: str, title: str):
    @st.dialog(f"Upload image for “{title}”")
    def _dlg():
        upl = st.file_uploader("Choose an image", type=["png", "jpg", "jpeg", "gif"])
        if upl and st.button("cloud_upload"):  # ← Material icon
            supabase.table("courses").update(
                {"course_img": "\\x" + upl.read().hex()}
            ).eq("id", course_id).execute()
            st.success("Image saved. Close dialog when done.")
    _dlg()


def open_notes_dialog(course_id: str, title: str, existing_notes: str):
    @st.dialog(f"Notes for “{title}”")
    def _dlg():
        txt = st.text_area("Course notes:", value=existing_notes, height=400)
        if st.button("save"):  # ← Material icon
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

    with st.container(border=True):
        info, pills_col, pub_col = st.columns([6, 3, 1])

        info.markdown(f"### {title}")
        info.markdown(f"🕒 **Created:** {created}")

        # public toggle
        now_pub = bool(course.get("Public", False))
        new_pub = pub_col.toggle("public", value=now_pub, key=f"pub_{cid}", help="Public?")
        if new_pub != now_pub:
            supabase.table("courses").update({"Public": new_pub}).eq("id", cid).execute()
            st.rerun()

        # pills replacing buttons
        option_map = {
            0: ":material/visibility:",
            1: ":material/delete:",
            2: ":material/image:",
            3: ":material/note:",
        }
        selected_action = pills_col.pills(
            label="",
            options=option_map.keys(),
            format_func=lambda option: option_map[option],
            selection_mode="single",
            key=f"pills_{cid}",
        )

        if selected_action == 0:
            st.session_state["current_course_id"] = cid
            st.switch_page("pages/course_view.py")

        elif selected_action == 1:
            if st.confirm(f"Delete “{title}”?", key=f"cfm_{cid}"):
                supabase.table("courses").delete().eq("id", cid).execute()
                st.rerun()

        elif selected_action == 2:
            open_image_dialog(cid, title)

        elif selected_action == 3:
            open_notes_dialog(cid, title, course.get("course_notes", ""))
