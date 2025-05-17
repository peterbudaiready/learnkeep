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
    if "user" not in st.session_state or st.session_state["user"] is None:
        @st.dialog("Login / Sign Up")
        def show_login_dialog():
            with st.form("login_form"):
                action = st.radio("Select Action", ["Login", "Sign Up"])
                if action == "Sign Up":
                    login_input = st.text_input("Login")
                    email = st.text_input("Email")
                    password = st.text_input("Password", type="password")
                    repeat_password = st.text_input("Repeat Password", type="password")
                else:
                    email = st.text_input("Email/Login")
                    password = st.text_input("Password", type="password")
                submitted = st.form_submit_button("Submit")
                if submitted:
                    if action == "Sign Up":
                        if password != repeat_password:
                            st.error("Passwords do not match.")
                            return
                        response = supabase.auth.sign_up({
                            "email": email,
                            "password": password,
                            "data": {"login": login_input}
                        })
                        response_dict = response.dict()
                        if response_dict.get("error") is not None:
                            st.error(response_dict["error"]["message"])
                        else:
                            st.success("Sign up successful! Please check your email for a confirmation link.")
                            st.session_state["user"] = response_dict.get("user")
                            st.experimental_set_query_params(page="app")
                            st.rerun(scope="app")
                    else:
                        response = supabase.auth.sign_in_with_password({"email": email, "password": password})
                        response_dict = response.dict()
                        if response_dict.get("error") is not None:
                            st.error(response_dict["error"]["message"])
                        else:
                            st.success("Login successful!")
                            st.session_state["user"] = response_dict.get("user")
                            st.experimental_set_query_params(page="app")
                            st.rerun(scope="app")
        show_login_dialog()
        st.stop()
