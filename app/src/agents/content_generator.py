from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain.tools import Tool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
import os
from dotenv import load_dotenv
from ..prompts.content_generator import CONTENT_PROMPT
from ..utils.session_manager import get_session_manager
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ContentGeneratorAgent:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.llm = ChatOpenAI(temperature=0.7, api_key=api_key, model="gpt-4o-mini")
        self.session_manager = get_session_manager()
        self.tools = [
            Tool(
                name="content_generator",
                description="Generates creative content based on user input",
                func=lambda x: f"Generated content: {x}"
            )
        ]
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", CONTENT_PROMPT),
            MessagesPlaceholder("chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])

    def process_message(self, user_input: str, session_id: str) -> str:
        """Process the user's message using session-specific memory."""
        logger.info(f"Processing message for session_id: {session_id}")
        
        # Get or create session executor using the session manager
        executor = self.session_manager.get_or_create_session(
            session_id=session_id,
            llm=self.llm,
            tools=self.tools,
            prompt=self.prompt,
            memory_k=20  # Use a smaller memory size for content generation
        )
        
        response = executor.invoke({"input": user_input})
        logger.info("Message processed successfully")
        return response["output"]

def main():
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("Please set OPENAI_API_KEY environment variable")
    
    agent = ContentGeneratorAgent(api_key)
    
    print("Chat started! Type 'q' or 'quit' to exit.")
    while True:
        user_input = input("\nEnter your message: ").strip().lower()
        
        if user_input in ['q', 'quit']:
            print("\nChat ended.")
            break
        
        session_id = "default_session"  # You can modify this to use different session IDs
        response = agent.process_message(user_input, session_id)
        print("\nResponse:", response)


if __name__ == "__main__":
    main()
