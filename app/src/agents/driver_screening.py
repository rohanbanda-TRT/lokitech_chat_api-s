from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain.tools import Tool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.memory import ConversationBufferMemory
from langchain_openai import ChatOpenAI
import os
from dotenv import load_dotenv
from ..core.company_questions import CompanyQuestionsManager
import json
from ..prompts.driver_screening import DRIVER_SCREENING_PROMPT_TEMPLATE

class DriverScreeningAgent:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.session_memories = {}
        self.llm = ChatOpenAI(temperature=0.7, api_key=api_key, model="gpt-4o-mini")
        self.questions_manager = CompanyQuestionsManager()
        self.tools = [
            Tool(
                name="driver_screening",
                description="Conducts structured driver screening conversations",
                func=lambda x: f"Screening response: {x}"
            )
        ]
        
    def _get_company_specific_questions_text(self, company_id: str) -> str:
        """
        Get company-specific questions formatted for the prompt
        
        Args:
            company_id: The unique identifier for the company
            
        Returns:
            Formatted string of company-specific questions
        """
        questions = self.questions_manager.get_questions(company_id)
        
        if not questions:
            return "   - No company-specific questions defined. Skip this section."
        
        formatted_questions = []
        for i, q in enumerate(questions, 1):
            required_text = " (Required)" if q.get("required", False) else " (Optional)"
            formatted_questions.append(f"   - Ask Question {i}: \"{q['question_text']}\"{required_text}")
            if q.get("required", False):
                formatted_questions.append(f"     * This question is required. If the driver does not provide a clear answer, politely ask again.")
            else:
                formatted_questions.append(f"     * This question is optional. The driver may choose not to answer.")
        
        return "\n".join(formatted_questions)
    
    def get_session_executor(self, session_id: str, company_id: str = None) -> AgentExecutor:
        """
        Get or create a session-specific agent executor
        
        Args:
            session_id: Unique session identifier
            company_id: Optional company ID to get company-specific questions
            
        Returns:
            AgentExecutor for the session
        """
        if session_id not in self.session_memories:
            # Format the prompt with company-specific questions if available
            company_questions_text = "   - No company-specific questions defined. Skip this section."
            if company_id:
                company_questions_text = self._get_company_specific_questions_text(company_id)
            
            prompt_text = DRIVER_SCREENING_PROMPT_TEMPLATE.format(
                company_specific_questions=company_questions_text
            )
            
            prompt = ChatPromptTemplate.from_messages([
                ("system", prompt_text),
                MessagesPlaceholder("chat_history"),
                ("human", "{input}"),
                MessagesPlaceholder(variable_name="agent_scratchpad"),
            ])
            
            memory = ConversationBufferMemory(
                memory_key="chat_history",
                input_key="input",
                return_messages=True,
                k=30
            )
            
            agent = create_openai_tools_agent(
                llm=self.llm,
                tools=self.tools,
                prompt=prompt
            )
            
            self.session_memories[session_id] = AgentExecutor(
                agent=agent,
                tools=self.tools,
                memory=memory,
                verbose=True
            )
        
        return self.session_memories[session_id]

    def process_message(self, user_input: str, session_id: str, company_id: str = None) -> str:
        """
        Process the screening conversation using session-specific memory.
        
        Args:
            user_input: The message from the driver candidate
            session_id: Unique session identifier
            company_id: Optional company ID to get company-specific questions
            
        Returns:
            Response from the agent
        """
        executor = self.get_session_executor(session_id, company_id)
        response = executor.invoke({"input": user_input})
        return response["output"]

def main():
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("Please set OPENAI_API_KEY environment variable")
    
    agent = DriverScreeningAgent(api_key)
    
    print("Driver Screening Started! Type 'q' or 'quit' to exit.")
    
    # Ask for company ID
    company_id = input("Enter company ID (or leave blank for default questions): ").strip()
    
    while True:
        user_input = input("\nEnter your message: ").strip().lower()
        
        if user_input in ['q', 'quit']:
            print("\nScreening ended.")
            break
        
        session_id = "default_session"  # You can modify this to use different session IDs
        response = agent.process_message(user_input, session_id, company_id if company_id else None)
        print("\nResponse:", response)

if __name__ == "__main__":
    main()
