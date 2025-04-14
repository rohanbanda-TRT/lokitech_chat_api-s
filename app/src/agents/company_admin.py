"""
Company Admin Agent implemented using LangGraph with ReAct pattern.
This module provides a LangGraph-based implementation of the company admin agent.
"""

import os
import logging
import uuid
import json
import re
from typing import Annotated, TypedDict, Dict, Any, Optional

from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_core.tools import BaseTool, Tool
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver

from ..prompts.company_admin import COMPANY_ADMIN_PROMPT
from ..models.question_models import CompanyQuestions
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

        # Set up tools using the standard Tool class
        self.tools = [
            Tool(
                name="create_questions",
                description="Create or add new questions to the database",
                func=self.admin_tools.create_questions,
            ),
            Tool(
                name="get_questions",
                description="Retrieve existing questions for a company",
                func=self.admin_tools.get_questions,
            ),
            Tool(
                name="update_question",
                description="Update a specific question for a company",
                func=self.admin_tools.update_question,
            ),
            Tool(
                name="delete_question",
                description="Delete a specific question for a company",
                func=self.admin_tools.delete_question,
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

        # Create the agent executor
        self.agent_executor = AgentExecutor(agent=self.agent, tools=self.tools)

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

                # If it's a tool exception related to delete_question, try to handle it
                if "Too many arguments to single-input tool delete_question" in str(e):
                    try:
                        # Extract the DSP code and question index from the error message
                        error_msg = str(e)
                        match = re.search(r"Args: \['([^']+)', (\d+)\]", error_msg)
                        if match:
                            dsp_code = match.group(1)
                            question_index = int(match.group(2))

                            # Create a proper JSON input for delete_question
                            delete_input = json.dumps(
                                {
                                    "dsp_code": dsp_code,
                                    "question_index": question_index,  # Use 0-based indexing
                                }
                            )

                            # Call the delete_question tool directly
                            result = self.admin_tools.delete_question(delete_input)
                            return {
                                "messages": [
                                    AIMessage(
                                        content=f"I've deleted the question as requested. {result}"
                                    )
                                ]
                            }
                    except Exception as inner_e:
                        logger.error(
                            f"Error handling delete_question exception: {str(inner_e)}"
                        )

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
