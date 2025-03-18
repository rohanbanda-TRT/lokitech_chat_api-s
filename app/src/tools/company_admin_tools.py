import json
import logging
from typing import List, Dict, Any, Optional, Union
from ..models.question_models import Question, CompanyQuestions, UpdateQuestionInput, DeleteQuestionInput
from ..managers.company_questions_manager import CompanyQuestionsManager

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CompanyAdminTools:
    """
    Tools for company admin operations
    """
    def __init__(self):
        self.questions_manager = CompanyQuestionsManager()
    
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
            
            # Handle different input formats
            if isinstance(data, dict):
                # Check if it's a properly formatted CompanyQuestions object
                if "company_id" in data and "questions" in data:
                    # Validate with Pydantic
                    try:
                        validated_data = CompanyQuestions.model_validate(data)
                        
                        # Convert to dict for database storage
                        questions_dict = [q.model_dump() for q in validated_data.questions]
                        
                        # Create in database
                        success = self.questions_manager.create_questions(
                            validated_data.company_id, 
                            questions_dict,
                            append=validated_data.append
                        )
                        
                        if success:
                            logger.info(f"Successfully created {len(questions_dict)} questions for company {validated_data.company_id}")
                            return f"Successfully created {len(questions_dict)} questions for company {validated_data.company_id}"
                        else:
                            logger.error("Failed to create questions in database")
                            return "Failed to create questions in database"
                    except Exception as e:
                        logger.error(f"Error validating data: {e}")
                        return f"Error validating data: {str(e)}"
                else:
                    logger.error("Missing required fields in input")
                    return "Error: Input must contain 'company_id' and 'questions' fields"
            elif isinstance(data, list):
                # If it's just a list of questions, we need a company_id from the conversation
                logger.error("Cannot process list without company_id")
                return "Error: When providing a list of questions, you must also provide a company_id"
            else:
                logger.error(f"Unexpected data format: {type(data)}")
                return f"Error: Unexpected data format: {type(data)}"
            
        except Exception as e:
            logger.error(f"Unexpected error in create_questions: {e}")
            return f"Error: {str(e)}"
    
    def get_questions(self, input_str: str) -> str:
        """Tool function to retrieve questions for a company"""
        try:
            logger.info(f"Retrieving questions for company_id: {input_str}")
            
            # Parse the input data
            try:
                # If input is a string, try to parse it as JSON
                if isinstance(input_str, str):
                    logger.info(f"Input is a string, attempting to parse as JSON: {input_str}")
                    data = json.loads(input_str)
                # If input is already a dict, use it directly
                elif isinstance(input_str, dict):
                    logger.info(f"Input is already a dict: {input_str}")
                    data = input_str
                else:
                    logger.error(f"Unexpected input type: {type(input_str)}")
                    return f"Error: Unexpected input type: {type(input_str)}"
                
                logger.info(f"Parsed data: {data}")
                
                # Extract company_id from the parsed data
                if isinstance(data, dict) and "company_id" in data:
                    company_id = data["company_id"]
                    logger.info(f"Extracted company_id: {company_id}")
                else:
                    logger.error(f"Invalid input format. Expected a dict with 'company_id' key")
                    return "Error: Invalid input format. Expected a dict with 'company_id' key"
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON: {e}")
                # If JSON parsing fails, try to use the input directly as a company_id
                company_id = input_str
                logger.info(f"Using input directly as company_id: {company_id}")
            
            # Get the questions
            questions = self.questions_manager.get_questions(company_id)
            
            if not questions:
                return "[]"
            
            # Format the questions for display
            formatted_questions = []
            for i, q in enumerate(questions):
                required_str = "(Required)" if q.get("required", False) else "(Optional)"
                formatted_questions.append(f"{i+1}. {q['question_text']} {required_str}")
            
            return json.dumps(questions)
            
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
            
            # Validate with Pydantic
            try:
                validated_data = UpdateQuestionInput.model_validate(data)
                
                # Convert to dict for database storage
                updated_question_dict = validated_data.updated_question.model_dump()
                
                # Update the question
                success = self.questions_manager.update_question(
                    validated_data.company_id,
                    validated_data.question_index,
                    updated_question_dict
                )
                
                if success:
                    logger.info(f"Successfully updated question at index {validated_data.question_index} for company {validated_data.company_id}")
                    return f"Successfully updated question at index {validated_data.question_index} for company {validated_data.company_id}"
                else:
                    logger.error("Failed to update question")
                    return "Failed to update question. Please check if the company ID and question index are valid."
            except Exception as e:
                logger.error(f"Error validating data: {e}")
                return f"Error validating data: {str(e)}"
            
        except Exception as e:
            logger.error(f"Unexpected error in update_question: {e}")
            return f"Error: {str(e)}"
    
    def delete_question(self, input_str: str) -> str:
        """Tool function to delete a specific question"""
        try:
            logger.info(f"Attempting to delete question with input: {input_str}")
            
            # Parse the input data
            try:
                # If input is a string, try to parse it as JSON
                if isinstance(input_str, str):
                    logger.info(f"Input is a string, attempting to parse as JSON: {input_str}")
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
            
            # Validate with Pydantic
            try:
                logger.info(f"Validating data with DeleteQuestionInput model: {data}")
                validated_data = DeleteQuestionInput.model_validate(data)
                logger.info(f"Validation successful: company_id={validated_data.company_id}, question_index={validated_data.question_index}")
                
                # Get questions before deletion for debugging
                before_questions = self.questions_manager.get_questions(validated_data.company_id)
                logger.info(f"Questions before deletion: {before_questions}")
                logger.info(f"Number of questions before deletion: {len(before_questions)}")
                
                # Delete the question
                success = self.questions_manager.delete_question(
                    validated_data.company_id,
                    validated_data.question_index
                )
                
                # Get questions after deletion for debugging
                after_questions = self.questions_manager.get_questions(validated_data.company_id)
                logger.info(f"Questions after deletion attempt: {after_questions}")
                logger.info(f"Number of questions after deletion attempt: {len(after_questions)}")
                
                if success:
                    logger.info(f"Successfully deleted question at index {validated_data.question_index} for company {validated_data.company_id}")
                    return f"Successfully deleted question at index {validated_data.question_index} for company {validated_data.company_id}"
                else:
                    logger.error(f"Failed to delete question at index {validated_data.question_index} for company {validated_data.company_id}")
                    return f"Failed to delete question at index {validated_data.question_index}. Please check if the company ID and question index are valid."
            except Exception as e:
                logger.error(f"Error validating data: {e}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                return f"Error validating data: {str(e)}"
            
        except Exception as e:
            logger.error(f"Unexpected error in delete_question: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return f"Error: {str(e)}"
