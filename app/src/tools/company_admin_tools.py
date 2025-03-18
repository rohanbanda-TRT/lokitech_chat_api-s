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
    
    def get_questions(self, company_id: str) -> str:
        """Tool function to retrieve questions from the database"""
        try:
            logger.info(f"Retrieving questions for company_id: {company_id}")
            questions = self.questions_manager.get_questions(company_id)
            return json.dumps(questions)
        except Exception as e:
            logger.error(f"Error retrieving questions: {e}")
            return f"Error retrieving questions: {str(e)}"
    
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
                validated_data = DeleteQuestionInput.model_validate(data)
                
                # Delete the question
                success = self.questions_manager.delete_question(
                    validated_data.company_id,
                    validated_data.question_index
                )
                
                if success:
                    logger.info(f"Successfully deleted question at index {validated_data.question_index} for company {validated_data.company_id}")
                    return f"Successfully deleted question at index {validated_data.question_index} for company {validated_data.company_id}"
                else:
                    logger.error("Failed to delete question")
                    return "Failed to delete question. Please check if the company ID and question index are valid."
            except Exception as e:
                logger.error(f"Error validating data: {e}")
                return f"Error validating data: {str(e)}"
            
        except Exception as e:
            logger.error(f"Unexpected error in delete_question: {e}")
            return f"Error: {str(e)}"
