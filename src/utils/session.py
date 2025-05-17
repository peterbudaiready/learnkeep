from typing import Optional, Dict, Any
import streamlit as st
from ..api.supabase_client import supabase

class SessionManager:
    def __init__(self):
        self._initialize_session_state()

    def _initialize_session_state(self):
        """Initialize session state variables"""
        if "user" not in st.session_state:
            st.session_state.user = None
        if "auth_token" not in st.session_state:
            st.session_state.auth_token = None
        if "remember_me" not in st.session_state:
            st.session_state.remember_me = False

    def get_current_user(self) -> Optional[Dict[str, Any]]:
        """Get the current user from session state or try to restore session"""
        if st.session_state.user:
            return st.session_state.user

        # Try to restore session from token
        if st.session_state.auth_token:
            try:
                supabase.client.auth.set_session(
                    st.session_state.auth_token,
                    st.session_state.refresh_token
                )
                user = supabase.client.auth.get_user()
                if user:
                    st.session_state.user = user.user
                    return user.user
            except Exception:
                self.clear_session()
        
        return None

    def set_user(self, user: Dict[str, Any], remember: bool = False):
        """Set the current user and optionally remember the session"""
        st.session_state.user = user
        st.session_state.remember_me = remember
        
        if remember:
            session = supabase.client.auth.get_session()
            if session:
                st.session_state.auth_token = session.access_token
                st.session_state.refresh_token = session.refresh_token

    def clear_session(self):
        """Clear the current session"""
        st.session_state.user = None
        st.session_state.auth_token = None
        st.session_state.refresh_token = None
        st.session_state.remember_me = False
        
        try:
            supabase.client.auth.sign_out()
        except Exception:
            pass

    def refresh_session(self) -> bool:
        """Refresh the current session if needed"""
        if not st.session_state.auth_token:
            return False

        try:
            session = supabase.client.auth.refresh_session()
            if session:
                st.session_state.auth_token = session.access_token
                st.session_state.refresh_token = session.refresh_token
                return True
        except Exception:
            self.clear_session()
        
        return False

    def require_auth(self):
        """Require authentication to proceed"""
        user = self.get_current_user()
        if not user:
            st.warning("Please log in to continue")
            st.stop()
        return user

# Initialize global session manager
session = SessionManager() 