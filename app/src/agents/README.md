# Agents Directory

This directory contains all the AI agent implementations used in the application. Each agent is responsible for a specific task and interacts with the OpenAI API to generate responses based on user input.

## Available Agents

### DriverScreeningAgent

Located in `driver_screening.py`, this agent conducts structured driver screening conversations with candidates. It uses company-specific questions from the database and manages the screening process.

#### Usage Example:

```python
from app.src.agents import DriverScreeningAgent
import os

# Initialize the agent with your OpenAI API key
api_key = os.getenv("OPENAI_API_KEY")
agent = DriverScreeningAgent(api_key)

# Process a message from a driver candidate
session_id = "unique_session_id"  # Use a unique ID for each conversation
dsp_code = "company_123"  # Optional, to include company-specific questions
response = agent.process_message("I'm interested in the driver position", session_id, dsp_code)
print(response)
```

### CompanyAdminAgent

Located in `company_admin.py`, this agent helps company administrators manage their screening questions. It can save new questions to the database and retrieve existing ones.

#### Usage Example:

```python
from app.src.agents import CompanyAdminAgent
import os

# Initialize the agent with your OpenAI API key
api_key = os.getenv("OPENAI_API_KEY")
agent = CompanyAdminAgent(api_key)

# Process a message from a company admin
session_id = "admin_session_id"
dsp_code = "company_123"  # Optional, to include company ID in the first message
response = agent.process_message("I want to add a new screening question", session_id, dsp_code)
print(response)
```

### ContentGeneratorAgent

Located in `content_generator.py`, this agent assists in generating creative content based on user input. It can be used for various content creation tasks.

#### Usage Example:

```python
from app.src.agents import ContentGeneratorAgent
import os

# Initialize the agent with your OpenAI API key
api_key = os.getenv("OPENAI_API_KEY")
agent = ContentGeneratorAgent(api_key)

# Process a message from a user
session_id = "content_session_id"
response = agent.process_message("Generate a job description for a delivery driver", session_id)
print(response)
```

### PerformanceAnalyzerAgent

Located in `performance_analyzer.py`, this agent analyzes delivery driver performance metrics and provides targeted feedback for improvement. It evaluates metrics against established standards and generates actionable suggestions.

#### Usage Example:

```python
from app.src.agents import PerformanceAnalyzerAgent
import os

# Initialize the agent with your OpenAI API key
api_key = os.getenv("OPENAI_API_KEY")
agent = PerformanceAnalyzerAgent(api_key)

# Analyze driver performance data
performance_data = "Driver Name POD: 97.8%, Sign/Signal Violations: 2"
analysis = agent.analyze_performance(performance_data)
print(analysis)
```

## Common Features

All agents share the following common features:

1. **Session-based Memory**: Each agent maintains conversation history for each session, allowing for contextual responses.
2. **OpenAI Integration**: All agents use the OpenAI API for generating responses.
3. **Tool-based Architecture**: Agents use LangChain tools to perform specific actions.

## Development Guidelines

When creating new agents or modifying existing ones:

1. Follow the established pattern of initializing the agent with an API key.
2. Implement a `process_message` method that takes user input and session ID.
3. Use appropriate prompts from the `prompts` directory.
4. Add appropriate logging for debugging and monitoring.
5. Update this README when adding new agents.
