from typing import Dict, Any, Optional
import time
import streamlit as st
from ..api.supabase_client import supabase

class Analytics:
    def __init__(self):
        self.enabled = st.secrets["analytics"]["enabled"]
        self._initialize_session()

    def _initialize_session(self):
        """Initialize analytics session state"""
        if "analytics_session_id" not in st.session_state:
            st.session_state.analytics_session_id = str(int(time.time()))
        if "page_view_time" not in st.session_state:
            st.session_state.page_view_time = time.time()

    def _track_event(self, event_type: str, properties: Optional[Dict[str, Any]] = None):
        """Track an analytics event"""
        if not self.enabled:
            return

        try:
            event_data = {
                "session_id": st.session_state.analytics_session_id,
                "user_id": st.session_state.user["id"] if "user" in st.session_state else None,
                "event_type": event_type,
                "timestamp": time.time(),
                "properties": properties or {}
            }
            
            supabase.client.table("analytics_events").insert(event_data).execute()
        except Exception as e:
            st.error(f"Failed to track event: {e}")

    def track_page_view(self, page_name: str):
        """Track page view event"""
        self._track_event("page_view", {"page_name": page_name})

    def track_course_start(self, course_id: str):
        """Track course start event"""
        self._track_event("course_start", {"course_id": course_id})

    def track_course_complete(self, course_id: str):
        """Track course completion event"""
        self._track_event("course_complete", {"course_id": course_id})

    def track_resource_view(self, resource_id: str, resource_type: str):
        """Track resource view event"""
        self._track_event("resource_view", {
            "resource_id": resource_id,
            "resource_type": resource_type
        })

    def track_quiz_attempt(self, quiz_id: str, score: float):
        """Track quiz attempt event"""
        self._track_event("quiz_attempt", {
            "quiz_id": quiz_id,
            "score": score
        })

    def track_search(self, query: str, results_count: int):
        """Track search event"""
        self._track_event("search", {
            "query": query,
            "results_count": results_count
        })

    def track_error(self, error_type: str, error_message: str):
        """Track error event"""
        self._track_event("error", {
            "error_type": error_type,
            "error_message": error_message
        })

# Initialize global analytics instance
analytics = Analytics() 