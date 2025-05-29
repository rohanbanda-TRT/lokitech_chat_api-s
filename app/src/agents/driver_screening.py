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
from typing_extensions import Literal, get_type_hints

from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_core.tools import BaseTool, Tool, StructuredTool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from ..utils.time_slot_parser import RecurrenceTimeSlot

from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver

from dotenv import load_dotenv
from ..managers.company_questions_factory import get_company_questions_manager
from ..tools.driver_screening_tools import DriverScreeningTools, UpdateApplicantStatusInput
from ..tools.dsp_api_client import DSPApiClient
from ..prompts.driver_screening import (
    DRIVER_SCREENING_PROMPT_TEMPLATE,
    DRIVER_SCREENING_WITH_NAME_PROMPT_TEMPLATE,
)
import datetime

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
                func=self.screening_tools.update_applicant_status_multi,
                name="update_applicant_status",
                description="Update the applicant status based on screening results (PASSED or FAILED)",
            ),
        ]

        # Initialize caches
        self.prompt_cache = {}
        self.applicant_details_cache = {}
        self.company_data_cache = {}
        self.agent_cache = {}
        self.executor_cache = {}

        # Create the LangGraph
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
        # Check if we have cached company questions for this DSP code
        cache_key = f"company_questions_{dsp_code}"
        if cache_key in self.company_data_cache:
            logger.info(f"Using cached company questions for DSP code: {dsp_code}")
            return self.company_data_cache[cache_key]
            
        try:
            # Get company questions from the manager
            company_questions = self.questions_manager.get_questions(dsp_code)

            if not company_questions or not company_questions.get("questions"):
                logger.warning(f"No questions found for DSP code: {dsp_code}")
                company_questions_text = "No company-specific questions are available at this time."
            else:
                # Format the questions for the prompt
                questions_list = company_questions.get("questions", [])
                company_questions_text = "Please ask the following company-specific questions:\n"
                
                # Log the structure of the first question to debug
                if questions_list:
                    logger.info(f"First question structure: {questions_list[0]}")
                
                for i, question in enumerate(questions_list, 1):
                    # Check for different possible field names for question text
                    question_text = ""
                    if "question_text" in question:
                        question_text = question.get("question_text", "")
                    elif "question" in question:
                        question_text = question.get("question", "")
                    elif "text" in question:
                        question_text = question.get("text", "")
                    
                    # Extract criteria
                    criteria = question.get("criteria", "")

                    # Add the question to the formatted text
                    company_questions_text += f"{i}. {question_text}\n"
                    if criteria:
                        company_questions_text += f"   Criteria: {criteria}\n"

            # Cache the formatted questions
            self.company_data_cache[cache_key] = company_questions_text
            return company_questions_text
        except Exception as e:
            logger.error(f"Error getting company questions: {e}")
            return "No company-specific questions are available at this time."

    def _get_company_time_slots_and_contact_info(self, dsp_code: str):
        """
        Get company time slots and contact information
        
        Args:
            dsp_code: The unique identifier for the company
            
        Returns:
            Tuple of (time_slots, contact_info, formatted_contact_info) 
        """
        try:
            # Get company questions which include time_slots and contact_info
            company_data = self.questions_manager.get_questions(dsp_code)
            
            # Extract time_slots, recurrence_time_slots, structured_recurrence_time_slots, and contact_info
            all_time_slots = company_data.get("time_slots", [])
            recurrence_time_slots = company_data.get("recurrence_time_slots", [])
            structured_recurrence_time_slots = company_data.get("structured_recurrence_time_slots", [])
            contact_info = company_data.get("contact_info", {})
            
            # Format legacy recurrence time slots with next occurrence dates
            from ..utils.time_slot_parser import format_recurrence_time_slots, generate_time_slots_from_recurrence
            formatted_recurrence_slots = format_recurrence_time_slots(recurrence_time_slots)
            
            # Format structured recurrence time slots
            formatted_structured_slots = []
            if structured_recurrence_time_slots:
                # Convert dictionary structured recurrence time slots to RecurrenceTimeSlot objects
                recurrence_objects = []
                for slot_dict in structured_recurrence_time_slots:
                    try:
                        recurrence_objects.append(RecurrenceTimeSlot(**slot_dict))
                    except Exception as e:
                        logger.error(f"Error converting structured recurrence time slot to object: {e}")
                
                # Generate the next few occurrences from structured recurrence patterns
                if recurrence_objects:
                    formatted_structured_slots = generate_time_slots_from_recurrence(
                        recurrence_objects, 
                        num_occurrences=3
                    )
            
            # Combine all time slots
            all_time_slots = all_time_slots + formatted_recurrence_slots + formatted_structured_slots
            
            # Filter out past time slots
            current_date = datetime.datetime.now().date()
            valid_time_slots = []
            
            for slot in all_time_slots:
                # Try to extract the date part from the time slot
                try:
                    # Expected format: "May 10, 2025 9 AM - 5 PM"
                    date_part = slot.split(' ', 3)[0:3]  # Extract "May", "10,", "2025"
                    date_str = ' '.join(date_part)  # Combine to "May 10, 2025"
                    slot_date = datetime.datetime.strptime(date_str, "%B %d, %Y").date()
                    
                    # Only include future dates
                    if slot_date >= current_date:
                        valid_time_slots.append(slot)
                except (ValueError, IndexError) as e:
                    # If we can't parse the date, include the slot (backward compatibility)
                    logger.warning(f"Could not parse date from time slot '{slot}': {e}")
                    valid_time_slots.append(slot)
            
            # Sort time slots by date
            try:
                valid_time_slots.sort(key=lambda x: datetime.datetime.strptime(' '.join(x.split(' ', 3)[0:3]), "%B %d, %Y"))
            except (ValueError, IndexError):
                # If sorting fails, keep the original order
                logger.warning("Could not sort time slots by date, keeping original order")
            
            # Format contact info if it's a dictionary (new format)
            if isinstance(contact_info, dict) and all(key in contact_info for key in ["contact_person_name", "contact_number", "email_id"]):
                # Create a formatted string from the structured contact info
                formatted_contact_info = f"{contact_info['contact_person_name']} ({contact_info['contact_number']}, {contact_info['email_id']})"
            else:
                # Fallback to the old format or default
                formatted_contact_info = contact_info if isinstance(contact_info, str) else "our hiring team"
                # Create a basic object if contact_info is not already a dict
                if isinstance(contact_info, str):
                    contact_info = {"contact_person_name": contact_info}
                elif not isinstance(contact_info, dict):
                    contact_info = {"contact_person_name": "Hiring Team"}
            
            return valid_time_slots, contact_info, formatted_contact_info
        except Exception as e:
            logger.error(f"Error getting company time slots and contact info: {e}")
            default_contact = {"contact_person_name": "Hiring Team"}
            return [], default_contact, "our hiring team"

    def _create_prompt(
            self, dsp_code: str = None, applicant_details: dict = None, session_id: str = None
        ) -> ChatPromptTemplate:
        """
        Create a prompt with company-specific questions if available

        Args:
            dsp_code: Optional DSP code to get company-specific questions
            applicant_details: Optional applicant details to personalize the greeting
            session_id: Optional session ID for caching

        Returns:
            Formatted prompt template
        """
        # Check cache first
        cache_key = f"prompt_{dsp_code}_{session_id}"
        if cache_key in self.prompt_cache:
            logger.info(f"Using cached prompt for DSP code: {dsp_code}, session: {session_id}")
            return self.prompt_cache[cache_key]

        # Get company-specific questions if DSP code is provided
        company_questions_text = ""
        time_slots_text = ""
        contact_info_text = ""
        
        # Get current date and time
        current_datetime = datetime.datetime.now()
        current_date_str = current_datetime.strftime("%B %d, %Y")
        if dsp_code:
            logger.info(f"Getting company-specific questions for DSP code: {dsp_code}")
            company_questions_text = self._get_company_specific_questions_text(dsp_code)
            
            # Get time slots and contact info
            time_slots, _, contact_info = self._get_company_time_slots_and_contact_info(dsp_code)
            
            if time_slots:
                time_slots_text = f"Available Time Slots: {', '.join(time_slots)}"
            else:
                time_slots_text = "No valid time slots available"
                
            if contact_info:
                contact_info_text = f"Contact Information: {contact_info}"
            else:
                contact_info_text = "Contact Information: our hiring team"

        # Create the prompt template
        if applicant_details and isinstance(applicant_details, dict):
            # Use the template with applicant name
            logger.info("Using prompt template with applicant name")
            
            # Get the applicant's name
            first_name = applicant_details.get("firstName", "")
            last_name = applicant_details.get("lastName", "")
            applicant_name = f"{first_name} {last_name}".strip()
            
            # Check if the applicant's status is already PASSED or FAILED
            current_status = applicant_details.get("applicantStatus", "").strip().upper()
            if current_status in ["PASSED", "FAILED"]:
                # Create a simplified prompt for completed screenings
                dsp_name = applicant_details.get('dspName', 'Lokiteck Logistics')
                prompt_text = f"""
                    You are a professional driver screening assistant for {dsp_name}.

                    Your task is to inform {applicant_name} that their screening process is already complete.

                    **Applicant Details (For Internal Reference Only - Do Not Share Directly):**
                    - DSP Code: {dsp_code if dsp_code else 'N/A'}
                    - DSP Station Code: {applicant_details.get('dspStationCode', 'N/A')}
                    - Applicant ID: {applicant_details.get('applicantID', 'N/A')}
                    - DSP Name: {applicant_details.get('dspName', 'N/A')}
                    - First Name: {applicant_details.get('firstName', 'N/A')}
                    - Last Name: {applicant_details.get('lastName', 'N/A')}
                    - Mobile Number: {applicant_details.get('mobileNumber', 'N/A')}
                    - Applicant Status: {current_status}

                    **Company Information:**
                    {time_slots_text}
                    {contact_info_text}
                    Current Date and Time: {current_date_str}

                    Instructions:
                    1. Greet {applicant_name} professionally
                    2. Inform them that their screening process is already complete with status: {current_status}
                    3. For any queries, direct them to contact: {contact_info if contact_info else "our hiring team"}
                    4. Do not ask them any screening questions
                    5. Do not attempt to update their status again
                    6. Be polite and professional at all times

                    Remember: The applicant has already completed the screening process. Your only job is to inform them of this fact and provide contact information for any questions they might have.
                    """
            else:
                # Replace placeholders in the template for normal screening
                prompt_text = DRIVER_SCREENING_WITH_NAME_PROMPT_TEMPLATE
                prompt_text = prompt_text.replace("{{applicant_name}}", applicant_name)
                prompt_text = prompt_text.replace("{{company_specific_questions}}", company_questions_text)
                prompt_text = prompt_text.replace("{{time_slots}}", ', '.join(time_slots) if time_slots else "No valid time slots available")
                prompt_text = prompt_text.replace("{{contact_info}}", contact_info if contact_info else "our hiring team")
                prompt_text = prompt_text.replace("{{current_datetime}}", current_date_str)
                prompt_text = prompt_text.replace("{{dsp_name}}", applicant_details.get('dspName', 'Lokiteck Logistics'))
                
                # Add applicant details section for the agent's reference
                applicant_details_text = f"""
                **Applicant Details (For Internal Reference Only - Do Not Share Directly):**
                - DSP Code: {dsp_code if dsp_code else 'N/A'}
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
                Current Date and Time: {current_date_str}

                Remember to use the above information for internal processing only. Never share these details directly with the applicant unless instructed to do so in the screening process.
                """
                # Insert the applicant details section after the initial message section
                prompt_text = prompt_text.replace(
                    "Screening Process:", f"{applicant_details_text}\nScreening Process:"
                )
        else:
            # Use the template without applicant name
            logger.info("Using prompt template without applicant name")
            prompt_text = DRIVER_SCREENING_PROMPT_TEMPLATE
            prompt_text = prompt_text.replace("{{company_specific_questions}}", company_questions_text)
            prompt_text = prompt_text.replace("{{time_slots}}", ', '.join(time_slots) if time_slots else "No valid time slots available")
            prompt_text = prompt_text.replace("{{contact_info}}", contact_info if contact_info else "our hiring team")
            prompt_text = prompt_text.replace("{{current_datetime}}", current_date_str)
            prompt_text = prompt_text.replace("{{dsp_name}}", "Lokiteck Logistics")

        prompt_template = ChatPromptTemplate.from_messages([
            ("system", prompt_text),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])
        
        # Cache the prompt
        self.prompt_cache[cache_key] = prompt_template
        
        return prompt_template

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

                # Call the API to update the status using the multi-argument tool
                result = self.screening_tools.update_applicant_status_multi(
                    dsp_code=dsp_code,
                    applicant_id=applicant_id,
                    current_status=current_status,
                    new_status="INPROGRESS",
                    responses={}
                )

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

            # Check if we have a cached agent and executor for this session
            agent_executor = None
            if session_id and session_id in self.executor_cache:
                logger.info(f"Using cached agent executor for session: {session_id}")
                agent_executor = self.executor_cache[session_id]
            else:
                # Create the prompt with company-specific questions and applicant details if available
                # Pass the session_id to enable caching
                prompt = self._create_prompt(dsp_code, applicant_details, session_id)

                # Check if we have a cached agent for this session
                if session_id and session_id in self.agent_cache:
                    logger.info(f"Using cached agent for session: {session_id}")
                    agent = self.agent_cache[session_id]
                else:
                    # Create the agent using the prompt
                    agent = create_openai_tools_agent(self.llm, self.tools, prompt)
                    
                    # Cache the agent if we have a session ID
                    if session_id:
                        self.agent_cache[session_id] = agent
                        logger.info(f"Cached agent for session: {session_id}")

                # Create the agent executor
                agent_executor = AgentExecutor(agent=agent, tools=self.tools,verbose=True)
                
                # Cache the executor if we have a session ID
                if session_id:
                    self.executor_cache[session_id] = agent_executor
                    logger.info(f"Cached agent executor for session: {session_id}")

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
                start_time = time.time()
                result = agent_executor.invoke(
                    {"input": user_input, "chat_history": history}
                )
                end_time = time.time()
                logger.info(f"Agent execution time: {end_time - start_time:.2f} seconds")

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

        # Compile the graph with the memory saver to maintain conversation history
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
        try:
            # Generate a unique session ID if not provided
            if not session_id:
                session_id = str(uuid.uuid4())
                is_new_session = True
                logger.info(f"Created new session with ID: {session_id}")
            else:
                # Check if this is a new session (not in our cache)
                is_new_session = session_id not in self.prompt_cache
                logger.info(
                    f"Using existing session with ID: {session_id}, is_new_session: {is_new_session}"
                )

            # Get a unique ID for this session's checkpointer
            unique_session_id = f"driver_screening_{session_id}"

            # Check if we need to fetch applicant details
            applicant_details = None
            if is_new_session:
                # Only fetch applicant details for new sessions or if not in cache
                if dsp_code and station_code and applicant_id is not None:
                    try:
                        # Get the applicant details from the API
                        logger.info(
                            f"Fetching applicant details for DSP code: {dsp_code}, "
                            f"station_code: {station_code}, applicant_id: {applicant_id}"
                        )

                        # Use the actual station code and applicant ID if provided
                        station_code_to_use = station_code
                        applicant_id_to_use = applicant_id

                        # Get the applicant details
                        applicant_details_obj = self.screening_tools.dsp_api_client.get_applicant_details(
                            dsp_code=dsp_code,
                            station_code=station_code_to_use,
                            applicant_id=applicant_id_to_use,
                        )

                        # Convert the ApplicantDetails object to a dictionary if it's not None
                        if applicant_details_obj:
                            # Use model_dump() to convert Pydantic model to dictionary
                            applicant_details = applicant_details_obj.model_dump()
                            
                            # Extract key fields
                            first_name = applicant_details.get("firstName", "").strip()
                            last_name = applicant_details.get("lastName", "").strip()
                            mobile_number = applicant_details.get("mobileNumber", "").strip()
                            applicant_status = applicant_details.get("applicantStatus", "").strip()

                            # Check if we have the required fields
                            if not (first_name and last_name and mobile_number):
                                logger.warning(
                                    f"Missing required fields in applicant details: "
                                    f"first_name={first_name}, last_name={last_name}, mobile_number={mobile_number}"
                                )

                                # Get company contact info if available
                                _, _, contact_info_text = self._get_company_time_slots_and_contact_info(dsp_code)
                                contact_info = contact_info_text if contact_info_text else "our support team"
                                
                                # Extract the DSP name from applicant details
                                dsp_name = applicant_details.get("dspName", "our company")
                                
                                return f"Thank you for your interest in driving with {dsp_name}. Our records show that you have already completed the screening process. If you have any questions or need assistance, please contact {contact_info}."
                                    
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
                            _, _, contact_info_text = self._get_company_time_slots_and_contact_info(dsp_code)
                            contact_info = contact_info_text if contact_info_text else "our support team"
                            
                            # Try to get the DSP name from the API client
                            dsp_name = None
                            try:
                                # Get company data to extract DSP name
                                company_data = self.questions_manager.get_questions(dsp_code)
                                if company_data and "companyName" in company_data:
                                    dsp_name = company_data.get("companyName")
                            except Exception as e:
                                logger.error(f"Error getting DSP name: {e}")
                                
                            # Use the DSP name or a default value
                            dsp_name = dsp_name or "our company"
                            
                            # Return a polite message to end the conversation if applicant details are not found
                            return f"I'm sorry, but I could not find your record in our system. Thank you for your interest in {dsp_name}."

                    except Exception as e:
                        logger.error(f"Error retrieving applicant details: {e}")
                        # Continue without applicant details
            else:
                # For existing sessions, use cached applicant details if available
                if session_id in self.applicant_details_cache:
                    applicant_details = self.applicant_details_cache[session_id]
                    logger.info(f"Using cached applicant details for session: {session_id}")

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
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return "I apologize, but I encountered an error while processing your message. Please try again later."

    def clear_cache(self, session_id: str = None):
        """
        Clear the prompt cache for a specific session or all sessions.
        
        Args:
            session_id: Optional session ID to clear cache for. If None, clears all caches.
        """
        if session_id:
            # Clear cache for a specific session
            if session_id in self.prompt_cache:
                del self.prompt_cache[session_id]
            if session_id in self.applicant_details_cache:
                del self.applicant_details_cache[session_id]
            if session_id in self.agent_cache:
                del self.agent_cache[session_id]
            if session_id in self.executor_cache:
                del self.executor_cache[session_id]
            logger.info(f"Cleared cache for session: {session_id}")
        else:
            # Clear all caches
            self.prompt_cache.clear()
            self.applicant_details_cache.clear()
            self.company_data_cache.clear()
            self.agent_cache.clear()
            self.executor_cache.clear()
            logger.info("Cleared all caches")


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
