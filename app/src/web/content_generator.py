import os
import sys
import uuid
import requests
import json

# Add the project root directory to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
sys.path.append(project_root)

import streamlit as st
from app.src.core.config import get_settings
from dotenv import load_dotenv

# Predefined content types
CONTENT_TYPES = [
    "SMS",  # Default first option
    "Email",
    "Social Media Post",
    "Formal Letter",
    "Newsletter",
    "Announcement"
]

def initialize_session_state():
    """Initialize session state variables"""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "session_id" not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())
    if "user_info_submitted" not in st.session_state:
        st.session_state.user_info_submitted = False
    if "name" not in st.session_state:
        st.session_state.name = ""
    if "company" not in st.session_state:
        st.session_state.company = ""
    if "subject" not in st.session_state:
        st.session_state.subject = "SMS"  # Default to SMS
    if "content_type_changed" not in st.session_state:
        st.session_state.content_type_changed = False
    if "previous_content_type" not in st.session_state:
        st.session_state.previous_content_type = ""

def generate_content(message, session_id, name=None, company=None, subject=None, content_type_changed=False, previous_content_type=""):
    """
    Generate content using the external API
    
    Args:
        message (str): The message to process
        session_id (str): The session ID
        name (str, optional): User's name
        company (str, optional): User's company
        subject (str, optional): Content subject
        content_type_changed (bool): Whether the content type has changed
        previous_content_type (str): The previous content type
        
    Returns:
        str: The generated content
    """
    try:
        # If content type has changed, append that information to the message
        modified_message = message
        if content_type_changed and previous_content_type:
            if message:
                modified_message = f"[Content type changed from {previous_content_type} to {subject}] {message}"
            else:
                modified_message = f"[Content type changed from {previous_content_type} to {subject}]"
        
        # Always include all required fields in the payload
        payload = {
            "message": modified_message,
            "session_id": session_id,
            "name": name if name else st.session_state.name,
            "company": company if company else st.session_state.company,
            "subject": subject if subject else st.session_state.subject
        }
            
        response = requests.post(
            'https://lokitech-demo-api.demotrt.com/chat',
            headers={
                'accept': 'application/json',
                'Content-Type': 'application/json'
            },
            json=payload
        )
        
        if response.status_code == 200:
            response_data = response.json()
            if "response" in response_data:
                return response_data["response"]
            else:
                return json.dumps(response_data, indent=2)
        else:
            return f"Error: API returned status code {response.status_code} - {response.text}"
    except Exception as e:
        return f"Error: Failed to connect to API - {str(e)}"

def main():
    # Load environment variables
    load_dotenv()
    
    # Page configuration
    st.set_page_config(
        page_title="Content Generator",
        page_icon="📝",
        layout="wide"
    )
    
    # Initialize session state
    initialize_session_state()
    
    # Header
    st.title("AI Content Generator")
    st.markdown("Generate professional content for various purposes.")
    
    # Sidebar with user information form and content type selector
    with st.sidebar:
        st.header("User Information")
        
        if not st.session_state.user_info_submitted:
            with st.form("user_info_form"):
                name = st.text_input("Your Name", value=st.session_state.name)
                company = st.text_input("Company Name", value=st.session_state.company)
                subject = st.selectbox("Content Type", CONTENT_TYPES, index=0)  # Default to SMS (first option)
                
                submit_button = st.form_submit_button("Start Session")
                
                if submit_button:
                    st.session_state.name = name
                    st.session_state.company = company
                    st.session_state.subject = subject
                    st.session_state.previous_content_type = subject
                    st.session_state.user_info_submitted = True
                    
                    # Make initial API call with user info
                    initial_message = ""  # Empty message for first call
                    response = generate_content(
                        initial_message,
                        st.session_state.session_id,
                        name,
                        company,
                        subject
                    )
                    
                    # Add assistant's response to chat history
                    st.session_state.messages.append({"role": "assistant", "content": response})
                    st.rerun()
        else:
            # Display current session info
            st.info(f"""
            **Current Session**
            - Name: {st.session_state.name}
            - Company: {st.session_state.company}
            - Session ID: {st.session_state.session_id[:8]}...
            """)
            
            # Allow changing content type anytime
            st.subheader("Content Settings")
            new_content_type = st.selectbox(
                "Content Type", 
                CONTENT_TYPES, 
                index=CONTENT_TYPES.index(st.session_state.subject) if st.session_state.subject in CONTENT_TYPES else 0
            )
            
            # Update content type if changed
            if new_content_type != st.session_state.subject:
                st.session_state.previous_content_type = st.session_state.subject
                st.session_state.subject = new_content_type
                st.session_state.content_type_changed = True
                
                # Make API call to notify about content type change
                change_message = f"[Content type changed to {new_content_type}]"
                response = generate_content(
                    "",  # Empty message
                    st.session_state.session_id,
                    st.session_state.name,
                    st.session_state.company,
                    new_content_type,
                    True,
                    st.session_state.previous_content_type
                )
                
                # Add system message about content type change
                st.session_state.messages.append({"role": "system", "content": f"Content type changed to: **{new_content_type}**"})
                
                # Add assistant's response to chat history
                st.session_state.messages.append({"role": "assistant", "content": response})
                
                st.rerun()
            else:
                st.session_state.content_type_changed = False
            
            st.divider()
            
            # Option to reset session
            if st.button("Start New Session"):
                st.session_state.user_info_submitted = False
                st.session_state.session_id = str(uuid.uuid4())
                st.session_state.messages = []
                st.session_state.content_type_changed = False
                st.session_state.previous_content_type = ""
                st.rerun()
            
            # Clear chat button
            if st.button("Clear Chat"):
                st.session_state.messages = []
                st.session_state.content_type_changed = False
                st.rerun()
    
    # Display current content type in main area
    if st.session_state.user_info_submitted:
        st.caption(f"Current content type: **{st.session_state.subject}**")
    
    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])
    
    # Chat input (only show if user info has been submitted)
    if st.session_state.user_info_submitted:
        if prompt := st.chat_input("Type your content request here..."):
            # Add user message to chat history
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.write(prompt)
                
            # Generate and display assistant response
            with st.chat_message("assistant"):
                with st.spinner("Generating content..."):
                    try:
                        # For subsequent messages, we still need to send all required fields
                        # Check if content type has changed recently
                        content_type_changed = st.session_state.content_type_changed
                        previous_content_type = st.session_state.previous_content_type if content_type_changed else ""
                        
                        # Reset the content_type_changed flag after using it
                        st.session_state.content_type_changed = False
                        
                        response = generate_content(
                            prompt, 
                            st.session_state.session_id,
                            content_type_changed=content_type_changed,
                            previous_content_type=previous_content_type
                        )
                        st.write(response)
                        st.session_state.messages.append({"role": "assistant", "content": response})
                    except Exception as e:
                        error_message = f"An error occurred: {str(e)}"
                        st.error(error_message)
                        st.session_state.messages.append({"role": "assistant", "content": error_message})
    else:
        # Prompt to fill out user info
        st.info("Please fill out your information in the sidebar to start generating content.")

if __name__ == "__main__":
    main()