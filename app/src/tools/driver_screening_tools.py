from typing import Dict, Any, List, Optional
import json
import logging
from pydantic import BaseModel, Field
from .dsp_api_client import DSPApiClient, ApplicantDetails
import datetime
import re
from ..utils.time_slot_parser import extract_time_slot_from_responses, format_company_time_slot

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class UpdateApplicantStatusInput(BaseModel):
    """Input model for update_applicant_status tool"""
    dsp_code: str = Field(..., description="The DSP short code")
    applicant_id: int = Field(..., description="The applicant ID")
    current_status: str = Field("INPROGRESS", description="Current status of the applicant")
    new_status: str = Field(..., description="New status to set (PASSED or FAILED)")
    responses: Dict[str, Any] = Field(default_factory=dict, description="Optional responses from the screening process")


class DriverScreeningTools:
    """
    Tools for driver screening operations
    """

    def __init__(self):
        self.dsp_api_client = DSPApiClient()

    def _get_applicant_details(self, dsp_code: str) -> str:
        """
        Get applicant details from the DSP API

        Args:
            dsp_code: The DSP short code

        Returns:
            JSON string with applicant details or error message
        """
        try:
            logger.info(f"Fetching applicant details for DSP code: {dsp_code}")

            # Use default values for station_code and applicant_id as per requirements
            applicant_details = self.dsp_api_client.get_applicant_details(
                dsp_code=dsp_code,
                station_code="DJE1",  # Static for now
                applicant_id=5,  # Static for now
            )

            if applicant_details:
                return json.dumps(
                    {"success": True, "data": applicant_details.model_dump()}
                )
            else:
                return json.dumps(
                    {
                        "success": False,
                        "message": f"Failed to retrieve applicant details for DSP code: {dsp_code}",
                    }
                )

        except Exception as e:
            logger.error(f"Error retrieving applicant details: {e}")
            return json.dumps({"success": False, "message": f"Error: {str(e)}"})

    def _update_applicant_status(self, input_data: UpdateApplicantStatusInput) -> str:
        """
        Update the applicant status based on screening results

        Args:
            input_data: UpdateApplicantStatusInput object containing update information

        Returns:
            Success or error message
        """
        # Extract email from responses if present
        email = None
        if input_data.responses and isinstance(input_data.responses, dict):
            email = input_data.responses.get("collected_email", None)
        try:
            # Convert to dictionary for logging
            input_dict = input_data.model_dump()
            logger.info(f"Updating applicant status: {input_dict}")

            # Extract required fields from the input model
            dsp_code = input_data.dsp_code
            applicant_id = input_data.applicant_id
            current_status = input_data.current_status
            new_status = input_data.new_status
            responses = input_data.responses

            # Update the applicant status
            status_updated = self.dsp_api_client.update_applicant_status(
                dsp_code=dsp_code,
                applicant_id=applicant_id,
                current_status=current_status,
                new_status=new_status,
                applicant_data={"responses": responses},
            )

            if status_updated:
                return json.dumps(
                    {
                        "success": True,
                        "message": f"Successfully updated applicant status to {new_status}",
                    }
                )
            else:
                return json.dumps(
                    {
                        "success": False,
                        "message": f"Failed to update applicant status to {new_status}",
                    }
                )

        except Exception as e:
            logger.error(f"Error updating applicant status: {e}")
            return json.dumps({"success": False, "message": f"Error: {str(e)}"})

    def update_applicant_status(self, input_str: str) -> str:
        """
        Update the applicant status based on screening results (string input version)

        Args:
            input_str: JSON string containing the update information

        Returns:
            Success or error message
        """
        try:
            logger.info(f"Updating applicant status with string input: {input_str}")
            
            # Parse the input string as JSON
            input_data = json.loads(input_str)
            
            # Create a Pydantic model from the parsed JSON
            model_input = UpdateApplicantStatusInput(**input_data)
            
            # Call the structured version of the method
            return self._update_applicant_status(model_input)
            
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing JSON input: {e}")
            return json.dumps({"success": False, "message": f"Invalid JSON input: {str(e)}"})
        except Exception as e:
            logger.error(f"Error in string version of update_applicant_status: {e}")
            return json.dumps({"success": False, "message": f"Error: {str(e)}"})

    def update_applicant_status_multi(
        self, 
        dsp_code: str, 
        applicant_id: int, 
        current_status: str, 
        new_status: str, 
        responses: dict
    ) -> str:
        """
        Update the applicant status based on screening results (multi-argument version)

        Args:
            dsp_code: The DSP short code
            applicant_id: The applicant ID
            current_status: Current status of the applicant
            new_status: New status to set (PASSED or FAILED)
            responses: Optional responses from the screening process

        Returns:
            Success or error message
        """
        try:
            logger.info(f"Updating applicant status with multi-args: {dsp_code}, {applicant_id}, {current_status}, {new_status}")
            
            # If the new status is PASSED, try to extract time slot information from responses
            selected_time_slot = None
            if new_status == "PASSED":
                # Extract time slot from responses
                selected_time_slot = extract_time_slot_from_responses(responses)
                logger.info(f"Time slot extracted from responses: {selected_time_slot}")
                
                # If no time slot was found in responses, try to get company time slots
                if not selected_time_slot:
                    try:
                        # Import here to avoid circular imports
                        from ..managers.company_questions_factory import get_company_questions_manager
                        
                        # Get company questions manager
                        questions_manager = get_company_questions_manager()
                        
                        # Get company data
                        company_data = questions_manager.get_questions(dsp_code)
                        
                        # Extract time slots if available
                        if company_data and "time_slots" in company_data and company_data["time_slots"] and len(company_data["time_slots"]) > 0:
                            # Just use the first available time slot
                            time_slot_text = company_data["time_slots"][0]
                            logger.info(f"Found company time slot: {time_slot_text}")
                            
                            # Format the company time slot
                            formatted_time_slot = format_company_time_slot(time_slot_text)
                            if formatted_time_slot:
                                selected_time_slot = formatted_time_slot
                                logger.info(f"Using company time slot: {selected_time_slot}")
                        else:
                            logger.info("No company time slots available, will pass null values to API")
                    except Exception as e:
                        logger.error(f"Error getting company time slots: {e}")
            
            # Add the selected time slot to responses if found
            if selected_time_slot and responses and isinstance(responses, dict):
                responses["selected_time_slot"] = selected_time_slot
            
            # Create a Pydantic model from the arguments
            model_input = UpdateApplicantStatusInput(
                dsp_code=dsp_code,
                applicant_id=applicant_id,
                current_status=current_status,
                new_status=new_status,
                responses=responses
            )
            
            # Call the structured version of the method
            return self._update_applicant_status(model_input)
            
        except Exception as e:
            logger.error(f"Error in multi-arg version of update_applicant_status: {e}")
            return json.dumps({"success": False, "message": f"Error: {str(e)}"})
