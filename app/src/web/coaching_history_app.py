"""
Streamlit app for generating coaching feedback with historical context
"""

import streamlit as st
import requests
import json
import os
from typing import Dict, Any

# API URL
API_URL = os.getenv("API_URL", "http://localhost:8000")

# Page configuration
st.set_page_config(
    page_title="Coaching Feedback Generator",
    page_icon="🚚",
    layout="wide"
)

def generate_coaching_feedback(query: str) -> Dict[str, Any]:
    """
    Generate coaching feedback by calling the API
    
    Args:
        query: Coaching query/reason
        
    Returns:
        API response as dictionary
    """
    try:
        # Prepare request data
        request_data = {
            "query": query
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
    
    st.sidebar.header("Instructions")
    st.sidebar.markdown(
        "1. Enter your coaching query\n"
        "2. The system will automatically identify the coaching category\n"
        "3. Click 'Generate Feedback' to get structured coaching feedback with historical context"
    )
    
    # Main content
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("Enter Coaching Query")
        
        # Coaching query
        query = st.text_area(
            "Coaching Query", 
            placeholder="e.g., Moises was cited for a speeding violation while operating a company vehicle.",
            height=150
        )
        
        # Example queries
        st.markdown("#### Example Queries")
        examples = [
            "John was cited for a hard braking violation while operating a company vehicle.",
            "Maria was cited for not maintaining proper following distance during her route.",
            "Carlos received feedback about his CDF score being below company standards.",
            "Alex was observed using his phone while driving, which is a driver distraction violation."
        ]
        
        for example in examples:
            if st.button(f"Use Example: {example[:50]}...", key=example):
                # Use this example
                st.session_state.query = example
                # Rerun to update the text area
                st.rerun()
        
        # Generate button
        if st.button("Generate Feedback", type="primary"):
            if not query:
                st.error("Please enter a coaching query")
            else:
                with st.spinner("Generating coaching feedback..."):
                    # Call API
                    result = generate_coaching_feedback(query=query)
                    
                    # Display results in the second column
                    if "error" not in result:
                        with col2:
                            st.subheader("Coaching Feedback")
                            st.markdown(result.get("feedback", "No feedback generated"))
                    
    with col2:
        st.subheader("Coaching Feedback")
        st.info("Enter your coaching query and click 'Generate Feedback' to see results here")

if __name__ == "__main__":
    main()
