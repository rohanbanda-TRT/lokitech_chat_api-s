from typing import List, Dict, Any, Optional
import json
import logging
from firebase_admin import firestore
from ..core.firebase_config import get_firestore_db

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class FirebaseCompanyQuestionsManager:
    """
    Manager class for company-specific questions using Firebase Firestore
    """

    def __init__(self):
        self.db = get_firestore_db()
        self.collection = self.db.collection("company_questions")
        logger.info("FirebaseCompanyQuestionsManager initialized")

    def create_questions(
        self, dsp_code: str, questions: List[Dict[str, Any]], append: bool = True,
        time_slots: Optional[List[str]] = None, recurrence_time_slots: Optional[List[str]] = None,
        structured_recurrence_time_slots: Optional[List[Dict[str, Any]]] = None,
        contact_info: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Create or add company-specific questions to the database

        Args:
            dsp_code: The unique identifier for the company
            questions: List of question objects with question_text and required fields
            append: If True, append new questions to existing ones; if False, replace them
            time_slots: Optional list of available time slots with specific dates
            recurrence_time_slots: Optional list of recurring time slots (e.g., "Monday 9 AM - 5 PM")
            structured_recurrence_time_slots: Optional list of structured recurring time slots
            contact_info: Optional contact information as a dictionary with contact_person_name, contact_number, and email_id

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            logger.info(f"Attempting to create questions for dsp_code: {dsp_code}")
            logger.info(f"Questions to create: {questions}")
            logger.info(f"Append mode: {append}")
            logger.info(f"Time slots: {time_slots}")
            logger.info(f"Recurrence time slots: {recurrence_time_slots}")
            logger.info(f"Structured recurrence time slots: {structured_recurrence_time_slots}")
            logger.info(f"Contact info: {contact_info}")

            # Reference to the document
            doc_ref = self.collection.document(dsp_code)

            # Get the document
            doc = doc_ref.get()
            
            # Prepare update data
            update_data = {}
            
            if questions:
                if doc.exists and append:
                    # Get existing questions and append new ones
                    doc_data = doc.to_dict()
                    existing_questions = doc_data.get("questions", [])
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
            
            # Add recurrence_time_slots if provided
            if recurrence_time_slots is not None:
                update_data["recurrence_time_slots"] = recurrence_time_slots
                
            # Add structured_recurrence_time_slots if provided
            if structured_recurrence_time_slots is not None:
                # Convert RecurrenceTimeSlot objects to dictionaries if they aren't already
                if structured_recurrence_time_slots and hasattr(structured_recurrence_time_slots[0], "dict"):
                    slot_dicts = [slot.dict() for slot in structured_recurrence_time_slots]
                else:
                    slot_dicts = structured_recurrence_time_slots
                update_data["structured_recurrence_time_slots"] = slot_dicts
                
            # Add contact_info if provided
            if contact_info is not None:
                update_data["contact_info"] = contact_info

            # Update or set the document
            if doc.exists:
                doc_ref.update(update_data)
                logger.info(f"Updated document with new data")
            else:
                doc_ref.set(update_data)
                logger.info(f"Created new document with data")
                
            return True

        except Exception as e:
            logger.error(f"Error creating/updating company data: {e}")
            import traceback

            logger.error(f"Traceback: {traceback.format_exc()}")
            return False

    def get_questions(self, dsp_code: str) -> Dict[str, Any]:
        """
        Retrieve company-specific questions and info from the database

        Args:
            dsp_code: The unique identifier for the company

        Returns:
            Dict containing questions, time_slots, recurrence_time_slots, structured_recurrence_time_slots, and contact_info
        """
        try:
            logger.info(f"Retrieving questions for dsp_code: {dsp_code}")

            # Get the document
            doc = self.collection.document(dsp_code).get()

            if doc.exists:
                # Convert to dict and remove _id field
                data = doc.to_dict()
                
                # Get questions and ensure they're in a consistent format
                questions = data.get("questions", [])
                formatted_questions = []
                
                # Process questions to ensure consistent format
                if isinstance(questions, list):
                    for q in questions:
                        if isinstance(q, dict):
                            formatted_questions.append(q)
                        elif isinstance(q, str):
                            try:
                                # Try to parse as JSON
                                q_dict = json.loads(q)
                                formatted_questions.append(q_dict)
                            except json.JSONDecodeError:
                                # If not JSON, create a simple question object
                                formatted_questions.append({"question_text": q, "criteria": "Not specified"})
                        else:
                            # For any other type, convert to string
                            formatted_questions.append({"question_text": str(q), "criteria": "Not specified"})
                elif isinstance(questions, dict):
                    # If it's a single dictionary, add it as a question
                    formatted_questions.append(questions)
                
                result = {
                    "questions": formatted_questions,
                    "time_slots": data.get("time_slots", []),
                    "recurrence_time_slots": data.get("recurrence_time_slots", []),
                    "structured_recurrence_time_slots": data.get("structured_recurrence_time_slots", []),
                    "contact_info": data.get("contact_info", None)
                }
                logger.info(f"Found data for dsp_code: {dsp_code}")
                return result
            else:
                logger.info(f"No data found for dsp_code: {dsp_code}")
                return {
                    "questions": [], 
                    "time_slots": [], 
                    "recurrence_time_slots": [], 
                    "structured_recurrence_time_slots": [],
                    "contact_info": None
                }

        except Exception as e:
            logger.error(f"Error retrieving questions: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {
                "questions": [], 
                "time_slots": [], 
                "recurrence_time_slots": [], 
                "structured_recurrence_time_slots": [],
                "contact_info": None
            }

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

            # Get the document
            doc_ref = self.collection.document(dsp_code)
            doc = doc_ref.get()

            if not doc.exists:
                logger.error(f"No document found for dsp_code: {dsp_code}")
                return False

            # Get current questions
            doc_data = doc.to_dict()
            questions = doc_data.get("questions", [])

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

            # Update the question at the specified index
            questions[question_index] = updated_question

            # Update the document
            doc_ref.update({"questions": questions})
            logger.info(f"Updated question at index {question_index}")
            return True

        except Exception as e:
            logger.error(f"Error updating question: {e}")
            import traceback

            logger.error(f"Traceback: {traceback.format_exc()}")
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

            # Get the document
            doc_ref = self.collection.document(dsp_code)
            doc = doc_ref.get()

            if not doc.exists:
                logger.error(f"No document found for dsp_code: {dsp_code}")
                return False

            # Get current questions
            doc_data = doc.to_dict()
            questions = doc_data.get("questions", [])

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

            # Update the document
            doc_ref.update({"questions": questions})
            logger.info(f"Updated document after removing question")
            return True

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

            # Reference to the document
            doc_ref = self.collection.document(dsp_code)
            
            # Update or create the document with time slots
            if doc_ref.get().exists:
                doc_ref.update({"time_slots": time_slots})
                logger.info(f"Updated document with time slots")
            else:
                doc_ref.set({"time_slots": time_slots})
                logger.info(f"Created new document with time slots")
                
            return True

        except Exception as e:
            logger.error(f"Error updating time slots: {e}")
            import traceback

            logger.error(f"Traceback: {traceback.format_exc()}")
            return False
            
    def update_contact_info(self, dsp_code: str, contact_info: Dict[str, Any]) -> bool:
        """
        Update contact information for a company

        Args:
            dsp_code: The unique identifier for the company
            contact_info: Contact information dictionary with contact_person_name, contact_number, and email_id

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            logger.info(f"Updating contact info for dsp_code: {dsp_code}")
            logger.info(f"Contact info: {contact_info}")

            # Reference to the document
            doc_ref = self.collection.document(dsp_code)
            
            # Update or create the document with contact info
            if doc_ref.get().exists:
                doc_ref.update({"contact_info": contact_info})
                logger.info(f"Updated document with contact info")
            else:
                doc_ref.set({"contact_info": contact_info})
                logger.info(f"Created new document with contact info")
                
            return True

        except Exception as e:
            logger.error(f"Error updating contact info: {e}")
            import traceback

            logger.error(f"Traceback: {traceback.format_exc()}")
            return False
            
    def update_recurrence_time_slots(self, dsp_code: str, recurrence_time_slots: List[str]) -> bool:
        """
        Update recurring time slots for a company

        Args:
            dsp_code: The unique identifier for the company
            recurrence_time_slots: List of recurring time slots (e.g., "Monday 9 AM - 5 PM")

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            logger.info(f"Updating recurrence time slots for dsp_code: {dsp_code}")
            logger.info(f"Recurrence time slots: {recurrence_time_slots}")

            # Reference to the document
            doc_ref = self.collection.document(dsp_code)
            
            # Update or create the document with recurrence time slots
            if doc_ref.get().exists:
                doc_ref.update({"recurrence_time_slots": recurrence_time_slots})
                logger.info(f"Updated document with recurrence time slots")
            else:
                doc_ref.set({"recurrence_time_slots": recurrence_time_slots})
                logger.info(f"Created new document with recurrence time slots")
                
            return True

        except Exception as e:
            logger.error(f"Error updating recurrence time slots: {e}")
            import traceback

            logger.error(f"Traceback: {traceback.format_exc()}")
            return False
            
    def update_structured_recurrence_time_slots(self, dsp_code: str, structured_recurrence_time_slots: List[Dict[str, Any]]) -> bool:
        """
        Update structured recurring time slots for a company

        Args:
            dsp_code: The unique identifier for the company
            structured_recurrence_time_slots: List of structured recurring time slots

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            logger.info(f"Updating structured recurrence time slots for dsp_code: {dsp_code}")
            logger.info(f"Structured recurrence time slots: {structured_recurrence_time_slots}")

            # Convert RecurrenceTimeSlot objects to dictionaries if they aren't already
            if structured_recurrence_time_slots and hasattr(structured_recurrence_time_slots[0], "dict"):
                slot_dicts = [slot.dict() for slot in structured_recurrence_time_slots]
            else:
                slot_dicts = structured_recurrence_time_slots

            # Reference to the document
            doc_ref = self.collection.document(dsp_code)
            
            # Update or create the document with structured recurrence time slots
            if doc_ref.get().exists:
                doc_ref.update({"structured_recurrence_time_slots": slot_dicts})
                logger.info(f"Updated document with structured recurrence time slots")
            else:
                doc_ref.set({"structured_recurrence_time_slots": slot_dicts})
                logger.info(f"Created new document with structured recurrence time slots")
                
            return True

        except Exception as e:
            logger.error(f"Error updating structured recurrence time slots: {e}")
            import traceback

            logger.error(f"Traceback: {traceback.format_exc()}")
            return False
            
    def delete_recurrence_time_slots(self, dsp_code: str, structured_recurrence: bool) -> bool:
        """
        Delete recurring time slots for a company

        Args:
            dsp_code: The unique identifier for the company
            structured_recurrence: If True, delete structured recurrence slots, if False delete legacy recurrence slots

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            logger.info(f"Deleting {'structured' if structured_recurrence else 'legacy'} recurrence time slots for dsp_code: {dsp_code}")

            # Reference to the document
            doc_ref = self.collection.document(dsp_code)
            doc = doc_ref.get()
            
            # Check if the document exists
            if not doc.exists:
                logger.error(f"No document found for dsp_code: {dsp_code}")
                return False

            # Update the document to remove either structured or legacy recurrence time slots
            update_data = {
                "structured_recurrence_time_slots": [] if structured_recurrence else doc.to_dict().get("structured_recurrence_time_slots", []),
                "recurrence_time_slots": [] if not structured_recurrence else doc.to_dict().get("recurrence_time_slots", [])
            }
            
            doc_ref.update(update_data)
            logger.info(f"Deleted {'structured' if structured_recurrence else 'legacy'} recurrence time slots for company {dsp_code}")
                
            return True

        except Exception as e:
            logger.error(f"Error deleting recurrence time slots: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False
