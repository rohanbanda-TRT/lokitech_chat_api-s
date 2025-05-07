"""
Company Admin Agent implemented using LangGraph with ReAct pattern.
This module provides a LangGraph-based implementation of the company admin agent.
"""

import os
import logging
import uuid
import json
import re
from typing import Annotated, TypedDict, Dict, Any, Optional, List

from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_core.tools import BaseTool, Tool, StructuredTool
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from pydantic import BaseModel, Field

from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver

from ..prompts.company_admin import COMPANY_ADMIN_PROMPT
from ..models.question_models import CompanyQuestions, Question
from ..managers.company_questions_factory import get_company_questions_manager
from ..tools.company_admin_tools import CompanyAdminTools

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class CompanyAdminState(TypedDict):
    """State schema for the company admin graph."""

    messages: Annotated[list[BaseMessage], add_messages]
    dsp_code: Optional[str]


# Tool input schemas
class CreateQuestionsInput(BaseModel):
    dsp_code: str = Field(description="Unique identifier for the company")
    questions: Optional[List[Dict[str, Any]]] = Field(default=None, description="List of questions with question_text and criteria")
    time_slots: Optional[List[str]] = Field(default=None, description="Available time slots for screening")
    contact_info: Optional[Dict[str, Any]] = Field(default=None, description="Structured contact information with contact_person_name, contact_number, and email_id fields")
    append: bool = Field(default=True, description="Whether to append to existing questions or replace them")


class GetQuestionsInput(BaseModel):
    dsp_code: str = Field(description="Unique identifier for the company")


class UpdateQuestionToolInput(BaseModel):
    dsp_code: str = Field(description="Unique identifier for the company")
    question_index: int = Field(description="Index of the question to update (0-based)")
    updated_question: Dict[str, Any] = Field(description="Updated question data")


class DeleteQuestionToolInput(BaseModel):
    dsp_code: str = Field(description="Unique identifier for the company")
    question_index: int = Field(description="Index of the question to delete (0-based)")


class UpdateTimeSlotsToolInput(BaseModel):
    dsp_code: str = Field(description="Unique identifier for the company")
    time_slots: List[str] = Field(description="Available time slots for screening")


class UpdateContactInfoToolInput(BaseModel):
    dsp_code: str = Field(description="Unique identifier for the company")
    contact_info: Dict[str, Any] = Field(description="Structured contact information with contact_person_name, contact_number, and email_id fields")


