from typing import List, Dict, Any
import json
import logging
from .database import get_db

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CompanyQuestionsManager:
    def __init__(self):
        self.db = get_db()
        self.collection = self.db.get_collection("company_questions")
        logger.info("CompanyQuestionsManager initialized")
    
    def save_questions(self, company_id: str, questions: List[Dict[str, Any]]) -> bool:
        """
        Save company-specific questions to the database
        
        Args:
            company_id: The unique identifier for the company
            questions: List of question objects with question_text and required fields
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            logger.info(f"Attempting to save questions for company_id: {company_id}")
            logger.info(f"Questions to save: {questions}")
            
            # Check if company already has questions
            existing = self.collection.find_one({"company_id": company_id})
            
            if existing:
                # Update existing questions
                logger.info(f"Updating existing questions for company_id: {company_id}")
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
            logger.info(f"Successfully saved questions for company_id: {company_id}")
            return True
        except Exception as e:
            logger.error(f"Error saving questions: {e}")
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

# Note: The CompanyAdminAgent class has been moved to app.src.agents.company_admin
# Please import it from there instead:
# from app.src.agents import CompanyAdminAgent
