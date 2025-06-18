import streamlit as st
from supabase import create_client, Client
from login_popup import display_login_popup
import base64
from datetime import datetime

# ─── Streamlit bootstrap ─────────────────────────────────────────────────
display_login_popup()  # stores logged‑in user in Session

# ─── Supabase Client ─────────────────────────────────────────────────────
SUPABASE_URL = "https://fcyutudqmkhrywffsjky.supabase.co"
SUPABASE_ANON_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImZjeXV0dWRxbWtocnl3ZmZzamt5Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDI0MjQ3OTAsImV4cCI6MjA1ODAwMDc5MH0."
    "IucZQwgH1CFYFCgb9E3-TV7I-NOnPq9-3lmrWc4ZE7I"
)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# ─── User Info ───────────────────────────────────────────────────────────
user = st.session_state.get("user")
if not user:
    st.warning("Please log in to view your dashboard.")
    st.stop()

user_id = user["id"]
profile = supabase.table("user_profile").select("*").eq("user_id", user_id).maybe_single().execute().data or {}

# Profile picture
pic_data = profile.get("profile_pic")
def get_pic_uri(pic_data):
    if isinstance(pic_data, str) and pic_data.startswith("\\x"):
        try:
            return f"data:image/png;base64,{base64.b64encode(bytes.fromhex(pic_data[2:])).decode()}"
        except Exception:
            return "https://via.placeholder.com/120"
    return "https://via.placeholder.com/120"

profile_pic = get_pic_uri(pic_data)

# XP/Level calculation
xp = profile.get("xp", 0) or 0
level = 1
xp_needed = 100
xp_total = 0
while xp >= xp_total + xp_needed:
    level += 1
    xp_total += xp_needed
    xp_needed += 50
current_level_xp = xp - xp_total
progress_percent = current_level_xp / xp_needed if xp_needed else 0

display_name = profile.get("profile_name") or user.get("email", "Unnamed User")
bio = profile.get("bio", "")

# ─── News Container (Dummy) ──────────────────────────────────────────────
st.markdown("""
<div style='background: linear-gradient(90deg, #08b9ff 0%, #ffc666 100%); border-radius: 12px; padding: 1.5rem 2rem; margin-bottom: 2rem; position: relative; overflow: hidden;'>
    <h2 style='color: #120709; margin: 0 0 0.5rem 0;'>🚀 Platform News</h2>
    <div id='news-slider' style='font-size: 1.1rem; color: #1c0c04; min-height: 32px;'>
        <span id='news-slide'>Welcome to Skillmea! 🎉 | New: Linux course library released! 🐧 | Earn XP for every completed course! ⭐ | Try our new AI tutor chat! 🤖</span>
    </div>
    <a href='#' style='position: absolute; right: 2rem; top: 1.5rem; background: #120709; color: #ffc666; padding: 0.5rem 1rem; border-radius: 6px; text-decoration: none; font-weight: 600;'>Read More</a>
</div>
<script>
let news = [
    'Welcome to Skillmea! 🎉',
    'New: Linux course library released! 🐧',
    'Earn XP for every completed course! ⭐',
    'Try our new AI tutor chat! 🤖',
    'Check out the new Achievements section! 🏆',
    'Invite friends and earn bonus XP! 🎁'
];
let idx = 0;
setInterval(function() {
    idx = (idx + 1) % news.length;
    document.getElementById('news-slide').textContent = news[idx];
}, 3500);
</script>
""", unsafe_allow_html=True)

# ─── Statistics Containers ──────────────────────────────────────────────
col1, col2, col3, col4 = st.columns(4, gap="large")

with col1:
    with st.container(border=True):
        # Get count of completed courses
        completed_count = len(
            supabase.table("courses")
            .select("id")
            .eq("user_id", user_id)
            .eq("completed", True)
            .execute().data or []
        )
        st.markdown(f"""
        <div style='text-align: center;'>
            <h4 style='margin: 0 0 1rem 0;'>Completed Courses</h4>
            <div style='font-size: 2rem; font-weight: bold;'>{completed_count}</div>
        </div>
        """, unsafe_allow_html=True)

