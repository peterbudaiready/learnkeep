import sqlite3
import pickle
import time
from typing import Any, Optional
from pathlib import Path
import streamlit as st

class LocalCache:
    def __init__(self, db_path: str = ".cache/streamlit.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_path)
        self._init_db()

    def _init_db(self):
        with self.conn:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS cache (
                    key TEXT PRIMARY KEY,
                    value BLOB,
                    timestamp REAL,
                    ttl REAL
                )
            """)

    def get(self, key: str) -> Optional[Any]:
        try:
            row = self.conn.execute(
                "SELECT value, timestamp, ttl FROM cache WHERE key = ?",
                (key,)
            ).fetchone()
            
            if not row:
                return None
                
            value, timestamp, ttl = row
            if ttl > 0 and time.time() - timestamp > ttl:
                self.delete(key)
                return None
                
            return pickle.loads(value)
        except Exception as e:
            st.error(f"Cache read error: {e}")
            return None

    def set(self, key: str, value: Any, ttl: float = 3600) -> None:
        try:
            with self.conn:
                self.conn.execute(
                    "INSERT OR REPLACE INTO cache (key, value, timestamp, ttl) VALUES (?, ?, ?, ?)",
                    (key, pickle.dumps(value), time.time(), ttl)
                )
        except Exception as e:
            st.error(f"Cache write error: {e}")

    def delete(self, key: str) -> None:
        with self.conn:
            self.conn.execute("DELETE FROM cache WHERE key = ?", (key,))

    def clear(self) -> None:
        with self.conn:
            self.conn.execute("DELETE FROM cache")

    def cleanup(self) -> None:
        with self.conn:
            self.conn.execute(
                "DELETE FROM cache WHERE ttl > 0 AND (? - timestamp) > ttl",
                (time.time(),)
            )

# Initialize global cache instance
cache = LocalCache() 