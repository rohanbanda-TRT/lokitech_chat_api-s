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
        st.session_state.messages = {}
    if "user_session_id" not in st.session_state:
        st.session_state.user_session_id = str(uuid.uuid4())
    if "admin_session_id" not in st.session_state:
        st.session_state.admin_session_id = str(uuid.uuid4())
    if "current_page" not in st.session_state:
        st.session_state.current_page = "User"
    if "dsp_code" not in st.session_state:
        st.session_state.dsp_code = ""
    if "chat_started" not in st.session_state:
        st.session_state.chat_started = {"user": False, "admin": False}
    if "last_dsp_code" not in st.session_state:
        st.session_state.last_dsp_code = {"user": "", "admin": ""}

def get_chat_history(page_key):
    """Get chat history for a specific page"""
    if page_key not in st.session_state.messages:
        st.session_state.messages[page_key] = []
    return st.session_state.messages[page_key]

def add_message(page_key, role, content):
    """Add a message to the chat history"""
    if page_key not in st.session_state.messages:
        st.session_state.messages[page_key] = []
    st.session_state.messages[page_key].append({"role": role, "content": content})

def start_chat(page_key, endpoint, dsp_code, session_id):
    """Start a new chat session"""
    try:
        payload = {
            "message": f"Start [DSP: {dsp_code}, Session: {session_id}]",
            "session_id": session_id,
            "dsp_code": dsp_code
        }
        
        response = requests.post(
            f"http://127.0.0.1:8000/{endpoint}",
            json=payload
        )
        if response.status_code == 200:
            assistant_message = response.json()["response"]
            add_message(page_key, "assistant", assistant_message)
            st.session_state.chat_started[page_key] = True
            st.session_state.last_dsp_code[page_key] = dsp_code
            return True
        else:
            st.error(f"Error starting chat: {response.status_code}")
            return False
    except Exception as e:
        st.error(f"Error starting chat: {str(e)}")
        return False

def user_page():
    st.title("Driver Screening Interview")
    st.subheader("User")
    
    # DSP code input
    dsp_code = st.text_input("DSP Code (Optional)", value=st.session_state.dsp_code, key="user_dsp_code")
    
    # Check if DSP code has changed and we need to restart chat
    dsp_code_changed = dsp_code != st.session_state.last_dsp_code["user"] and dsp_code
    
    # Start chat button - disabled if no DSP code or chat already started
    start_button_disabled = st.session_state.chat_started["user"] or not dsp_code
    
    if st.button("Start Screening", disabled=start_button_disabled, key="start_user_chat") or dsp_code_changed:
        # Update DSP code
        st.session_state.dsp_code = dsp_code
        # Clear previous messages
        if "user" in st.session_state.messages:
            st.session_state.messages["user"] = []
        # Start new chat
        if start_chat("user", "driver-screening", dsp_code, st.session_state.user_session_id):
            st.rerun()
    
    # Reset button
    if st.button("Reset Chat", key="reset_user_chat"):
        st.session_state.chat_started["user"] = False
        st.session_state.last_dsp_code["user"] = ""
        if "user" in st.session_state.messages:
            st.session_state.messages["user"] = []
        st.rerun()
    
    # Display chat messages
    for message in get_chat_history("user"):
        with st.chat_message(message["role"]):
            st.write(message["content"])
    
    # Chat input (only show if chat has started)
    if st.session_state.chat_started["user"]:
        if prompt := st.chat_input("Type your response here...", key="user_input"):
            # Add user message to chat history
            add_message("user", "user", prompt)
            
            # Make API call with user message
            try:
                payload = {
                    "message": prompt,
                    "session_id": st.session_state.user_session_id
                }
                
                if dsp_code:
                    payload["dsp_code"] = dsp_code
                    
                response = requests.post(
                    "http://127.0.0.1:8000/driver-screening",
                    json=payload
                )
                
                if response.status_code == 200:
                    assistant_message = response.json()["response"]
                    add_message("user", "assistant", assistant_message)
                    st.rerun()
                else:
                    st.error(f"Error: {response.status_code}")
            except Exception as e:
                st.error(f"Error: {str(e)}")
    else:
        if not dsp_code:
            st.info("Please enter a DSP code to begin the interview")
        else:
            st.info("Click 'Start Screening' to begin the interview")

