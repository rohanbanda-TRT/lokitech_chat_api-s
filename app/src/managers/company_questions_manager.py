from typing import List, Dict, Any, Optional
import json
import logging
from pymongo import IndexModel, ASCENDING
from pymongo.errors import PyMongoError
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
        
        # Create indexes for better query performance
        try:
            self.collection.create_index("dsp_code", unique=True)
            logger.info("Created index on dsp_code field")
        except PyMongoError as e:
            logger.warning(f"Index creation warning (may already exist): {e}")
        
        logger.info("CompanyQuestionsManager initialized")
    
    def create_questions(self, dsp_code: str, questions: List[Dict[str, Any]], append: bool = True) -> bool:
        """
        Create or add company-specific questions to the database
        
        Args:
            dsp_code: The unique identifier for the company
            questions: List of question objects with question_text and required fields
            append: If True, append new questions to existing ones; if False, replace them
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            logger.info(f"Attempting to create questions for dsp_code: {dsp_code}")
            logger.info(f"Questions to create: {questions}")
            logger.info(f"Append mode: {append}")
            
            # Check if company already has questions
            existing = self.collection.find_one({"dsp_code": dsp_code})
            
            if existing and append:
                # Get existing questions and append new ones
                existing_questions = existing.get("questions", [])
                logger.info(f"Found {len(existing_questions)} existing questions")
                
                # Combine existing questions with new ones
                combined_questions = existing_questions + questions
                logger.info(f"Combined questions count: {len(combined_questions)}")
                
                # Update with combined questions
                result = self.collection.update_one(
                    {"dsp_code": dsp_code},
                    {"$set": {"questions": combined_questions}},
                    upsert=False  # Don't create a new document if it doesn't exist
                )
                
                logger.info(f"Update result: {result.modified_count} documents modified")
                return result.modified_count > 0
            else:
                # Either no existing questions or not in append mode
                # Use upsert to either update or insert
                result = self.collection.update_one(
                    {"dsp_code": dsp_code},
                    {"$set": {"questions": questions}},
                    upsert=True  # Create a new document if it doesn't exist
                )
                
                logger.info(f"Upsert result: {result.modified_count} modified, {result.upserted_id is not None} upserted")
                return result.modified_count > 0 or result.upserted_id is not None
                
        except Exception as e:
            logger.error(f"Error creating questions: {e}")
            return False
    
    def get_questions(self, dsp_code: str) -> List[Dict[str, Any]]:
        """
        Retrieve company-specific questions from the database
        
        Args:
            dsp_code: The unique identifier for the company
            
        Returns:
            List of question objects
        """
        try:
            logger.info(f"Retrieving questions for dsp_code: {dsp_code}")
            
            # Find company questions document
            company_doc = self.collection.find_one(
                {"dsp_code": dsp_code},
                {"_id": 0, "questions": 1}  # Projection to only return the questions field
            )
            
            if company_doc and "questions" in company_doc:
                questions = company_doc["questions"]
                logger.info(f"Found {len(questions)} questions for dsp_code: {dsp_code}")
                return questions
            else:
                logger.info(f"No questions found for dsp_code: {dsp_code}")
                return []
                
        except Exception as e:
            logger.error(f"Error retrieving questions: {e}")
            return []
    
    def update_question(self, dsp_code: str, question_index: int, updated_question: Dict[str, Any]) -> bool:
        """
        Update a specific question for a company
        
        Args:
            dsp_code: The unique identifier for the company
            question_index: The index of the question to update
            updated_question: The updated question object
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            logger.info(f"Updating question at index {question_index} for dsp_code: {dsp_code}")
            logger.info(f"Updated question: {updated_question}")
            
            # Update the specific question using the positional $ operator
            result = self.collection.update_one(
                {"dsp_code": dsp_code},
                {"$set": {f"questions.{question_index}": updated_question}}
            )
            
            success = result.modified_count > 0
            logger.info(f"Update result: {result.modified_count} documents modified")
            return success
            
        except Exception as e:
            logger.error(f"Error updating question: {e}")
            return False
    
    def delete_question(self, dsp_code: str, question_index: int) -> bool:
        """
        Delete a specific question for a company
        
        Args:
            dsp_code: The unique identifier for the company
            question_index: The index of the question to delete
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            logger.info(f"Deleting question at index {question_index} for dsp_code: {dsp_code}")
            
            # Get current questions
            company_doc = self.collection.find_one({"dsp_code": dsp_code})
            
            if not company_doc:
                logger.error(f"No document found for dsp_code: {dsp_code}")
                return False
                
            if "questions" not in company_doc:
                logger.error(f"No 'questions' field in document for dsp_code: {dsp_code}")
                logger.error(f"Document structure: {company_doc}")
                return False
                
            questions = company_doc["questions"]
            logger.info(f"Found {len(questions)} questions for dsp_code: {dsp_code}")
            logger.info(f"Current questions: {questions}")
            
            if not isinstance(questions, list):
                logger.error(f"'questions' field is not a list. Type: {type(questions)}")
                return False
            
            if question_index < 0 or question_index >= len(questions):
                logger.error(f"Question index {question_index} out of range (0-{len(questions)-1})")
                return False
                
            # Remove the question at the specified index
            logger.info(f"Removing question at index {question_index}: {questions[question_index]}")
            questions.pop(question_index)
            logger.info(f"Questions after removal: {questions}")
            
            # Update the document with the modified questions list
            result = self.collection.update_one(
                {"dsp_code": dsp_code},
                {"$set": {"questions": questions}}
            )
            
            success = result.modified_count > 0
            logger.info(f"Delete result: {result.modified_count} documents modified, matched_count: {result.matched_count}")
            return success
            
        except Exception as e:
            logger.error(f"Error deleting question: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False