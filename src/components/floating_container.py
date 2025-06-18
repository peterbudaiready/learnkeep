import streamlit as st
from supabase import create_client, Client
import time
from openai import OpenAI

def render_floating_container(
    done: int,
    total: int,
    wk: int,
    show_test: bool,
    show_test_dialog: callable,
    notes: str,
    notes_input_key: str,
    supabase: Client,
    course_id: str,
    st_session_state: dict,
    duration: int,
    max_week: int,
    update_course_final_completion: callable,
    course_dict: dict,
    subject: str
):
    # Initialize OpenAI client with API key from secrets.toml
    client = OpenAI(
        api_key=st.secrets["openai"]["api_key"],
        organization=st.secrets["openai"]["org_id"]
    )

    st.markdown('<div class="floating"></div>', unsafe_allow_html=True)
    with st.container():
        st.header("Progress")
        try:
            # Get progress from database for this specific course
            response = supabase.table("courses").select("progress").eq("id", course_id).single().execute()
            current_progress = int(response.data.get("progress", 0) or 0)
            
            # Calculate total paragraphs for this course
            total_paragraphs = sum(len(week.get("paragraphs", {})) for week in course_dict.values())
            
            # Calculate progress percentage based on database value
            progress_percentage = (current_progress / (total_paragraphs - 1)) * 100 if total_paragraphs > 1 else 100
            # Ensure percentage doesn't exceed 100
            progress_percentage = min(100, progress_percentage)
            
            st.progress(progress_percentage / 100, text=f"{int(progress_percentage)}%")
        except Exception as e:
            st.error(f"Could not load progress: {e}")

    if show_test:
        show_test_dialog()
    elif done == total and total > 0:  # Only show test button when all checkboxes are checked
        if st.button("Take a test"):
            st_session_state.show_test = True
            st.rerun()

    if total and done == total and wk >= max_week:
        st.success("Course complete!")
        # Check if all tests are completed
        try:
            comp = supabase.table("courses").select("completition, completed").eq("id", course_id).single().execute().data
            tests_completed = int(comp.get("completition") or 0)
            if tests_completed >= duration:  # All tests completed
                # Update final completion status
                update_course_final_completion(supabase, course_id)
        except Exception as e:
            st.error(f"Could not verify test completion: {e}")

    st.subheader("Notes")
    notes_val = st.text_area("", value=notes, height=200, key=notes_input_key)
    if notes_val != notes:
        try:
            supabase.table("courses").update({"course_notes": notes_val}).eq("id", course_id).execute()
            st_session_state.notes = notes_val
            st.toast("Notes saved!", icon="💾")
        except Exception as e:
            st.error(f"Could not save notes: {e}")

    st.subheader("Tutor Chat")
    for m in st_session_state.chat_history:
        with st.chat_message(m["role"]):
            st.markdown(m["content"], unsafe_allow_html=True)
    if prompt := st.chat_input("Ask …"):
        st_session_state.chat_history.append({"role":"user","content":prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        stream = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role":"system","content":f"You are a professional, sarcastic, satirical teacher of {subject}. You are overwhelmingly funny on a very sarcastic(smart ass) way but your main tasks to help students according to their level and course topic. You always respond in only few but very meaningful, funny and complex sentences."}
            ] + st_session_state.chat_history,
            stream=True
        )
        with st.chat_message("assistant"):
            reply = st.write_stream(stream)
        st_session_state.chat_history.append({"role":"assistant","content":reply}) 