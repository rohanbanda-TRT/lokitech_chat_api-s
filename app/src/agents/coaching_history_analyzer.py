"""
Agent for analyzing driver coaching history and providing structured feedback.
"""

import os
import json
import logging
import pandas as pd
from typing import Dict, List, Optional, Any
from datetime import datetime
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from dotenv import load_dotenv
from ..prompts.coaching_history import COACHING_HISTORY_PROMPT_TEMPLATE

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class CoachingHistoryAnalyzer:
    """
    Agent for analyzing delivery driver coaching history and providing structured feedback.
    """
    
    def __init__(self, api_key: str, coaching_data_path: str):
        """
        Initialize the Coaching History Analyzer Agent.
        
        Args:
            api_key: OpenAI API key
            coaching_data_path: Path to the coaching history data file (Excel or JSON)
        """
        self.api_key = api_key
        self.coaching_data_path = coaching_data_path
        self.coaching_history = self._load_coaching_data()
        self.llm = ChatOpenAI(temperature=0.2, api_key=api_key)
        
        # Create prompt
        self.prompt = PromptTemplate(
            input_variables=["employee_name", "coaching_category", "coaching_reason", "coaching_history"],
            template=COACHING_HISTORY_PROMPT_TEMPLATE
        )
        
        # Create chain using LCEL (LangChain Expression Language)
        self.chain = self.prompt | self.llm | StrOutputParser()
        
        logger.info("Coaching History Analyzer initialized successfully")
    
    def _load_coaching_data(self) -> List[Dict[str, Any]]:
        """
        Load coaching history data from file.
        
        Returns:
            List of coaching history records
        """
        try:
            file_extension = os.path.splitext(self.coaching_data_path)[1].lower()
            
            if file_extension == '.xlsx':
                # Load from Excel
                df = pd.read_excel(self.coaching_data_path, header=1)
                # Rename columns based on the first row
                df.columns = ['Status', 'Date', 'Category', 'Subcategory', 'Severity', 
                            'Statement_of_Problem', 'Prior_Discussion', 'Corrective_Action', 'Uploaded_Pictures']
                coaching_data = df.to_dict(orient='records')
                logger.info(f"Loaded {len(coaching_data)} coaching records from Excel file")
                return coaching_data
            
            elif file_extension == '.json':
                # Load from JSON
                with open(self.coaching_data_path, 'r') as f:
                    coaching_data = json.load(f)
                logger.info(f"Loaded {len(coaching_data)} coaching records from JSON file")
                return coaching_data
            
            else:
                logger.error(f"Unsupported file format: {file_extension}")
                raise ValueError(f"Unsupported file format: {file_extension}. Please provide an Excel (.xlsx) or JSON (.json) file.")
                
        except Exception as e:
            logger.error(f"Error loading coaching data: {str(e)}")
            raise
    
    def _get_relevant_coaching_history(self, category: str) -> List[Dict[str, Any]]:
        """
        Get coaching history records relevant to the specified category.
        
        Args:
            category: The coaching category to filter by
            
        Returns:
            List of relevant coaching history records
        """
        try:
            # Filter coaching history by category or severity
            relevant_history = []
            
            for record in self.coaching_history:
                # Check if category matches either the Category field or Severity field
                if (str(record.get('Category', '')).lower() == category.lower() or
                    str(record.get('Severity', '')).lower() == category.lower()):
                    relevant_history.append(record)
            
            logger.info(f"Found {len(relevant_history)} relevant coaching records for category: {category}")
            return relevant_history
            
        except Exception as e:
            logger.error(f"Error getting relevant coaching history: {str(e)}")
            return []
    
    def _format_coaching_history(self, history: List[Dict[str, Any]]) -> str:
        """
        Format coaching history records into a readable string.
        
        Args:
            history: List of coaching history records
            
        Returns:
            Formatted coaching history string
        """
        if not history:
            return "No previous coaching history found for this category."
        
        formatted_history = []
        
        for i, record in enumerate(history, 1):
            date = record.get('Date', 'Unknown Date')
            severity = record.get('Severity', 'Unknown Issue')
            statement = record.get('Statement_of_Problem', 'No statement provided')
            prior = record.get('Prior_Discussion', 'No prior discussion')
            action = record.get('Corrective_Action', 'No corrective action specified')
            
            entry = f"Record {i}:\n"
            entry += f"Date: {date}\n"
            entry += f"Issue: {severity}\n"
            entry += f"Statement of Problem: {statement}\n"
            entry += f"Prior Discussion: {prior}\n"
            entry += f"Corrective Action: {action}\n"
            
            formatted_history.append(entry)
        
        return "\n\n".join(formatted_history)
    
    def analyze_coaching_history(self, employee_name: str, coaching_category: str, coaching_reason: str = "") -> str:
        """
        Analyze coaching history and provide structured feedback.
        
        Args:
            employee_name: Name of the employee
            coaching_category: Category of coaching (e.g., "Speeding Violations")
            coaching_reason: Additional details about the coaching reason
            
        Returns:
            Formatted feedback with statement of problem, prior discussion, and corrective action
        """
        try:
            logger.info(f"Analyzing coaching history for {employee_name} - Category: {coaching_category}")
            
            # Get relevant coaching history
            relevant_history = self._get_relevant_coaching_history(coaching_category)
            
            # Format coaching history
            formatted_history = self._format_coaching_history(relevant_history)
            
            # Run chain with properly formatted input
            response = self.chain.invoke({
                "employee_name": employee_name,
                "coaching_category": coaching_category,
                "coaching_reason": coaching_reason,
                "coaching_history": formatted_history
            })
            
            logger.info(f"Successfully generated coaching analysis for {employee_name}")
            return response
            
        except Exception as e:
            error_msg = f"Error analyzing coaching history: {str(e)}"
            logger.error(error_msg)
            return f"An error occurred while analyzing coaching history: {str(e)}"


def main():
    """
    Main function to demonstrate the usage of the CoachingHistoryAnalyzer.
    """
    # Load environment variables
    load_dotenv()
    
    # Get API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("Please set OPENAI_API_KEY environment variable")
    
    # Path to coaching data
    coaching_data_path = os.path.join(os.getcwd(), "coaching_history.json")
    if not os.path.exists(coaching_data_path):
        coaching_data_path = os.path.join(os.getcwd(), "Coaching Details.xlsx")
    
    # Initialize the agent
    analyzer = CoachingHistoryAnalyzer(api_key, coaching_data_path)
    
    # Sample query
    employee_name = "Moises"
    coaching_category = "Speeding Violations"
    coaching_reason = "Moises was cited for a speeding violation while operating a company vehicle."
    
    # Analyze the coaching history
    result = analyzer.analyze_coaching_history(employee_name, coaching_category, coaching_reason)
    
    # Print results
    print("\nCoaching History Analysis:")
    print("---------------------------")
    print(result)


if __name__ == "__main__":
    main()
