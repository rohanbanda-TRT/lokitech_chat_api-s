"""
Driver Screening Agent implemented using LangGraph with ReAct pattern.
This module provides a LangGraph-based implementation of the driver screening agent.
"""

import os
import logging
import uuid
import json
import time
import re
from typing import Annotated, TypedDict, Dict, Any, Optional, List

from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_core.tools import BaseTool, Tool, StructuredTool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver

from dotenv import load_dotenv
from ..managers.company_questions_factory import get_company_questions_manager
from ..tools.driver_screening_tools import DriverScreeningTools, GetDateBasedTimeSlotsInput
from ..tools.dsp_api_client import DSPApiClient
from ..prompts.driver_screening import (
    DRIVER_SCREENING_PROMPT_TEMPLATE,
    DRIVER_SCREENING_WITH_NAME_PROMPT_TEMPLATE,
)

# Comment out Google Calendar related imports and initializations
# credentials = get_gmail_credentials(
#     token_file="token.json",
#     scopes=["https://www.googleapis.com/auth/calendar"],
#     client_secrets_file="credentials.json",
# )
#
# calendar_service = build_resource_service(
#     credentials=credentials, service_name="calendar", service_version="v3"
# )

# Initialize empty variables for Google Calendar tools (not used)
credentials = None
calendar_service = None
createeventtool = None
listeventtool = None

# Comment out Google Calendar tool imports
# from ..tools.googleCalender import CreateGoogleCalendarEvent, ListGoogleCalendarEvents
#
# createeventtool = CreateGoogleCalendarEvent.from_api_resource(calendar_service)
# listeventtool = ListGoogleCalendarEvents.from_api_resource(calendar_service)


# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class DriverScreeningState(TypedDict):
    """State schema for the driver screening graph."""

    messages: Annotated[list[BaseMessage], add_messages]
    session_id: Optional[str]
    dsp_code: Optional[str]
    station_code: Optional[str]
    applicant_id: Optional[int]
    applicant_details: Optional[Dict[str, Any]]
    is_new_session: Optional[bool]


