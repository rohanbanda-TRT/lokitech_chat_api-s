import os
from dotenv import load_dotenv
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from ..prompts.analyzer import ANALYZER_PROMPT_TEMPLATE
import uuid
import logging
from typing import Dict, Any, TypedDict
from langgraph.graph import StateGraph, END

logger = logging.getLogger(__name__)


# Define a simple state schema for the LangGraph
class AnalyzerState(TypedDict):
    """State for the performance analyzer graph."""

    messages: str
    response: str


class PerformanceAnalyzerAgent:
    """
    Agent for analyzing driver performance data using LangGraph.

    This agent processes performance data and generates structured feedback
    and suggestions for improvement.
    """

    def __init__(self, api_key: str):
        """
        Initialize the PerformanceAnalyzerAgent with an OpenAI API key.

        Args:
            api_key: OpenAI API key
        """
        self.api_key = api_key
        self.llm = ChatOpenAI(temperature=0.3, api_key=api_key)
        self.prompt = PromptTemplate(
            input_variables=["messages"], template=ANALYZER_PROMPT_TEMPLATE
        )
        self.parser = StrOutputParser()
        self.graph = self._build_graph()

    def _build_graph(self):
        """
        Build a LangGraph for performance analysis.

        Returns:
            A compiled LangGraph workflow
        """

        # Define the agent node function
        def analyze_agent(state: AnalyzerState) -> AnalyzerState:
            """Process the performance data and generate analysis."""
            # Step 1: Format the prompt
            formatted_prompt = self.prompt.invoke({"messages": state["messages"]})

            # Step 2: Call the LLM
            llm_result = self.llm.invoke(formatted_prompt)

            # Step 3: Parse the output
            parsed_result = self.parser.invoke(llm_result)

            # Return the updated state
            return {"messages": state["messages"], "response": parsed_result}

        # Create the graph
        workflow = StateGraph(AnalyzerState)

        # Add the single agent node
        workflow.add_node("performance_analyzer", analyze_agent)

        # Add edges
        workflow.set_entry_point("performance_analyzer")
        workflow.add_edge("performance_analyzer", END)

        # Compile the graph
        return workflow.compile()

    def analyze_performance(self, performance_data: str, session_id: str = None) -> str:
        """
        Analyze driver performance data and generate structured feedback.

        Args:
            performance_data: String containing performance metrics
            session_id: Optional session ID for conversation tracking

        Returns:
            Structured analysis and suggestions
        """
        # Generate a session ID if not provided
        if not session_id:
            session_id = str(uuid.uuid4())
            logger.info(
                f"Generated new session_id for performance analysis: {session_id}"
            )

        try:
            # Initialize state
            initial_state = {"messages": performance_data, "response": ""}

            # Run the graph
            result = self.graph.invoke(initial_state)

            # Extract the response
            return result["response"]
        except Exception as e:
            logger.error(f"Error analyzing performance with LangGraph: {str(e)}")
            # Fallback to direct LLM call if the graph fails
            try:
                prompt_value = self.prompt.invoke({"messages": performance_data})
                llm_result = self.llm.invoke(prompt_value)
                return self.parser.invoke(llm_result)
            except Exception as inner_e:
                logger.error(f"Fallback also failed: {str(inner_e)}")
                return f"Error analyzing performance data: {str(e)}"


def main():
    """
    Main function to demonstrate the usage of the PerformanceAnalyzerAgent.
    """
    # Load environment variables
    load_dotenv()

    # Get API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("Please set OPENAI_API_KEY environment variable")

    # Create the agent
    agent = PerformanceAnalyzerAgent(api_key)

    # Sample performance data
    sample_data = "Ronaldo Pacora Flores Sign/Signal Violations Rate: 0, POD: 97.8%"

    # Run the analysis
    result = agent.analyze_performance(sample_data)

    # Print results
    print("\nDriver Performance Analysis:")
    print("---------------------------")
    print(result)


if __name__ == "__main__":
    main()
