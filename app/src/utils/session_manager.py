"""
Session management utilities for agent conversations.
This module provides a centralized way to manage conversation sessions across different agents.
"""

from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain.memory import ConversationBufferMemory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
from typing import List, Dict, Any, Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SessionManager:
    """
    Manages conversation sessions for agents.
    Provides methods to create and retrieve session-specific agent executors.
    """
    
    def __init__(self):
        """Initialize the session manager with an empty sessions dictionary."""
        self.sessions = {}
        logger.info("SessionManager initialized")
    
    def get_or_create_session(
        self, 
        session_id: str, 
        llm: ChatOpenAI,
        tools: List[Any],
        prompt: ChatPromptTemplate,
        memory_k: int = 30,
        verbose: bool = True
    ) -> AgentExecutor:
        """
        Get an existing session or create a new one if it doesn't exist.
        
        Args:
            session_id: Unique identifier for the session
            llm: Language model to use for the agent
            tools: List of tools available to the agent
            prompt: Chat prompt template for the agent
            memory_k: Number of previous exchanges to keep in memory
            verbose: Whether to enable verbose output for the agent executor
            
        Returns:
            AgentExecutor for the session
        """
        # Create a unique key for this agent type + session combination
        agent_type = llm.__class__.__name__
        key = f"{agent_type}_{session_id}"
        
        if key not in self.sessions:
            logger.info(f"Creating new session executor for key: {key}")
            
            # Create memory for the session
            memory = ConversationBufferMemory(
                memory_key="chat_history",
                input_key="input",
                return_messages=True,
                k=memory_k
            )
            
            # Create the agent
            agent = create_openai_tools_agent(
                llm=llm,
                tools=tools,
                prompt=prompt
            )
            
            # Create the executor
            self.sessions[key] = AgentExecutor(
                agent=agent,
                tools=tools,
                memory=memory,
                verbose=verbose
            )
        
        return self.sessions[key]
    
    def clear_session(self, session_id: str, agent_type: Optional[str] = None) -> bool:
        """
        Clear a specific session from memory.
        
        Args:
            session_id: The session ID to clear
            agent_type: Optional agent type to specify which agent's session to clear
            
        Returns:
            True if session was found and cleared, False otherwise
        """
        if agent_type:
            key = f"{agent_type}_{session_id}"
            if key in self.sessions:
                del self.sessions[key]
                logger.info(f"Cleared session with key: {key}")
                return True
        else:
            # Clear all sessions with this session_id regardless of agent type
            keys_to_delete = [k for k in self.sessions.keys() if k.endswith(f"_{session_id}")]
            for key in keys_to_delete:
                del self.sessions[key]
                logger.info(f"Cleared session with key: {key}")
            return len(keys_to_delete) > 0
        
        return False
    
    def get_all_sessions(self) -> Dict[str, AgentExecutor]:
        """
        Get all active sessions.
        
        Returns:
            Dictionary of session keys to agent executors
        """
        return self.sessions

# Create a singleton instance of the session manager
session_manager = SessionManager()

def get_session_manager() -> SessionManager:
    """
    Get the singleton instance of the session manager.
    
    Returns:
        SessionManager instance
    """
    return session_manager