with col2:
    with st.container(border=True):
        # Get average duration of completed courses
        completed_courses = (
            supabase.table("courses")
            .select("created_at, completed_at")
            .eq("user_id", user_id)
            .eq("completed", True)
            .execute().data or []
        )
        
        total_duration = 0
        for course in completed_courses:
            if course.get("created_at") and course.get("completed_at"):
                try:
                    created = datetime.fromisoformat(course["created_at"].replace('Z', '+00:00'))
                    completed = datetime.fromisoformat(course["completed_at"].replace('Z', '+00:00'))
                    duration = (completed - created).total_seconds()
                    total_duration += duration
                except Exception:
                    continue
        
        avg_duration = total_duration / len(completed_courses) if completed_courses else 0
        days = int(avg_duration // (24 * 3600))
        hours = int((avg_duration % (24 * 3600)) // 3600)
        
        st.markdown(f"""
        <div style='text-align: center;'>
            <h4 style='margin: 0 0 1rem 0;'>Average Duration</h4>
            <div style='font-size: 2rem; font-weight: bold;'>{days}d {hours}h</div>
        </div>
        """, unsafe_allow_html=True)

with col3:
    with st.container(border=True):
        # Get best duration
        best_duration = float('inf')
        for course in completed_courses:
            if course.get("created_at") and course.get("completed_at"):
                try:
                    created = datetime.fromisoformat(course["created_at"].replace('Z', '+00:00'))
                    completed = datetime.fromisoformat(course["completed_at"].replace('Z', '+00:00'))
                    duration = (completed - created).total_seconds()
                    best_duration = min(best_duration, duration)
                except Exception:
                    continue
        
        if best_duration != float('inf'):
            days = int(best_duration // (24 * 3600))
            hours = int((best_duration % (24 * 3600)) // 3600)
            duration_text = f"{days}d {hours}h"
        else:
            duration_text = "N/A"
        
        st.markdown(f"""
        <div style='text-align: center;'>
            <h4 style='margin: 0 0 1rem 0;'>Best Duration</h4>
            <div style='font-size: 2rem; font-weight: bold;'>{duration_text}</div>
        </div>
        """, unsafe_allow_html=True)

with col4:
    with st.container(border=True):
        st.markdown("""
        <div style='text-align: center;'>
            <h4 style='margin: 0 0 1rem 0;'>Coming Soon</h4>
            <div style='font-size: 1.2rem; color: #666;'>New features on the way!</div>
        </div>
        """, unsafe_allow_html=True)

# ─── Dashboard Layout ────────────────────────────────────────────────────
user_col, stats_col = st.columns([2, 3], gap="large")

with user_col:
    with st.container(border=True):
        st.markdown(f"""
        <div class='card' style='min-height: 320px; display: flex; flex-direction: column; align-items: center; justify-content: center;'>
            <img src='{profile_pic}' alt='Profile' style='width: 120px; height: 120px; border-radius: 50%; object-fit: cover; margin-bottom: 1rem; border: 3px solid #222;'>
            <h3 style='margin: 0;'>{display_name}</h3>
            <div style='margin-bottom: 0.5rem;'>Level {level}</div>
            <div style='width: 80%; margin-bottom: 0.5rem;'>
        """, unsafe_allow_html=True)
        st.progress(progress_percent if progress_percent <= 1 else 1.0)
        st.markdown(f"""
            <div style='font-size: 0.9rem; text-align: right;'>{current_level_xp}/{xp_needed} XP</div>
            </div>
            <div style='font-size: 0.95rem; text-align: center;'>{bio}</div>
        </div>
        """, unsafe_allow_html=True)

with stats_col:
    with st.container(border=True):
        st.markdown("<h4>🏆 Achievements</h4>", unsafe_allow_html=True)
        completed_courses = (
            supabase.table("courses")
            .select("id, title, completed, created_at, course_img")
            .eq("user_id", user_id)
            .eq("completed", True)
            .order("created_at", desc=True)
            .limit(3)
            .execute().data or []
        )
        if completed_courses:
            for course in completed_courses:
                st.markdown(f"""
                <div>
                    <b>{course.get('title','Untitled')}</b><br>
                    <span style='font-size:0.9rem;'>Completed {datetime.fromisoformat(course['created_at']).strftime('%b %d, %Y')}</span>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No completed courses yet. Finish a course to earn achievements!")

    with st.container(border=True):
        st.markdown("<h4 style='margin-top:2rem;margin-bottom:0.5rem;'>📚 In Progress</h4>", unsafe_allow_html=True)
        in_progress = (
            supabase.table("courses")
            .select("id, title, progress, created_at, course_img, completed")
            .eq("user_id", user_id)
            .eq("completed", False)
            .order("created_at", desc=True)
            .limit(3)
            .execute().data or []
        )
        if in_progress:
            for course in in_progress:
                with st.container():
                    img_html = ""
                    if course.get("course_img"):
                        try:
                            img_bytes = bytes.fromhex(course["course_img"][2:]) if course["course_img"].startswith("\\x") else bytes.fromhex(course["course_img"])
                            img_b64 = base64.b64encode(img_bytes).decode()
                            img_html = f"<img src='data:image/png;base64,{img_b64}' style='width:40px;height:40px;border-radius:8px;margin-right:1rem;object-fit:cover;border:2px solid #08b9ff;'>"
                        except Exception:
                            pass
                    progress = course.get("progress", 0) or 0
                    try:
                        start_date = datetime.fromisoformat(course["created_at"].replace('Z', '+00:00')).strftime('%b %d, %Y')
                    except Exception:
                        start_date = "Unknown date"
                    
                    col1, col2 = st.columns([1, 4])
                    with col1:
                        st.markdown(img_html, unsafe_allow_html=True)
                    with col2:
                        st.markdown(f"""
                        <div>
                            <b>{course.get('title','Untitled')}</b><br>
                            <span style='font-size:0.9rem;'>Started {start_date}</span>
                        </div>
                        """, unsafe_allow_html=True)
                    st.progress(progress/100 if progress <= 100 else 1.0)
        else:
            st.info("No active courses. Start a new course to see it here!")
