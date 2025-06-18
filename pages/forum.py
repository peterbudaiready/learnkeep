import streamlit as st
from supabase import create_client, Client
from login_popup import display_login_popup
import base64
from datetime import datetime
import time

# Initialize Supabase client
SUPABASE_URL = "https://fcyutudqmkhrywffsjky.supabase.co"
SUPABASE_ANON_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImZjeXV0dWRxbWtocnl3ZmZzamt5Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDI0MjQ3OTAsImV4cCI6MjA1ODAwMDc5MH0."
    "IucZQwgH1CFYFCgb9E3-TV7I-NOnPq9-3lmrWc4ZE7I"
)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# Display login popup
display_login_popup()

# Get current user
user = st.session_state.get("user")
if not user:
    st.warning("Please log in to access the forum.")
    st.stop()

# Initialize session state
if "current_page" not in st.session_state:
    st.session_state.current_page = 1
if "sort_by" not in st.session_state:
    st.session_state.sort_by = "newest"
if "search_query" not in st.session_state:
    st.session_state.search_query = ""
if "selected_category" not in st.session_state:
    st.session_state.selected_category = "All"

# Constants
THREADS_PER_PAGE = 10
CATEGORIES = ["All", "Announcements", "General Discussion", "Help & Support", "Feedback & Suggestions", "Introductions", "Off-Topic / Lounge", "Bug Reports"]

# Helper functions
def get_user_avatar(user_id):
    try:
        profile = supabase.table("user_profile").select("profile_pic").eq("user_id", user_id).single().execute()
        pic_data = profile.data.get("profile_pic")
        if isinstance(pic_data, str) and pic_data.startswith("\\x"):
            return f"data:image/png;base64,{base64.b64encode(bytes.fromhex(pic_data[2:])).decode()}"
    except Exception:
        pass
    return "https://via.placeholder.com/40"

def get_user_name(user_id):
    try:
        profile = supabase.table("user_profile").select("profile_name").eq("user_id", user_id).single().execute()
        return profile.data.get("profile_name", "Anonymous User")
    except Exception:
        return "Anonymous User"

def format_timestamp(timestamp):
    try:
        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        return dt.strftime("%b %d, %Y %H:%M")
    except Exception:
        return "Unknown date"

# Main forum layout
st.title("💬 Forum")

# Search and filter bar
col1, col2, col3 = st.columns([2, 2, 1])
with col1:
    search_query = st.text_input("🔍 Search threads", value=st.session_state.search_query)
    if search_query != st.session_state.search_query:
        st.session_state.search_query = search_query
        st.session_state.current_page = 1
        st.rerun()

with col2:
    sort_by = st.selectbox(
        "Sort by",
        ["newest", "most_liked", "most_commented"],
        index=["newest", "most_liked", "most_commented"].index(st.session_state.sort_by)
    )
    if sort_by != st.session_state.sort_by:
        st.session_state.sort_by = sort_by
        st.session_state.current_page = 1
        st.rerun()

with col3:
    category = st.selectbox("Category", CATEGORIES, index=CATEGORIES.index(st.session_state.selected_category))
    if category != st.session_state.selected_category:
        st.session_state.selected_category = category
        st.session_state.current_page = 1
        st.rerun()

# Create new thread button
if st.button("📝 Create New Thread", use_container_width=True):
    st.session_state.show_new_thread = True

# New thread dialog
if st.session_state.get("show_new_thread", False):
    @st.dialog("Create New Thread", width="large")
    def new_thread_dialog():
        with st.form("new_thread_form"):
            title = st.text_input("Title")
            category = st.selectbox("Category", ["Announcements", "General Discussion", "Help & Support", "Feedback & Suggestions", "Introductions", "Off-Topic / Lounge", "Bug Reports"])
            content = st.text_area("Content")
            submitted = st.form_submit_button("Create Thread")
            
            if submitted:
                if not title or not content:
                    st.error("Please fill in all fields.")
                else:
                    try:
                        thread_data = {
                            "title": title,
                            "content": content,
                            "category": category,
                            "user_id": user["id"],
                            "created_at": datetime.utcnow().isoformat(),
                            "likes": 0,
                            "comments": 0
                        }
                        supabase.table("forum_threads").insert(thread_data).execute()
                        st.success("Thread created successfully!")
                        st.session_state.show_new_thread = False
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to create thread: {e}")
    new_thread_dialog()