class DriverScreeningAgent:
    """Driver Screening Agent implemented using LangGraph with ReAct pattern."""

    def __init__(self, api_key: str = None):
        """
        Initialize the driver screening agent with LangGraph.

        Args:
            api_key: OpenAI API key. If not provided, will try to get from environment.
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "OpenAI API key is required. Please provide it or set OPENAI_API_KEY environment variable."
            )

        self.llm = ChatOpenAI(
            temperature=0.7, api_key=self.api_key, model="gpt-4o-mini"
        )
        self.memory = MemorySaver()

        # Initialize managers and tools
        self.questions_manager = get_company_questions_manager()
        self.screening_tools = DriverScreeningTools()

        # Set up tools using the standard Tool class
        self.tools = [
            StructuredTool.from_function(
                func=self.screening_tools._update_applicant_status,
                name="update_applicant_status",
                description="Update the applicant status based on screening results (PASSED or FAILED)",
            ),
            StructuredTool.from_function(
                func=self.screening_tools._get_date_based_time_slots,
                name="get_date_based_time_slots",
                description="Convert day-based time slots to actual dates for the next N occurrences",
            ),
        ]

        # Build the graph
        self.graph = self._create_graph()
        logger.info("DriverScreeningAgent initialized with ReAct agent")

    def _get_company_specific_questions_text(self, dsp_code: str) -> str:
        """
        Get company-specific questions formatted for the prompt

        Args:
            dsp_code: The unique identifier for the company

        Returns:
            Formatted string of company-specific questions
        """
        result = self.questions_manager.get_questions(dsp_code)
        
        # Handle the new dictionary structure returned by the questions manager
        if isinstance(result, dict):
            questions = result.get("questions", [])
        else:
            # For backward compatibility with older implementations
            questions = result
            
        if not questions:
            return "   - No company-specific questions defined. Skip this section."

        formatted_questions = []
        for i, q in enumerate(questions, 1):
            question_text = q["question_text"]
            criteria = q.get("criteria", "No specific criteria defined")

            formatted_questions.append(f'   - Ask Question {i}: "{question_text}"')
            formatted_questions.append(f'     * Evaluation criteria: "{criteria}"')
        formatted_questions.append(
            f"     * All questions are required. If the driver does not provide a clear answer, politely ask again."
        )
        formatted_questions.append(
            f"     * Note: Do NOT mention the criteria to the driver. Use it only for internal evaluation."
        )

        return "\n".join(formatted_questions)

    def _get_company_time_slots_and_contact_info(self, dsp_code: str) -> tuple:
        """
        Get company time slots and contact information
        
        Args:
            dsp_code: The unique identifier for the company
            
        Returns:
            Tuple of (time_slots, contact_info) 
        """
        result = self.questions_manager.get_questions(dsp_code)
        
        # Default values
        time_slots = []
        contact_info = "our support team"
        
        # Extract time slots and contact info if available
        if isinstance(result, dict):
            time_slots = result.get("time_slots", [])
            contact_info = result.get("contact_info", "our support team")
            
        return time_slots, contact_info

    def _get_date_based_time_slots(self, time_slots: List[str], num_occurrences: int = 2) -> List[str]:
        """
        Convert day-based time slots to date-based time slots using the structured tool
        
        Args:
            time_slots: List of time slots in format 'Day Time Range'
            num_occurrences: Number of future occurrences to generate for each day
            
        Returns:
            List of date-based time slots
        """
        try:
            # Create input for the structured tool
            input_data = GetDateBasedTimeSlotsInput(
                time_slots=time_slots,
                num_occurrences=num_occurrences
            )
            
            # Call the tool function directly
            result_json = self.screening_tools._get_date_based_time_slots(input_data)
            result = json.loads(result_json)
            
            if result.get("success", False):
                return result.get("date_based_slots", [])
            else:
                logger.error(f"Error getting date-based time slots: {result.get('message')}")
                return []
                
        except Exception as e:
            logger.error(f"Error in _get_date_based_time_slots: {e}")
            return []

    def _create_prompt(
        self, dsp_code: str = None, applicant_details: dict = None
    ) -> ChatPromptTemplate:
        """
        Create a prompt with company-specific questions if available

        Args:
            dsp_code: Optional DSP code to get company-specific questions
            applicant_details: Optional applicant details to personalize the greeting

        Returns:
            Formatted prompt template
        """
        # Format the prompt with company-specific questions if available
        company_questions_text = (
            "   - No company-specific questions defined. Skip this section."
        )
        if dsp_code:
            company_questions_text = self._get_company_specific_questions_text(dsp_code)
            
        # Get time slots and contact info
        time_slots_text = "No specific time slots are available."
        contact_info_text = "No specific contact information available."
        
        if dsp_code:
            time_slots, contact_info = self._get_company_time_slots_and_contact_info(dsp_code)
            
            # Format time slots if available
            if time_slots and len(time_slots) > 0:
                # Convert day-based time slots to date-based time slots
                # Explicitly set num_occurrences to 2
                date_based_slots = self._get_date_based_time_slots(time_slots, num_occurrences=2)
                
                if date_based_slots and len(date_based_slots) > 0:
                    time_slots_text = "Available interview time slots:\n"
                    for i, slot in enumerate(date_based_slots, 1):
                        time_slots_text += f"   {i}. {slot}\n"
                else:
                    # Fallback to original time slots if conversion failed
                    time_slots_text = "Available interview time slots:\n"
                    for i, slot in enumerate(time_slots, 1):
                        time_slots_text += f"   {i}. {slot}\n"
            
            # Format contact info if available
            if contact_info:
                contact_info_text = f"Company contact information: {contact_info}"

        # Choose the appropriate prompt template based on whether we have the applicant's details
        if applicant_details:
            # Use the template specifically designed for when we know the applicant's name
            first_name = applicant_details.get("firstName", "").strip()
            last_name = applicant_details.get("lastName", "").strip()
            applicant_name = f"{first_name} {last_name}".strip()

            logger.info(
                f"Using personalized prompt template for applicant: {applicant_name}"
            )

            # Replace placeholders in the template
            prompt_text = DRIVER_SCREENING_WITH_NAME_PROMPT_TEMPLATE.replace(
                "{{company_specific_questions}}", company_questions_text
            )
            # Replace the applicant name placeholder with the actual name
            prompt_text = prompt_text.replace("{{applicant_name}}", applicant_name)

            # Add applicant details section to the prompt
            applicant_details_text = f"""
            **Applicant Details (For Internal Reference Only - DO NOT share with the applicant):**
            - DSP Short Code: {applicant_details.get('dspShortCode', 'N/A')}
            - DSP Station Code: {applicant_details.get('dspStationCode', 'N/A')}
            - Applicant ID: {applicant_details.get('applicantID', 'N/A')}
            - DSP Name: {applicant_details.get('dspName', 'N/A')}
            - First Name: {applicant_details.get('firstName', 'N/A')}
            - Last Name: {applicant_details.get('lastName', 'N/A')}
            - Mobile Number: {applicant_details.get('mobileNumber', 'N/A')}
            - Applicant Status: {applicant_details.get('applicantStatus', 'N/A')}

            **Company Information (For Internal Reference Only - Use as directed in the instructions):**
            {time_slots_text}
            {contact_info_text}

            Remember to use the above information for internal processing only. Never share these details directly with the applicant unless instructed to do so in the screening process.
            """
            # Insert the applicant details section after the initial message section
            prompt_text = prompt_text.replace(
                "Screening Process:", f"{applicant_details_text}\nScreening Process:"
            )
        else:
            # Use the standard template that asks for the applicant's name
            logger.info("Using standard prompt template (will ask for name)")

            # The prompt template uses double curly braces for JSON examples
            # We only need to replace the company_specific_questions placeholder
            prompt_text = DRIVER_SCREENING_PROMPT_TEMPLATE.replace(
                "{{company_specific_questions}}", company_questions_text
            )

        return ChatPromptTemplate.from_messages(
            [
                ("system", prompt_text),
                MessagesPlaceholder(variable_name="chat_history"),
                ("human", "{input}"),
                MessagesPlaceholder(variable_name="agent_scratchpad"),
            ]
        )

    def _update_applicant_status(
        self, dsp_code: str, applicant_name: str, applicant_details: dict
    ) -> None:
        """
        Update the applicant status to INPROGRESS when screening starts

        Args:
            dsp_code: The DSP code
            applicant_name: The applicant's full name
            applicant_details: The applicant details dictionary
        """
        try:
            # Only update if the current status is SENT or empty
            current_status = applicant_details.get("applicantStatus", "").strip()
            if current_status == "SENT" or current_status == "":
                logger.info(
                    f"Updating applicant status for {applicant_name} from {current_status if current_status else 'empty'} to INPROGRESS"
                )

                # Get the required parameters from applicant_details
                applicant_id = applicant_details.get("applicantID")

                # Create the JSON input string that the tool expects
                input_data = {
                    "dsp_code": dsp_code,
                    "applicant_id": applicant_id,
                    "current_status": current_status,
                    "new_status": "INPROGRESS",
                }

                # Convert to JSON string
                input_str = json.dumps(input_data)

                # Call the API to update the status
                result = self.screening_tools._update_applicant_status(input_str)

                # Log the result
                logger.info(f"Status update result: {result}")
            else:
                logger.info(
                    f"Not updating applicant status for {applicant_name} as current status is {current_status}"
                )
        except Exception as e:
            logger.error(f"Error updating applicant status: {e}")

    def _create_graph(self) -> StateGraph:
        """
        Create the LangGraph for the driver screening agent.

        Returns:
            Compiled StateGraph
        """
        # Create the graph builder with our state schema
        graph_builder = StateGraph(DriverScreeningState)

        # Define the agent node
        def agent_node(state: DriverScreeningState) -> Dict[str, Any]:
            """Process messages using the agent."""
            # Extract the last message from the user
            last_message = state["messages"][-1]

            # Extract session information from state
            session_id = state.get("session_id")
            dsp_code = state.get("dsp_code")
            station_code = state.get("station_code")
            applicant_id = state.get("applicant_id")
            applicant_details = state.get("applicant_details")
            is_new_session = state.get("is_new_session", False)

            # Check for special triggers
            user_input = last_message.content

            # For the first message in a new session with applicant details,
            # we want to ensure the agent greets the applicant by name
            if is_new_session and applicant_details and not user_input.strip():
                # For the first message, we'll use a special trigger to ensure the agent
                # starts with the personalized greeting
                if not user_input.strip() or user_input.lower().strip() in [
                    "hi",
                    "hello",
                    "hey",
                ]:
                    # Replace with a special trigger that the agent will recognize
                    user_input = "START_GREETING"
                    logger.info("Using special greeting trigger for first message")

            # Create the prompt with company-specific questions and applicant details if available
            prompt = self._create_prompt(dsp_code, applicant_details)

            # Create the agent using the prompt
            agent = create_openai_tools_agent(self.llm, self.tools, prompt)

            # Create the agent executor
            agent_executor = AgentExecutor(agent=agent, tools=self.tools)

            # Extract conversation history
            history = []
            if len(state["messages"]) > 1:
                # Skip the last message as it's the current user input
                for msg in state["messages"][:-1]:
                    if isinstance(msg, HumanMessage):
                        history.append(("human", msg.content))
                    elif isinstance(msg, AIMessage):
                        history.append(("ai", msg.content))

            try:
                # Call the agent with history
                result = agent_executor.invoke(
                    {"input": user_input, "chat_history": history}
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

    def process_message(
        self,
        user_input: str,
        session_id: str = None,
        dsp_code: str = None,
        station_code: str = None,
        applicant_id: int = None,
    ) -> str:
        """
        Process a message using the driver screening agent.

        Args:
            user_input: The user message to process
            session_id: Optional session ID for conversation history
            dsp_code: Optional DSP code for company-specific questions
            station_code: Optional station code for the DSP location
            applicant_id: Optional applicant ID for the driver being screened

        Returns:
            The generated response
        """
        # Create a unique session ID if not provided
        if not session_id:
            timestamp = int(time.time())
            session_id = f"SESSION-{timestamp}"
            logger.info(f"Generated new session_id: {session_id}")

        # Create a unique session ID that includes the dsp_code to ensure
        # we get the right prompt with company-specific questions
        unique_session_id = f"{session_id}_{dsp_code}" if dsp_code else session_id

        # Check if this is a new session by trying to get the checkpoint
        try:
            # Try to get the checkpoint for this session ID
            checkpoint = self.memory.get(unique_session_id)
            is_new_session = checkpoint is None
        except:
            # If there's an error, assume it's a new session
            is_new_session = True

        # Get applicant details if dsp_code is provided and this is the first message
        applicant_details = None

        if dsp_code and is_new_session:
            logger.info(
                f"New session detected. Fetching applicant details for DSP code: {dsp_code}, "
                f"station_code: {station_code}, applicant_id: {applicant_id}"
            )

            # Use the DSP API client directly to pass the new parameters
            api_client = DSPApiClient()

            # Use provided station_code and applicant_id if available, otherwise use defaults
            station_code_to_use = station_code if station_code else "DJE1"
            applicant_id_to_use = applicant_id if applicant_id is not None else 57

            applicant_details_obj = api_client.get_applicant_details(
                dsp_code=dsp_code,
                station_code=station_code_to_use,
                applicant_id=applicant_id_to_use,
            )

            if applicant_details_obj:
                applicant_details = applicant_details_obj.model_dump()

                # Check if required fields (name, mobile) are present
                first_name = applicant_details.get("firstName", "").strip()
                last_name = applicant_details.get("lastName", "").strip()
                mobile_number = applicant_details.get("mobileNumber", "").strip()
                applicant_status = applicant_details.get("applicantStatus", "").strip()

                # If any of the required fields are missing, stop the screening
                if (
                    not first_name
                    or not last_name
                    or not mobile_number
                ):
                    logger.warning(
                        f"Missing required applicant details. Name: '{first_name} {last_name}', "
                        f"Mobile: '{mobile_number}', Status: '{applicant_status}'"
                    )
                    
                    # Get company contact info if available
                    _, contact_info_text = self._get_company_time_slots_and_contact_info(dsp_code)
                    contact_info = contact_info_text if contact_info_text else "our support team"
                    
                    return f"I apologize, but I couldn't find your record in our system. This could be due to a technical issue. Please contact {contact_info} for assistance. Thank you for your interest in driving with Lokiteck Logistics."

                # Check if the applicant status is not SENT or INPROGRESS, which means screening is already done
                if applicant_status != "SENT" and applicant_status != "INPROGRESS" and applicant_status != "":
                    logger.warning(
                        f"Applicant with ID {applicant_id_to_use} has already been screened. Current status: {applicant_status}"
                    )
                    
                    # Get company contact info if available
                    _, contact_info_text = self._get_company_time_slots_and_contact_info(dsp_code)
                    contact_info = contact_info_text if contact_info_text else "our support team"
                    
                    return f"Thank you for your interest in driving with Lokiteck Logistics. Our records show that you have already completed the screening process. If you have any questions or need assistance, please contact {contact_info}."

                # Format the full name from first and last name
                applicant_name = f"{first_name} {last_name}".strip()
                logger.info(
                    f"Found applicant name: {applicant_name}, mobile: {mobile_number}, status: {applicant_status}"
                )

                # Update the applicant status to INPROGRESS
                self._update_applicant_status(
                    dsp_code, applicant_name, applicant_details
                )
            else:
                logger.warning(
                    f"Could not retrieve applicant details for DSP code: {dsp_code}, "
                    f"station_code: {station_code_to_use}, applicant_id: {applicant_id_to_use}"
                )

                # Get company contact info if available
                _, contact_info_text = self._get_company_time_slots_and_contact_info(dsp_code)
                contact_info = contact_info_text if contact_info_text else "our support team"
                
                # Return a polite message to end the conversation if applicant details are not found
                return f"I apologize, but I couldn't find your record in our system. This could be due to a technical issue. Please contact {contact_info} for assistance. Thank you for your interest in driving with Lokiteck Logistics."

        # Create a human message
        human_message = HumanMessage(content=user_input)

        # Set up the config for this session
        config = {"configurable": {"thread_id": unique_session_id}}

        # Prepare the initial state
        initial_state = {
            "messages": [human_message],
            "session_id": session_id,
            "is_new_session": is_new_session,
        }

        if dsp_code:
            initial_state["dsp_code"] = dsp_code
            logger.info(f"Using dsp_code: {dsp_code}")

        if station_code:
            initial_state["station_code"] = station_code
            logger.info(f"Using station_code: {station_code}")

        if applicant_id is not None:
            initial_state["applicant_id"] = applicant_id
            logger.info(f"Using applicant_id: {applicant_id}")

        if applicant_details:
            initial_state["applicant_details"] = applicant_details
            logger.info(
                f"Using applicant details for: {applicant_details.get('firstName', '')} {applicant_details.get('lastName', '')}"
            )

        # Invoke the graph with the message
        result = self.graph.invoke(
            initial_state,
            config=config,
        )

        # Extract and return the response content
        if result and "messages" in result and len(result["messages"]) > 0:
            # Get the last message (the response)
            last_message = result["messages"][-1]
            if isinstance(last_message, AIMessage):
                return last_message.content

        logger.info("Message processed successfully")
        return "Sorry, I couldn't generate a response."


def main():
    """Run a simple CLI demo of the driver screening agent."""
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("Please set OPENAI_API_KEY environment variable")

    agent = DriverScreeningAgent(api_key)

    print("Driver Screening Started! Type 'q' or 'quit' to exit.")

    # Ask for DSP code
    dsp_code = input("Enter DSP code (or leave blank for default questions): ").strip()

    # Generate a unique session ID
    timestamp = int(time.time())
    session_id = f"SESSION-{timestamp}"

    if dsp_code:
        # Send an empty first message to trigger the greeting with the applicant's name
        print("\nFetching applicant details and starting conversation...")
        first_response = agent.process_message("", session_id, dsp_code)
        print("\nResponse:", first_response)

    while True:
        user_input = input("\nEnter your message: ").strip().lower()

        if user_input in ["q", "quit"]:
            print("\nScreening ended.")
            break

        response = agent.process_message(
            user_input, session_id, dsp_code if dsp_code else None
        )
        print("\nResponse:", response)


if __name__ == "__main__":
    main()
