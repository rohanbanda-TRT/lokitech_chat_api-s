from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
import os
from dotenv import load_dotenv
from ..prompts.analyzer import ANALYZER_PROMPT_TEMPLATE

class PerformanceAnalyzerAgent:
    """
    Agent for analyzing delivery driver performance metrics and providing feedback.
    """
    
    def __init__(self, api_key: str):
        """
        Initialize the Performance Analyzer Agent.
        
        Args:
            api_key: OpenAI API key
        """
        self.api_key = api_key
        self.llm = ChatOpenAI(temperature=0.3, api_key=api_key)
        
        # Create prompt
        self.prompt = PromptTemplate(
            input_variables=["messages"],
            template=ANALYZER_PROMPT_TEMPLATE
        )
        
        # Create chain using LCEL (LangChain Expression Language)
        self.chain = self.prompt | self.llm | StrOutputParser()
    
    def analyze_performance(self, data: str) -> str:
        """
        Analyze driver performance data and provide feedback.
        
        Args:
            data: String containing performance metrics
            
        Returns:
            Formatted feedback with suggestions for improvement
        """
        # Run chain with properly formatted input
        response = self.chain.invoke({"messages": data})
        return response

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
    
    # Initialize the agent
    analyzer = PerformanceAnalyzerAgent(api_key)
    
    # Sample performance data
    sample_data = "Ronaldo Pacora Flores Sign/Signal Violations Rate: 0, POD: 97.8%"
    
    # Analyze the performance data
    result = analyzer.analyze_performance(sample_data)
    
    # Print results
    print("\nDriver Performance Analysis:")
    print("---------------------------")
    print(result)

if __name__ == "__main__":
    main()
