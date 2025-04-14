import os
import sys
import requests
import json

# Add the project root directory to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
sys.path.append(project_root)

import streamlit as st
from app.src.core.config import get_settings

# Replace the load_dotenv() and os.getenv() calls with:
settings = get_settings()
api_key = settings.OPENAI_API_KEY

import streamlit as st
import os
from dotenv import load_dotenv

# Predefined questions based on the analyzer prompts
PREDEFINED_QUESTIONS = [
    "John's FICO score is 790",
    "Sarah had 2 speeding events yesterday",
    "Michael's seatbelt compliance is at 95%",
    "David's CDR is at 97.5%",
    "Emma had 1 sign violation this week",
    "Robert's DVIC duration was 75 seconds",
    "Jessica's POD acceptance rate is 97%",
    "Thomas had 3 harsh braking events",
    "Lisa's customer delivery feedback is at 96%",
    "Kevin's following distance rate shows 2 violations",
]


def initialize_session_state():
    if "messages" not in st.session_state:
        st.session_state.messages = []


def analyze_dsp_performance(messages):
    """
    Analyze DSP performance using the external API

    Args:
        messages (str): The messages to analyze

    Returns:
        str: The analysis result
    """
    try:
        response = requests.post(
            "https://lokitech-demo-api.demotrt.com/analyze-performance",
            headers={"accept": "application/json", "Content-Type": "application/json"},
            json={"messages": messages},
        )

        if response.status_code == 200:
            # Extract the analysis from the JSON response
            response_data = response.json()

            # Check if response contains analysis field
            if isinstance(response_data, dict) and "analysis" in response_data:
                return response_data["analysis"]
            elif isinstance(response_data, str):
                return response_data
            else:
                # Return the formatted JSON as a fallback
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
        page_title="DSP Driver Performance Analyzer", page_icon="🚚", layout="wide"
    )

    # Initialize session state
    initialize_session_state()

    # Header
    st.title("DSP Driver Performance Analyzer")
    st.markdown("Chat with our AI to analyze driver performance data.")

    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])

    # Predefined questions section
    with st.sidebar:
        st.subheader("Example Performance Queries")
        st.markdown("Click on any example to analyze:")

        for question in PREDEFINED_QUESTIONS:
            if st.button(question, key=f"btn_{question}"):
                # Add user message to chat history
                st.session_state.messages.append({"role": "user", "content": question})

                # Generate and display assistant response
                try:
                    analysis = analyze_dsp_performance(question)
                    st.session_state.messages.append(
                        {"role": "assistant", "content": analysis}
                    )
                    st.rerun()
                except Exception as e:
                    error_message = f"An error occurred: {str(e)}"
                    st.session_state.messages.append(
                        {"role": "assistant", "content": error_message}
                    )
                    st.rerun()

        # Add a clear chat button
        if st.button("Clear Chat"):
            st.session_state.messages = []
            st.rerun()

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
                    analysis = analyze_dsp_performance(prompt)
                    st.write(analysis)
                    st.session_state.messages.append(
                        {"role": "assistant", "content": analysis}
                    )
                except Exception as e:
                    error_message = f"An error occurred: {str(e)}"
                    st.error(error_message)
                    st.session_state.messages.append(
                        {"role": "assistant", "content": error_message}
                    )


if __name__ == "__main__":
    main()
