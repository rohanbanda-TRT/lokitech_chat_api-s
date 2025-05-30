from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from ..agents import CompanyAdminAgent
from ..core.config import get_settings
from ..managers.company_questions_factory import get_company_questions_manager
from ..models.question_models import Question
from ..utils.time_slot_parser import format_recurrence_time_slots, RecurrenceTimeSlot, generate_time_slots_from_recurrence
from typing import Optional, List, Dict
import logging
import json
import traceback

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Admin"])
settings = get_settings()
company_admin_agent = CompanyAdminAgent(settings.OPENAI_API_KEY)


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


@router.post(
    "/company-admin",
    summary="Manage company-specific screening questions",
    description="Interactive conversation with company admin to manage screening questions"
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
    description="Retrieve the list of questions for a specific company"
)
async def get_company_questions(dsp_code: str):
    try:
        questions_manager = get_company_questions_manager()
        result = questions_manager.get_questions(dsp_code)
        logger.info(f"Retrieved questions for dsp_code: {result}")
        
        # Extract the questions data from the result
        questions_data = result.get("questions", [])
        recurrence_time_slots = result.get("recurrence_time_slots", [])
        structured_recurrence_time_slots = result.get("structured_recurrence_time_slots", [])
        
        # Log the raw questions data for debugging
        logger.info(f"Raw questions data: {questions_data}")
        
        # Ensure questions is a properly formatted list of question objects
        formatted_questions = []
        
        # Handle different data structures
        if isinstance(questions_data, list):
            # If it's already a list, process each item
            for q in questions_data:
                # Handle string items (might be JSON strings)
                if isinstance(q, str):
                    try:
                        q_obj = json.loads(q)
                        formatted_questions.append(q_obj)
                    except json.JSONDecodeError:
                        # If it's not JSON, create a question object with the string as text
                        formatted_questions.append({"question_text": q, "criteria": "Not specified"})
                elif isinstance(q, dict):
                    formatted_questions.append(q)
                else:
                    # For non-dict, non-string values, convert to string
                    formatted_questions.append({"question_text": str(q), "criteria": "Not specified"})
        elif isinstance(questions_data, dict):
            # If it's a dictionary (single question), convert it to a list with one item
            formatted_questions.append(questions_data)
        
        # Get other company info
        time_slots = result.get("time_slots", [])
        contact_info = result.get("contact_info", {})

        return {
            "dsp_code": dsp_code, 
            "questions": formatted_questions,
            "time_slots": time_slots,
            "contact_info": contact_info,
            "recurrence_time_slots": recurrence_time_slots,
            "structured_recurrence_time_slots": structured_recurrence_time_slots
        }

    except Exception as e:
        logger.error(f"Error in get_company_questions: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/formatted-questions/{dsp_code}",
    summary="Get human-readable formatted questions",
    description="Retrieve the list of questions and criteria in a human-readable format for a specific company"
)
async def get_formatted_questions(dsp_code: str):
    try:
        questions_manager = get_company_questions_manager()
        company_data = questions_manager.get_questions(dsp_code)
        questions = company_data.get("questions", [])
        
        if not questions:
            return {
                "dsp_code": dsp_code,
                "formatted_questions": "No screening questions available for this company."
            }
        
        # Format questions in a human-readable format
        formatted_text = f"Screening Questions for Company {dsp_code}:\n\n"
        
        for i, question in enumerate(questions, 1):
            formatted_text += f"{i}. {question.get('question_text', 'No question text')}\n"
            
            # Add criteria if available
            criteria = question.get('criteria', '')
            if criteria:
                formatted_text += f"   Criteria: {criteria}\n"
            
            # Add a blank line between questions
            formatted_text += "\n"
        
        return {
            # "dsp_code": dsp_code,
            "formatted_questions": formatted_text.strip()
        }

    except Exception as e:
        logger.error(f"Error formatting questions: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/company-time-slots/{dsp_code}",
    summary="Get company time slots",
    description="Retrieve the available time slots for a specific company"
)
async def get_company_time_slots(dsp_code: str):
    try:
        questions_manager = get_company_questions_manager()
        company_data = questions_manager.get_questions(dsp_code)
        
        # Get all types of time slots
        time_slots = company_data.get("time_slots", [])
        recurrence_time_slots = company_data.get("recurrence_time_slots", [])
        structured_recurrence_time_slots = company_data.get("structured_recurrence_time_slots", [])
        
        # Format legacy recurrence time slots with dates
        formatted_legacy_slots = format_recurrence_time_slots(recurrence_time_slots)
        
        # Format structured recurrence time slots
        structured_slots = []
        if structured_recurrence_time_slots:
            # Convert dictionaries to RecurrenceTimeSlot objects if needed
            recurrence_objects = []
            for slot_dict in structured_recurrence_time_slots:
                try:
                    recurrence_objects.append(RecurrenceTimeSlot(**slot_dict))
                except Exception as e:
                    logger.error(f"Error converting structured time slot: {e}")
            
            # Generate concrete time slots from the recurrence patterns
            if recurrence_objects:
                structured_slots = generate_time_slots_from_recurrence(recurrence_objects, num_occurrences=2)
        
        # Combine all types of time slots
        all_time_slots = time_slots + formatted_legacy_slots + structured_slots
        
        if not all_time_slots:
            return {
                "dsp_code": dsp_code,
                "time_slots": [],
                "formatted_time_slots": "No available time slots for this company."
            }
        
        # Create a human-readable format
        formatted_text = f"Available Time Slots for Company {dsp_code}:\n\n"
        for i, slot in enumerate(all_time_slots, 1):
            formatted_text += f"{i}. {slot}\n"
        
        return {
            "formatted_time_slots": formatted_text.strip()
        }

    except Exception as e:
        logger.error(f"Error retrieving time slots: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/company-questions",
    summary="Save company-specific questions",
    description="Save a list of questions for a specific company"
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
