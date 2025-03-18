from typing import List, Dict, Any, Optional
import json
import logging
from ..core.database import get_db

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CompanyQuestionsManager:
    """
    Manager class for company-specific questions
    """
    def __init__(self):
        self.db = get_db()
        self.collection = self.db.get_collection("company_questions")
        logger.info("CompanyQuestionsManager initialized")
    
    def create_questions(self, company_id: str, questions: List[Dict[str, Any]], append: bool = True) -> bool:
        """
        Create or add company-specific questions to the database
        
        Args:
            company_id: The unique identifier for the company
            questions: List of question objects with question_text and required fields
            append: If True, append new questions to existing ones; if False, replace them
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            logger.info(f"Attempting to create questions for company_id: {company_id}")
            logger.info(f"Questions to create: {questions}")
            logger.info(f"Append mode: {append}")
            
            # Check if company already has questions
            existing = self.collection.find_one({"company_id": company_id})
            
            if existing and append:
                # Get existing questions and append new ones
                existing_questions = existing.get("questions", [])
                logger.info(f"Found {len(existing_questions)} existing questions")
                
                # Combine existing questions with new ones
                combined_questions = existing_questions + questions
                logger.info(f"Combined questions count: {len(combined_questions)}")
                
                # Update with combined questions
                self.collection.update_one(
                    {"company_id": company_id},
                    {"$set": {"questions": combined_questions}}
                )
            elif existing:
                # Replace existing questions
                logger.info(f"Replacing existing questions for company_id: {company_id}")
                self.collection.update_one(
                    {"company_id": company_id},
                    {"$set": {"questions": questions}}
                )
            else:
                # Insert new document
                logger.info(f"Inserting new questions for company_id: {company_id}")
                self.collection.insert_one({
                    "company_id": company_id,
                    "questions": questions
                })
            logger.info(f"Successfully created questions for company_id: {company_id}")
            return True
        except Exception as e:
            logger.error(f"Error creating questions: {e}")
            return False
    
    def get_questions(self, company_id: str) -> List[Dict[str, Any]]:
        """
        Retrieve company-specific questions from the database
        
        Args:
            company_id: The unique identifier for the company
            
        Returns:
            List of question objects or empty list if none found
        """
        try:
            logger.info(f"Retrieving questions for company_id: {company_id}")
            result = self.collection.find_one({"company_id": company_id})
            if result and "questions" in result:
                logger.info(f"Found {len(result['questions'])} questions for company_id: {company_id}")
                return result["questions"]
            logger.info(f"No questions found for company_id: {company_id}")
            return []
        except Exception as e:
            logger.error(f"Error retrieving questions: {e}")
            return []
    
    def update_question(self, company_id: str, question_index: int, updated_question: Dict[str, Any]) -> bool:
        """
        Update a specific question for a company
        
        Args:
            company_id: The unique identifier for the company
            question_index: The index of the question to update (0-based)
            updated_question: The updated question object
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            logger.info(f"Attempting to update question at index {question_index} for company_id: {company_id}")
            logger.info(f"Updated question: {updated_question}")
            
            # Get current questions
            current_questions = self.get_questions(company_id)
            
            # Check if index is valid
            if not current_questions or question_index < 0 or question_index >= len(current_questions):
                logger.error(f"Invalid question index: {question_index}")
                return False
            
            # Update the question at the specified index
            current_questions[question_index] = updated_question
            
            # Save the updated questions directly
            existing = self.collection.find_one({"company_id": company_id})
            if existing:
                self.collection.update_one(
                    {"company_id": company_id},
                    {"$set": {"questions": current_questions}}
                )
                logger.info(f"Successfully updated question at index {question_index} for company_id: {company_id}")
                return True
            else:
                logger.error(f"Company with ID {company_id} not found")
                return False
        except Exception as e:
            logger.error(f"Error updating question: {e}")
            return False
    
    def delete_question(self, company_id: str, question_index: int) -> bool:
        """
        Delete a specific question for a company
        
        Args:
            company_id: The unique identifier for the company
            question_index: The index of the question to delete (0-based)
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            logger.info(f"Attempting to delete question at index {question_index} for company_id: {company_id}")
            
            # Get current questions
            current_questions = self.get_questions(company_id)
            
            # Check if index is valid
            if not current_questions or question_index < 0 or question_index >= len(current_questions):
                logger.error(f"Invalid question index: {question_index}")
                return False
            
            # Remove the question at the specified index
            deleted_question = current_questions.pop(question_index)
            logger.info(f"Deleted question: {deleted_question}")
            
            # Save the updated questions directly
            existing = self.collection.find_one({"company_id": company_id})
            if existing:
                self.collection.update_one(
                    {"company_id": company_id},
                    {"$set": {"questions": current_questions}}
                )
                logger.info(f"Successfully deleted question at index {question_index} for company_id: {company_id}")
                return True
            else:
                logger.error(f"Company with ID {company_id} not found")
                return False
        except Exception as e:
            logger.error(f"Error deleting question: {e}")
            return False
