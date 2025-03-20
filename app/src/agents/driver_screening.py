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
        
        prompt_text = DRIVER_SCREENING_PROMPT_TEMPLATE.format(
            company_specific_questions=company_questions_text
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
