"""
Streamlit app for generating coaching feedback with historical context
"""

import streamlit as st
import requests
import json
import os
import uuid
from typing import Dict, Any

# API URL
API_URL = os.getenv("API_URL", "http://localhost:8000")

# Page configuration
st.set_page_config(
    page_title="Coaching Feedback Generator",
    page_icon="🚚",
    layout="wide"
)

# Initialize session state variables
if 'session_id' not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if 'conversation_started' not in st.session_state:
    st.session_state.conversation_started = False
if 'messages' not in st.session_state:
    st.session_state.messages = []

def generate_coaching_feedback(query: str, session_id: str) -> Dict[str, Any]:
    """
    Generate coaching feedback by calling the API
    
    Args:
        query: Coaching query/reason
        session_id: Session ID for maintaining conversation history
        
    Returns:
        API response as dictionary
    """
    try:
        # Prepare request data
        request_data = {
            "query": query,
            "session_id": session_id
        }
        
        # Make API request
        response = requests.post(
            f"{API_URL}/coaching-feedback",
            json=request_data
        )
        
        # Check response
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Error: {response.status_code} - {response.text}")
            return {"error": response.text}
            
    except Exception as e:
        st.error(f"Error: {str(e)}")
        return {"error": str(e)}

def main():
    """
    Main function for the Streamlit app
    """
    # Header
    st.title("📋 Coaching Feedback Generator")
    st.markdown("Generate structured coaching feedback with historical context")
    
    # Sidebar
    st.sidebar.header("About")
    st.sidebar.info(
        "This application generates structured coaching feedback for delivery drivers "
        "based on their coaching history. It provides a statement of the problem, "
        "prior discussion points, and recommended corrective actions."
    )
    
    st.sidebar.header("Session Information")
    st.sidebar.text(f"Session ID: {st.session_state.session_id}")
    
    if st.sidebar.button("New Session"):
        st.session_state.session_id = str(uuid.uuid4())
        st.session_state.conversation_started = False
        st.session_state.messages = []
        st.sidebar.success(f"New session created: {st.session_state.session_id}")
        st.rerun()
    
    st.sidebar.header("Instructions")
    st.sidebar.markdown(
        "1. Enter your coaching query or question\n"
        "2. You can ask for employee-specific coaching feedback by mentioning the employee name\n"
        "3. You can also ask to list all available employees or severity categories\n"
        "4. The system will generate structured coaching feedback based on your query"
    )
    
    # Display chat history
    st.subheader("Coaching Assistant")
    
    # Initial greeting if conversation not started
    if not st.session_state.conversation_started:
        st.info("👋 Hello! I'm your coaching assistant. I can help you generate coaching feedback for employees based on their history. You can ask me about specific employees, severity categories, or enter a general coaching query.")
    
    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Chat input
    if prompt := st.chat_input("Enter your coaching query or question"):
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Generate response
        with st.chat_message("assistant"):
            with st.spinner("Generating response..."):
                # Call API
                result = generate_coaching_feedback(prompt, st.session_state.session_id)
                
                if "error" not in result:
                    feedback = result.get("feedback", "")
                    st.markdown(feedback)
                    
                    # Add assistant message to chat history
                    st.session_state.messages.append({"role": "assistant", "content": feedback})
                    st.session_state.conversation_started = True
                else:
                    st.error(f"Error: {result['error']}")
    
    # Example queries
    if not st.session_state.conversation_started:
        st.subheader("Example Queries")
        col1, col2 = st.columns(2)
        
        examples = [
            "Please list all available employees",
            "What severity categories are available?",
            "Get coaching history for employee John Smith with severity Critical",
            "John was cited for a hard braking violation while operating a company vehicle",
            "Maria was cited for not maintaining proper following distance during her route",
            "What kind of coaching feedback can you generate?"
        ]
        
        with col1:
            for i in range(0, len(examples), 2):
                if st.button(f"{examples[i]}", key=f"example_{i}"):
                    # Add user message to chat history
                    st.session_state.messages.append({"role": "user", "content": examples[i]})
                    
                    # Generate response
                    result = generate_coaching_feedback(examples[i], st.session_state.session_id)
                    
                    if "error" not in result:
                        feedback = result.get("feedback", "")
                        
                        # Add assistant message to chat history
                        st.session_state.messages.append({"role": "assistant", "content": feedback})
                        st.session_state.conversation_started = True
                    
                    st.rerun()
        
        with col2:
            for i in range(1, len(examples), 2):
                if st.button(f"{examples[i]}", key=f"example_{i}"):
                    # Add user message to chat history
                    st.session_state.messages.append({"role": "user", "content": examples[i]})
                    
                    # Generate response
                    result = generate_coaching_feedback(examples[i], st.session_state.session_id)
                    
                    if "error" not in result:
                        feedback = result.get("feedback", "")
                        
                        # Add assistant message to chat history
                        st.session_state.messages.append({"role": "assistant", "content": feedback})
                        st.session_state.conversation_started = True
                    
                    st.rerun()

if __name__ == "__main__":
    main()
