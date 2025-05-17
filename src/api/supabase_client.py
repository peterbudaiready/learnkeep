from typing import Any, Optional
import streamlit as st
from supabase import create_client, Client
from ..utils.cache import cache
from ..utils.rate_limiter import rate_limit

class SupabaseWrapper:
    def __init__(self):
        self.url = st.secrets["supabase"]["url"]
        self.key = st.secrets["supabase"]["anon_key"]
        self._client: Optional[Client] = None

    @property
    def client(self) -> Client:
        if not self._client:
            self._client = create_client(self.url, self.key)
        return self._client

    @rate_limit(max_requests=5, window_seconds=1)
    def _execute_query(self, query_func: callable, cache_key: Optional[str] = None, ttl: int = 3600) -> Any:
        if cache_key:
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                return cached_result

        result = query_func()
        
        if cache_key:
            cache.set(cache_key, result, ttl)
        
        return result

    def get_user_profile(self, user_id: str) -> dict:
        def query():
            return (
                self.client.table("user_profile")
                .select("*")
                .eq("user_id", user_id)
                .single()
                .execute()
                .data
            )
        
        cache_key = f"user_profile_{user_id}"
        return self._execute_query(query, cache_key)

    def update_user_profile(self, user_id: str, data: dict) -> dict:
        def query():
            return (
                self.client.table("user_profile")
                .update(data)
                .eq("user_id", user_id)
                .execute()
            )
        
        result = self._execute_query(query)
        # Invalidate cache
        cache.delete(f"user_profile_{user_id}")
        return result

    def get_course(self, course_id: str) -> dict:
        def query():
            return (
                self.client.table("courses")
                .select("*")
                .eq("id", course_id)
                .single()
                .execute()
                .data
            )
        
        cache_key = f"course_{course_id}"
        return self._execute_query(query, cache_key)

    def update_course_progress(self, course_id: str, progress: int) -> None:
        def query():
            return (
                self.client.table("courses")
                .update({"progress": progress})
                .eq("id", course_id)
                .execute()
            )
        
        self._execute_query(query)
        # Invalidate cache
        cache.delete(f"course_{course_id}")

    def get_public_courses(self, offset: int = 0, limit: int = 8) -> list:
        def query():
            return (
                self.client.table("courses")
                .select("id, title, rating, public, course_img")
                .eq("public", True)
                .range(offset, offset + limit - 1)
                .execute()
                .data
            )
        
        cache_key = f"public_courses_{offset}_{limit}"
        return self._execute_query(query, cache_key, ttl=300)  # Cache for 5 minutes

# Initialize global Supabase client
supabase = SupabaseWrapper() 