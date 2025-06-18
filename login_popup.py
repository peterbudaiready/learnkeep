import streamlit as st
from supabase import create_client, Client

# Supabase credentials (ensure these match your other pages)
SUPABASE_URL = "https://fcyutudqmkhrywffsjky.supabase.co"
SUPABASE_ANON_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImZjeXV0dWRxbWtocnl3ZmZzamt5Iiwicm9sZSI6ImFub24iLC"
    "JpYXQiOjE3NDI0MjQ3OTAsImV4cCI6MjA1ODAwMDc5MH0."
    "IucZQwgH1CFYFCgb9E3-TV7I-NOnPq9-3lmrWc4ZE7I"
)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

def display_login_popup():
    # Use session state for user authentication
    user = st.session_state.get("user")
    if not user:
        @st.dialog("Login / Sign Up")
        def show_login_dialog():
            st.header("This app is private.")
            st.subheader("Please log in.")
            # Normal login form
            with st.form("login_form"):
                email = st.text_input("Email")
                password = st.text_input("Password", type="password")
                login_submitted = st.form_submit_button("Log in with Email")
            if login_submitted:
                try:
                    auth_resp = supabase.auth.sign_in_with_password({"email": email, "password": password})
                    user = auth_resp.user
                    if user:
                        st.session_state["user"] = {"id": user.id, "email": user.email, "name": user.user_metadata.get("name", "")}
                        st.rerun()
                    else:
                        st.error("Invalid email or password.")
                except Exception as e:
                    st.error(f"Login failed: {e}")
            st.divider()
            st.button("Log in with Google", on_click=st.login)
        show_login_dialog()
        st.stop()
    # Do not show anything if user is logged in
