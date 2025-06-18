import streamlit as st
import time
import requests
import json
import re
import pandas as pd
from supabase import create_client, Client
from login_popup import display_login_popup
import pathlib
from src.utils.xp_manager import xp_manager

# Supabase credentials
SUPABASE_URL = "https://fcyutudqmkhrywffsjky.supabase.co"
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImZjeXV0dWRxbWtocnl3ZmZzamt5Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDI0MjQ3OTAsImV4cCI6MjA1ODAwMDc5MH0.IucZQwgH1CFYFCgb9E3-TV7I-NOnPq9-3lmrWc4ZE7I"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# Hide default Streamlit menu, header, and footer
st.markdown("""
    <style>
      #MainMenu {visibility: hidden;}
      footer {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

def rerun_app():
    st.rerun()

def get_course_summary_obj(details: dict):
    raw_topic = details["course_topic"]
    sanitized_topic = "".join(c if c.isalnum() else "_" for c in raw_topic)
    CourseSummary = type(sanitized_topic, (), {})
    CourseSummary.__module__ = ""
    obj = CourseSummary()
    obj.__doc__ = (
        f"Course Topic: {details['course_topic']}\n"
        f"Course Length: {details['course_length']} weeks\n"
        f"Skill Level: {details['course_level']}\n"
        f"Resource Types: {', '.join(details['resource_types'])}\n"
        f"Emphasis: {details['emphasis']}\n"
        f"Knowledge Check: {details['knowledge_check']}\n"
        f"Learning Curve: {details['learning_curve']}%\n"
    )
    return obj

display_login_popup()

# State setup
if "course_validated" not in st.session_state:
    st.session_state.course_validated = False
if "current_course_id" not in st.session_state:
    st.session_state.current_course_id = None
if "inputs_disabled" not in st.session_state:
    st.session_state.inputs_disabled = False
if "fixed_topic" not in st.session_state:
    st.session_state.fixed_topic = None

# Course parsing
def parse_course_text(plain_text):
    course_struct = {
        "title": "",
        "introduction": "",
        "weeks": [],
        "tests": [],
        "conclusion": ""
    }
    current_section = None
    current_week_content = ""
    current_test_content = ""
    lines = plain_text.splitlines()
    is_parsing_test = False

    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.startswith("# "):
            course_struct["title"] = line[2:].strip()
            current_section = "title"
            continue
        if re.match(r"^#{2,}\s*Introduction", line, re.I):
            current_section = "introduction"
            continue
        if re.match(r"^#{2,}\s*Conclusion", line, re.I):
            current_section = "conclusion"
            continue
        if re.match(r"^#{2,}\s*Week\s*\d+", line, re.I):
            if current_week_content:
                course_struct["weeks"].append(current_week_content.strip())
                current_week_content = ""
            current_section = "week"
            current_week_content = line
            continue
        if line.lower() == "test":
            is_parsing_test = True
            current_test_content = ""
            continue
        if line.lower().startswith("answer key"):
            if current_test_content:
                course_struct["tests"].append(current_test_content.strip())
                current_test_content = ""
            is_parsing_test = False
            continue
        if is_parsing_test:
            current_test_content += line + "\n"
        elif current_section == "introduction":
            course_struct["introduction"] += line + "\n"
        elif current_section == "week":
            current_week_content += "\n" + line
        elif current_section == "conclusion":
            course_struct["conclusion"] += line + "\n"

    if current_week_content:
        course_struct["weeks"].append(current_week_content.strip())
    return course_struct

def store_course(user_topic, plain_text):
    structured_dict = parse_course_text(plain_text)
    data = {
        "title": user_topic.strip(),
        "content": structured_dict,
        "creators_id": st.session_state["user"]["id"]
    }
    try:
        response = supabase.table("courses").insert(data).execute()
        return response.data[0]["id"]
    except Exception as e:
        st.error(f"Insert failed: {e}")
        return None

def validate_course(topic, length, level, resources, emphasis, knowledge_check, learning_curve):
    with st.spinner("Validating course topic..."):
        payload = {
            "topic": topic,
            "course_length": length,
            "course_level": level,
            "resources": resources,
            "emphasis": emphasis,
            "knowledge_check": knowledge_check,
            "learning_curve": learning_curve
        }
        try:
            response = requests.post("https://hook.eu2.make.com/vviezwjv11n99p4jgaoazsofg9wq7ehb", json=payload)
            response_text = response.text.strip()
            
            if response.status_code == 200:
                if response_text.startswith("Error:"):
                    st.warning(response_text)
                    st.session_state.course_validated = False
                    st.rerun()
                elif response_text.startswith("Fix:"):
                    fixed_topic = response_text[5:].strip()  # Remove "Fix:" prefix
                    st.session_state.fixed_topic = fixed_topic
                    st.session_state.course_validated = True
                    st.session_state.inputs_disabled = True
                    st.success("✅ Course topic validated!")
                    st.rerun()
                elif response_text == "Correct":
                    st.session_state.course_validated = True
                    st.session_state.inputs_disabled = True
                    st.success("✅ Course topic validated!")
                    st.rerun()
                else:
                    st.error("❌ Invalid response from validation service.")
            else:
                st.error("❌ Invalid course topic.")
        except requests.exceptions.RequestException as e:
            st.error(f"⚠️ Network error: {e}")

def generate_course(topic, length, level, resources, emphasis, knowledge_check, learning_curve):
    if not topic.strip():
        st.error("❌ Enter a valid topic.")
        return
    if "user" not in st.session_state or not st.session_state["user"]:
        st.error("⚠️ User not authenticated.")
        return

    user_id = st.session_state["user"]["id"]
    with st.spinner("Generating course..."):
        payload = {
            "topic": topic.strip(),
            "duration": length,
            "level": level,
            "resources": resources,
            "user_id": user_id,
            "emphasis": emphasis,
            "knowledge_check": knowledge_check,
            "learning_curve": learning_curve
        }
        try:
            response = requests.post("https://hook.eu2.make.com/wpt0ou5l5u8merimwvdqr5t67ul7e6f5", json=payload)
            if response.status_code == 200:
                course_id = response.text.strip()
                if course_id.isdigit():  # Ensure the course ID is a valid number
                    st.session_state.current_course_id = int(course_id)  # Convert to integer
                    # Add XP reward for course generation
                    xp_manager.reward_course_generation(user_id)
                    st.success("📖 Course generated! Click below:")
                    st.page_link("pages/course_view.py", label="📖 Start Course", icon="📖")
                else:
                    st.error("⚠️ Invalid course ID received from server.")
            else:
                st.error("⚠️ Course generation failed.")
        except requests.exceptions.RequestException as e:
            st.error(f"⚠️ Request failed: {e}")

# Main UI

col1, col2 = st.columns(2, gap="large", vertical_alignment="top")

with col1:
    initial_value = st.session_state.fixed_topic if st.session_state.fixed_topic else "AI in Education"
    course_topic = st.text_input("", value=initial_value, key="course_topic", disabled=st.session_state.inputs_disabled)
    course_length = st.selectbox("**Course Length (weeks)**", [1, 4, 12], index=0, key="course_length", disabled=st.session_state.inputs_disabled)
    course_level = st.radio("**Current Skill Level**", ["Beginner", "Intermediate", "Expert"], key="course_level", disabled=st.session_state.inputs_disabled)
    st.markdown("**Select Resource Types:**")
    resource_types = []
    if st.checkbox("📺 YouTube", key="res_youtube", disabled=st.session_state.inputs_disabled):
        resource_types.append("YouTube")
    if st.checkbox("📄 Scientific Research", key="res_scientific", disabled=st.session_state.inputs_disabled):
        resource_types.append("Scientific Research")
    if st.checkbox("📚 General Knowledge", key="res_general", disabled=st.session_state.inputs_disabled):
        resource_types.append("General Knowledge")
    if st.checkbox("💰 Paid Resources", key="res_paid", disabled=st.session_state.inputs_disabled):
        resource_types.append("Paid Resources")

with col2:
    with st.expander("Additional settings"):
        emphasis = st.text_input("**Emphasis on**", key="emphasis", disabled=st.session_state.inputs_disabled)
        knowledge_check = st.radio("**Knowledge Check**", ["Normal", "Hard core"], key="knowledge_check", disabled=st.session_state.inputs_disabled)
        learning_curve = st.slider("**Learning Curve**", 0, 100, 50, format="%d%%", key="learning_curve", disabled=st.session_state.inputs_disabled)

st.markdown("---")

if st.session_state.get("course_validated", False):
    details = {
        "course_topic": st.session_state["course_topic"],
        "course_length": st.session_state["course_length"],
        "course_level": st.session_state["course_level"],
        "resource_types": resource_types,
        "emphasis": st.session_state["emphasis"],
        "knowledge_check": st.session_state["knowledge_check"],
        "learning_curve": st.session_state["learning_curve"]
    }
    course_summary = get_course_summary_obj(details)
    st.help(course_summary)
    if st.button("🚀 Generate Course"):
        generate_course(
            details["course_topic"],
            details["course_length"],
            details["course_level"],
            details["resource_types"],
            details["emphasis"],
            details["knowledge_check"],
            details["learning_curve"]
        )
else:
    if st.button("✅ Validate Course"):
        validate_course(
            st.session_state["course_topic"],
            st.session_state["course_length"],
            st.session_state["course_level"],
            resource_types,
            st.session_state["emphasis"],
            st.session_state["knowledge_check"],
            st.session_state["learning_curve"]
        )

st.page_link("pages/database_view.py", label="📖 View Stored Courses", icon="📖")
