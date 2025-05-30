from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from ..agents.coaching_history_analyzer import CoachingFeedbackGenerator
from ..core.config import get_settings
from typing import Optional, List, Dict
import logging
import re
import json

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Coaching"])
settings = get_settings()

# Initialize coaching feedback generator
logger.info("Initializing coaching feedback generator")
coaching_feedback_generator = CoachingFeedbackGenerator(
    settings.OPENAI_API_KEY
)


class EmployeeInfo(BaseModel):
    userID: Optional[str] = None
    driverName: str


class CoachingFeedbackRequest(BaseModel):
    message: str = Field(
        ...,
        # min_length=2,
        description="Coaching query (e.g., 'Moises was cited for a speeding violation while operating a company vehicle.')",
    )
    session_id: Optional[str] = Field(
        None,
        description="Optional session identifier for maintaining conversation history",
    )
    name: str = Field(
        ...,
        min_length=2,
        description="Name of the user",
    )
    company: Optional[str] = Field(
        None, description="Company name of the user"
    )
    subject: Optional[str] = Field(
        None, description="Subject or topic for the conversation"
    )
    coachingDetailsData: Optional[List[Dict]] = Field(
        None, description="Optional coaching details data containing coaching history and other relevant information"
    )


@router.post(
    "/coaching-feedback",
    summary="Generate structured coaching feedback",
    description="Generates structured coaching feedback with historical context"
)
async def generate_coaching_feedback(request: CoachingFeedbackRequest):
    try:
        # Log the request details
        logger.info(f"Coaching feedback request - message: {request.message}")
        
        # Handle empty message
        message = request.message
        if not message or message.strip() == "":
            message = "Start"
            logger.info("Empty message detected, using default 'Start' message")

        # Generate coaching feedback
        result = coaching_feedback_generator.generate_feedback(
            query=message, 
            session_id=request.session_id,
            coaching_details_data=request.coachingDetailsData
        )

        # Initialize response data
        response_data = {}
        
        # Extract JSON if present
        backtick_pattern = r"```(?:\w*\n)?(.*?)```"
        match = re.search(backtick_pattern, result, re.DOTALL)
        if match:
            try:
                json_str = match.group(1).strip()
                json_data = json.loads(json_str)
                
                # Extract additional fields if present
                for field in ["statementOfProblem", "priorDiscussionOrWarning", "summaryOfCorrectiveAction"]:
                    if field in json_data:
                        response_data[field] = json_data[field]
                        logger.info(f"Extracted {field}")

            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse JSON from response: {e}")
            except Exception as e:
                logger.warning(f"Error extracting data from response: {e}")

        # Remove the JSON content from response after extraction
        clean_result = re.sub(r"```[\s\S]*?```", "", result).strip()
        response_data["response"] = clean_result

        return response_data

    except Exception as e:
        logger.error(f"Error generating coaching feedback: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
