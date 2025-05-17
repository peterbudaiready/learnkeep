import streamlit as st
from datetime import datetime
from supabase import create_client, Client
from login_popup import display_login_popup

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
    st.warning("Please log in to access support.")
    st.stop()

st.title("🎯 Support Line")

# FAQ Section
st.header("Frequently Asked Questions")

with st.expander("How do I create a course?"):
    st.write("""
    1. Click on "New Course" in the navigation menu
    2. Enter your desired topic
    3. Configure course parameters (length, level, etc.)
    4. Click "Generate Course"
    
    For detailed instructions, check our documentation.
    """)

with st.expander("How does the XP system work?"):
    st.write("""
    You earn XP (Experience Points) by:
    - Completing course modules (100 XP)
    - Passing knowledge checks (50 XP)
    - Writing course reviews (25 XP)
    - Helping others in the forum (10 XP per helpful post)
    
    XP determines your level and unlocks new features.
    """)

with st.expander("I can't access my course"):
    st.write("""
    Common solutions:
    1. Ensure you're logged in
    2. Clear your browser cache
    3. Check your internet connection
    4. Try a different browser
    
    If the problem persists, create a support ticket below.
    """)

with st.expander("How do I reset my password?"):
    st.write("""
    1. Click "Forgot Password" on the login screen
    2. Enter your email address
    3. Check your email for reset instructions
    4. Follow the link to set a new password
    
    If you don't receive the email, check your spam folder.
    """)

# Support Ticket System
st.header("Support Tickets")

# Display existing tickets
try:
    tickets = (
        supabase.table("support_tickets")
        .select("*")
        .eq("user_id", user["id"])
        .order("created_at", desc=True)
        .execute()
        .data
    )
    
    if tickets:
        st.subheader("Your Tickets")
        for ticket in tickets:
            with st.expander(f"#{ticket['id']} - {ticket['subject']} ({ticket['status']})"):
                st.write(f"**Created:** {ticket['created_at']}")
                st.write(f"**Category:** {ticket['category']}")
                st.write("**Description:**")
                st.write(ticket['description'])
                
                if ticket.get('response'):
                    st.write("**Support Response:**")
                    st.write(ticket['response'])
except Exception as e:
    st.error(f"Failed to fetch tickets: {e}")
    tickets = []

# Create new ticket
st.subheader("Create New Ticket")

with st.form("support_ticket"):
    subject = st.text_input("Subject")
    category = st.selectbox(
        "Category",
        ["Technical Issue", "Course Problem", "Account Issue", "Billing", "Other"]
    )
    description = st.text_area("Description")
    submitted = st.form_submit_button("Submit Ticket")
    
    if submitted:
        if not subject or not description:
            st.error("Please fill in all fields.")
        else:
            try:
                ticket_data = {
                    "user_id": user["id"],
                    "subject": subject,
                    "category": category,
                    "description": description,
                    "status": "Open",
                    "created_at": datetime.utcnow().isoformat()
                }
                
                supabase.table("support_tickets").insert(ticket_data).execute()
                st.success("Ticket submitted successfully!")
                st.rerun()
                
            except Exception as e:
                st.error(f"Failed to submit ticket: {e}")

# Contact Information
st.header("Direct Contact")
st.write("""
For urgent issues or direct communication:
- Email: support@skillmea.com
- Phone: +1 (555) 123-4567
- Hours: Monday-Friday, 9:00 AM - 5:00 PM EST
""")

# Footer
st.divider()
st.caption("Response time: We aim to respond to all tickets within 24 hours.")
