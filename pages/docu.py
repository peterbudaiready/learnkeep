import streamlit as st

st.title("📚 Documentation")

# Introduction
st.header("Welcome to Skillmea")
st.write("""
Skillmea is an AI-powered learning platform that helps you create and follow personalized learning paths.
This documentation will help you understand how to use the platform effectively.
""")

# Getting Started
st.header("Getting Started")

with st.expander("Account Setup"):
    st.write("""
    1. **Sign Up**: Create an account using your email address
    2. **Profile Setup**: Complete your profile with:
        - Display name
        - Profile picture
        - Bio
        - Skill level preferences
    3. **Verify Email**: Click the verification link sent to your email
    """)

with st.expander("Navigation"):
    st.write("""
    The platform has several main sections:
    
    - **Course Generation**: Create new personalized courses
    - **My Courses**: Access your enrolled and created courses
    - **Libraries**: Browse public course libraries
    - **My Notes**: View and manage your course notes
    - **Profile**: Manage your account settings
    - **Support**: Get help when needed
    """)

# Course Generation
st.header("Course Generation")

with st.expander("Creating a Course"):
    st.write("""
    1. **Topic Selection**:
        - Enter your desired learning topic
        - The AI will validate and suggest improvements
    
    2. **Course Parameters**:
        - Course Length: Choose 1, 4, or 12 weeks
        - Skill Level: Beginner, Intermediate, or Expert
        - Resource Types: YouTube, Scientific Research, General Knowledge, Paid Resources
    
    3. **Advanced Settings**:
        - Emphasis: Focus areas within the topic
        - Learning Objective: Learn new skill, Recollect skill, Fast skilling, Genius mode
        - Scheme: Free form, Structured data, Knowledge check, Showcase
        - Knowledge Check Difficulty: Normal or Hard core
        - Learning Curve: Adjust the pace (0-100%)
    """)

with st.expander("Course Structure"):
    st.write("""
    Each generated course includes:
    
    - Course introduction
    - Weekly modules with:
        - Learning materials
        - Resource links
        - Progress tracking
        - Knowledge checks
    - Course conclusion
    - Final assessment
    """)

# Learning Features
st.header("Learning Features")

with st.expander("Progress Tracking"):
    st.write("""
    - **XP System**: Earn experience points by:
        - Completing course modules
        - Passing knowledge checks
        - Contributing reviews
        - Helping others
    
    - **Level System**:
        - Progress through levels as you earn XP
        - Unlock new features and capabilities
        - Track your learning journey
    """)

with st.expander("Note Taking"):
    st.write("""
    - Take notes within each course
    - Notes are automatically saved
    - Access all notes from the My Notes section
    - Export notes as PDF
    """)

with st.expander("Course Feedback"):
    st.write("""
    - Rate courses (1-5 stars)
    - Write detailed reviews
    - View others' feedback
    - Help improve course quality
    """)

# Tips and Best Practices
st.header("Tips and Best Practices")

with st.expander("Getting the Most from Courses"):
    st.write("""
    1. **Set Clear Goals**:
        - Define what you want to learn
        - Choose appropriate difficulty levels
        - Set realistic timeframes
    
    2. **Stay Consistent**:
        - Follow the suggested pace
        - Complete knowledge checks
        - Take regular notes
    
    3. **Engage with Content**:
        - Use multiple resource types
        - Practice with examples
        - Share your progress
    """)

with st.expander("Troubleshooting"):
    st.write("""
    Common issues and solutions:
    
    1. **Course Generation**:
        - If validation fails, try being more specific
        - Check your internet connection
        - Ensure topic is well-defined
    
    2. **Progress Tracking**:
        - Clear browser cache if progress isn't saving
        - Ensure you're logged in
        - Contact support for persistent issues
    
    3. **Resource Access**:
        - Check your internet connection
        - Try different resource types
        - Report broken links
    """)

# Support and Community
st.header("Support and Community")

with st.expander("Getting Help"):
    st.write("""
    - Use the Support Line for technical issues
    - Join the Forum to connect with other learners
    - Check FAQ for common questions
    - Email support for complex issues
    """)

with st.expander("Contributing"):
    st.write("""
    Ways to contribute to the community:
    
    - Share your course experiences
    - Help other learners
    - Suggest improvements
    - Report issues
    """)

# Footer
st.divider()
st.caption("Need more help? Contact our support team or visit the forum.")
