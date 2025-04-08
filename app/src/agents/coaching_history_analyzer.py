"""
Agent for generating structured coaching feedback with historical context.
"""

import os
import json
import logging
import pandas as pd
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from langchain_core.tools import Tool
from pydantic import BaseModel, Field
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain_core.runnables import RunnablePassthrough
from dotenv import load_dotenv
from ..prompts.coaching_history import COACHING_HISTORY_PROMPT_TEMPLATE_STR

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class CoachingFeedbackGenerator:
    """
    Agent for generating structured coaching feedback with historical context.
    """
    
    def __init__(self, api_key: str, coaching_data_path: str):
        """
        Initialize the Coaching Feedback Generator.
        
        Args:
            api_key: OpenAI API key
            coaching_data_path: Path to the coaching history data file (Excel or JSON)
        """
        self.api_key = api_key
        self.coaching_data_path = coaching_data_path
        self.coaching_history = self._load_coaching_data()
        self.llm = ChatOpenAI(temperature=0.2, api_key=api_key, verbose=True)
        
        # Create the prompt template
        self.prompt = ChatPromptTemplate.from_template(COACHING_HISTORY_PROMPT_TEMPLATE_STR)
        
        # Create the chain
        self.chain = (
            {"query": RunnablePassthrough(), "coaching_history": self._get_coaching_history}
            | self.prompt
            | self.llm
            | StrOutputParser()
        )
        
        logger.info("Coaching Feedback Generator initialized successfully")
    
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
    
    def _get_coaching_history(self, query: str) -> str:
        """
        Extract category from query and retrieve relevant coaching history.
        
        Args:
            query: The coaching query
            
        Returns:
            Formatted string with coaching history
        """
        try:
            # Use a simple LLM call to extract the category
            category_prompt = ChatPromptTemplate.from_template(
                """Extract the coaching category from the following query. 
                Return only the category name, nothing else.
                
                Common categories:
                - Speeding Violations
                - Hard Braking
                - Following Distance
                - Traffic Light Violation
                - CDF Score
                - Sign Violation
                - Driver Distraction
                - Total Breaches
                
                Query: {query}
                
                Category:"""
            )
            
            category_chain = category_prompt | self.llm | StrOutputParser()
            category = category_chain.invoke({"query": query}).lower().strip()
            
            logger.info(f"Extracted category from query: {category}")
            
            # Find relevant records
            relevant_records = []
            
            for record in self.coaching_history:
                record_category = str(record.get('Category', '')).lower()
                record_severity = str(record.get('Severity', '')).lower()
                
                if category in record_category or category in record_severity:
                    relevant_records.append(record)
            
            logger.info(f"Found {len(relevant_records)} relevant coaching records for category: {category}")
            
            # Format the results
            if not relevant_records:
                return f"No coaching history found for category '{category}'."
            
            formatted_records = []
            
            for i, record in enumerate(relevant_records, 1):
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
                
                formatted_records.append(entry)
            
            return "\n\n".join(formatted_records)
            
        except Exception as e:
            logger.error(f"Error retrieving coaching history: {str(e)}")
            return f"Error retrieving coaching history: {str(e)}"
    
    def generate_feedback(self, query: str) -> str:
        """
        Generate coaching feedback based on the query.
        
        Args:
            query: The coaching query/reason (e.g., "Moises was cited for a speeding violation")
            
        Returns:
            Structured coaching feedback
        """
        try:
            logger.info(f"Generating coaching feedback for query: {query}")
            
            # Run the chain
            result = self.chain.invoke(query)
            
            logger.info("Successfully generated coaching feedback")
            return result
            
        except Exception as e:
            error_msg = f"Error generating coaching feedback: {str(e)}"
            logger.error(error_msg)
            return f"An error occurred while generating coaching feedback: {str(e)}"


def main():
    """
    Main function to demonstrate the usage of the CoachingFeedbackGenerator.
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
    generator = CoachingFeedbackGenerator(api_key, coaching_data_path)
    
    # Sample query
    query = "Moises was cited for a speeding violation while operating a company vehicle."
    
    # Generate coaching feedback
    result = generator.generate_feedback(query)
    
    # Print results
    print("\nCoaching Feedback:")
    print("---------------------------")
    print(result)


if __name__ == "__main__":
    main()
