import streamlit as st
from menu import get_pages
import toml
from supabase import create_client, Client
import base64

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

st.set_page_config(page_title="Skillmea", layout="wide", initial_sidebar_state="expanded")
st.logo("logo.png", size="large", link=None, icon_image=None)

# Add profile picture and theme toggle in sidebar
with st.sidebar:
    
    profile_pic = get_user_profile_pic()
    st.image(profile_pic, width=50, use_container_width=False)
    
    # Get user's XP and calculate level
    if "user" in st.session_state:
        try:
            user_id = st.session_state["user"]["id"]
            response = supabase.table("user_profile").select("xp").eq("user_id", user_id).execute()
            if response.data and response.data[0].get("xp") is not None:
                xp = response.data[0]["xp"]
                
                # Calculate level and progress
                level = 1
                xp_needed = 100
                xp_total = 0
                
                while xp >= xp_total + xp_needed:
                    level += 1
                    xp_total += xp_needed
                    xp_needed += 50
                
                # Calculate progress to next level
                current_level_xp = xp - xp_total
                progress_percent = current_level_xp / xp_needed
                
                # Get user's display name
                response = supabase.table("user_profile").select("profile_name").eq("user_id", user_id).execute()
                display_name = response.data[0].get("profile_name") if response.data else "Unnamed User"
                
                st.caption(display_name)
                st.caption(f"Level {level}")
                st.progress(progress_percent)
                st.caption(f"XP: {current_level_xp}/{xp_needed}")
        except Exception:
            st.caption("Unnamed User")
            st.caption("Level 1") 
            st.progress(0)
            st.caption("XP: 0/100")
    else:
        st.caption("Unnamed User")
        st.caption("Level 1")
        st.progress(0)
        st.caption("XP: 0/100")


pages = get_pages()
pg = st.navigation(pages, position="sidebar", expanded=True)
pg.run()