# Fetch and display threads
try:
    query = supabase.table("forum_threads").select("*")
    
    # Apply category filter
    if st.session_state.selected_category != "All":
        query = query.eq("category", st.session_state.selected_category)
    
    # Apply search filter
    if st.session_state.search_query:
        query = query.ilike("title", f"%{st.session_state.search_query}%")
    
    # Apply sorting
    if st.session_state.sort_by == "newest":
        query = query.order("created_at", desc=True)
    elif st.session_state.sort_by == "most_liked":
        query = query.order("likes", desc=True)
    elif st.session_state.sort_by == "most_commented":
        query = query.order("comments", desc=True)
    
    # Apply pagination
    start = (st.session_state.current_page - 1) * THREADS_PER_PAGE
    end = start + THREADS_PER_PAGE - 1
    query = query.range(start, end)
    
    threads = query.execute().data
    
    # Display threads
    for thread in threads:
        with st.container(border=True):
            col1, col2 = st.columns([1, 5])
            
            with col1:
                st.image(get_user_avatar(thread["user_id"]), width=40)
            
            with col2:
                st.markdown(f"### {thread['title']}")
                st.markdown(f"Posted by {get_user_name(thread['user_id'])} • {format_timestamp(thread['created_at'])}")
                st.markdown(f"Category: {thread['category']}")
                st.markdown(thread['content'])
                
                # Thread actions
                col3, col4, col5 = st.columns([1, 1, 1])
                with col3:
                    if st.button(f"👍 {thread['likes']}", key=f"like_{thread['id']}"):
                        try:
                            # Check if user already liked
                            like = supabase.table("forum_likes").select("*").eq("thread_id", thread["id"]).eq("user_id", user["id"]).execute()
                            if not like.data:
                                # Add like
                                supabase.table("forum_likes").insert({
                                    "thread_id": thread["id"],
                                    "user_id": user["id"]
                                }).execute()
                                # Update thread likes
                                supabase.table("forum_threads").update({"likes": thread["likes"] + 1}).eq("id", thread["id"]).execute()
                                st.rerun()
                        except Exception as e:
                            st.error(f"Failed to like thread: {e}")
                
                with col4:
                    if st.button(f"💬 {thread['comments']}", key=f"comments_{thread['id']}"):
                        st.session_state.selected_thread = thread["id"]
                        st.rerun()
                
                with col5:
                    if st.button("🔗 View", key=f"view_{thread['id']}"):
                        st.session_state.selected_thread = thread["id"]
                        st.rerun()
    
    # Pagination
    total_threads = len(supabase.table("forum_threads").select("id").execute().data)
    total_pages = (total_threads + THREADS_PER_PAGE - 1) // THREADS_PER_PAGE
    
    if total_pages > 1:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown(f"Page {st.session_state.current_page} of {total_pages}")
            prev, next = st.columns(2)
            with prev:
                if st.button("Previous", disabled=st.session_state.current_page == 1):
                    st.session_state.current_page -= 1
                    st.rerun()
            with next:
                if st.button("Next", disabled=st.session_state.current_page == total_pages):
                    st.session_state.current_page += 1
                    st.rerun()

except Exception as e:
    st.error(f"Error loading threads: {e}")

# Thread view dialog
if st.session_state.get("selected_thread"):
    @st.dialog("Thread View", width="large")
    def thread_view_dialog():
        thread_id = st.session_state.selected_thread
        thread = supabase.table("forum_threads").select("*").eq("id", thread_id).single().execute().data
        
        if thread:
            st.markdown(f"### {thread['title']}")
            st.markdown(f"Posted by {get_user_name(thread['user_id'])} • {format_timestamp(thread['created_at'])}")
            st.markdown(f"Category: {thread['category']}")
            st.markdown(thread['content'])
            
            # Comments section
            st.markdown("### Comments")
            
            # New comment form
            with st.form("new_comment_form"):
                comment = st.text_area("Add a comment")
                submitted = st.form_submit_button("Post Comment")
                
                if submitted:
                    if not comment:
                        st.error("Please enter a comment.")
                    else:
                        try:
                            comment_data = {
                                "thread_id": thread_id,
                                "user_id": user["id"],
                                "content": comment,
                                "created_at": datetime.utcnow().isoformat()
                            }
                            supabase.table("forum_comments").insert(comment_data).execute()
                            # Update thread comment count
                            supabase.table("forum_threads").update({"comments": thread["comments"] + 1}).eq("id", thread_id).execute()
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed to post comment: {e}")
            
            # Display comments
            comments = supabase.table("forum_comments").select("*").eq("thread_id", thread_id).order("created_at", desc=True).execute().data
            
            for comment in comments:
                with st.container(border=True):
                    col1, col2 = st.columns([1, 5])
                    with col1:
                        st.image(get_user_avatar(comment["user_id"]), width=40)
                    with col2:
                        st.markdown(f"**{get_user_name(comment['user_id'])}** • {format_timestamp(comment['created_at'])}")
                        st.markdown(comment["content"])
        
        if st.button("Close"):
            st.session_state.selected_thread = None
            st.rerun()
    
    thread_view_dialog()
