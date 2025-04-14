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


class CompanyQuestions(BaseModel):
    """
    Model for a set of company questions
    """

    dsp_code: str = Field(description="Unique identifier for the company")
    questions: List[Question] = Field(description="List of screening questions")
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
