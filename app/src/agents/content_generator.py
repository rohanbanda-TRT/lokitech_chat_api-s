import os
import uuid
import logging
from typing import Annotated, TypedDict, Dict, Any, Optional
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver

from ..prompts.content_generator import CONTENT_PROMPT

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class ContentGeneratorState(TypedDict):
    """State schema for the content generator graph."""
    messages: Annotated[list[BaseMessage], add_messages]
    # Additional fields can be added here if needed


class ContentGeneratorAgent:
    """Content Generator Agent implemented using LangGraph."""
    
    def __init__(self, api_key: str = None):
        """
        Initialize the content generator agent with LangGraph.
        
        Args:
            api_key: OpenAI API key. If not provided, will try to get from environment.
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key is required. Please provide it or set OPENAI_API_KEY environment variable.")
        
        self.llm = ChatOpenAI(temperature=0.7, api_key=self.api_key, model="gpt-4o-mini")
        self.memory = MemorySaver()
        self.graph = self._create_graph()
        logger.info("ContentGeneratorAgent initialized with LangGraph implementation")
    
    def _create_graph(self) -> StateGraph:
        """
        Create the LangGraph for content generation.
        
        Returns:
            Compiled StateGraph
        """
        # Create the graph builder with our state schema
        graph_builder = StateGraph(ContentGeneratorState)
        
        # Define the content generator node
        def content_generator(state: ContentGeneratorState) -> Dict[str, Any]:
            """Process messages and generate content."""
            # Format system message with the content prompt
            system_message = {"role": "system", "content": CONTENT_PROMPT}
            
            # Prepare messages for the LLM
            messages = [system_message] + [
                {"role": m.type, "content": m.content} 
                for m in state["messages"]
            ]
            
            # Call the LLM
            response = self.llm.invoke(messages)
            
            # Return updated state with the new AI message
            return {"messages": [response]}
        
        # Add the node to the graph
        graph_builder.add_node("content_generator", content_generator)
        
        # Add edges
        graph_builder.add_edge(START, "content_generator")
        graph_builder.add_edge("content_generator", END)
        
        # Compile the graph with the memory saver
        return graph_builder.compile(checkpointer=self.memory)
    
    def process_message(self, user_input: str, session_id: str = None) -> str:
        """
        Process a message using the content generator.
        
        Args:
            user_input: The user message to process
            session_id: Optional session ID for conversation persistence
                        If not provided, a new UUID will be generated
        
        Returns:
            Generated response from the agent
        """
        # Generate a session ID if not provided
        if not session_id:
            session_id = str(uuid.uuid4())
            logger.info(f"Generated new session_id: {session_id}")
        else:
            logger.info(f"Using existing session_id: {session_id}")
        
        # Create a human message
        human_message = HumanMessage(content=user_input)
        
        # Set up the config for this session
        config = {"configurable": {"thread_id": session_id}}
        
        # Invoke the graph with the message
        result = self.graph.invoke(
            {"messages": [human_message]},
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
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("Please set OPENAI_API_KEY environment variable")
    
    agent = ContentGeneratorAgent(api_key)
    
    print("Chat started! Type 'q' or 'quit' to exit.")
    session_id = str(uuid.uuid4())
    print(f"Session ID: {session_id}")
    
    while True:
        user_input = input("\nEnter your message: ").strip()
        
        if user_input.lower() in ['q', 'quit']:
            print("\nChat ended.")
            break
        
        response = agent.process_message(user_input, session_id)
        print("\nResponse:", response)


if __name__ == "__main__":
    main()
