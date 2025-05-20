import json
import logging
from typing import List, Dict, Any, Optional, Union
from ..models.question_models import (
    Question,
    CompanyQuestions,
    UpdateQuestionInput,
    DeleteQuestionInput,
    UpdateTimeSlotsInput,
    UpdateContactInfoInput,
)
from ..managers.company_questions_factory import get_company_questions_manager
import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class CompanyAdminTools:
    """
    Tools for company admin operations
    """

    def __init__(self):
        self.questions_manager = get_company_questions_manager()

    def create_questions(self, input_str: str) -> str:
        """Tool function to create questions in the database"""
        try:
            logger.info(f"Attempting to create questions with input: {input_str}")

            # Parse the input data
            try:
                # If input is a string, try to parse it as JSON
                if isinstance(input_str, str):
                    data = json.loads(input_str)
                # If input is already a dict or list, use it directly
                elif isinstance(input_str, (dict, list)):
                    data = input_str
                else:
                    logger.error(f"Unexpected input type: {type(input_str)}")
                    return f"Error: Unexpected input type: {type(input_str)}"

                logger.info(f"Parsed data: {data}")
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON: {e}")
                return f"Error: Invalid JSON format - {str(e)}"

            # Extract the fields
            if isinstance(data, dict) and "dsp_code" in data:
                dsp_code = data.get("dsp_code")
                questions = data.get("questions", [])
                time_slots = data.get("time_slots")
                recurrence_time_slots = data.get("recurrence_time_slots")
                contact_info = data.get("contact_info")
                append = data.get("append", True)
                
                # Check if we're only updating time slots or contact info without questions
                questions_provided = len(questions) > 0
                time_slots_provided = time_slots is not None
                recurrence_time_slots_provided = recurrence_time_slots is not None
                contact_info_provided = contact_info is not None
                
                # If we're only updating time slots, use the dedicated method
                if (time_slots_provided or recurrence_time_slots_provided) and not questions_provided and not contact_info_provided:
                    logger.info("Only time slots provided, using update_time_slots method")
                    update_data = {
                        "dsp_code": dsp_code,
                    }
                    
                    if time_slots_provided:
                        update_data["time_slots"] = time_slots
                        update_data["is_recurrence"] = False
                    
                    if recurrence_time_slots_provided:
                        update_data["time_slots"] = recurrence_time_slots
                        update_data["is_recurrence"] = True
                        
                    return self.update_time_slots(json.dumps(update_data))
                
                # If we're only updating contact info, use the dedicated method
                if contact_info_provided and not questions_provided and not time_slots_provided:
                    logger.info("Only contact info provided, using update_contact_info method")
                    return self.update_contact_info(json.dumps({
                        "dsp_code": dsp_code,
                        "contact_info": contact_info
                    }))
                
                # If we're updating multiple components, check if we need to fetch existing data
                if not append and questions_provided:
                    # We're replacing all questions, no need to fetch existing ones
                    logger.info("Replacing all questions (append=False)")
                else:
                    # Check if we need to fetch existing data for partial updates
                    if (time_slots_provided or recurrence_time_slots_provided or contact_info_provided) and not questions_provided:
                        # Fetch existing questions to avoid losing them
                        logger.info("Fetching existing questions for partial update")
                        existing_data = self.questions_manager.get_questions(dsp_code)
                        if existing_data and "questions" in existing_data:
                            questions = existing_data["questions"]
                            logger.info(f"Using {len(questions)} existing questions")

                # Validate contact_info structure if provided
                if contact_info_provided:
                    if not isinstance(contact_info, dict):
                        logger.error("Contact info must be a dictionary with contact_person_name, contact_number, and email_id fields")
                        return "Error: Contact info must be a dictionary with contact_person_name, contact_number, and email_id fields"
                    
                    # Check if all required fields are present
                    required_fields = ["contact_person_name", "contact_number", "email_id"]
                    missing_fields = [field for field in required_fields if field not in contact_info]
                    if missing_fields:
                        logger.error(f"Missing required fields in contact_info: {missing_fields}")
                        return f"Error: Missing required fields in contact_info: {missing_fields}"

                # Convert questions to dict if they're not already
                questions_dict = []
                for q in questions:
                    if isinstance(q, dict):
                        questions_dict.append(q)
                    else:
                        # This shouldn't happen with LLM-generated content
                        questions_dict.append(q.model_dump() if hasattr(q, "model_dump") else q)
                
                # Create in database
                success = self.questions_manager.create_questions(
                    dsp_code,
                    questions_dict,
                    append=append,
                    time_slots=time_slots,
                    recurrence_time_slots=recurrence_time_slots,
                    contact_info=contact_info,
                )

                if success:
                    logger.info(
                        f"Successfully created/updated {len(questions)} questions for company {dsp_code}"
                    )
                    return f"Successfully created/updated {len(questions)} questions for company {dsp_code}"
                else:
                    logger.error("Failed to create/update questions")
                    return "Failed to create/update questions. Please check the input data."
            else:
                logger.error("Missing required field 'dsp_code' in input")
                return "Error: Input must contain 'dsp_code' field"

        except Exception as e:
            logger.error(f"Unexpected error in create_questions: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return f"Error: {str(e)}"

    def get_questions(self, input_str: str) -> str:
        """Tool function to retrieve questions for a company"""
        try:
            logger.info(f"Retrieving questions for input: {input_str}")

            # Extract dsp_code
            dsp_code = input_str
            if isinstance(input_str, str):
                # Try to parse as JSON if it looks like JSON
                if input_str.strip().startswith("{"):
                    try:
                        data = json.loads(input_str)
                        if isinstance(data, dict) and "dsp_code" in data:
                            dsp_code = data["dsp_code"]
                    except json.JSONDecodeError:
                        # If it's not valid JSON, use the string directly
                        pass
            elif isinstance(input_str, dict) and "dsp_code" in input_str:
                dsp_code = input_str["dsp_code"]
                
            logger.info(f"Using dsp_code: {dsp_code}")

            # Get the questions and other company info
            company_data = self.questions_manager.get_questions(dsp_code)

            # Return formatted JSON with all company data
            return json.dumps(company_data)

        except Exception as e:
            logger.error(f"Error retrieving questions: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return f"Error: {str(e)}"

    def update_question(self, input_str: str) -> str:
        """Tool function to update a specific question"""
        try:
            logger.info(f"Attempting to update question with input: {input_str}")

            # Parse the input data
            try:
                # If input is a string, try to parse it as JSON
                if isinstance(input_str, str):
                    data = json.loads(input_str)
                # If input is already a dict, use it directly
                elif isinstance(input_str, dict):
                    data = input_str
                else:
                    logger.error(f"Unexpected input type: {type(input_str)}")
                    return f"Error: Unexpected input type: {type(input_str)}"

                logger.info(f"Parsed data: {data}")
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON: {e}")
                return f"Error: Invalid JSON format - {str(e)}"

            # Extract the fields
            if "dsp_code" in data and "question_index" in data and "updated_question" in data:
                dsp_code = data["dsp_code"]
                question_index = data["question_index"]
                updated_question = data["updated_question"]
                
                # Update the question
                success = self.questions_manager.update_question(
                    dsp_code,
                    question_index,
                    updated_question,
                )

                if success:
                    logger.info(
                        f"Successfully updated question at index {question_index} for company {dsp_code}"
                    )
                    return f"Successfully updated question at index {question_index} for company {dsp_code}"
                else:
                    logger.error("Failed to update question")
                    return "Failed to update question. Please check if the DSP code and question index are valid."
            else:
                logger.error("Missing required fields in input")
                return "Error: Input must contain 'dsp_code', 'question_index', and 'updated_question' fields"

        except Exception as e:
            logger.error(f"Unexpected error in update_question: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return f"Error: {str(e)}"

    def delete_question(self, input_str: str) -> str:
        """Tool function to delete a specific question"""
        try:
            logger.info(f"Attempting to delete question with input: {input_str}")

            # Parse the input data
            try:
                # If input is a string, try to parse it as JSON
                if isinstance(input_str, str):
                    logger.info(
                        f"Input is a string, attempting to parse as JSON: {input_str}"
                    )
                    data = json.loads(input_str)
                # If input is already a dict, use it directly
                elif isinstance(input_str, dict):
                    logger.info(f"Input is already a dict: {input_str}")
                    data = input_str
                else:
                    logger.error(f"Unexpected input type: {type(input_str)}")
                    return f"Error: Unexpected input type: {type(input_str)}"

                logger.info(f"Parsed data: {data}")
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON: {e}")
                return f"Error: Invalid JSON format - {str(e)}"

            # Extract the fields
            if "dsp_code" in data and "question_index" in data:
                dsp_code = data["dsp_code"]
                question_index = data["question_index"]
                
                # Delete the question
                success = self.questions_manager.delete_question(
                    dsp_code, question_index
                )

                if success:
                    logger.info(
                        f"Successfully deleted question at index {question_index} for company {dsp_code}"
                    )
                    return f"Successfully deleted question at index {question_index} for company {dsp_code}"
                else:
                    logger.error("Failed to delete question")
                    return "Failed to delete question. Please check if the DSP code and question index are valid."
            else:
                logger.error("Missing required fields in input")
                return "Error: Input must contain 'dsp_code' and 'question_index' fields"

        except Exception as e:
            logger.error(f"Unexpected error in delete_question: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return f"Error: {str(e)}"

    def update_time_slots(self, input_str: str) -> str:
        """Tool function to update time slots for a company"""
        try:
            logger.info(f"Attempting to update time slots with input: {input_str}")

            # Parse the input data
            try:
                # If input is a string, try to parse it as JSON
                if isinstance(input_str, str):
                    data = json.loads(input_str)
                # If input is already a dict, use it directly
                elif isinstance(input_str, dict):
                    data = input_str
                else:
                    logger.error(f"Unexpected input type: {type(input_str)}")
                    return f"Error: Unexpected input type: {type(input_str)}"

                logger.info(f"Parsed data: {data}")
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON: {e}")
                return f"Error: Invalid JSON format - {str(e)}"

            # Extract the fields
            if "dsp_code" in data:
                dsp_code = data["dsp_code"]
                time_slots = data.get("time_slots", [])
                is_recurrence = data.get("is_recurrence", False)
                
                # For structured recurrence patterns
                if "recurrence_patterns" in data:
                    from ..utils.time_slot_parser import parse_recurrence_pattern, RecurrenceTimeSlot
                    
                    recurrence_patterns = data["recurrence_patterns"]
                    structured_patterns = []
                    legacy_patterns = []
                    
                    # First pass: Parse all patterns
                parsed_patterns = []
                for pattern_text in recurrence_patterns:
                    # Parse the pattern text into a structured format
                    structured_pattern = parse_recurrence_pattern(pattern_text)
                    if structured_pattern:
                        parsed_patterns.append(structured_pattern)
                    else:
                        # If parsing fails, store as legacy format
                        legacy_patterns.append(pattern_text)
                
                # Second pass: Group similar patterns by day_of_week and time
                pattern_groups = {}
                for pattern in parsed_patterns:
                    if pattern.pattern_type == "monthly" and pattern.day_of_week and pattern.week_of_month:
                        # Create a key based on day_of_week and time
                        key = f"{pattern.day_of_week.lower()}_{pattern.time}"
                        if key not in pattern_groups:
                            pattern_groups[key] = []
                        pattern_groups[key].append(pattern)
                    else:
                        # Add non-monthly patterns directly
                        structured_patterns.append(pattern)
                
                # Third pass: Combine patterns with the same day_of_week and time
                for key, patterns in pattern_groups.items():
                    if len(patterns) > 1:
                        # Combine multiple patterns into one with a list of week_of_month values
                        week_positions = []
                        for pattern in patterns:
                            if isinstance(pattern.week_of_month, list):
                                week_positions.extend(pattern.week_of_month)
                            else:
                                week_positions.append(pattern.week_of_month)
                        
                        # Create a new pattern with combined week positions
                        combined_pattern = RecurrenceTimeSlot(
                            pattern_type="monthly",
                            day_of_week=patterns[0].day_of_week,
                            week_of_month=week_positions,
                            time=patterns[0].time
                        )
                        structured_patterns.append(combined_pattern)
                    else:
                        # Add single patterns directly
                        structured_patterns.append(patterns[0])
                
                # Update with the structured patterns if any were successfully parsed
                if structured_patterns:
                    logger.info(f"Updating with {len(structured_patterns)} structured patterns")
                    for pattern in structured_patterns:
                        logger.info(f"Pattern: {pattern}")
                    
                    success = self.questions_manager.update_structured_recurrence_time_slots(
                        dsp_code, structured_patterns
                    )
                    
                    if not success:
                        logger.error("Failed to update structured recurring time slots")
                        return "Failed to update structured recurring time slots. Please check if the DSP code is valid."
                    
                    # Update with legacy patterns if any couldn't be parsed
                    if legacy_patterns:
                        success = self.questions_manager.update_recurrence_time_slots(
                            dsp_code, legacy_patterns
                        )
                        
                        if not success:
                            logger.error("Failed to update legacy recurring time slots")
                            return "Failed to update legacy recurring time slots. Please check if the DSP code is valid."
                    
                    logger.info(f"Successfully updated recurring time slots for company {dsp_code}")
                    return f"Successfully updated recurring time slots for company {dsp_code}"
                elif is_recurrence:
                    # Update recurrence time slots (legacy format)
                    success = self.questions_manager.update_recurrence_time_slots(
                        dsp_code, time_slots
                    )
                    
                    if success:
                        logger.info(
                            f"Successfully updated recurring time slots for company {dsp_code}"
                        )
                        return f"Successfully updated recurring time slots for company {dsp_code}"
                    else:
                        logger.error("Failed to update recurring time slots")
                        return "Failed to update recurring time slots. Please check if the DSP code is valid."
                else:
                    # Update regular time slots
                    success = self.questions_manager.update_time_slots(
                        dsp_code, time_slots
                    )
                    
                    if success:
                        logger.info(
                            f"Successfully updated time slots for company {dsp_code}"
                        )
                        return f"Successfully updated time slots for company {dsp_code}"
                    else:
                        logger.error("Failed to update time slots")
                        return "Failed to update time slots. Please check if the DSP code is valid."
            else:
                logger.error("Missing required fields in input")
                return "Error: Input must contain 'dsp_code' field"

        except Exception as e:
            logger.error(f"Unexpected error in update_time_slots: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return f"Error: {str(e)}"
            
    def update_contact_info(self, input_str: str) -> str:
        """Tool function to update contact information for a company"""
        try:
            logger.info(f"Attempting to update contact info with input: {input_str}")

            # Parse the input data
            try:
                # If input is a string, try to parse it as JSON
                if isinstance(input_str, str):
                    data = json.loads(input_str)
                # If input is already a dict, use it directly
                elif isinstance(input_str, dict):
                    data = input_str
                else:
                    logger.error(f"Unexpected input type: {type(input_str)}")
                    return f"Error: Unexpected input type: {type(input_str)}"

                logger.info(f"Parsed data: {data}")
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON: {e}")
                return f"Error: Invalid JSON format - {str(e)}"

            # Extract the fields
            if "dsp_code" in data and "contact_info" in data:
                dsp_code = data["dsp_code"]
                contact_info = data["contact_info"]
                
                # Validate contact_info structure
                if not isinstance(contact_info, dict):
                    logger.error("Contact info must be a dictionary with contact_person_name, contact_number, and email_id fields")
                    return "Error: Contact info must be a dictionary with contact_person_name, contact_number, and email_id fields"
                
                # Check if all required fields are present
                required_fields = ["contact_person_name", "contact_number", "email_id"]
                missing_fields = [field for field in required_fields if field not in contact_info]
                if missing_fields:
                    logger.error(f"Missing required fields in contact_info: {missing_fields}")
                    return f"Error: Missing required fields in contact_info: {missing_fields}"
                
                # Update the contact info
                success = self.questions_manager.update_contact_info(
                    dsp_code,
                    contact_info,
                )

                if success:
                    logger.info(
                        f"Successfully updated contact information for company {dsp_code}"
                    )
                    return f"Successfully updated contact information for company {dsp_code}"
                else:
                    logger.error("Failed to update contact information")
                    return "Failed to update contact information. Please check if the DSP code is valid."
            else:
                logger.error("Missing required fields in input")
                return "Error: Input must contain 'dsp_code' and 'contact_info' fields"

        except Exception as e:
            logger.error(f"Unexpected error in update_contact_info: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return f"Error: {str(e)}"
            
    def delete_recurrence_time_slots(self, input_str: str) -> str:
        """Tool function to delete all recurring time slots for a company"""
        try:
            logger.info(f"Attempting to delete recurrence time slots with input: {input_str}")

            # Parse the input data
            try:
                # If input is a string, try to parse it as JSON
                if isinstance(input_str, str):
                    data = json.loads(input_str)
                # If input is already a dict, use it directly
                elif isinstance(input_str, dict):
                    data = input_str
                else:
                    logger.error(f"Unexpected input type: {type(input_str)}")
                    return f"Error: Unexpected input type: {type(input_str)}"

                logger.info(f"Parsed data: {data}")
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON: {e}")
                return f"Error: Invalid JSON format - {str(e)}"

            # Extract the fields
            if "dsp_code" in data:
                dsp_code = data["dsp_code"]
                
                # Delete the recurrence time slots
                success = self.questions_manager.delete_recurrence_time_slots(dsp_code)

                if success:
                    logger.info(
                        f"Successfully deleted recurring time slots for company {dsp_code}"
                    )
                    return f"Successfully deleted recurring time slots for company {dsp_code}"
                else:
                    logger.error("Failed to delete recurring time slots")
                    return "Failed to delete recurring time slots. Please check if the DSP code is valid."
            else:
                logger.error("Missing required fields in input")
                return "Error: Input must contain 'dsp_code' field"

        except Exception as e:
            logger.error(f"Unexpected error in delete_recurrence_time_slots: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return f"Error: {str(e)}"
