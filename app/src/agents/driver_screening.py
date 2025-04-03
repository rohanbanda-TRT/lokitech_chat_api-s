from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain.tools import Tool
from langchain_core.tools import StructuredTool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
import os
from dotenv import load_dotenv
from ..managers.company_questions_factory import get_company_questions_manager
from ..tools.driver_screening_tools import DriverScreeningTools
import json
from ..prompts.driver_screening import DRIVER_SCREENING_PROMPT_TEMPLATE, DRIVER_SCREENING_WITH_NAME_PROMPT_TEMPLATE
from ..utils.session_manager import get_session_manager
from langchain_community.tools.gmail.utils import (
    build_resource_service,
    get_gmail_credentials,
)
credentials = get_gmail_credentials(
    token_file="token.json",
    scopes=["https://www.googleapis.com/auth/calendar"],
    client_secrets_file="credentials.json",
)

calendar_service = build_resource_service(
    credentials=credentials, service_name="calendar", service_version="v3"
)
import logging
from ..tools.googleCalender import CreateGoogleCalendarEvent, ListGoogleCalendarEvents
createeventtool = CreateGoogleCalendarEvent.from_api_resource(calendar_service)
listeventtool = ListGoogleCalendarEvents.from_api_resource(calendar_service)



# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DriverScreeningAgent:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.llm = ChatOpenAI(temperature=0.7, api_key=api_key, model="gpt-4o-mini")
        # Use Firebase for company questions via the factory
        self.questions_manager = get_company_questions_manager()
        self.session_manager = get_session_manager()
        self.screening_tools = DriverScreeningTools()
        self.tools = [
            StructuredTool.from_function(
                func=self.screening_tools._store_driver_screening,
                name="store_driver_screening",
                description="Store all driver screening data including responses and evaluation in one operation"
            ),
            createeventtool,
            listeventtool
        ]
        
    def _get_company_specific_questions_text(self, dsp_code: str) -> str:
        """
        Get company-specific questions formatted for the prompt
        
        Args:
            dsp_code: The unique identifier for the company
            
        Returns:
            Formatted string of company-specific questions
        """
        questions = self.questions_manager.get_questions(dsp_code)
        
        if not questions:
            return "   - No company-specific questions defined. Skip this section."
        
        formatted_questions = []
        for i, q in enumerate(questions, 1):
            question_text = q['question_text']
            criteria = q.get('criteria', "No specific criteria defined")
            
            formatted_questions.append(f"   - Ask Question {i}: \"{question_text}\"")
            formatted_questions.append(f"     * Evaluation criteria: \"{criteria}\"")
        formatted_questions.append(f"     * All questions are required. If the driver does not provide a clear answer, politely ask again.")
        formatted_questions.append(f"     * Note: Do NOT mention the criteria to the driver. Use it only for internal evaluation.")
        
        return "\n".join(formatted_questions)
    
    def _create_prompt(self, dsp_code: str = None, applicant_name: str = None) -> ChatPromptTemplate:
        """
        Create a prompt with company-specific questions if available
        
        Args:
            dsp_code: Optional DSP code to get company-specific questions
            applicant_name: Optional applicant name to personalize the greeting
            
        Returns:
            Formatted prompt template
        """
        # Format the prompt with company-specific questions if available
        company_questions_text = "   - No company-specific questions defined. Skip this section."
        if dsp_code:
            company_questions_text = self._get_company_specific_questions_text(dsp_code)
        
        # Choose the appropriate prompt template based on whether we have the applicant's name
        if applicant_name:
            # Use the template specifically designed for when we know the applicant's name
            logger.info(f"Using personalized prompt template for applicant: {applicant_name}")
            
            # Replace placeholders in the template
            prompt_text = DRIVER_SCREENING_WITH_NAME_PROMPT_TEMPLATE.replace(
                "{{company_specific_questions}}", company_questions_text
            )
            # Replace the applicant name placeholder with the actual name
            prompt_text = prompt_text.replace("{{applicant_name}}", applicant_name)
        else:
            # Use the standard template that asks for the applicant's name
            logger.info("Using standard prompt template (will ask for name)")
            
            # The prompt template uses double curly braces for JSON examples
            # We only need to replace the company_specific_questions placeholder
            prompt_text = DRIVER_SCREENING_PROMPT_TEMPLATE.replace(
                "{{company_specific_questions}}", company_questions_text
            )
        
        return ChatPromptTemplate.from_messages([
            ("system", prompt_text),
            MessagesPlaceholder("chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])

    def _get_applicant_details(self, dsp_code: str):
        """
        Get applicant details from the DSP API
        
        Args:
            dsp_code: The DSP code
            
        Returns:
            Applicant details dict or None if not found
        """
        try:
            # Call the API client through the tool
            result_json = self.screening_tools._get_applicant_details(dsp_code)
            result = json.loads(result_json)
            
            if result.get("success", False):
                return result.get("data")
            else:
                logger.warning(f"Failed to get applicant details: {result.get('message')}")
                return None
        except Exception as e:
            logger.error(f"Error getting applicant details: {e}")
            return None

    def _update_applicant_status(self, dsp_code: str, applicant_name: str, applicant_details: dict):
        """
        Update the applicant status to INPROGRESS
        
        Args:
            dsp_code: The DSP code
            applicant_name: The applicant name
            applicant_details: The applicant details
            
        Returns:
            True if the status was updated successfully, False otherwise
        """
        current_status = applicant_details.get('applicantStatus', 'SENT')
        applicant_id = applicant_details.get('applicantID')
        
        # Create an instance of the DSP API client
        from ..tools.dsp_api_client import DSPApiClient
        api_client = DSPApiClient()
        
        # Update the applicant status - only changing the status field
        status_updated = api_client.update_applicant_status(
            dsp_code=dsp_code,
            applicant_id=applicant_id,  # Pass the applicant ID from the details
            current_status=current_status,
            new_status="INPROGRESS",
            # Pass empty dict to ensure we don't modify any other data
            applicant_data={}
        )
        
        if status_updated:
            logger.info(f"Successfully updated applicant status to INPROGRESS for {applicant_name} (ID: {applicant_id})")
        else:
            logger.warning(f"Failed to update applicant status for {applicant_name} (ID: {applicant_id})")
        
        return status_updated

    def process_message(self, user_input: str, session_id: str, dsp_code: str = None) -> str:
        """
        Process the screening conversation using session-specific memory.
        
        Args:
            user_input: The message from the driver candidate
            session_id: Unique session identifier
            dsp_code: Optional DSP code to get company-specific questions
            
        Returns:
            Response from the agent
        """
        logger.info(f"Processing message for session_id: {session_id}, dsp_code: {dsp_code}")
        logger.info(f"Received user input: '{user_input}'")
        
        # Validate session_id
        if not session_id or session_id.strip() == "":
            # Generate a unique session ID if none provided
            import time
            timestamp = int(time.time())
            session_id = f"SESSION-{timestamp}"
            logger.info(f"Generated new session_id: {session_id}")
        
        # Create a unique session ID that includes the dsp_code to ensure
        # we get the right prompt with company-specific questions
        unique_session_id = f"{session_id}_{dsp_code}" if dsp_code else session_id
        
        # Check if this is a new session
        is_new_session = not self.session_manager.session_exists(unique_session_id)
        
        # Get applicant details if dsp_code is provided and this is the first message
        applicant_name = None
        applicant_details = None
        
        if dsp_code and is_new_session:
            logger.info(f"New session detected. Fetching applicant details for DSP code: {dsp_code}")
            applicant_details = self._get_applicant_details(dsp_code)
            
            if applicant_details:
                # Format the full name from first and last name
                first_name = applicant_details.get('firstName', '').strip()
                last_name = applicant_details.get('lastName', '').strip()
                applicant_name = f"{first_name} {last_name}".strip()
                logger.info(f"Found applicant name: {applicant_name}")
                
                # Update the applicant status to INPROGRESS
                self._update_applicant_status(dsp_code, applicant_name, applicant_details)
            else:
                logger.warning(f"Could not retrieve applicant details for DSP code: {dsp_code}")
        
        # Create the prompt with company-specific questions and applicant name if available
        prompt = self._create_prompt(dsp_code, applicant_name)
        
        # Get or create session executor using the session manager
        executor = self.session_manager.get_or_create_session(
            session_id=unique_session_id,
            llm=self.llm,
            tools=self.tools,
            prompt=prompt
        )
        
        # For the first message in a new session with applicant details,
        # we want to ensure the agent greets the applicant by name
        if is_new_session and applicant_name:
            # For the first message, we'll use a special trigger to ensure the agent
            # starts with the personalized greeting
            if not user_input.strip() or user_input.lower().strip() in ["hi", "hello", "hey"]:
                # Replace with a special trigger that the agent will recognize
                user_input = "START_GREETING"
                logger.info("Using special greeting trigger for first message")
        
        # Add session_id, dsp_code, and applicant_details to the input context
        input_context = {
            "input": user_input,
            "session_id": session_id,
            "dsp_code": dsp_code if dsp_code else "unknown"
        }
        
        # Add applicant details to the context if available
        if applicant_details:
            input_context["applicant_details"] = applicant_details
            # Also add the name directly for easier access
            if applicant_name:
                input_context["applicant_name"] = applicant_name
        
        response = executor.invoke(input_context)
        logger.info("Message processed successfully")
        return response["output"]

def main():
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("Please set OPENAI_API_KEY environment variable")
    
    agent = DriverScreeningAgent(api_key)
    
    print("Driver Screening Started! Type 'q' or 'quit' to exit.")
    
    # Ask for DSP code
    dsp_code = input("Enter DSP code (or leave blank for default questions): ").strip()
    
    # Generate a unique session ID
    import time
    timestamp = int(time.time())
    session_id = f"SESSION-{timestamp}"
    
    if dsp_code:
        # Send an empty first message to trigger the greeting with the applicant's name
        print("\nFetching applicant details and starting conversation...")
        first_response = agent.process_message("", session_id, dsp_code)
        print("\nResponse:", first_response)
    
    while True:
        user_input = input("\nEnter your message: ").strip().lower()
        
        if user_input in ['q', 'quit']:
            print("\nScreening ended.")
            break
        
        response = agent.process_message(user_input, session_id, dsp_code if dsp_code else None)
        print("\nResponse:", response)

if __name__ == "__main__":
    main()
