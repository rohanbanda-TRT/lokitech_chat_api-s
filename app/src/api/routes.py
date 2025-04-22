from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from ..agents.performance_analyzer import PerformanceAnalyzerAgent
from ..agents.coaching_history_analyzer import CoachingFeedbackGenerator
from ..core.config import get_settings
from ..agents import ContentGeneratorAgent, DriverScreeningAgent, CompanyAdminAgent
from typing import Optional, List, Dict
from ..managers.company_questions_factory import get_company_questions_manager
from ..models.question_models import Question
import logging
import re
import json

logger = logging.getLogger(__name__)

router = APIRouter()
settings = get_settings()
content_agent = ContentGeneratorAgent(settings.OPENAI_API_KEY)
driver_screening_agent = DriverScreeningAgent(settings.OPENAI_API_KEY)
company_admin_agent = CompanyAdminAgent(settings.OPENAI_API_KEY)
performance_analyzer = PerformanceAnalyzerAgent(settings.OPENAI_API_KEY)

# Initialize coaching feedback generator
logger.info("Initializing coaching feedback generator")
coaching_feedback_generator = CoachingFeedbackGenerator(
    settings.OPENAI_API_KEY
)


class PerformanceRequest(BaseModel):
    messages: str


class ChatRequest(BaseModel):
    message: str

    session_id: str = Field(
        ...,
        min_length=1,
        description="Unique session identifier for conversation tracking",
    )
    name: str = Field(..., min_length=2, description="Name of the user")
    company: str = Field(..., min_length=2, description="Company name of the user")
    subject: str = Field(
        ..., min_length=2, description="Subject or topic for the conversation"
    )


class DriverScreeningRequest(BaseModel):
    message: str

    session_id: str = Field(
        ...,
        min_length=1,
        description="Unique session identifier for screening conversation",
    )
    dsp_code: Optional[str] = Field(
        None, description="Optional DSP code to use company-specific questions"
    )
    station_code: Optional[str] = Field(
        None, description="Station code for the DSP location"
    )
    applicant_id: Optional[int] = Field(
        None, description="Applicant ID for the driver being screened"
    )


class CompanyAdminRequest(BaseModel):
    message: str

    session_id: str = Field(
        ...,
        min_length=1,
        description="Unique session identifier for company admin conversation",
    )
    dsp_code: str = Field(
        ..., min_length=1, description="DSP code to associate with questions"
    )


class CompanyQuestionsRequest(BaseModel):
    dsp_code: str
    questions: List[Question]


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
    driver_list: Optional[List[EmployeeInfo]] = Field(
        None, description="List of employees with their names and optional user IDs"
    )
    coachingDetailsData: Optional[List[Dict]] = Field(
        None, description="Optional coaching details data containing coaching history and other relevant information"
    )


@router.post(
    "/analyze-performance",
    summary="Analyze driver performance",
    description="Analyzes driver performance based on provided metrics and returns structured feedback",
)
async def analyze_performance(request: PerformanceRequest):
    try:
        settings = get_settings()

        # Analyze the performance data
        result = performance_analyzer.analyze_performance(request.messages)

        return {"analysis": result}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat")
