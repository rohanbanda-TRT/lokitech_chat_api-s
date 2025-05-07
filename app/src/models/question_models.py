from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional


class Question(BaseModel):
    """
    Model for a screening question
    """

    question_text: str = Field(description="The text of the question to ask the driver")
    criteria: Optional[str] = Field(
        default=None, description="Criteria to evaluate the driver's answer against"
    )


class ContactInfo(BaseModel):
    """
    Model for structured contact information
    """
    
    contact_person_name: str = Field(description="Name of the contact person")
    contact_number: str = Field(description="Contact phone number")
    email_id: str = Field(description="Email address for contact")


class CompanyQuestions(BaseModel):
    """
    Model for a set of company questions
    """

    dsp_code: str = Field(description="Unique identifier for the company")
    questions: List[Question] = Field(description="List of screening questions")
    time_slots: Optional[List[str]] = Field(
        default=None, description="Available time slots for screening"
    )
    contact_info: Optional[ContactInfo] = Field(
        default=None, description="Structured contact information for the company"
    )
    append: bool = Field(
        default=True,
        description="Whether to append to existing questions or replace them",
    )


class UpdateQuestionInput(BaseModel):
    """
    Model for updating a specific question
    """

    dsp_code: str = Field(description="Unique identifier for the company")
    question_index: int = Field(description="Index of the question to update (0-based)")
    updated_question: Question = Field(description="Updated question data")


class DeleteQuestionInput(BaseModel):
    """
    Model for deleting a specific question
    """

    dsp_code: str = Field(description="Unique identifier for the company")
    question_index: int = Field(description="Index of the question to delete (0-based)")


class UpdateTimeSlotsInput(BaseModel):
    """
    Model for updating time slots
    """
    
    dsp_code: str = Field(description="Unique identifier for the company")
    time_slots: List[str] = Field(description="Available time slots for screening")


class UpdateContactInfoInput(BaseModel):
    """
    Model for updating contact information
    """
    
    dsp_code: str = Field(description="Unique identifier for the company")
    contact_info: ContactInfo = Field(description="Structured contact information for the company")
