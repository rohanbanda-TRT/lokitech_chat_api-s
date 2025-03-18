from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class Question(BaseModel):
    """
    Model for a screening question
    """
    question_text: str = Field(description="The text of the question to ask the driver")
    required: bool = Field(default=False, description="Whether this question is required to be answered")

class CompanyQuestions(BaseModel):
    """
    Model for a set of company questions
    """
    company_id: str = Field(description="Unique identifier for the company")
    questions: List[Question] = Field(description="List of screening questions for driver candidates")
    append: bool = Field(default=True, description="Whether to append the question or replace it")

class UpdateQuestionInput(BaseModel):
    """
    Model for updating a specific question
    """
    company_id: str = Field(description="Unique identifier for the company")
    question_index: int = Field(description="The index of the question to update (0-based)")
    updated_question: Question = Field(description="The updated question")

class DeleteQuestionInput(BaseModel):
    """
    Model for deleting a specific question
    """
    company_id: str = Field(description="Unique identifier for the company")
    question_index: int = Field(description="The index of the question to delete (0-based)")
