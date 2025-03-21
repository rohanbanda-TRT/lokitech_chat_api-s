from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from ..agents.performance_analyzer import PerformanceAnalyzerAgent
from ..core.config import get_settings
from ..agents import ContentGeneratorAgent, DriverScreeningAgent, CompanyAdminAgent
from typing import Optional, List
from ..managers.company_questions_factory import get_company_questions_manager
from ..models.question_models import Question
import logging

logger = logging.getLogger(__name__)

router = APIRouter()
settings = get_settings()
content_agent = ContentGeneratorAgent(settings.OPENAI_API_KEY)
driver_screening_agent = DriverScreeningAgent(settings.OPENAI_API_KEY)
company_admin_agent = CompanyAdminAgent(settings.OPENAI_API_KEY)
performance_analyzer = PerformanceAnalyzerAgent(settings.OPENAI_API_KEY)

class PerformanceRequest(BaseModel):
    messages: str

class ChatRequest(BaseModel):
    message: str
    
    session_id: str = Field(
        ...,  
        min_length=1,
        description="Unique session identifier for conversation tracking"
    )
    name: str = Field(
        ...,
        min_length=2,
        description="Name of the user"
    )
    company: str = Field(
        ...,
        min_length=2,
        description="Company name of the user"
    )
    subject: str = Field(
        ...,
        min_length=2,
        description="Subject or topic for the conversation"
    )

class DriverScreeningRequest(BaseModel):
    message: str
    
    session_id: str = Field(
        ...,
        min_length=1,
        description="Unique session identifier for screening conversation"
    )
    dsp_code: Optional[str] = Field(
        None,
        description="Optional DSP code to use company-specific questions"
    )

class CompanyAdminRequest(BaseModel):
    message: str
    
    session_id: str = Field(
        ...,
        min_length=1,
        description="Unique session identifier for company admin conversation"
    )
    dsp_code: str = Field(
        ...,
        min_length=1,
        description="DSP code to associate with questions"
    )

class CompanyQuestionsRequest(BaseModel):
    dsp_code: str
    questions: List[Question]


@router.post("/analyze-performance",
         summary="Analyze driver performance",
         description="Analyzes driver performance based on provided metrics and returns structured feedback")

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
        
        return {
            "response": result
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/driver-screening",
         summary="Screen potential drivers",
         description="Conducts an interactive screening conversation with potential drivers")
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
        
        # Validate message
        default_message = f"Start [DSP: {dsp_code}, Session: {session_id}]"
        message = (
            default_message
            if not request.message or request.message.strip() == ""
            else request.message
        )
        
        # Process message using driver screening agent with dsp_code if provided
        try:
            result = driver_screening_agent.process_message(
                message, 
                session_id,
                dsp_code
            )
            
            return {
                "response": result,
                "session_id": session_id,
                "dsp_code": dsp_code
            }
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            raise HTTPException(
                status_code=500, 
                detail=f"Error processing message: {str(e)}"
            )
    
    except Exception as e:
        logger.error(f"Unexpected error in driver_screening endpoint: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Unexpected error: {str(e)}"
        )

@router.post("/company-admin",
         summary="Manage company-specific screening questions",
         description="Interactive conversation with company admin to manage screening questions")
async def company_admin(request: CompanyAdminRequest):
    try:
        # Process message using company admin agent
        result = company_admin_agent.process_message(
            request.message,
            request.session_id,
            request.dsp_code
        )
        
        return {
            "response": result,
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/company-questions/{dsp_code}",
         summary="Get company-specific questions",
         description="Retrieve the list of questions for a specific company")
async def get_company_questions(dsp_code: str):
    try:
        questions_manager = get_company_questions_manager()
        questions = questions_manager.get_questions(dsp_code)
        
        return {
            "dsp_code": dsp_code,
            "questions": questions
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/company-questions",
         summary="Save company-specific questions",
         description="Save a list of questions for a specific company")
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
            "question_count": len(request.questions)
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))