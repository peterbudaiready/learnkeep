import streamlit as st
from menu import get_pages
import toml
from supabase import create_client, Client
import base64

st.set_page_config(layout="wide")

# Initialize Supabase client
SUPABASE_URL = "https://fcyutudqmkhrywffsjky.supabase.co"
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImZjeXV0dWRxbWtocnl3ZmZzamt5Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDI0MjQ3OTAsImV4cCI6MjA1ODAwMDc5MH0.IucZQwgH1CFYFCgb9E3-TV7I-NOnPq9-3lmrWc4ZE7I"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# Load current theme from config
def get_current_theme():
    config = toml.load(".streamlit/config.toml")
    return config["theme"]["base"]

# Toggle theme function
def toggle_theme():
    config = toml.load(".streamlit/config.toml")
    current_theme = config["theme"]["base"]
    new_theme = "rpg" if current_theme == "light" else "light"
    config["theme"]["base"] = new_theme
    with open(".streamlit/config.toml", "w") as f:
        toml.dump(config, f)
    st.rerun()

# Get user profile picture
def get_user_profile_pic():
    if "user" not in st.session_state:
        return "https://via.placeholder.com/40"
    
    try:
        user_id = st.session_state["user"]["id"]
        response = supabase.table("user_profile").select("profile_pic").eq("user_id", user_id).execute()
        if response.data and response.data[0].get("profile_pic"):
            pic_data = response.data[0]["profile_pic"]
            if isinstance(pic_data, str) and pic_data.startswith("\\x"):
                return f"data:image/png;base64,{base64.b64encode(bytes.fromhex(pic_data[2:])).decode()}"
    except Exception:
        pass
    return "https://via.placeholder.com/40"

st.logo("logo.png", size="large", link=None, icon_image=None)

# Add profile picture and theme toggle in sidebar
with st.sidebar:
    if "user" in st.session_state:
        col1, col2 = st.columns([1,3])
        
        with col1:
            profile_pic = get_user_profile_pic()
            st.image(profile_pic, width=50, use_container_width=False, )
        
        with col2:
            try:
                user_id = st.session_state["user"]["id"]
                response = supabase.table("user_profile").select("xp").eq("user_id", user_id).execute()
                if response.data and response.data[0].get("xp") is not None:
                    xp = response.data[0]["xp"]
                    level = 1
                    xp_needed = 100
                    xp_total = 0
                    while xp >= xp_total + xp_needed:
                        level += 1
                        xp_total += xp_needed
                        xp_needed += 50
                    current_level_xp = xp - xp_total
                    progress_percent = current_level_xp / xp_needed
                    response = supabase.table("user_profile").select("profile_name").eq("user_id", user_id).execute()
                    display_name = response.data[0].get("profile_name") if response.data else "Unnamed User"
                    st.markdown(f"<div style='line-height:1'><b>{display_name}</b><br>Level {level}</div>", unsafe_allow_html=True)
                    st.progress(progress_percent, "")
                    st.markdown(f"<div style='line-height:0.5;font-size:0.8em'>XP: {current_level_xp}/{xp_needed}</div>", unsafe_allow_html=True)
            except Exception:
                st.markdown("<div style='line-height:1'><b>Unnamed User</b><br>Level 1</div>", unsafe_allow_html=True)
                st.progress(0, "")
                st.markdown("<div style='line-height:1;font-size:0.8em'>XP: 0/100</div>", unsafe_allow_html=True)

pages = get_pages()
pg = st.navigation(pages, position="sidebar", expanded=True)
pg.run()
