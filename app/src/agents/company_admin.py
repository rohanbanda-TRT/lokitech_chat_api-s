from langchain.tools import Tool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import JsonOutputParser
from typing import Optional
import logging
from ..prompts.company_admin import COMPANY_ADMIN_PROMPT
from ..utils.session_manager import get_session_manager
from ..models.question_models import CompanyQuestions
from ..managers.company_questions_manager import CompanyQuestionsManager
from ..tools.company_admin_tools import CompanyAdminTools

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CompanyAdminAgent:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.llm = ChatOpenAI(temperature=0.7, api_key=api_key, model="gpt-4o-mini")
        self.questions_manager = CompanyQuestionsManager()
        self.session_manager = get_session_manager()
        self.admin_tools = CompanyAdminTools()
        
        # Set up JSON output parser with Pydantic schema
        self.parser = JsonOutputParser(pydantic_object=CompanyQuestions)
        
        self.tools = [
            Tool(
                name="create_questions",
                description="Create or add new questions to the database",
                func=self.admin_tools.create_questions
            ),
            Tool(
                name="get_questions",
                description="Retrieve existing questions for a company",
                func=self.admin_tools.get_questions
            ),
            Tool(
                name="update_question",
                description="Update a specific question for a company",
                func=self.admin_tools.update_question
            ),
            Tool(
                name="delete_question",
                description="Delete a specific question for a company",
                func=self.admin_tools.delete_question
            )
        ]
        
        # Create prompt without directly embedding the format_instructions
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", COMPANY_ADMIN_PROMPT),
            MessagesPlaceholder("chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])
        
        logger.info("CompanyAdminAgent initialized with JsonOutputParser")
    
    def process_message(self, user_input: str, session_id: str, dsp_code: Optional[str] = None) -> str:
        """
        Process messages from company admin to collect and manage questions
        
        Args:
            user_input: The message from the company admin
            session_id: Unique session identifier
            dsp_code: Optional DSP code if already known
            
        Returns:
            Response from the agent
        """
        logger.info(f"Processing message for session_id: {session_id}, dsp_code: {dsp_code}")
        
        # Get or create session executor using the session manager
        executor = self.session_manager.get_or_create_session(
            session_id=session_id,
            llm=self.llm,
            tools=self.tools,
            prompt=self.prompt
        )
        # If dsp_code is provided and this is the first message, include it
        if dsp_code and (not executor.memory.chat_memory.messages or 
                          f"DSP Code: {dsp_code}" not in executor.memory.chat_memory.messages[0].content):
            logger.info(f"Adding dsp_code {dsp_code} to first message")
            modified_input = f"DSP Code: {dsp_code}. Query : {user_input}"
        else:
            modified_input = user_input
        
        logger.info(f"Modified input: {modified_input}")
        response = executor.invoke({"input": modified_input})
        logger.info("Message processed successfully")
        return response["output"]
