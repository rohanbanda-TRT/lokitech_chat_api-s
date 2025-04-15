from typing import List, Dict, Any, Optional
import json
import logging
from pymongo import IndexModel, ASCENDING
from pymongo.errors import PyMongoError
from ..core.database import get_db

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
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

    def create_questions(
        self, dsp_code: str, questions: List[Dict[str, Any]], append: bool = True,
        time_slots: Optional[List[str]] = None, contact_info: Optional[str] = None
    ) -> bool:
        """
        Create or add company-specific questions to the database

        Args:
            dsp_code: The unique identifier for the company
            questions: List of question objects with question_text and required fields
            append: If True, append new questions to existing ones; if False, replace them
            time_slots: Optional list of available time slots
            contact_info: Optional contact information

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            logger.info(f"Attempting to create questions for dsp_code: {dsp_code}")
            logger.info(f"Questions to create: {questions}")
            logger.info(f"Append mode: {append}")
            logger.info(f"Time slots: {time_slots}")
            logger.info(f"Contact info: {contact_info}")

            # Check if company already has questions
            existing = self.collection.find_one({"dsp_code": dsp_code})
            
            # Prepare update data
            update_data = {}
            
            if questions:
                if existing and append:
                    # Get existing questions and append new ones
                    existing_questions = existing.get("questions", [])
                    logger.info(f"Found {len(existing_questions)} existing questions")

                    # Combine existing questions with new ones
                    combined_questions = existing_questions + questions
                    logger.info(f"Combined questions count: {len(combined_questions)}")
                    
                    update_data["questions"] = combined_questions
                else:
                    update_data["questions"] = questions
            
            # Add time_slots if provided
            if time_slots is not None:
                update_data["time_slots"] = time_slots
                
            # Add contact_info if provided
            if contact_info is not None:
                update_data["contact_info"] = contact_info
                
            # Use upsert to either update or insert
            result = self.collection.update_one(
                {"dsp_code": dsp_code},
                {"$set": update_data},
                upsert=True,  # Create a new document if it doesn't exist
            )

            logger.info(
                f"Upsert result: {result.modified_count} modified, {result.upserted_id is not None} upserted"
            )
            return result.modified_count > 0 or result.upserted_id is not None

        except Exception as e:
            logger.error(f"Error creating questions: {e}")
            return False

    def get_questions(self, dsp_code: str) -> Dict[str, Any]:
        """
        Retrieve company-specific questions and info from the database

        Args:
            dsp_code: The unique identifier for the company

        Returns:
            Dict containing questions, time_slots, and contact_info
        """
        try:
            logger.info(f"Retrieving questions for dsp_code: {dsp_code}")

            # Find company questions document
            company_doc = self.collection.find_one(
                {"dsp_code": dsp_code},
                {
                    "_id": 0,
                },  # Exclude _id field
            )

            if company_doc:
                result = {
                    "questions": company_doc.get("questions", []),
                    "time_slots": company_doc.get("time_slots", None),
                    "contact_info": company_doc.get("contact_info", None)
                }
                logger.info(f"Found data for dsp_code: {dsp_code}")
                return result
            else:
                logger.info(f"No data found for dsp_code: {dsp_code}")
                return {"questions": [], "time_slots": None, "contact_info": None}

        except Exception as e:
            logger.error(f"Error retrieving questions: {e}")
            return {"questions": [], "time_slots": None, "contact_info": None}

    def update_question(
        self, dsp_code: str, question_index: int, updated_question: Dict[str, Any]
    ) -> bool:
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
            logger.info(
                f"Updating question at index {question_index} for dsp_code: {dsp_code}"
            )
            logger.info(f"Updated question: {updated_question}")

            # Update the specific question using the positional $ operator
            result = self.collection.update_one(
                {"dsp_code": dsp_code},
                {"$set": {f"questions.{question_index}": updated_question}},
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
            logger.info(
                f"Deleting question at index {question_index} for dsp_code: {dsp_code}"
            )

            # Get current questions
            company_doc = self.collection.find_one({"dsp_code": dsp_code})

            if not company_doc:
                logger.error(f"No document found for dsp_code: {dsp_code}")
                return False

            if "questions" not in company_doc:
                logger.error(
                    f"No 'questions' field in document for dsp_code: {dsp_code}"
                )
                logger.error(f"Document structure: {company_doc}")
                return False

            questions = company_doc["questions"]
            logger.info(f"Found {len(questions)} questions for dsp_code: {dsp_code}")
            logger.info(f"Current questions: {questions}")

            if not isinstance(questions, list):
                logger.error(
                    f"'questions' field is not a list. Type: {type(questions)}"
                )
                return False

            if question_index < 0 or question_index >= len(questions):
                logger.error(
                    f"Question index {question_index} out of range (0-{len(questions)-1})"
                )
                return False

            # Remove the question at the specified index
            logger.info(
                f"Removing question at index {question_index}: {questions[question_index]}"
            )
            questions.pop(question_index)
            logger.info(f"Questions after removal: {questions}")

            # Update the document with the modified questions list
            result = self.collection.update_one(
                {"dsp_code": dsp_code}, {"$set": {"questions": questions}}
            )

            success = result.modified_count > 0
            logger.info(
                f"Delete result: {result.modified_count} documents modified, matched_count: {result.matched_count}"
            )
            return success

        except Exception as e:
            logger.error(f"Error deleting question: {e}")
            import traceback

            logger.error(f"Traceback: {traceback.format_exc()}")
            return False

    def update_time_slots(self, dsp_code: str, time_slots: List[str]) -> bool:
        """
        Update time slots for a company

        Args:
            dsp_code: The unique identifier for the company
            time_slots: List of available time slots

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            logger.info(f"Updating time slots for dsp_code: {dsp_code}")
            logger.info(f"Time slots: {time_slots}")

            # Update the time slots
            result = self.collection.update_one(
                {"dsp_code": dsp_code},
                {"$set": {"time_slots": time_slots}},
                upsert=True  # Create if it doesn't exist
            )

            success = result.modified_count > 0 or result.upserted_id is not None
            logger.info(f"Update result: {result.modified_count} documents modified, {result.upserted_id is not None} upserted")
            return success

        except Exception as e:
            logger.error(f"Error updating time slots: {e}")
            return False
            
    def update_contact_info(self, dsp_code: str, contact_info: str) -> bool:
        """
        Update contact information for a company

        Args:
            dsp_code: The unique identifier for the company
            contact_info: Contact information

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            logger.info(f"Updating contact info for dsp_code: {dsp_code}")
            logger.info(f"Contact info: {contact_info}")

            # Update the contact info
            result = self.collection.update_one(
                {"dsp_code": dsp_code},
                {"$set": {"contact_info": contact_info}},
                upsert=True  # Create if it doesn't exist
            )

            success = result.modified_count > 0 or result.upserted_id is not None
            logger.info(f"Update result: {result.modified_count} documents modified, {result.upserted_id is not None} upserted")
            return success

        except Exception as e:
            logger.error(f"Error updating contact info: {e}")
            return False
