# Prompts and Agents Restructuring

## Overview
This document describes the restructuring of prompts and agents in the Lokitech application. The goal was to move all prompts to a separate directory and all agent classes to a dedicated agents directory, making the codebase more organized and easier to maintain.

## Changes Made

### 1. Created Prompts Package
Created a dedicated package for all prompts:
```
app/src/prompts/
├── __init__.py
├── analyzer.py
├── company_admin.py
├── content_generator.py
├── driver_screening.py
├── common.py
└── README.md
```

### 2. Created Agents Package
Created a dedicated package for all agent classes:
```
app/src/agents/
├── __init__.py
├── company_admin.py
├── content_generator.py
├── driver_screening.py
├── performance_analyzer.py
└── README.md
```

### 3. Moved Existing Prompts
- Moved `DRIVER_SCREENING_PROMPT_TEMPLATE` from `driver_assesment.py` to `prompts/driver_screening.py`
- Moved `COMPANY_ADMIN_PROMPT` from `company_questions.py` to `prompts/company_admin.py`
- Moved `CONTENT_PROMPT` from `content_generator.py` to `prompts/content_generator.py`
- Moved analyzer prompt from `analyzer.py` to `prompts/analyzer.py`

### 4. Moved Agent Classes
- Moved `DriverScreeningAgent` from `driver_assesment.py` to `agents/driver_screening.py`
- Moved `CompanyAdminAgent` from `company_questions.py` to `agents/company_admin.py`
- Moved `ContentGeneratorAgent` from `content_generator.py` to `agents/content_generator.py`
- Moved analyzer functionality from `analyzer.py` to `agents/performance_analyzer.py`

### 5. Added Common Prompts
Created `prompts/common.py` with:
- `LOKITECH_GENERAL_PROMPT`: A general-purpose prompt for Lokitech assistants
- `ERROR_HANDLING_PROMPT`: A prompt for handling errors

### 6. Updated Imports
Modified the relevant files to import prompts from the new location and to use the agent classes from the agents directory.

### 7. Added Documentation
- Created `app/src/prompts/README.md` with detailed documentation on how to use and maintain prompts
- Created `app/src/agents/README.md` with detailed documentation on how to use and maintain agents
- Created this document to summarize the changes

## Benefits

1. **Improved Organization**: All prompts and agents are now in dedicated locations, making them easier to find and manage.
2. **Better Maintainability**: Changes to prompts or agent logic can be made in one place without affecting other components.
3. **Consistency**: Having prompts and agents in dedicated packages encourages consistent formatting and structure.
4. **Reusability**: Prompts and agent classes can now be easily shared across different parts of the application.
5. **Versioning**: Changes to prompts and agents can be tracked more easily in version control.
6. **Separation of Concerns**: Clear separation between data access, business logic, and AI agent functionality.

## How to Use

### Using Prompts

To use a prompt in your code:

```python
from app.src.prompts.driver_screening import DRIVER_SCREENING_PROMPT_TEMPLATE
from app.src.prompts.company_admin import COMPANY_ADMIN_PROMPT
from app.src.prompts.content_generator import CONTENT_PROMPT
from app.src.prompts.analyzer import ANALYZER_PROMPT_TEMPLATE
from app.src.prompts.common import LOKITECH_GENERAL_PROMPT, ERROR_HANDLING_PROMPT
```

### Using Agents

To use an agent in your code:

```python
from app.src.agents import DriverScreeningAgent, CompanyAdminAgent, ContentGeneratorAgent, PerformanceAnalyzerAgent
import os

# Get API key
api_key = os.getenv("OPENAI_API_KEY")

# Initialize agents
driver_agent = DriverScreeningAgent(api_key)
admin_agent = CompanyAdminAgent(api_key)
content_agent = ContentGeneratorAgent(api_key)
analyzer_agent = PerformanceAnalyzerAgent(api_key)
```

## Best Practices

### For Prompts

When working with prompts:

1. Always add new prompts to the appropriate file in the prompts package
2. Follow the naming and formatting conventions described in the prompts README
3. Keep prompts focused and explicit
4. Test prompts thoroughly with a variety of inputs
5. Document any placeholders or special formatting requirements

### For Agents

When working with agents:

1. Always add new agent classes to the appropriate file in the agents package
2. Follow the established patterns for agent initialization and methods
3. Use session-based memory for conversational agents
4. Implement proper error handling and logging
5. Document the purpose and usage of each agent class
