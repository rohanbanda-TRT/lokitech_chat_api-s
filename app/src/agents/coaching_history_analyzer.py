"""
Agent for generating structured coaching feedback with historical context.
"""

import os
import json
import logging
import uuid
from typing import Dict, List, Optional, Any, TypedDict
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
from langchain_core.tools import StructuredTool
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from pydantic import BaseModel
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph.message import add_messages
from typing_extensions import Annotated
from ..prompts.coaching_history import COACHING_HISTORY_PROMPT_TEMPLATE_STR

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# Define the state schema for the coaching feedback generator
class CoachingFeedbackState(TypedDict):
    """State schema for the coaching feedback generator graph."""

    messages: Annotated[list[BaseMessage], add_messages]
    employee_name: Optional[str]
    severity_category: Optional[str]


class CoachingFeedbackGenerator:
    """
    Agent for generating structured coaching feedback with historical context using LangGraph.
    """

    def __init__(self, api_key: str = None):
        """
        Initialize the Coaching Feedback Generator with LangGraph.

        Args:
            api_key: OpenAI API key. If not provided, will try to get from environment.
        """
        # Get API key from environment if not provided
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "OpenAI API key is required. Please provide it or set OPENAI_API_KEY environment variable."
            )

        self.llm = ChatOpenAI(
            temperature=0.2, api_key=self.api_key, model="gpt-4o-mini"
        )
        self.memory = MemorySaver()

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
            ),
        ]

        # Create the prompt template (employee list will be added dynamically)
        self.prompt = None
        
        # Create the agent (will be initialized with each request)
        self.agent = None
        self.agent_executor = None

        # Build the graph
        self.graph = self._create_graph()
        logger.info("Coaching Feedback Generator initialized with LangGraph")

        self.coaching_details_data = None

    def _format_employee_list(self, driver_list: List[Dict[str, str]]) -> str:
        """
        Format the list of employees from the provided driver list.

        Args:
            driver_list: List of driver information dictionaries

        Returns:
            Formatted string with numbered list of employees including IDs
        """
        try:
            logger.info(f"Formatting employee list from driver_list: {driver_list}")
            
            if not driver_list:
                logger.warning("No driver_list provided or empty list")
                return "No employees provided in the request."
                
            # Extract employee names and IDs from the driver list
            employees = []
            for driver in driver_list:
                if "driverName" in driver:
                    name = driver["driverName"]
                    user_id = driver.get("userID", "No ID")
                    employees.append((name, user_id))
            
            logger.info(f"Extracted employee data: {employees}")
            
            if employees:
                formatted_list = "\n".join(f"{i+1}. {name} (ID: {user_id})" for i, (name, user_id) in enumerate(employees))
                logger.info(f"Formatted employee list: {formatted_list}")
                return formatted_list
            else:
                logger.warning("No valid employee names found in driver_list")
                return "No valid employee names found in the provided driver list."
                
        except Exception as e:
            logger.error(f"Error formatting employee list: {str(e)}")
            return f"Error formatting employee list: {str(e)}"

    def _list_severity_categories(self, employee: str) -> str:
        """
        List all severity categories available for a specific employee from coaching details.
        
        Args:
            employee: Employee name (may include ID information in parentheses)

        Returns:
            Formatted string with severity categories
        """
        # Extract employee name and ID from the input
        employee_name = employee.split(" (ID:")[0] if " (ID:" in employee else employee
        employee_id = employee.split("ID: ")[1].rstrip(")") if " (ID:" in employee else None
        
        logger.info(f"Listing severity categories for employee: {employee_name} (ID: {employee_id})")
        
        categories = set()
        if self.coaching_details_data:
            try:
                # Filter coaching details for this specific employee
                employee_details = [
                    detail for detail in self.coaching_details_data 
                    if (
                        detail.get("driverName", "").strip() == employee_name.strip() 
                        or (employee_id and str(detail.get("userID", "")) == str(employee_id))
                    )
                ]
                
                logger.info(f"Found {len(employee_details)} coaching records for {employee_name}")
                
                # Extract categories from the coachingDetailsData
                for detail in employee_details:
                    if "coachingCategoryReasonText" in detail:
                        reasons = detail["coachingCategoryReasonText"].split(",")
                        categories.update(reason.strip() for reason in reasons)
                    if "subject" in detail:
                        categories.add(detail["subject"])
                
                categories = sorted(list(categories))
                logger.info(f"Extracted categories: {categories}")
                
            except Exception as e:
                logger.error(f"Error processing coaching details: {e}")
        
        # Use default categories if none found
        if not categories:
            categories = ["Performance", "Attendance", "Safety", "Other"]
            logger.info("Using default categories as no categories found in coaching details")
        
        formatted_categories = "\n".join(
            [f"{i+1}. **{category}**" for i, category in enumerate(categories)]
        )
        
        return f"Severity categories for coaching feedback for {employee_name}:\n{formatted_categories}"

    def _get_employee_coaching(self, employee: str, severity: str) -> str:
        """
        Get coaching history for a specific employee and severity category.

        Args:
            employee: Employee name (may include ID information in parentheses)
            severity: Optional severity category to filter by

        Returns:
            JSON string containing matching coaching records
        """
        # Extract employee name and ID from the input
        employee_name = employee.split(" (ID:")[0] if " (ID:" in employee else employee
        employee_id = employee.split("ID: ")[1].rstrip(")") if " (ID:" in employee else None
        
        logger.info(f"Getting coaching history for employee: {employee_name} (ID: {employee_id}), severity: {severity}")
        
        matching_records = []
        if self.coaching_details_data:
            try:
                # Filter records by employee and severity
                for detail in self.coaching_details_data:
                    # Match employee by name or ID
                    is_employee_match = (
                        detail.get("driverName", "").strip() == employee_name.strip()
                        or (employee_id and str(detail.get("userID", "")) == str(employee_id))
                    )
                    
                    # Match severity with coachingCategoryReasonText
                    coaching_category = detail.get("coachingCategoryReasonText", "")
                    categories = [cat.strip() for cat in coaching_category.split(",")]
                    is_severity_match = (
                        severity is None 
                        or any(severity.strip().lower() == cat.lower() for cat in categories)
                    )
                    
                    if is_employee_match and is_severity_match:
                        record = {
                            "driverName": detail.get("driverName", ""),
                            "coachingDate": detail.get("coachingDate", ""),
                            "coachingCategoryReasonText": coaching_category,
                            "pip": detail.get("pip", ""),
                            "coachingDetails": detail.get("coachingDetails", ""),
                            "coachingStatus": detail.get("coachingStatus", "")
                        }
                        matching_records.append(record)
                        logger.info(f"Added matching record for date: {detail.get('coachingDate', '')}")
                
                logger.info(f"Found {len(matching_records)} matching coaching records")
                
                # Sort records by date (newest first)
                matching_records.sort(key=lambda x: x["coachingDate"], reverse=True)
                
                if matching_records:
                    return json.dumps(matching_records, indent=2)
                
            except Exception as e:
                logger.error(f"Error processing coaching history: {e}")
        
        return json.dumps([])

    def _create_graph(self) -> StateGraph:
        """
        Create the LangGraph state graph for the coaching feedback generator.

        Returns:
            Compiled StateGraph
        """
        # Create the graph builder
        graph_builder = StateGraph(CoachingFeedbackState)

        # Define the agent node
        def agent_node(state: CoachingFeedbackState) -> Dict[str, Any]:
            """Process messages using the agent."""
            # Get the last message from the user
            last_message = state["messages"][-1]

            # Extract conversation history
            history = []
            if len(state["messages"]) > 1:
                for msg in state["messages"][:-1]:
                    if isinstance(msg, HumanMessage):
                        history.append(("human", msg.content))
                    elif isinstance(msg, AIMessage):
                        history.append(("ai", msg.content))

            try:
                # Call the agent with history
                result = self.agent_executor.invoke(
                    {"input": last_message.content, "chat_history": history}
                )

                # Return the response as an AI message
                return {"messages": [AIMessage(content=result["output"])]}
            except Exception as e:
                # Log the error
                logger.error(f"Error in agent_node: {str(e)}")

                # Return a generic error message
                return {
                    "messages": [
                        AIMessage(
                            content="I'm sorry, I encountered an error while processing your request. Please try again with more specific instructions."
                        )
                    ]
                }

        # Add the node to the graph
        graph_builder.add_node("agent", agent_node)

        # Add edges
        graph_builder.add_edge(START, "agent")
        graph_builder.add_edge("agent", END)

        # Compile the graph with the memory saver
        return graph_builder.compile(checkpointer=self.memory)

    def generate_feedback(self, query: str, session_id: str = None, driver_list: List[Dict[str, str]] = None, coaching_details_data: List[Dict] = None) -> str:
        """
        Generate coaching feedback based on the query using LangGraph.

        Args:
            query: The coaching query/reason (e.g., "Moises was cited for a speeding violation")
            session_id: Optional session ID for maintaining conversation history
            driver_list: Optional list of driver information dictionaries
            coaching_details_data: Optional list of coaching details data containing coaching history

        Returns:
            Structured coaching feedback
        """
        try:
            # Store coaching details data for use in other methods
            self.coaching_details_data = coaching_details_data

            logger.info(f"Generating feedback for query: {query}")

            # Generate a unique session ID if not provided
            if not session_id:
                session_id = str(uuid.uuid4())
                logger.info(f"Generated new session ID: {session_id}")
            else:
                logger.info(f"Using existing session ID: {session_id}")
                
            # Process the driver_list
            logger.info(f"Processing driver_list: {driver_list}")
            
            # Handle different formats of driver_list
            processed_driver_list = []
            if driver_list:
                for driver in driver_list:
                    # If driver is a Pydantic model or dict with model_dump method
                    if hasattr(driver, 'model_dump'):
                        processed_driver_list.append(driver.model_dump())
                    # If driver is already a dict
                    elif isinstance(driver, dict):
                        processed_driver_list.append(driver)
                    # If driver is a string or other format
                    else:
                        logger.warning(f"Unexpected driver format: {type(driver)}")
            
            logger.info(f"Processed driver_list: {processed_driver_list}")
            
            # Log coaching details data if provided
            if coaching_details_data:
                logger.info(f"Received coaching details data: {coaching_details_data}")
            
            # Format the employee list from the processed driver list
            employee_list = self._format_employee_list(processed_driver_list)
            logger.info(f"Formatted employee list: {employee_list}")
            
            # Create the prompt template with the employee list
            self.prompt = ChatPromptTemplate.from_messages(
                [
                    (
                        "system",
                        COACHING_HISTORY_PROMPT_TEMPLATE_STR.format(
                            employee_list=employee_list
                        )
                    ),
                    MessagesPlaceholder(variable_name="chat_history"),
                    ("human", "{input}"),
                    MessagesPlaceholder(variable_name="agent_scratchpad"),
                ]
            )
            
            # Create the agent using LangChain's create_openai_tools_agent
            self.agent = create_openai_tools_agent(self.llm, self.tools, self.prompt)
            
            # Create the agent executor
            self.agent_executor = AgentExecutor(agent=self.agent, tools=self.tools,verbose=True)

            # Create a human message
            human_message = HumanMessage(content=query)

            # Set up the config for this session
            config = {"configurable": {"thread_id": session_id}}

            # Prepare the initial state
            initial_state = {
                "messages": [human_message],
                "employee_name": None,
                "severity_category": None,
            }

            # Invoke the graph with the message
            result = self.graph.invoke(initial_state, config=config)

            # Extract and return the response content
            if result and "messages" in result and len(result["messages"]) > 0:
                # Get the last message (the response)
                last_message = result["messages"][-1]
                if isinstance(last_message, AIMessage):
                    return last_message.content

            logger.info("Message processed successfully")
            return "Sorry, I couldn't generate a response."

        except Exception as e:
            error_msg = f"Error generating feedback: {str(e)}"
            logger.error(error_msg)
            return f"An error occurred while generating feedback: {str(e)}"


def main():
    """
    Main function to demonstrate the usage of the CoachingFeedbackGenerator.
    """
    try:
        # Initialize the generator
        generator = CoachingFeedbackGenerator()

        # Example driver list
        driver_list = [
            {"driverName": "John Doe", "userID": "JD001"},
            {"driverName": "Jane Smith", "userID": "JS002"},
        ]

        # Generate feedback for a sample query
        query = "John Doe was cited for a speeding violation while operating a company vehicle."
        feedback = generator.generate_feedback(query=query, driver_list=driver_list)

        print("\nCoaching Feedback:")
        print(feedback)

    except Exception as e:
        print(f"Error in main: {str(e)}")


if __name__ == "__main__":
    main()
