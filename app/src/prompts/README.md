# Prompts Package

## Overview
This package contains all the system prompts used throughout the Lokitech application. By centralizing prompts in one location, we make it easier to maintain consistency, update prompts across the application, and track changes.

## Structure

```
prompts/
├── __init__.py        # Package initialization
├── company_admin.py   # Prompts for company admin interactions
├── content_generator.py # Prompts for content generation
├── driver_screening.py # Prompts for driver screening conversations
├── common.py          # Common prompts used across different modules
└── README.md          # This documentation file
```

## Usage

To use a prompt in your code:

```python
from app.src.prompts.driver_screening import DRIVER_SCREENING_PROMPT_TEMPLATE
from app.src.prompts.company_admin import COMPANY_ADMIN_PROMPT
from app.src.prompts.content_generator import CONTENT_PROMPT
from app.src.prompts.common import LOKITECH_GENERAL_PROMPT, ERROR_HANDLING_PROMPT
```

## Prompt Format

All prompts should follow these guidelines:

1. **Use Triple-quoted Strings**: All prompts should be defined as triple-quoted strings for better readability.
2. **Use ALL_CAPS for Variable Names**: Prompt variable names should be in ALL_CAPS to distinguish them from regular variables.
3. **Include Placeholders**: If a prompt needs dynamic content, use named placeholders like `{company_specific_questions}`.
4. **Document Placeholders**: Include comments explaining what each placeholder is for and what format it expects.
5. **Use Markdown Formatting**: Structure prompts with markdown for better readability by the LLM.

## Adding New Prompts

When adding a new prompt:

1. Decide if it belongs in an existing file or needs a new file
2. Follow the naming and formatting conventions
3. Add appropriate documentation
4. Update this README if adding a new prompt file

## Best Practices

1. **Keep Prompts Focused**: Each prompt should have a clear purpose and focus.
2. **Be Explicit**: Provide clear instructions to the LLM about what it should and shouldn't do.
3. **Test Thoroughly**: Always test prompts with a variety of inputs to ensure they produce the desired outputs.
4. **Version Control**: Track changes to prompts to understand how they evolve over time.
5. **Review Regularly**: Periodically review prompts to ensure they still meet the needs of the application.

## Prompt Templates

Some prompts may include placeholders for dynamic content. When using these templates, make sure to provide all required placeholders. For example:

```python
from app.src.prompts.driver_screening import DRIVER_SCREENING_PROMPT_TEMPLATE

# Format the prompt with company-specific questions
formatted_prompt = DRIVER_SCREENING_PROMPT_TEMPLATE.format(
    company_specific_questions="- Question 1: Do you have experience with refrigerated transport? (Required)"
)

```