def admin_page():
    st.title("Company Admin Panel")
    st.subheader("Manage Screening Questions")
    
    # DSP code input (required for admin)
    dsp_code = st.text_input("DSP Code (Required)", value=st.session_state.dsp_code, key="admin_dsp_code")
    
    if not dsp_code:
        st.warning("Please enter a DSP Code to manage questions")
        return
    
    # Check if DSP code has changed and we need to restart chat
    dsp_code_changed = dsp_code != st.session_state.last_dsp_code["admin"] and dsp_code
    
    # Start chat button
    start_button_disabled = st.session_state.chat_started["admin"]
    
    if st.button("Start Admin Session", disabled=start_button_disabled, key="start_admin_chat") or dsp_code_changed:
        # Update DSP code
        st.session_state.dsp_code = dsp_code
        # Clear previous messages
        if "admin" in st.session_state.messages:
            st.session_state.messages["admin"] = []
        # Start new chat
        if start_chat("admin", "company-admin", dsp_code, st.session_state.admin_session_id):
            st.rerun()
    
    # Reset button
    if st.button("Reset Chat", key="reset_admin_chat"):
        st.session_state.chat_started["admin"] = False
        st.session_state.last_dsp_code["admin"] = ""
        if "admin" in st.session_state.messages:
            st.session_state.messages["admin"] = []
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
    for message in get_chat_history("admin"):
        with st.chat_message(message["role"]):
            st.write(message["content"])
    
    # Chat input (only show if chat has started)
    if st.session_state.chat_started["admin"]:
        if prompt := st.chat_input("Type your command here...", key="admin_input"):
            # Add user message to chat history
            add_message("admin", "user", prompt)
            
            # Make API call with admin message
            try:
                response = requests.post(
                    "http://127.0.0.1:8000/company-admin",
                    json={
                        "message": prompt,
                        "session_id": st.session_state.admin_session_id,
                        "dsp_code": dsp_code
                    }
                )
                
                if response.status_code == 200:
                    assistant_message = response.json()["response"]
                    add_message("admin", "assistant", assistant_message)
                    st.rerun()
                else:
                    st.error(f"Error: {response.status_code}")
            except Exception as e:
                st.error(f"Error: {str(e)}")
    else:
        st.info("Click 'Start Admin Session' to begin managing questions")

def main():
    # Set page config
    st.set_page_config(
        page_title="Lokiteck Driver Screening",
        page_icon="🚚",
        layout="wide"
    )
    
    # Initialize session state
    initialize_session_state()
    
    # Sidebar navigation
    st.sidebar.title("Navigation")
    page = st.sidebar.radio("Select Page", ["User", "Admin"], index=0 if st.session_state.current_page == "User" else 1)
    
    # Update current page in session state
    if page != st.session_state.current_page:
        st.session_state.current_page = page
        st.rerun()
    
    # Display session information
    st.sidebar.divider()
    st.sidebar.subheader("Session Info")
    st.sidebar.text(f"User Session ID: {st.session_state.user_session_id}")
    st.sidebar.text(f"Admin Session ID: {st.session_state.admin_session_id}")
    
    if st.sidebar.button("Generate New Session IDs"):
        st.session_state.user_session_id = str(uuid.uuid4())
        st.session_state.admin_session_id = str(uuid.uuid4())
        st.session_state.messages = {}
        st.session_state.chat_started = {"user": False, "admin": False}
        st.session_state.last_company_id = {"user": "", "admin": ""}
        st.rerun()
    
    # Display selected page
    if page == "User":
        user_page()
    else:
        admin_page()

if __name__ == "__main__":
    main()