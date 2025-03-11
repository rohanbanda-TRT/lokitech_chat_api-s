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
        st.session_state.session_id = str(uuid.uuid4()) if not st.session_state.get("session_id") else st.session_state.session_id
    if "interview_started" not in st.session_state:
        st.session_state.interview_started = True

    # Initialize chat with first message if empty
    if not st.session_state.messages:
        try:
            response = requests.post(
                "http://127.0.0.1:8000/driver-screening",
                json={
                    "message": "",
                    "session_id": st.session_state.session_id
                }
            )
            if response.status_code == 200:
                assistant_message = response.json()["response"]
                st.session_state.messages.append({"role": "assistant", "content": assistant_message})
        except Exception as e:
            st.error(f"Error initializing chat: {str(e)}")

def main():
    # Page configuration
    st.set_page_config(
        page_title="Driver Screening Interview",
        page_icon="🚛",
        layout="wide"
    )
    
    # Initialize session state
    initialize_session_state()
    
    # Header
    st.title("Driver Screening Interview")

    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])
    
    # Chat input
    if prompt := st.chat_input("Type your response here..."):
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Make API call with user message
        try:
            response = requests.post(
                "http://127.0.0.1:8000/driver-screening",
                json={
                    "message": prompt,
                    "session_id": st.session_state.session_id
                }
            )
            
            if response.status_code == 200:
                assistant_message = response.json()["response"]
                st.session_state.messages.append({"role": "assistant", "content": assistant_message})
                st.rerun()
            else:
                st.error(f"Error: {response.status_code}")
        except Exception as e:
            st.error(f"Error: {str(e)}")

if __name__ == "__main__":
    main()