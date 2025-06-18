from typing import Optional
import streamlit as st
from supabase import create_client, Client

# Initialize Supabase client
SUPABASE_URL = "https://fcyutudqmkhrywffsjky.supabase.co"
SUPABASE_ANON_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImZjeXV0dWRxbWtocnl3ZmZzamt5Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDI0MjQ3OTAsImV4cCI6MjA1ODAwMDc5MH0."
    "IucZQwgH1CFYFCgb9E3-TV7I-NOnPq9-3lmrWc4ZE7I"
)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

class XPManager:
    def __init__(self):
        self.xp_rewards = {
            "course_generation": 10,
            "course_completion": 25,
            "course_saved": 45
        }

    def add_xp(self, user_id: str, amount: int) -> bool:
        """Add XP to a user's profile"""
        try:
            # Get current XP
            response = supabase.table("user_profile").select("xp").eq("user_id", user_id).single().execute()
            current_xp = response.data.get("xp", 0) if response.data else 0
            
            # Add new XP
            new_xp = current_xp + amount
            
            # Update user profile
            supabase.table("user_profile").update({"xp": new_xp}).eq("user_id", user_id).execute()
            return True
        except Exception as e:
            st.error(f"Failed to add XP: {e}")
            return False

    def reward_course_generation(self, user_id: str) -> bool:
        """Reward user for generating a new course"""
        return self.add_xp(user_id, self.xp_rewards["course_generation"])

    def reward_course_completion(self, user_id: str) -> bool:
        """Reward user for completing a course"""
        return self.add_xp(user_id, self.xp_rewards["course_completion"])

    def reward_course_saved(self, creator_id: str) -> bool:
        """Reward course creator when their course is saved by another user"""
        return self.add_xp(creator_id, self.xp_rewards["course_saved"])

    def get_user_level(self, xp: int) -> int:
        """Calculate user level based on XP"""
        level = 1
        xp_needed = 100
        xp_total = 0
        
        while xp >= xp_total + xp_needed:
            level += 1
            xp_total += xp_needed
            xp_needed += 50
            
        return level

    def get_level_progress(self, xp: int) -> tuple[float, int, int]:
        """Calculate level progress, current XP, and XP needed for next level"""
        level = 1
        xp_needed = 100
        xp_total = 0
        
        while xp >= xp_total + xp_needed:
            level += 1
            xp_total += xp_needed
            xp_needed += 50
            
        current_level_xp = xp - xp_total
        progress_percent = current_level_xp / xp_needed if xp_needed else 0
        
        return progress_percent, current_level_xp, xp_needed

# Initialize global XP manager
xp_manager = XPManager() 