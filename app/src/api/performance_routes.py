from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from ..agents.performance_analyzer import PerformanceAnalyzerAgent
from ..core.config import get_settings
import logging

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Performance"])
settings = get_settings()
performance_analyzer = PerformanceAnalyzerAgent(settings.OPENAI_API_KEY)


class PerformanceRequest(BaseModel):
    messages: str


@router.post(
    "/analyze-performance",
    summary="Analyze driver performance",
    description="Analyzes driver performance based on provided metrics and returns structured feedback"
)
async def analyze_performance(request: PerformanceRequest):
    try:
        # Analyze the performance data
        result = performance_analyzer.analyze_performance(request.messages)

        return {"analysis": result}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
