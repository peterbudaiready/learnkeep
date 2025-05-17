import time
from functools import wraps
from typing import Callable, Dict, List
import streamlit as st

class RateLimiter:
    def __init__(self, max_requests: int = 5, window_seconds: int = 1):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: Dict[str, List[float]] = {}

    def _cleanup_old_requests(self, key: str):
        if key not in self.requests:
            self.requests[key] = []
        
        current_time = time.time()
        self.requests[key] = [
            req_time for req_time in self.requests[key]
            if current_time - req_time <= self.window_seconds
        ]

    def is_allowed(self, key: str) -> bool:
        self._cleanup_old_requests(key)
        return len(self.requests[key]) < self.max_requests

    def add_request(self, key: str):
        self._cleanup_old_requests(key)
        self.requests[key].append(time.time())

    def time_until_next(self, key: str) -> float:
        if self.is_allowed(key):
            return 0
        oldest_request = min(self.requests[key])
        return self.window_seconds - (time.time() - oldest_request)

def rate_limit(
    max_requests: int = 5,
    window_seconds: int = 1,
    key_func: Callable = lambda: "default"
):
    limiter = RateLimiter(max_requests, window_seconds)
    
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            key = key_func()
            
            if not limiter.is_allowed(key):
                wait_time = limiter.time_until_next(key)
                st.warning(
                    f"Rate limit exceeded. Please wait {wait_time:.1f} seconds."
                )
                return None
            
            limiter.add_request(key)
            return func(*args, **kwargs)
        return wrapper
    return decorator

# Example usage:
# @rate_limit(max_requests=5, window_seconds=60)
# def api_call():
#     pass 