async def chat(request: ChatRequest):
    try:
        message = (
            f"I am {request.name} from {request.company} and I want your help with {request.subject}"
            if not request.message or request.message.strip() == ""
            else request.message
        )

        # Process message using agent with session_id
        result = content_agent.process_message(message, request.session_id)

        return {"response": result}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/driver-screening",
    summary="Screen potential drivers",
    description="Conducts an interactive screening conversation with potential drivers",
)
async def driver_screening(request: DriverScreeningRequest):
    try:
        # Validate session_id
        session_id = request.session_id
        if not session_id or session_id.strip() == "":
            # Generate a unique session ID if none provided
            import uuid

            session_id = str(uuid.uuid4())
            logger.info(f"Generated new session_id: {session_id}")

        # Validate dsp_code
        dsp_code = request.dsp_code
        if not dsp_code or dsp_code.strip() == "":
            dsp_code = "DEMO"  # Use a default DSP code
            logger.info(f"Using default dsp_code: {dsp_code}")

        # Get station_code and applicant_id
        station_code = request.station_code
        applicant_id = request.applicant_id

        # Validate message
        default_message = f"Start [DSP: {dsp_code}, Session: {session_id}, Station Code: {station_code}, Applicant ID: {applicant_id}]"
        message = (
            default_message
            if not request.message or request.message.strip() == ""
            else request.message
        )

        # Process message using driver screening agent with dsp_code if provided
        try:
            # Get applicant details first if this is a new session
            applicant_details = None
            if message.startswith("Start [DSP:") or message == default_message:
                # This is likely the first message, try to get applicant details
                from ..tools.dsp_api_client import DSPApiClient

                api_client = DSPApiClient()

                # Use provided station_code and applicant_id if available, otherwise use defaults
                station_code_to_use = station_code if station_code else "DJE1"
                applicant_id_to_use = applicant_id if applicant_id is not None else 5

                applicant_details_obj = api_client.get_applicant_details(
                    dsp_code=dsp_code,
                    station_code=station_code_to_use,
                    applicant_id=applicant_id_to_use,
                )

                if applicant_details_obj:
                    applicant_details = applicant_details_obj.model_dump()
                    logger.info(f"Retrieved applicant details: {applicant_details}")

            result = driver_screening_agent.process_message(
                message, session_id, dsp_code, station_code, applicant_id
            )

            response_data = {
                "response": result,
                "session_id": session_id,
                "dsp_code": dsp_code,
                "station_code": station_code,
                "applicant_id": applicant_id,
            }

            # Include applicant details in the response if available
            if applicant_details:
                response_data["applicant_details"] = applicant_details

            return response_data
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            raise HTTPException(
                status_code=500, detail=f"Error processing message: {str(e)}"
            )

    except Exception as e:
        logger.error(f"Unexpected error in driver_screening endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


@router.post(
    "/company-admin",
    summary="Manage company-specific screening questions",
    description="Interactive conversation with company admin to manage screening questions",
)
async def company_admin(request: CompanyAdminRequest):
    try:
        # Process message using company admin agent
        result = company_admin_agent.process_message(
            request.message, request.session_id, request.dsp_code
        )

        return {
            "response": result,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/company-questions/{dsp_code}",
    summary="Get company-specific questions",
    description="Retrieve the list of questions for a specific company",
)
async def get_company_questions(dsp_code: str):
    try:
        questions_manager = get_company_questions_manager()
        questions = questions_manager.get_questions(dsp_code)

        return {"dsp_code": dsp_code, "questions": questions}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/company-questions",
    summary="Save company-specific questions",
    description="Save a list of questions for a specific company",
)
async def save_company_questions(request: CompanyQuestionsRequest):
    try:
        questions_manager = get_company_questions_manager()
        questions = [q.model_dump() for q in request.questions]
        success = questions_manager.create_questions(request.dsp_code, questions)

        if not success:
            raise HTTPException(status_code=500, detail="Failed to save questions")

        return {
            "success": True,
            "dsp_code": request.dsp_code,
            "question_count": len(request.questions),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/coaching-feedback",
    summary="Generate structured coaching feedback",
    description="Generates structured coaching feedback with historical context",
)
async def generate_coaching_feedback(request: CoachingFeedbackRequest):
    try:
        # Log the request details
        logger.info(f"Coaching feedback request - message: {request.message}")
        logger.info(f"Coaching feedback request - driver_list: {request.driver_list}")
        
        # Handle empty message
        message = request.message
        if not message or message.strip() == "":
            if request.driver_list and len(request.driver_list) > 0:
                # Convert driver list to a string representation
                driver_info = []
                for driver in request.driver_list:
                    driver_info.append(f"{driver.driverName} (ID: {driver.userID})")
                
                drivers_str = ", ".join(driver_info)
                message = f"Start [Available drivers: {drivers_str}]"
                logger.info(f"Empty message detected, using default message with driver list: {message}")
            else:
                message = "Start"
                logger.info("Empty message detected, using default 'Start' message")

        # Generate coaching feedback
        result = coaching_feedback_generator.generate_feedback(
            query=message, 
            session_id=request.session_id,
            driver_list=request.driver_list,
            coaching_details_data=request.coachingDetailsData
        )

        # Check if the response contains JSON with driver ID in triple backticks
        response_data = {"response": result}
        
        # Extract driver ID if present in triple backticks
        # Look for content between triple backticks
        backtick_pattern = r"```(?:\w*\n)?(.*?)```"
        match = re.search(backtick_pattern, result, re.DOTALL)
        
        if match:
            try:
                # Try to parse the content as JSON
                json_str = match.group(1).strip()
                json_data = json.loads(json_str)
                
                # Check if it contains employee_id or driverId
                driver_id = json_data.get("employee_id") or json_data.get("driverId")
                if driver_id:
                    response_data["driverId"] = driver_id
                    logger.info(f"Extracted driver ID: {driver_id}")
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse JSON from response: {e}")
            except Exception as e:
                logger.warning(f"Error extracting driver ID: {e}")

        return response_data

    except Exception as e:
        logger.error(f"Error generating coaching feedback: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
