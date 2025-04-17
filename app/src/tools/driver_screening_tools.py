from typing import Dict, Any, List, Optional
import json
import logging
from pydantic import BaseModel, Field
from .dsp_api_client import DSPApiClient, ApplicantDetails
import datetime
import re

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class GetDateBasedTimeSlotsInput(BaseModel):
    """Input model for get_date_based_time_slots tool"""
    time_slots: List[str] = Field(..., description="List of time slots in format 'Day Time Range' (e.g., 'Monday 9-5')")
    num_occurrences: int = Field(2, description="Number of future occurrences to generate for each day")


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
            # Parse the input JSON string
            logger.info(f"Received input string: {input_str}")
            input_data = json.loads(input_str)
            
            # Create a Pydantic model from the parsed data
            model_input = UpdateApplicantStatusInput(
                dsp_code=input_data.get("dsp_code"),
                applicant_id=input_data.get("applicant_id"),
                current_status=input_data.get("current_status", "INPROGRESS"),
                new_status=input_data.get("new_status"),
                responses=input_data.get("responses", {})
            )
            
            # Call the structured version of the method
            return self._update_applicant_status(model_input)
            
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

    def _get_date_based_time_slots(self, input_data: GetDateBasedTimeSlotsInput) -> str:
        """
        Convert day-based time slots (e.g., 'Monday 9-5') to actual dates
        for the next N occurrences of those days.

        Args:
            input_data: GetDateBasedTimeSlotsInput object containing time_slots and num_occurrences

        Returns:
            JSON string with date-based time slots
        """
        try:
            logger.info(f"Generating date-based time slots for: {input_data.time_slots}")

            # Dictionary to map day names to weekday numbers (0 = Monday in datetime)
            day_to_weekday = {
                'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
                'friday': 4, 'saturday': 5, 'sunday': 6
            }

            # Get current date
            today = datetime.datetime.now().date()

            # Initialize result
            date_based_slots = []

            # Process each time slot
            for slot in input_data.time_slots:
                # Extract day and time range using regex
                match = re.match(r'(\w+)\s+(.*)', slot, re.IGNORECASE)
                if not match:
                    logger.warning(f"Invalid time slot format: {slot}")
                    continue

                day_name, time_range = match.groups()
                day_name = day_name.lower()

                # Skip if day name is not recognized
                if day_name not in day_to_weekday:
                    logger.warning(f"Unrecognized day name: {day_name}")
                    continue

                target_weekday = day_to_weekday[day_name]

                # Calculate days until next occurrence of this weekday
                days_ahead = (target_weekday - today.weekday()) % 7
                if days_ahead == 0:  # If today is the target day, start from next week
                    days_ahead = 7

                # Generate the next N occurrences
                for i in range(input_data.num_occurrences):
                    next_date = today + datetime.timedelta(days=days_ahead + (i * 7))
                    formatted_date = next_date.strftime("%A, %B %d, %Y")  # e.g., "Monday, April 21, 2025"
                    date_based_slots.append(f"{formatted_date} {time_range}")

            return json.dumps({
                "success": True,
                "date_based_slots": date_based_slots
            })

        except Exception as e:
            logger.error(f"Error generating date-based time slots: {e}")
            return json.dumps({
                "success": False,
                "message": f"Error generating date-based time slots: {str(e)}"
            })
