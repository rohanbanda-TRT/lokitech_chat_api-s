from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain.tools import Tool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.memory import ConversationBufferMemory
from langchain_openai import ChatOpenAI
import os
from dotenv import load_dotenv

# System prompt definition
CONTENT_PROMPT = """
**Hi there! I'm your AI assistant, ready to help you create engaging, professional, and impactful content for any purpose.**  

I can assist with:  
- Writing emails, SMS, social media posts, and more  
- Keeping the tone natural, engaging, and suited to your audience  
- Ensuring clarity, professionalism, and creativity  
- Tailoring content to your specific needs  

When you send your first message in this format:  
**"I am [name] from [company] and I want your help with [subject]"**,  
I’ll respond with:  
*"Hello [name], I'd be happy to help you with [subject]. What specific details or requirements do you have?"*  

I’ll format the closing based on the type of content:  
- **For emails:**  
  **Best regards,**  
  *[Your Name]*  
  *[Company Name] Team*  

- **For SMS:**  
  `– [Your Name], [Company Name]`  

- **For social media posts:**  
  *(Company branding or signature as needed)*  

- **For formal documents or letters:**  
  **Sincerely,**  
  *[Your Name]*  
  *[Company Name]*  

**Only the generated content will be enclosed in triple backticks (` ``` `), ensuring clarity while keeping our conversation natural.**  

Let me know how you'd like to refine or adjust the content—I'm here to make your message stand out!
"""


class ContentGeneratorAgent:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.session_memories = {}
        self.llm = ChatOpenAI(temperature=0.7, api_key=api_key,model="gpt-4o-mini")
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

    def get_session_executor(self, session_id: str) -> AgentExecutor:
        if session_id not in self.session_memories:
            memory = ConversationBufferMemory(
                memory_key="chat_history",
                input_key="input",
                return_messages=True,
                k =20
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
        """Process the user's message using session-specific memory."""
        executor = self.get_session_executor(session_id)
        response = executor.invoke({"input": user_input})
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
            print("\nChat ended. Final conversation history:")
            print(agent.memory.chat_memory.messages)
            break
        
        session_id = "default_session"  # You can modify this to use different session IDs
        response = agent.process_message(user_input, session_id)
        print("\nResponse:", response)


if __name__ == "__main__":
    main()