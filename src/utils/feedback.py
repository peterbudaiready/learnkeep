from typing import Dict, Any, List, Optional
import streamlit as st
from datetime import datetime
from ..api.supabase_client import supabase

class FeedbackManager:
    def __init__(self):
        self._initialize_session_state()

    def _initialize_session_state(self):
        """Initialize feedback-related session state"""
        if "feedback_submitted" not in st.session_state:
            st.session_state.feedback_submitted = set()

    def submit_rating(self, course_id: str, rating: int, review: Optional[str] = None) -> bool:
        """Submit a rating and optional review for a course"""
        if not st.session_state.get("user"):
            st.warning("Please log in to submit feedback")
            return False

        try:
            user_id = st.session_state["user"]["id"]
            
            # Check if user has already rated this course
            existing = (
                supabase.client.table("course_ratings")
                .select("*")
                .eq("user_id", user_id)
                .eq("course_id", course_id)
                .execute()
                .data
            )
            
            feedback_data = {
                "user_id": user_id,
                "course_id": course_id,
                "rating": rating,
                "review": review,
                "updated_at": datetime.utcnow().isoformat()
            }
            
            if existing:
                # Update existing rating
                supabase.client.table("course_ratings").update(feedback_data).eq("id", existing[0]["id"]).execute()
            else:
                # Insert new rating
                supabase.client.table("course_ratings").insert(feedback_data).execute()
            
            # Update average rating in courses table
            self._update_course_rating(course_id)
            
            # Mark as submitted in session state
            st.session_state.feedback_submitted.add(course_id)
            return True
            
        except Exception as e:
            st.error(f"Failed to submit feedback: {e}")
            return False

    def get_course_feedback(self, course_id: str) -> Dict[str, Any]:
        """Get feedback statistics and reviews for a course"""
        try:
            # Get all ratings for the course
            ratings = (
                supabase.client.table("course_ratings")
                .select("rating, review, user_id, created_at")
                .eq("course_id", course_id)
                .execute()
                .data
            )
            
            if not ratings:
                return {
                    "average_rating": 0,
                    "total_ratings": 0,
                    "rating_distribution": {i: 0 for i in range(1, 6)},
                    "reviews": []
                }
            
            # Calculate statistics
            total = len(ratings)
            avg = sum(r["rating"] for r in ratings) / total
            distribution = {i: sum(1 for r in ratings if r["rating"] == i) for i in range(1, 6)}
            
            # Get user details for reviews
            reviews = []
            for rating in ratings:
                if rating.get("review"):
                    user = (
                        supabase.client.table("user_profile")
                        .select("profile_name")
                        .eq("user_id", rating["user_id"])
                        .single()
                        .execute()
                        .data
                    )
                    reviews.append({
                        "rating": rating["rating"],
                        "review": rating["review"],
                        "user": user.get("profile_name", "Anonymous"),
                        "date": rating["created_at"]
                    })
            
            return {
                "average_rating": round(avg, 1),
                "total_ratings": total,
                "rating_distribution": distribution,
                "reviews": sorted(reviews, key=lambda x: x["date"], reverse=True)
            }
            
        except Exception as e:
            st.error(f"Failed to get course feedback: {e}")
            return {
                "average_rating": 0,
                "total_ratings": 0,
                "rating_distribution": {i: 0 for i in range(1, 6)},
                "reviews": []
            }

    def _update_course_rating(self, course_id: str):
        """Update the average rating in the courses table"""
        try:
            # Get all ratings for the course
            ratings = (
                supabase.client.table("course_ratings")
                .select("rating")
                .eq("course_id", course_id)
                .execute()
                .data
            )
            
            if ratings:
                avg_rating = sum(r["rating"] for r in ratings) / len(ratings)
                # Update course table
                supabase.client.table("courses").update({
                    "rating": round(avg_rating, 1),
                    "rating_count": len(ratings)
                }).eq("id", course_id).execute()
                
        except Exception as e:
            st.error(f"Failed to update course rating: {e}")

    def can_submit_feedback(self, course_id: str) -> bool:
        """Check if the current user can submit feedback for a course"""
        return (
            st.session_state.get("user") is not None and
            course_id not in st.session_state.feedback_submitted
        )

    def render_rating_widget(self, course_id: str):
        """Render a rating widget for a course"""
        if not self.can_submit_feedback(course_id):
            return
        
        st.write("Rate this course:")
        rating = st.slider("Rating", 1, 5, 5, key=f"rating_{course_id}")
        review = st.text_area("Review (optional)", key=f"review_{course_id}")
        
        if st.button("Submit Feedback", key=f"submit_{course_id}"):
            if self.submit_rating(course_id, rating, review):
                st.success("Thank you for your feedback!")
                st.rerun()

# Initialize global feedback manager
feedback = FeedbackManager() 