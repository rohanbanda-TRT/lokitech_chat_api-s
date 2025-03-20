from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain.tools import Tool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
import os
from dotenv import load_dotenv
from ..managers.company_questions_manager import CompanyQuestionsManager
import json
from ..prompts.driver_screening import DRIVER_SCREENING_PROMPT_TEMPLATE
from ..utils.session_manager import get_session_manager
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DriverScreeningAgent:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.llm = ChatOpenAI(temperature=0.7, api_key=api_key, model="gpt-4o-mini")
        self.questions_manager = CompanyQuestionsManager()
        self.session_manager = get_session_manager()
        self.tools = [
            Tool(
                name="driver_screening",
                description="Conducts structured driver screening conversations",
                func=lambda x: f"Screening response: {x}"
            )
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
            required_text = " (Required)" if q.get("required", False) else " (Optional)"
            formatted_questions.append(f"   - Ask Question {i}: \"{q['question_text']}\"{required_text}")
            if q.get("required", False):
                formatted_questions.append(f"     * This question is required. If the driver does not provide a clear answer, politely ask again.")
            else:
                formatted_questions.append(f"     * This question is optional. The driver may choose not to answer.")
        
        return "\n".join(formatted_questions)
    
    def _get_static_user_details(self, user_id: str = None) -> dict:
        """
        Get static user details for the prompt
        
        Args:
            user_id: Optional user ID to retrieve specific user details
            
        Returns:
            Dictionary containing user details
        """
        # For now, return static user details
        # In the future, this could be fetched from a database or API
        static_user_details = {
            "user_id": "12345",
            "first_name": "John",
            "last_name": "Doe",
            "email": "john.doe@example.com",
            "mobile_number": "1234500000"
        }
        
        return static_user_details
    
    def _format_user_details_text(self, user_details: dict) -> str:
        """
        Format user details for the prompt
        
        Args:
            user_details: Dictionary containing user details
            
        Returns:
            Formatted string of user details
        """
        if not user_details:
            return "No user details provided. Ask for the driver's name first."
        
        full_name = f"{user_details.get('first_name', '')} {user_details.get('last_name', '')}".strip()
        first_name = user_details.get('first_name', '')
        
        return f"""
        User Details:
        - User ID: {user_details.get('user_id', 'Not provided')}
        - Name: {full_name}
        - Email: {user_details.get('email', 'Not provided')}
        - Mobile Number: {user_details.get('mobile_number', 'Not provided')}

        IMPORTANT: The user's first name is "{first_name}". Greet them directly using this name.
"""
    
    def _create_prompt(self, dsp_code: str = None, user_details = None, user_id: str = None):
        """
        Create a prompt with company-specific questions if available
        
        Args:
            dsp_code: Optional DSP code to get company-specific questions
            user_details: Optional user details for personalized conversation
            user_id: Optional user ID to retrieve static user details
            
        Returns:
            Formatted prompt template
        """
        # Format the prompt with company-specific questions if available
        company_questions_text = "   - No company-specific questions defined. Skip this section."
        if dsp_code:
            company_questions_text = self._get_company_specific_questions_text(dsp_code)
        
        # Format user details if available or get static user details
        user_details_text = "No user details provided. Ask for the driver's name first."
        if user_details:
            # If user_details is a dictionary
            if isinstance(user_details, dict):
                user_details_text = self._format_user_details_text(user_details)
            # If user_details is a UserDetails object
            else:
                full_name = f"{user_details.first_name or ''} {user_details.last_name or ''}".strip()
                user_details_text = f"""
                    User Details:
                    - User ID: {user_details.user_id or 'Not provided'}
                    - Name: {full_name}
                    - Email: {user_details.email or 'Not provided'}
                    - Mobile Number: {user_details.mobile_number or 'Not provided'}

                    IMPORTANT: The user's first name is "{user_details.first_name}". Greet them directly using this name.
                    """
        elif user_id:
            # Get static user details based on user_id
            static_user_details = self._get_static_user_details(user_id)
            user_details_text = self._format_user_details_text(static_user_details)
        
        prompt_text = DRIVER_SCREENING_PROMPT_TEMPLATE.format(
            company_specific_questions=company_questions_text,
            user_details=user_details_text
        )
        
        return ChatPromptTemplate.from_messages([
            ("system", prompt_text),
            MessagesPlaceholder("chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])

    def process_message(self, user_input: str, session_id: str, dsp_code: str = None, user_details = None, user_id: str = None):
        """
        Process the screening conversation using session-specific memory.
        
        Args:
            user_input: The message from the driver candidate
            session_id: Unique session identifier
            dsp_code: Optional DSP code to get company-specific questions
            user_details: Optional user details for personalized conversation
            user_id: Optional user ID to retrieve static user details
            
        Returns:
            Response from the agent
        """
        logger.info(f"Processing message for session_id: {session_id}, dsp_code: {dsp_code}")
        
        # Create a unique session ID that includes the dsp_code to ensure
        # we get the right prompt with company-specific questions
        unique_session_id = f"{session_id}_{dsp_code}" if dsp_code else session_id
        
        # Create the prompt with company-specific questions
        prompt = self._create_prompt(dsp_code, user_details, user_id)
        
        # Get or create session executor using the session manager
        executor = self.session_manager.get_or_create_session(
            session_id=unique_session_id,
            llm=self.llm,
            tools=self.tools,
            prompt=prompt
        )
        
        response = executor.invoke({"input": user_input})
        logger.info("Message processed successfully")
        return response["output"]

def main():
    """
    Example usage of the DriverScreeningAgent
    """
    import os
    import uuid
    
    # Get API key from environment variable
    api_key = os.environ.get("OPENAI_API_KEY", "")
    
    # Create the agent
    agent = DriverScreeningAgent(api_key)
    
    # Create a unique session ID
    session_id = str(uuid.uuid4())
    
    # Example with user_id (static user details)
    print("\n=== Example with user_id (static user details) ===")
    response = agent.process_message("Hello", f"{session_id}_with_user_id", None, None, "12345")
    print(f"Agent: {response}")
    
    # Example without user details
    print("\n=== Example without user details ===")
    response = agent.process_message("Hello", session_id)
    print(f"Agent: {response}")

if __name__ == "__main__":
    main()
