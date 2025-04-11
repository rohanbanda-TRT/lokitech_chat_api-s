"""
Agent for generating structured coaching feedback with historical context.
"""

import os
import json
import logging
import pandas as pd
from typing import Dict, List, Optional, Any, Callable, Set
from datetime import datetime
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from langchain_core.tools import Tool, StructuredTool
from pydantic import BaseModel, Field
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.runnables import RunnablePassthrough
from dotenv import load_dotenv
from ..prompts.coaching_history import COACHING_HISTORY_PROMPT_TEMPLATE_STR
from ..utils.session_manager import get_session_manager

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
        self.session_manager = get_session_manager()
        
        # Get the list of employees
        self.employee_list = self._get_employee_list()
        
        # Create tools
        self.tools = [
            StructuredTool.from_function(
                func=self._list_severity_categories,
                name="list_severity_categories",
                description="List all severity categories available for a specific employee",
                return_direct=True,
            ),
            StructuredTool.from_function(
                func=self._get_employee_coaching,
                name="get_employee_coaching",
                description="Get coaching history for a specific employee and severity category",
                return_direct=False,
            )
        ]
        
        # Create the prompt template with employee list
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", COACHING_HISTORY_PROMPT_TEMPLATE_STR.format(employee_list=self.employee_list)),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])
        
        logger.info("Coaching Feedback Generator initialized successfully")
    
    def _load_coaching_data(self) -> Dict[str, Any]:
        """
        Load coaching history data from file.
        
        Returns:
            Dictionary of coaching history records, organized by employee if available
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
                return {"records": coaching_data}
            
            elif file_extension == '.json':
                # Load from JSON
                with open(self.coaching_data_path, 'r') as f:
                    coaching_data = json.load(f)
                
                # Check if the JSON is organized by employee or just a list of records
                if isinstance(coaching_data, list):
                    logger.info(f"Loaded {len(coaching_data)} coaching records from JSON file")
                    return {"records": coaching_data}
                elif isinstance(coaching_data, dict):
                    # Count total records across all employees
                    total_records = sum(len(records) for employee, records in coaching_data.items())
                    logger.info(f"Loaded {total_records} coaching records for {len(coaching_data)} employees from JSON file")
                    return coaching_data
                else:
                    logger.error("Unexpected JSON format")
                    raise ValueError("Unexpected JSON format. Expected a list of records or a dictionary of employees to records.")
            
            else:
                logger.error(f"Unsupported file format: {file_extension}")
                raise ValueError(f"Unsupported file format: {file_extension}. Please provide an Excel (.xlsx) or JSON (.json) file.")
                
        except Exception as e:
            logger.error(f"Error loading coaching data: {str(e)}")
            raise
    
    def _get_employee_list(self) -> str:
        """
        Get formatted list of employees from coaching history.
        
        Returns:
            Formatted string with numbered list of employees
        """
        try:
            if isinstance(self.coaching_history, dict) and not "records" in self.coaching_history:
                employees = sorted(list(self.coaching_history.keys()))
                if employees:
                    return "\n".join(f"{i+1}. {name}" for i, name in enumerate(employees))
                else:
                    return "No employees found in the coaching history database."
            else:
                return "Coaching history data is not organized by employee."
        except Exception as e:
            logger.error(f"Error getting employee list: {str(e)}")
            return f"Error getting employee list: {str(e)}"
    
    def _list_severity_categories(self, employee: str) -> str:
        """
        List all severity categories available for a specific employee in the coaching history database.
        
        Args:
            employee: Employee name
            
        Returns:
            Formatted string with all severity categories for the specified employee
        """
        try:
            categories = set()
            
            # Check if data is organized by employee
            if isinstance(self.coaching_history, dict) and employee in self.coaching_history:
                # Extract categories from employee's records
                employee_records = self.coaching_history[employee]
                for record in employee_records:
                    if "Severity" in record and record["Severity"]:
                        categories.add(record["Severity"])
                
                # Format the output
                if categories:
                    categories_list = sorted(list(categories))
                    # Format each category on a new line with numbered list for better visibility
                    formatted_categories = "\n".join([f"{i+1}. **{category}**" for i, category in enumerate(categories_list)])
                    return f"""
## Available Severity Categories for {employee}:

{formatted_categories}

