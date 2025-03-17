from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain.tools import Tool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.memory import ConversationBufferMemory
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import JsonOutputParser
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
import json
import logging
from ..core.company_questions import CompanyQuestionsManager
from ..prompts.company_admin import COMPANY_ADMIN_PROMPT

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class Question(BaseModel):
    question_text: str = Field(description="The text of the question to ask the driver")
    required: bool = Field(default=False, description="Whether this question is required to be answered")

class CompanyQuestions(BaseModel):
    company_id: str = Field(description="Unique identifier for the company")
    questions: List[Question] = Field(description="List of screening questions for driver candidates")

class CompanyAdminAgent:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.session_memories = {}
        self.llm = ChatOpenAI(temperature=0.7, api_key=api_key, model="gpt-4o-mini")
        self.questions_manager = CompanyQuestionsManager()
        
        # Set up JSON output parser with Pydantic schema
        self.parser = JsonOutputParser(pydantic_object=CompanyQuestions)
        
        self.tools = [
            Tool(
                name="save_questions",
                description="Save the collected questions to the database",
                func=self._save_questions
            ),
            Tool(
                name="get_questions",
                description="Retrieve existing questions for a company",
                func=self._get_questions
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
    
    def _save_questions(self, input_str: str) -> str:
        """Tool function to save questions to the database"""
        try:
            logger.info(f"Attempting to save questions with input: {input_str}")
            
            # Parse the input data
            try:
                # If input is a string, try to parse it as JSON
                if isinstance(input_str, str):
                    data = json.loads(input_str)
                # If input is already a dict or list, use it directly
                elif isinstance(input_str, (dict, list)):
                    data = input_str
                else:
                    logger.error(f"Unexpected input type: {type(input_str)}")
                    return f"Error: Unexpected input type: {type(input_str)}"
                
                logger.info(f"Parsed data: {data}")
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON: {e}")
                return f"Error: Invalid JSON format - {str(e)}"
            
            # Handle different input formats
            if isinstance(data, dict):
                # Check if it's a properly formatted CompanyQuestions object
                if "company_id" in data and "questions" in data:
                    # Validate with Pydantic
                    try:
                        validated_data = CompanyQuestions.model_validate(data)
                        
                        # Convert to dict for database storage
                        questions_dict = [q.model_dump() for q in validated_data.questions]
                        
                        # Save to database
                        success = self.questions_manager.save_questions(
                            validated_data.company_id, 
                            questions_dict
                        )
                        
                        if success:
                            logger.info(f"Successfully saved {len(questions_dict)} questions for company {validated_data.company_id}")
                            return f"Successfully saved {len(questions_dict)} questions for company {validated_data.company_id}"
                        else:
                            logger.error("Failed to save questions to database")
                            return "Failed to save questions to database"
                    except Exception as e:
                        logger.error(f"Error validating data: {e}")
                        return f"Error validating data: {str(e)}"
                else:
                    logger.error("Missing required fields in input")
                    return "Error: Input must contain 'company_id' and 'questions' fields"
            elif isinstance(data, list):
                # If it's just a list of questions, we need a company_id from the conversation
                logger.error("Cannot process list without company_id")
                return "Error: When providing a list of questions, you must also provide a company_id"
            else:
                logger.error(f"Unexpected data format: {type(data)}")
                return f"Error: Unexpected data format: {type(data)}"
            
        except Exception as e:
            logger.error(f"Unexpected error in _save_questions: {e}")
            return f"Error: {str(e)}"
    
    def _get_questions(self, company_id: str) -> str:
        """Tool function to retrieve questions from the database"""
        try:
            logger.info(f"Retrieving questions for company_id: {company_id}")
            questions = self.questions_manager.get_questions(company_id)
            return json.dumps(questions)
        except Exception as e:
            logger.error(f"Error retrieving questions: {e}")
            return f"Error retrieving questions: {str(e)}"
    
    def get_session_executor(self, session_id: str) -> AgentExecutor:
        """Get or create a session-specific agent executor"""
        if session_id not in self.session_memories:
            logger.info(f"Creating new session executor for session_id: {session_id}")
            memory = ConversationBufferMemory(
                memory_key="chat_history",
                input_key="input",
                return_messages=True,
                k=30
            )
            agent = create_openai_tools_agent(
                llm=self.llm,
                tools=self.tools,
                prompt=self.prompt
            )
            self.session_memories[session_id] = AgentExecutor(
                agent=agent,
                tools=self.tools,
                memory=memory,
                verbose=True
            )
        return self.session_memories[session_id]
    
    def process_message(self, user_input: str, session_id: str, company_id: Optional[str] = None) -> str:
        """
        Process messages from company admin to collect and manage questions
        
        Args:
            user_input: The message from the company admin
            session_id: Unique session identifier
            company_id: Optional company ID if already known
            
        Returns:
            Response from the agent
        """
        logger.info(f"Processing message for session_id: {session_id}, company_id: {company_id}")
        executor = self.get_session_executor(session_id)
        
        # If company_id is provided and this is the first message, include it
        if company_id and "company_id" not in str(executor.memory.chat_memory.messages):
            logger.info(f"Adding company_id {company_id} to first message")
            modified_input = f"I'm from company {company_id}. {user_input}"
        else:
            modified_input = user_input
        
        logger.info(f"Modified input: {modified_input}")
        response = executor.invoke({"input": modified_input})
        logger.info("Message processed successfully")
        return response["output"]
