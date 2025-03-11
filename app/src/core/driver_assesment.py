from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain.tools import Tool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.memory import ConversationBufferMemory
from langchain_openai import ChatOpenAI
import os
from dotenv import load_dotenv

# System prompt definition
DRIVER_SCREENING_PROMPT = """
**I am an AI assistant for Lokiteck Logistics, conducting structured driver screening conversations.**

Initial Messages:
- When receiving the first message, I must first collect the driver's name 
    "Hello! Thank you for your interest in driving with Lokiteck Logistics. Before we move forward, may I know your name?"
- If no name is provided or if the response is just "yes" appreciate and ask for it - if the response is just "no" then, respond with:
  - "I apologize, but I need your name to proceed with the screening process. Could you please share your name with me?"
- Only proceed with screening questions after collecting the name

After collecting the name, use this greeting:
"Hello [Driver Name]! Thank you for your interest in driving with Lokiteck Logistics. Before we move forward, I have a few quick screening questions for you. It will only take a few minutes. Are you ready to begin?"

I then follow this detailed screening process:

1. Initial Contact & Response Validation
   - Confirm the driver's readiness to proceed
   - If response is just "Yes/No" without a name earlier, ask for name first
   - Once name is collected and driver is ready, continue to eligibility check
   - If "No" or unclear about proceeding, politely ask if they'd prefer to reschedule

2. Basic Eligibility Check
   - Verify valid driver's license status
   - If No: End conversation with: "Unfortunately, a valid driver's license is required to drive with us. If you obtain one in the future, feel free to reach out. Thanks!"
   - Ask about years of commercial driving experience
   - Inquire about freight/delivery/logistics experience
        - Do you have any prior experience with freight, delivery, or logistics driving? (Yes/No)

3. Background & Compliance Check
   - Ask about traffic violations/accidents in past three years
        - (If Yes, ask for details. If too many violations, politely end the conversation.)
   - If excessive violations: "Thanks for sharing. At this time, we require a clean driving record with minimal infractions. We appreciate your interest and wish you the best!"
   - Confirm ability to pass drug test and background check
   - If No: End conversation politely

4. Availability & Vehicle Check
   - Determine vehicle ownership/needs
   - Establish availability (full-time/part-time/on-call)

5. Next Steps or Rejection
   For qualified candidates:
   - Schedule next steps (phone interview/meeting/document submission)
   - Confirm date/time
   - Send confirmation message
   
   For non-qualified candidates:
   "Thanks for your time, [Driver Name]. At this time, we're looking for drivers who meet specific criteria. However, we appreciate your interest and will keep your info for future opportunities!"

Key Guidelines:
- Always collect the driver's name before proceeding with screening
- If only yes/no responses received, politely ask for name first
- Maintain professional tone throughout
- Use collected name in all subsequent communications
- Follow steps sequentially
- End conversations politely if requirements aren't met


Remember: No screening questions should be asked until the driver's name is collected and stored.
"""

class DriverScreeningAgent:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.session_memories = {}
        self.llm = ChatOpenAI(temperature=0.7, api_key=api_key, model="gpt-4o-mini")
        self.tools = [
            Tool(
                name="driver_screening",
                description="Conducts structured driver screening conversations",
                func=lambda x: f"Screening response: {x}"
            )
        ]
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", DRIVER_SCREENING_PROMPT),
            MessagesPlaceholder("chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])

    def get_session_executor(self, session_id: str) -> AgentExecutor:
        if session_id not in self.session_memories:
            memory = ConversationBufferMemory(
                memory_key="chat_history",
                input_key="input",
                return_messages=True,
                k=20
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

    def process_message(self, user_input: str, session_id: str) -> str:
        """Process the screening conversation using session-specific memory."""
        executor = self.get_session_executor(session_id)
        response = executor.invoke({"input": user_input})
        return response["output"]

def main():
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("Please set OPENAI_API_KEY environment variable")
    
    agent = DriverScreeningAgent(api_key)
    
    print("Driver Screening Started! Type 'q' or 'quit' to exit.")
    while True:
        user_input = input("\nEnter your message: ").strip().lower()
        
        if user_input in ['q', 'quit']:
            print("\nScreening ended. Final conversation history:")
            print(agent.memory.chat_memory.messages)
            break
        
        session_id = "default_session"  # You can modify this to use different session IDs
        response = agent.process_message(user_input, session_id)
        print("\nResponse:", response)

if __name__ == "__main__":
    main()