Please select a severity category from the list above for this coaching feedback.
"""
                else:
                    return f"No severity categories found for employee '{employee}' in the coaching history database."
            else:
                return f"Employee '{employee}' not found in the coaching history database."
        except Exception as e:
            logger.error(f"Error listing severity categories: {str(e)}")
            return f"Error listing severity categories: {str(e)}"
    
    def _get_employee_coaching(self, employee: str, severity: str) -> str:
        """
        Get coaching history for a specific employee and severity category.
        
        Args:
            employee: Employee name
            severity: Severity category
            
        Returns:
            Formatted string with coaching history for the employee and severity
        """
        try:
            logger.info(f"Retrieving coaching for employee: {employee}, severity: {severity}")
            
            # Check if data is organized by employee
            if isinstance(self.coaching_history, dict) and employee in self.coaching_history:
                # Find relevant records for this employee and severity
                relevant_records = []
                employee_records = self.coaching_history[employee]
                
                for record in employee_records:
                    record_severity = str(record.get('Severity', '')).lower()
                    if severity.lower() in record_severity:
                        relevant_records.append(record)
                
                logger.info(f"Found {len(relevant_records)} relevant coaching records for employee: {employee}, severity: {severity}")
                
                # Format the results
                if not relevant_records:
                    return f"No coaching history found for employee '{employee}' with severity '{severity}'."
                
                formatted_records = []
                
                for i, record in enumerate(relevant_records, 1):
                    date = record.get('Date', 'Unknown Date')
                    severity_value = record.get('Severity', 'Unknown Issue')
                    statement = record.get('Statement_of_Problem', 'No statement provided')
                    prior = record.get('Prior_Discussion', 'No prior discussion')
                    action = record.get('Corrective_Action', 'No corrective action specified')
                    
                    entry = f"Record {i}:\n"
                    entry += f"Date: {date}\n"
                    entry += f"Issue: {severity_value}\n"
                    entry += f"Improvement Discussion: {statement}\n"
                    entry += f"Prior Discussion: {prior}\n"
                    entry += f"Corrective Action: {action}\n"
                    
                    formatted_records.append(entry)
                
                return f"Coaching history for {employee} - {severity}:\n\n" + "\n\n".join(formatted_records)
            else:
                return f"Employee '{employee}' not found in the coaching history database."
        except Exception as e:
            logger.error(f"Error retrieving employee coaching: {str(e)}")
            return f"Error retrieving employee coaching: {str(e)}"
    
    def _is_coaching_request(self, query: str) -> bool:
        """
        Determine if the query is a coaching feedback request or normal conversation.
        
        Args:
            query: The user's query
            
        Returns:
            True if the query is a coaching request, False if it's normal conversation
        """
        try:
            # Check if this is a first-time user (empty or greeting query)
            if not query or query.strip() == "" or any(greeting in query.lower() for greeting in ["hello", "hi", "hey", "greetings"]):
                return True  # Treat as coaching request to start the guided flow
                
            # Keywords that indicate a coaching request
            coaching_keywords = [
                "coach", "feedback", "employee", "driver", "violation", "warning",
                "performance", "issue", "problem", "citation", "infraction",
                "speeding", "braking", "severity", "mentor", "netradyne"
            ]
            
            # Check if any coaching keywords are in the query
            for keyword in coaching_keywords:
                if keyword in query.lower():
                    return True
                    
            return False
            
        except Exception as e:
            logger.error(f"Error determining if query is a coaching request: {str(e)}")
            return True  # Default to treating as coaching request
            
    def generate_feedback(self, query: str, session_id: str = None) -> str:
        """
        Generate coaching feedback based on the query.
        
        Args:
            query: The coaching query/reason (e.g., "Moises was cited for a speeding violation")
            session_id: Optional session ID for maintaining conversation history
            
        Returns:
            Structured coaching feedback
        """
        try:
            logger.info(f"Generating feedback for query: {query}")
            
            # Generate a unique session ID if not provided
            if not session_id:
                import time
                timestamp = int(time.time())
                session_id = f"COACHING-{timestamp}"
                logger.info(f"Generated new session ID: {session_id}")
            
            # Check if this is a new conversation
            is_new_conversation = not self.session_manager.session_exists(session_id)
            
            # Get or create the agent executor using the session manager
            executor = self.session_manager.get_or_create_session(
                session_id=session_id,
                llm=self.llm,
                tools=self.tools,
                prompt=self.prompt,
                verbose=True
            )
            
            # First, determine if this is a coaching request or normal conversation
            is_coaching_request = self._is_coaching_request(query)
            
            # Prepare the input for the agent
            if is_coaching_request:
                # For a new conversation, we'll let the agent handle the introduction
                # and guided flow based on the prompt template
                input_text = query if query.strip() else "Hello"
            else:
                # For normal conversation, just pass the query directly
                input_text = query
            
            # Run the agent executor
            result = executor.invoke({"input": input_text})
            
            logger.info("Successfully generated feedback")
            return result["output"]
            
        except Exception as e:
            error_msg = f"Error generating feedback: {str(e)}"
            logger.error(error_msg)
            return f"An error occurred while generating feedback: {str(e)}"


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
    
    # Path to coaching data - prioritize the combined JSON file
    coaching_data_path = os.path.join(os.getcwd(), "json_output", "combined_coaching_history.json")
    if not os.path.exists(coaching_data_path):
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
