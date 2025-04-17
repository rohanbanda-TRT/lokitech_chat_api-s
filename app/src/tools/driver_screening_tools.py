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

    def _update_applicant_status(self, input_str: str) -> str:
        """
        Update the applicant status based on screening results

        Args:
            input_str: JSON string containing the update information

        Returns:
            Success or error message
        """
        try:
            logger.info(f"Updating applicant status: {input_str}")

            # Parse input
            input_data = json.loads(input_str)

            # Extract required fields
            dsp_code = input_data.get("dsp_code")
            applicant_id = input_data.get("applicant_id")
            current_status = input_data.get("current_status", "INPROGRESS")
            new_status = input_data.get("new_status")  # Should be "PASSED" or "FAILED"

            # Extract optional responses if available
            responses = input_data.get("responses", {})

            # Validate required fields
            if not dsp_code:
                return json.dumps(
                    {"success": False, "message": "Missing required field: dsp_code"}
                )

            if not applicant_id:
                return json.dumps(
                    {
                        "success": False,
                        "message": "Missing required field: applicant_id",
                    }
                )

            if not new_status:
                return json.dumps(
                    {"success": False, "message": "Missing required field: new_status"}
                )

            # Prepare applicant data with responses only
            applicant_data = {"responses": responses}

            # Update the applicant status
            status_updated = self.dsp_api_client.update_applicant_status(
                dsp_code=dsp_code,
                applicant_id=applicant_id,
                current_status=current_status,
                new_status=new_status,
                applicant_data=applicant_data,
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
