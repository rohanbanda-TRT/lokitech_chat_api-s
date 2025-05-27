from pydantic import BaseModel, Field, model_validator
from typing import Annotated, TypedDict, Dict, Any, Optional, List




class CreateQuestionsInput(BaseModel):
    dsp_code: str = Field(description="Unique identifier for the company")
    questions: Optional[List[Dict[str, Any]]] = Field(default=None, description="List of questions with question_text and criteria")
    time_slots: Optional[List[str]] = Field(default=None, description="Available time slots for screening")
    contact_info: Optional[Dict[str, Any]] = Field(default=None, description="Structured contact information with contact_person_name, contact_number, and email_id fields")
    append: bool = Field(default=True, description="Whether to append to existing questions or replace them")


class GetQuestionsInput(BaseModel):
    dsp_code: str = Field(description="Unique identifier for the company")


class UpdateQuestionToolInput(BaseModel):
    dsp_code: str = Field(description="Unique identifier for the company")
    question_index: int = Field(description="Index of the question to update (0-based)")
    updated_question: Dict[str, Any] = Field(description="Updated question data")


class DeleteQuestionToolInput(BaseModel):
    dsp_code: str = Field(description="Unique identifier for the company")
    question_index: int = Field(description="Index of the question to delete (0-based)")


class UpdateTimeSlotsToolInput(BaseModel):
    dsp_code: str = Field(description="Unique identifier for the company")
    time_slots: List[str] = Field(description="Available time slots for screening")
    is_recurrence: bool = Field(default=False, description="Whether these are recurring time slots")


class UpdateStructuredRecurrenceToolInput(BaseModel):
    dsp_code: str = Field(description="Unique identifier for the company")
    structured_recurrence_patterns: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="List of structured recurrence patterns with fields like pattern_type, day_of_week, etc."
    )
    recurrence_patterns: Optional[List[str]] = Field(
        default=None,
        description="List of recurrence patterns in natural language format (legacy field)"
    )
    
    @model_validator(mode='after')
    def check_at_least_one_pattern_field(self) -> 'UpdateStructuredRecurrenceToolInput':
        if self.structured_recurrence_patterns is None and self.recurrence_patterns is None:
            raise ValueError("Either structured_recurrence_patterns or recurrence_patterns must be provided")
        return self


class UpdateContactInfoToolInput(BaseModel):
    dsp_code: str = Field(description="Unique identifier for the company")
    contact_info: Dict[str, Any] = Field(description="Structured contact information with contact_person_name, contact_number, and email_id fields")


class DeleteRecurrenceTimeSlotsToolInput(BaseModel):
    dsp_code: str = Field(description="Unique identifier for the company")
