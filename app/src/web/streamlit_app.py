import os
import sys

# Add the project root directory to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
sys.path.append(project_root)

import streamlit as st
from app.src.core.analyzer import analyze_dsp_performance
from app.src.core.config import get_settings

# ... rest of the existing app.py code ...
# Replace the load_dotenv() and os.getenv() calls with:
settings = get_settings()
api_key = settings.OPENAI_API_KEY

import streamlit as st
# from dsp_scorecard_analyzer import analyze_dsp_performance
import os
from dotenv import load_dotenv

def initialize_session_state():
    if "messages" not in st.session_state:
        st.session_state.messages = []

def main():
    # Load environment variables
    load_dotenv()
    
    # Page configuration
    st.set_page_config(
        page_title="DSP Driver Performance Analyzer",
        page_icon="🚚",
        layout="wide"
    )
    
    # Initialize session state
    initialize_session_state()
    
    # Header
    st.title("DSP Driver Performance Analyzer")
    st.markdown("Chat with our AI to analyze driver performance data.")
    
    # Get API key from environment
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        st.error("Please set OPENAI_API_KEY in your environment variables")
        return
    
    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])
    
    # Chat input
    if prompt := st.chat_input("Enter driver performance data here..."):
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)
            
        # Generate and display assistant response
        with st.chat_message("assistant"):
            with st.spinner("Analyzing..."):
                try:
                    analysis = analyze_dsp_performance(api_key, prompt)
                    st.write(analysis)
                    st.session_state.messages.append({"role": "assistant", "content": analysis})
                except Exception as e:
                    error_message = f"An error occurred: {str(e)}"
                    st.error(error_message)
                    st.session_state.messages.append({"role": "assistant", "content": error_message})

    # Add a clear chat button
    if st.sidebar.button("Clear Chat"):
        st.session_state.messages = []
        st.rerun()

if __name__ == "__main__":
    main() 