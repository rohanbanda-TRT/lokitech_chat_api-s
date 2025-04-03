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
from ..prompts.driver_screening import DRIVER_SCREENING_PROMPT_TEMPLATE
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
    
    def _create_prompt(self, dsp_code: str = None) -> ChatPromptTemplate:
        """
        Create a prompt with company-specific questions if available
        
        Args:
            dsp_code: Optional DSP code to get company-specific questions
            
        Returns:
            Formatted prompt template
        """
        # Format the prompt with company-specific questions if available
        company_questions_text = "   - No company-specific questions defined. Skip this section."
        if dsp_code:
            company_questions_text = self._get_company_specific_questions_text(dsp_code)
        
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
        
        # Create the prompt with company-specific questions
        prompt = self._create_prompt(dsp_code)
        
        # Get or create session executor using the session manager
        executor = self.session_manager.get_or_create_session(
            session_id=unique_session_id,
            llm=self.llm,
            tools=self.tools,
            prompt=prompt
        )
        
        # Add session_id and dsp_code to the input context
        input_context = {
            "input": user_input,
            "session_id": session_id,
            "dsp_code": dsp_code if dsp_code else "unknown"
        }
        
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
    
    while True:
        user_input = input("\nEnter your message: ").strip().lower()
        
        if user_input in ['q', 'quit']:
            print("\nScreening ended.")
            break
        
        session_id = "default_session"  # You can modify this to use different session IDs
        response = agent.process_message(user_input, session_id, dsp_code if dsp_code else None)
        print("\nResponse:", response)

if __name__ == "__main__":
    main()
