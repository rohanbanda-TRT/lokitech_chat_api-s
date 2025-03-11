from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from ..core.analyzer import analyze_dsp_performance
from ..core.config import get_settings
from ..core.content_generator import ContentGeneratorAgent

router = APIRouter()
settings = get_settings()
content_agent = ContentGeneratorAgent(settings.OPENAI_API_KEY)

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


@router.post("/analyze-performance",
         summary="Analyze driver performance",
         description="Analyzes driver performance based on provided metrics and returns structured feedback")

async def analyze_performance(request: PerformanceRequest):
    try:
        settings = get_settings()
        
        # Analyze the performance data
        result = analyze_dsp_performance(settings.OPENAI_API_KEY, request.messages)
        
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