class CompanyAdminAgent:
    """Company Admin Agent implemented using LangGraph with ReAct pattern."""

    def __init__(self, api_key: str = None):
        """
        Initialize the company admin agent with LangGraph.

        Args:
            api_key: OpenAI API key. If not provided, will try to get from environment.
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "OpenAI API key is required. Please provide it or set OPENAI_API_KEY environment variable."
            )

        self.llm = ChatOpenAI(
            temperature=0.7, api_key=self.api_key, model="gpt-4o-mini"
        )
        self.memory = MemorySaver()

        # Use the same tools as in the original implementation
        self.admin_tools = CompanyAdminTools()

        # Helper methods for tools
        def create_questions_tool(data: CreateQuestionsInput) -> str:
            """Create or update company questions, time slots, and contact info"""
            # Convert to dict for the tool
            input_data = {
                "dsp_code": data.dsp_code,
                "append": data.append
            }
            
            # Add optional fields if provided
            if data.questions is not None:
                input_data["questions"] = data.questions
            if data.time_slots is not None:
                input_data["time_slots"] = data.time_slots
            if data.contact_info is not None:
                # Ensure contact_info has all required fields
                if not all(key in data.contact_info for key in ["contact_person_name", "contact_number", "email_id"]):
                    return "Error: Contact info must include contact_person_name, contact_number, and email_id fields"
                input_data["contact_info"] = data.contact_info
                
            return self.admin_tools.create_questions(json.dumps(input_data))
            
        def get_questions_tool(data: GetQuestionsInput) -> str:
            """Get company questions, time slots, and contact info"""
            return self.admin_tools.get_questions(data.dsp_code)
            
        def update_question_tool(data: UpdateQuestionToolInput) -> str:
            """Update a specific question"""
            return self.admin_tools.update_question(json.dumps(data.model_dump()))
            
        def delete_question_tool(data: DeleteQuestionToolInput) -> str:
            """Delete a specific question"""
            return self.admin_tools.delete_question(json.dumps(data.model_dump()))
            
        def update_time_slots_tool(data: UpdateTimeSlotsToolInput) -> str:
            """Update time slots"""
            return self.admin_tools.update_time_slots(json.dumps(data.model_dump()))
            
        def update_contact_info_tool(data: UpdateContactInfoToolInput) -> str:
            """Update contact info"""
            # Ensure contact_info has all required fields
            if not all(key in data.contact_info for key in ["contact_person_name", "contact_number", "email_id"]):
                return "Error: Contact info must include contact_person_name, contact_number, and email_id fields"
                
            # Convert to dict for the tool
            input_data = {
                "dsp_code": data.dsp_code,
                "contact_info": data.contact_info
            }
            return self.admin_tools.update_contact_info(json.dumps(input_data))

        # Set up tools using StructuredTool for better argument handling
        self.tools = [
            StructuredTool.from_function(
                func=create_questions_tool,
                name="create_questions",
                description="Create or add new questions, time slots, and contact info to the database",
            ),
            StructuredTool.from_function(
                func=get_questions_tool,
                name="get_questions",
                description="Retrieve existing questions, time slots, and contact info for a company",
            ),
            StructuredTool.from_function(
                func=update_question_tool,
                name="update_question",
                description="Update a specific question for a company",
            ),
            StructuredTool.from_function(
                func=delete_question_tool,
                name="delete_question",
                description="Delete a specific question for a company",
            ),
            StructuredTool.from_function(
                func=update_time_slots_tool,
                name="update_time_slots",
                description="Update available time slots for a company",
            ),
            StructuredTool.from_function(
                func=update_contact_info_tool,
                name="update_contact_info",
                description="Update contact information for a company",
            ),
        ]

        # Create the prompt
        self.prompt = ChatPromptTemplate.from_messages(
            [
                ("system", COMPANY_ADMIN_PROMPT),
                MessagesPlaceholder(variable_name="chat_history"),
                ("human", "{input}"),
                MessagesPlaceholder(variable_name="agent_scratchpad"),
            ]
        )

        # Create the agent using LangChain's create_openai_tools_agent
        self.agent = create_openai_tools_agent(self.llm, self.tools, self.prompt)

        # Create the agent executor with proper configuration
        self.agent_executor = AgentExecutor(
            agent=self.agent, 
            tools=self.tools,
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=5,
            early_stopping_method="generate"
        )

        # Build the graph
        self.graph = self._create_graph()
        logger.info("CompanyAdminAgent initialized with ReAct agent")

    def _create_graph(self) -> StateGraph:
        """
        Create the LangGraph for the company admin agent.

        Returns:
            Compiled StateGraph
        """
        # Create the graph builder with our state schema
        graph_builder = StateGraph(CompanyAdminState)

        # Define the agent node
        def agent_node(state: CompanyAdminState) -> Dict[str, Any]:
            """Process messages using the agent."""
            # Extract the last message from the user
            last_message = state["messages"][-1]

            # Check if we need to add DSP code to the message
            if state.get("dsp_code") and "DSP Code:" not in last_message.content:
                modified_input = (
                    f"DSP Code: {state['dsp_code']}. Query: {last_message.content}"
                )
            else:
                modified_input = last_message.content

            # Extract conversation history
            history = []
            if len(state["messages"]) > 1:
                # Skip the last message as it's the current user input
                for msg in state["messages"][:-1]:
                    if isinstance(msg, HumanMessage):
                        history.append(("human", msg.content))
                    elif isinstance(msg, AIMessage):
                        history.append(("ai", msg.content))

            try:
                # Call the agent with history
                result = self.agent_executor.invoke(
                    {"input": modified_input, "chat_history": history}
                )

                # Return the response as an AI message
                return {"messages": [AIMessage(content=result["output"])]}
            except Exception as e:
                # Log the error
                logger.error(f"Error in agent_node: {str(e)}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")

                # Return a generic error message
                return {
                    "messages": [
                        AIMessage(
                            content="I'm sorry, I encountered an error while processing your request. Please try again with more specific instructions."
                        )
                    ]
                }

        # Add the node to the graph
        graph_builder.add_node("agent", agent_node)

        # Add edges
        graph_builder.add_edge(START, "agent")
        graph_builder.add_edge("agent", END)

        # Compile the graph with the memory saver
        return graph_builder.compile(checkpointer=self.memory)

    def process_message(
        self, message: str, session_id: str = None, dsp_code: Optional[str] = None
    ) -> str:
        """
        Process a message using the company admin agent.

        Args:
            message: The user message to process
            session_id: Optional session ID for conversation history
            dsp_code: Optional DSP code if already known

        Returns:
            The generated response
        """
        # Create a unique session ID if not provided
        if not session_id:
            session_id = str(uuid.uuid4())
            logger.info(f"Created new session_id: {session_id}")
        else:
            logger.info(f"Using existing session_id: {session_id}")

        # Create a human message
        human_message = HumanMessage(content=message)

        # Set up the config for this session
        config = {"configurable": {"thread_id": session_id}}

        # Prepare the initial state
        initial_state = {"messages": [human_message]}
        if dsp_code:
            initial_state["dsp_code"] = dsp_code
            logger.info(f"Using dsp_code: {dsp_code}")

        # Invoke the graph with the message
        result = self.graph.invoke(
            initial_state,
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
    """Run a simple CLI demo of the company admin agent."""
    agent = CompanyAdminAgent()

    print("Chat started! Type 'q' or 'quit' to exit.")
    session_id = str(uuid.uuid4())
    print(f"Session ID: {session_id}")

    # Optional DSP code
    dsp_code = input("Enter DSP code (or leave blank): ").strip()
    if not dsp_code:
        dsp_code = None

    while True:
        user_input = input("\nEnter your message: ").strip()

        if user_input.lower() in ["q", "quit"]:
            print("\nChat ended.")
            break

        response = agent.process_message(user_input, session_id, dsp_code)
        print("\nResponse:", response)


if __name__ == "__main__":
    main()
