import sqlite3
from typing import List, Dict, Any
import streamlit as st
import json

class CourseSearch:
    def __init__(self, db_path: str = ".cache/search.db"):
        self.conn = sqlite3.connect(db_path)
        self._init_db()

    def _init_db(self):
        """Initialize the FTS5 virtual table"""
        with self.conn:
            # Create the FTS5 table for course content
            self.conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS course_content USING fts5(
                    course_id,
                    title,
                    content,
                    metadata
                )
            """)

    def index_course(self, course_id: str, title: str, content: Dict[str, Any], metadata: Dict[str, Any] = None):
        """Index a course's content for searching"""
        try:
            # Convert content to searchable text
            searchable_content = self._content_to_text(content)
            metadata_json = json.dumps(metadata) if metadata else "{}"
            
            # Insert or replace in FTS5 table
            with self.conn:
                self.conn.execute(
                    "INSERT OR REPLACE INTO course_content (course_id, title, content, metadata) VALUES (?, ?, ?, ?)",
                    (course_id, title, searchable_content, metadata_json)
                )
        except Exception as e:
            st.error(f"Failed to index course: {e}")

    def search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search courses using FTS5"""
        try:
            cursor = self.conn.execute(
                """
                SELECT course_id, title, snippet(course_content, 2, '<mark>', '</mark>', '...', 64) as excerpt,
                       metadata, rank
                FROM course_content
                WHERE course_content MATCH ?
                ORDER BY rank
                LIMIT ?
                """,
                (query, limit)
            )
            
            results = []
            for row in cursor:
                result = {
                    "course_id": row[0],
                    "title": row[1],
                    "excerpt": row[2],
                    "metadata": json.loads(row[3]) if row[3] else {},
                    "rank": row[4]
                }
                results.append(result)
            
            return results
        except Exception as e:
            st.error(f"Search failed: {e}")
            return []

    def _content_to_text(self, content: Dict[str, Any]) -> str:
        """Convert course content dictionary to searchable text"""
        text_parts = []
        
        # Extract text from course structure
        if isinstance(content, dict):
            # Add introduction
            if "introduction" in content:
                text_parts.append(content["introduction"])
            
            # Add week content
            for week in content.get("weeks", []):
                text_parts.append(week)
            
            # Add conclusion
            if "conclusion" in content:
                text_parts.append(content["conclusion"])
            
            # Add any parameters/metadata
            params = content.get("parameters", {})
            if params:
                text_parts.append(str(params))
        
        return "\n".join(text_parts)

    def reindex_all_courses(self, courses: List[Dict[str, Any]]):
        """Reindex all courses in the database"""
        try:
            with self.conn:
                # Clear existing index
                self.conn.execute("DELETE FROM course_content")
                
                # Reindex all courses
                for course in courses:
                    self.index_course(
                        course["id"],
                        course.get("title", "Untitled"),
                        course.get("content", {}),
                        {
                            "level": course.get("level"),
                            "rating": course.get("rating"),
                            "public": course.get("public", False)
                        }
                    )
        except Exception as e:
            st.error(f"Failed to reindex courses: {e}")

# Initialize global search instance
search = CourseSearch() 