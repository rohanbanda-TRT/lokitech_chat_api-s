"""
Streamlit web application for the Coaching History Analyzer
"""

import os
import json
import streamlit as st
from dotenv import load_dotenv
from app.src.agents.coaching_history_analyzer import CoachingHistoryAnalyzer

# Load environment variables
load_dotenv()

def initialize_analyzer():
    """
    Initialize the Coaching History Analyzer
    """
    # Get API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        st.error("OpenAI API key not found. Please set the OPENAI_API_KEY environment variable.")
        st.stop()
    
    # Path to coaching data
    coaching_data_path = os.path.join(os.getcwd(), "coaching_history.json")
    if not os.path.exists(coaching_data_path):
        coaching_data_path = os.path.join(os.getcwd(), "Coaching Details.xlsx")
    
    if not os.path.exists(coaching_data_path):
        st.error(f"Coaching data file not found at {coaching_data_path}")
        st.stop()
    
    # Initialize the analyzer
    return CoachingHistoryAnalyzer(api_key, coaching_data_path)

def main():
    """
    Main function for the Streamlit web application
    """
    # Set page config
    st.set_page_config(
        page_title="DSP Coaching History Analyzer",
        page_icon="🚚",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Page title
    st.title("DSP Coaching History Analyzer")
    st.markdown("Analyze driver coaching history and generate structured feedback")
    
    # Initialize analyzer
    analyzer = initialize_analyzer()
    
    # Sidebar for coaching categories
    st.sidebar.header("Coaching Categories")
    
    # Get unique categories from the coaching history
    categories = set()
    for record in analyzer.coaching_history:
        if 'Severity' in record and record['Severity']:
            categories.add(record['Severity'])
    
    # Sort categories alphabetically
    categories = sorted(list(categories))
    
    # Employee information
    st.sidebar.header("Employee Information")
    employee_name = st.sidebar.text_input("Employee Name", "Moises")
    
    # Category selection
    selected_category = st.sidebar.selectbox(
        "Select Coaching Category",
        options=categories,
        index=0 if categories else None
    )
    
    # Additional reason
    coaching_reason = st.sidebar.text_area(
        "Additional Details (Optional)",
        f"{employee_name} was cited for a {selected_category.lower() if selected_category else ''} issue while operating a company vehicle."
    )
    
    # Main content area
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.header("Coaching History")
        
        if selected_category:
            # Get relevant coaching history
            relevant_history = analyzer._get_relevant_coaching_history(selected_category)
            
            if relevant_history:
                for i, record in enumerate(relevant_history, 1):
                    with st.expander(f"Record {i}: {record.get('Date', 'Unknown Date')} - {record.get('Severity', 'Unknown Issue')}"):
                        st.write(f"**Statement of Problem:** {record.get('Statement_of_Problem', 'No statement provided')}")
                        st.write(f"**Prior Discussion:** {record.get('Prior_Discussion', 'No prior discussion')}")
                        st.write(f"**Corrective Action:** {record.get('Corrective_Action', 'No corrective action specified')}")
            else:
                st.info(f"No coaching history found for category: {selected_category}")
    
    with col2:
        st.header("Analysis Results")
        
        # Generate button
        if st.button("Generate Coaching Analysis", type="primary"):
            with st.spinner("Analyzing coaching history..."):
                if not selected_category:
                    st.error("Please select a coaching category")
                else:
                    # Get analysis
                    result = analyzer.analyze_coaching_history(
                        employee_name,
                        selected_category,
                        coaching_reason
                    )
                    
                    # Display result
                    st.markdown(result)
                    
                    # Option to download as text
                    st.download_button(
                        label="Download Analysis",
                        data=result,
                        file_name=f"{employee_name}_{selected_category}_analysis.txt",
                        mime="text/plain"
                    )

if __name__ == "__main__":
    main()
