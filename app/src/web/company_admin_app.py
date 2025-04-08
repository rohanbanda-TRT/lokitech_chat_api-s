import os
import sys
import uuid
import requests
import streamlit as st

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
sys.path.insert(0, project_root)

from app.src.core.config import get_settings

def initialize_session_state():
    """Initialize session state variables"""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "session_id" not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())
    if "dsp_code" not in st.session_state:
        st.session_state.dsp_code = ""
    if "chat_started" not in st.session_state:
        st.session_state.chat_started = False
    if "last_dsp_code" not in st.session_state:
        st.session_state.last_dsp_code = ""
    if "station_code" not in st.session_state:
        st.session_state.station_code = ""
    if "applicant_id" not in st.session_state:
        st.session_state.applicant_id = 0

def add_message(role, content):
    """Add a message to the chat history"""
    st.session_state.messages.append({"role": role, "content": content})

def start_chat(dsp_code, session_id, station_code, applicant_id):
    """Start a new chat session"""
    try:
        payload = {
            "message": f"Start [DSP: {dsp_code}, Session: {session_id}, Station Code: {station_code}, Applicant ID: {applicant_id}]",
            "session_id": session_id,
            "dsp_code": dsp_code,
            "station_code": station_code,
            "applicant_id": applicant_id
        }
        
        response = requests.post(
            "http://127.0.0.1:8000/company-admin",
            json=payload
        )
        if response.status_code == 200:
            assistant_message = response.json()["response"]
            add_message("assistant", assistant_message)
            
            st.session_state.chat_started = True
            st.session_state.last_dsp_code = dsp_code
            return True
        else:
            st.error(f"Error starting chat: {response.status_code}")
            return False
    except Exception as e:
        st.error(f"Error starting chat: {str(e)}")
        return False

def main():
    # Set page config
    st.set_page_config(
        page_title="Lokiteck Company Admin",
        page_icon="🏢",
        layout="wide"
    )
    
    # Initialize session state
    initialize_session_state()
    
    st.title("Company Admin Panel")
    st.subheader("Manage Screening Questions")
    
    # Sidebar with session info
    st.sidebar.title("Session Information")
    st.sidebar.text(f"Session ID: {st.session_state.session_id}")
    
    if st.sidebar.button("Generate New Session ID"):
        st.session_state.session_id = str(uuid.uuid4())
        st.session_state.messages = []
        st.session_state.chat_started = False
        st.session_state.last_dsp_code = ""
        st.rerun()
    
    # Main content
    # DSP code input (required for admin)
    dsp_code = st.text_input("DSP Code (Required)", value=st.session_state.dsp_code)
    
    # Add station code and applicant ID inputs for consistency
    col1, col2 = st.columns(2)
    with col1:
        station_code = st.text_input("Station Code", value="DJE1")
    with col2:
        applicant_id = st.number_input("Applicant ID", value=5, min_value=1)
    
    if not dsp_code:
        st.warning("Please enter a DSP Code to manage questions")
        return
    
    # Check if DSP code has changed and we need to restart chat
    dsp_code_changed = dsp_code != st.session_state.last_dsp_code and dsp_code
    
    # Start chat button
    start_button_disabled = st.session_state.chat_started
    
    if st.button("Start Admin Session", disabled=start_button_disabled) or dsp_code_changed:
        # Update DSP code
        st.session_state.dsp_code = dsp_code
        # Clear previous messages
        st.session_state.messages = []
        # Start new chat
        if start_chat(dsp_code, st.session_state.session_id, station_code, applicant_id):
            st.rerun()
    
    # Reset button
    if st.button("Reset Chat"):
        st.session_state.chat_started = False
        st.session_state.last_dsp_code = ""
        st.session_state.messages = []
        st.rerun()
    
    # Display current questions if available
    with st.expander("View Current Questions", expanded=False):
        if st.button("Refresh Questions"):
            try:
                response = requests.get(f"http://127.0.0.1:8000/company-questions/{dsp_code}")
                if response.status_code == 200:
                    questions = response.json().get("questions", [])
                    if questions:
                        for i, q in enumerate(questions):
                            st.write(f"{i+1}. {q.get('question_text')} (Required)")
                            if 'criteria' in q and q['criteria']:
                                st.markdown(f"   - **Criteria:** {q.get('criteria')}")
                                st.divider()
                            else:
                                st.markdown(f"   - **Criteria:** Not specified")
                                st.divider()
                    else:
                        st.info("No questions found for this company")
                else:
                    st.error(f"Error fetching questions: {response.status_code}")
            except Exception as e:
                st.error(f"Error: {str(e)}")
    
    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])
    
    # Chat input (only show if chat has started)
    if st.session_state.chat_started:
        if prompt := st.chat_input("Type your command here..."):
            # Add user message to chat history
            add_message("user", prompt)
            
            # Make API call with admin message
            try:
                response = requests.post(
                    "http://127.0.0.1:8000/company-admin",
                    json={
                        "message": prompt,
                        "session_id": st.session_state.session_id,
                        "dsp_code": dsp_code
                    }
                )
                
                if response.status_code == 200:
                    assistant_message = response.json()["response"]
                    add_message("assistant", assistant_message)
                    st.rerun()
                else:
                    st.error(f"Error: {response.status_code}")
            except Exception as e:
                st.error(f"Error: {str(e)}")
    else:
        st.info("Click 'Start Admin Session' to begin managing questions")

if __name__ == "__main__":
    main()
