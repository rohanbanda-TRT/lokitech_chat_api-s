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
        
    def _get_company_specific_questions_text(self, company_id: str) -> str:
        """
        Get company-specific questions formatted for the prompt
        
        Args:
            company_id: The unique identifier for the company
            
        Returns:
            Formatted string of company-specific questions
        """
        questions = self.questions_manager.get_questions(company_id)
        
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
    
    def _create_prompt(self, company_id: str = None) -> ChatPromptTemplate:
        """
        Create a prompt with company-specific questions if available
        
        Args:
            company_id: Optional company ID to get company-specific questions
            
        Returns:
            Formatted prompt template
        """
        # Format the prompt with company-specific questions if available
        company_questions_text = "   - No company-specific questions defined. Skip this section."
        if company_id:
            company_questions_text = self._get_company_specific_questions_text(company_id)
        
        prompt_text = DRIVER_SCREENING_PROMPT_TEMPLATE.format(
            company_specific_questions=company_questions_text
        )
        
        return ChatPromptTemplate.from_messages([
            ("system", prompt_text),
            MessagesPlaceholder("chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])

    def process_message(self, user_input: str, session_id: str, company_id: str = None) -> str:
        """
        Process the screening conversation using session-specific memory.
        
        Args:
            user_input: The message from the driver candidate
            session_id: Unique session identifier
            company_id: Optional company ID to get company-specific questions
            
        Returns:
            Response from the agent
        """
        logger.info(f"Processing message for session_id: {session_id}, company_id: {company_id}")
        
        # Create a unique session ID that includes the company_id to ensure
        # we get the right prompt with company-specific questions
        unique_session_id = f"{session_id}_{company_id}" if company_id else session_id
        
        # Create the prompt with company-specific questions
        prompt = self._create_prompt(company_id)
        
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
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("Please set OPENAI_API_KEY environment variable")
    
    agent = DriverScreeningAgent(api_key)
    
    print("Driver Screening Started! Type 'q' or 'quit' to exit.")
    
    # Ask for company ID
    company_id = input("Enter company ID (or leave blank for default questions): ").strip()
    
    while True:
        user_input = input("\nEnter your message: ").strip().lower()
        
        if user_input in ['q', 'quit']:
            print("\nScreening ended.")
            break
        
        session_id = "default_session"  # You can modify this to use different session IDs
        response = agent.process_message(user_input, session_id, company_id if company_id else None)
        print("\nResponse:", response)

if __name__ == "__main__":
    main()
