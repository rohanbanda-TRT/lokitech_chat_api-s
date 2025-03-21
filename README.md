# Lokitech DSP Bot

A structured, AI-powered platform for delivery service providers (DSPs) that automates driver screening, provides performance analysis, and offers content generation capabilities.

## Overview

The Lokitech DSP Bot is a comprehensive solution designed to streamline operations for delivery service providers. It leverages OpenAI's GPT models to provide intelligent automation for various tasks including:

1. **Driver Screening**: Automated interview process for driver candidates using customizable screening questions
2. **Performance Analysis**: Evaluation of driver performance metrics with actionable feedback
3. **Content Generation**: Creation of job descriptions, training materials, and other content
4. **Company Admin**: Management interface for company-specific screening questions

## Project Structure

```
DSP_BOT_Structured/
├── app/                        # Main application directory
│   ├── main.py                 # FastAPI application entry point
│   └── src/                    # Source code
│       ├── agents/             # AI agent implementations
│       │   ├── company_admin.py        # Company admin agent
│       │   ├── content_generator.py    # Content generation agent
│       │   ├── driver_screening.py     # Driver screening agent
│       │   ├── performance_analyzer.py # Performance analysis agent
│       │   └── README.md               # Agent documentation
│       ├── api/                # API endpoints
│       │   └── routes.py       # FastAPI route definitions
│       ├── core/               # Core functionality
│       │   ├── config.py       # Application configuration
│       │   ├── database.py     # Database connection management
│       │   └── firebase_config.py # Firebase configuration
│       ├── managers/           # Business logic managers
│       │   ├── company_questions_manager.py # MongoDB implementation for company questions
│       │   ├── firebase_company_questions_manager.py # Firebase implementation for company questions
│       │   └── company_questions_factory.py # Factory for selecting the appropriate implementation
│       ├── models/             # Data models
│       │   └── question_models.py      # Question-related models
│       ├── prompts/            # LLM prompts
│       │   ├── analyzer.py     # Performance analyzer prompts
│       │   ├── common.py       # Common prompts
│       │   ├── company_admin.py # Company admin prompts
│       │   ├── content_generator.py # Content generator prompts
│       │   ├── driver_screening.py # Driver screening prompts
│       │   └── README.md       # Prompts documentation
│       ├── services/           # External service integrations
│       ├── tools/              # Agent tools
│       │   └── company_admin_tools.py  # Tools for company admin agent
│       ├── utils/              # Utility functions
│       │   └── session_manager.py      # Manages conversation sessions
│       └── web/                # Web interface
│           └── streamlit_app.py # Streamlit web application
├── requirements.txt            # Python dependencies
└── README.md                   # This file
```

## Features

### Driver Screening

The Driver Screening module automates the interview process for driver candidates:

- Conducts structured conversations with candidates
- Uses company-specific screening questions
- Evaluates candidate responses
- Maintains conversation context across multiple messages
- Provides a summary of candidate suitability

### Performance Analysis

The Performance Analyzer evaluates driver performance metrics:

- Analyzes delivery metrics (POD rates, delivery times, etc.)
- Compares performance against benchmarks
- Identifies areas for improvement
- Provides actionable feedback
- Generates performance reports

### Content Generation

The Content Generator creates various types of content:

- Job descriptions
- Training materials
- Standard operating procedures
- Email templates
- And more

### Company Admin

The Company Admin module allows companies to manage their screening questions:

- Create new screening questions
- Retrieve existing questions
- Update specific questions
- Delete questions
- Customize the screening process

## Storage Architecture

The application uses a dual-storage approach:

1. **Company Questions**: Stored in Firebase Firestore
   - Managed by the `FirebaseCompanyQuestionsManager`
   - Used by both the Company Admin Agent and Driver Screening Agent

2. **Driver Screening Data**: Stored in MongoDB
   - Managed by the `DriverScreeningManager`
   - Used by the Driver Screening Agent

For detailed setup instructions, see:
- [Firebase Setup](README_FIREBASE.md)
- [MongoDB Setup](README_MONGODB.md)

## Technology Stack

- **Backend**: FastAPI (Python)
- **Database**: MongoDB Atlas
- **AI**: OpenAI GPT models via LangChain
- **Web Interface**: Streamlit
- **Observability**: LangSmith for LLM tracing

## Setup and Installation

### Prerequisites

- Python 3.8+
- MongoDB Atlas account
- OpenAI API key
- Firebase account

### Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd DSP_BOT_Structured
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Create a `.env` file in the project root with the following variables:
   ```
   OPENAI_API_KEY=your_openai_api_key
   MONGODB_PASSWORD=your_mongodb_password
   FIREBASE_API_KEY=your_firebase_api_key
   ```

### Running the Application

#### FastAPI Backend

```bash
cd DSP_BOT_Structured
uvicorn app.main:app --reload
```

The API will be available at http://localhost:8000

#### Streamlit Web Interface

```bash
cd DSP_BOT_Structured
streamlit run app/src/web/streamlit_app.py
```

The web interface will be available at http://localhost:8501

## API Endpoints

- **POST /analyze**: Analyze driver performance metrics
- **POST /chat**: General content generation chat
- **POST /driver-screening**: Driver screening conversation
- **POST /company-admin**: Company admin conversation
- **GET /company-questions/{dsp_code}**: Get company questions
- **POST /company-questions**: Save company questions

## MongoDB Integration

The application uses MongoDB Atlas as the database backend with the following features:

- Connection pooling for efficient database access
- Error handling with fallback to local MongoDB
- Connection timeouts and retry settings
- Proper logging of connection status
- Optimized queries with indexes

## Development Guidelines

### Adding New Agents

1. Create a new file in the `app/src/agents/` directory
2. Follow the established pattern for agent initialization
3. Implement a `process_message` method
4. Use appropriate prompts from the `prompts` directory
5. Add logging for debugging and monitoring
6. Update the agents README

### Working with Prompts

1. Add new prompts to the appropriate file in the `prompts` package
2. Follow the naming and formatting conventions
3. Keep prompts focused and explicit
4. Test prompts thoroughly with a variety of inputs
5. Document any placeholders or special formatting requirements
