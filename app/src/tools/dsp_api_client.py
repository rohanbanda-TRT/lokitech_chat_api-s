import requests
import logging
import json
from typing import Dict, Any, Optional, List
from pydantic import BaseModel
import datetime
from ..utils.time_slot_parser import parse_time_slot, extract_time_slot_from_responses

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ApplicantDetails(BaseModel):
    dspShortCode: str
    dspStationCode: str
    dspName: str
    firstName: str
    lastName: str
    mobileNumber: str
    applicantStatus: str
    email: Optional[str] = None
    applicantID: Optional[int] = (
        None  # Add applicantID field, make it optional for backward compatibility
    )


class DSPApiClient:
    """
    Client for interacting with the DSP API endpoints
    """

    def __init__(self):
        self.base_url = "https://lokitech-dev.azurewebsites.net/Api"
        self.headers = {
            "Content-Type": "application/json",
            "Cookie": "ARRAffinity=fcf7d5fdf37b512af754feef42838265fe0e7417851b1dfbd69931bcc7d991e4; ARRAffinitySameSite=fcf7d5fdf37b512af754feef42838265fe0e7417851b1dfbd69931bcc7d991e4",
        }

    def get_applicant_details(
        self, dsp_code: str, station_code: str = "DJE1", applicant_id: int = 5
    ) -> Optional[ApplicantDetails]:
        """
        Get applicant details from the DSP API

        Args:
            dsp_code: The DSP short code
            station_code: The station code (default: DJE1)
            applicant_id: The applicant ID (default: 5)

        Returns:
            ApplicantDetails object if successful, None otherwise
        """
        try:
            logger.info(f"Fetching applicant details for DSP code: {dsp_code}")

            # Exactly match the curl command format
            url = f"{self.base_url}/DSPnUserDetails/getDSPnApplicantDetails"
            payload = {
                "companyShortCode": dsp_code,
                "companyStationCode": station_code,
                "applicantID": applicant_id,
            }

            # The curl example uses GET with --data which sends the data in the request body
            # This is unusual but we'll replicate it exactly
            response = requests.request(
                method="GET",
                url=url,
                headers=self.headers,
                data=json.dumps(payload),  # Convert to JSON string
            )

            if response.status_code == 200:
                data = response.json()
                # Add the applicantID to the response data
                data["applicantID"] = applicant_id
                logger.info(f"Successfully retrieved applicant details: {data}")
                return ApplicantDetails(**data)
            else:
                logger.error(
                    f"Failed to retrieve applicant details. Status code: {response.status_code}"
                )
                logger.error(f"Response: {response.text}")
                return None

        except Exception as e:
            logger.error(f"Error retrieving applicant details: {e}")
            return None

    def add_pre_manage_applicant(self, applicant_details: Dict[str, Any], time_slot: Optional[str] = None, email: Optional[str] = None) -> bool:
        """
        Add a pre-manage applicant to the system when they pass the screening
        
        Args:
            applicant_details: Dictionary containing applicant details
            time_slot: Optional time slot selected by the applicant
            
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Adding pre-manage applicant: {applicant_details['firstName']} {applicant_details['lastName']}")
            logger.info(f"Time slot provided: {time_slot}")
            
            # Parse the time slot if provided
            scheduled_date, scheduled_time = parse_time_slot(time_slot)
            
            # If no date and time were found, leave them as None
            if not scheduled_date and not scheduled_time:
                logger.info("No date and time found, will pass null values to API")
            # Otherwise, ensure we have values for both
            elif scheduled_date and not scheduled_time:
                # If we have a date but no time, use a default time
                scheduled_time = "10:00 AM"
                logger.info(f"Using default time: {scheduled_time} with date: {scheduled_date}")
            elif not scheduled_date and scheduled_time:
                # If we have a time but no date, use tomorrow's date
                tomorrow = datetime.datetime.now() + datetime.timedelta(days=1)
                scheduled_date = tomorrow.strftime("%Y-%m-%d")
                logger.info(f"Using tomorrow's date: {scheduled_date} with time: {scheduled_time}")
            
            url = f"{self.base_url}/PreManageApplicant/AddpreManageApplicants"
            
            # Use provided email or empty string
            email = email or ""
            
            # Prepare the payload according to the API requirements
            payload = {
                "FirstName": applicant_details.get("firstName", ""),
                "LastName": applicant_details.get("lastName", ""),
                "Email": email,  # Use email from responses
                "MobileNumber": applicant_details.get("mobileNumber", ""),
                "Designation": "Delivery Associate",  # Always set to this value as specified
                "SourceOfApplication": "None",  # Always set to this value as specified
                "ScheduleInterview": "Yes" if scheduled_date and scheduled_time else "",
                "ScheduleType": "In-Person",  # Always set to this value as specified
                "ScheduledInterviewDate": scheduled_date if scheduled_date else None,
                "ScheduledInterviewTime": scheduled_time if scheduled_time else None,
                "dspSchortCode": applicant_details.get("dspShortCode", "")
            }
            
            logger.info(f"Sending add pre-manage applicant payload: {payload}")
            
            # Send POST request to add the pre-manage applicant
            response = requests.request(
                method="POST",
                url=url,
                headers=self.headers,
                data=json.dumps(payload),  # Convert to JSON string
            )
            
            if response.status_code == 200:
                logger.info(f"Successfully added pre-manage applicant")
                logger.info(f"Response: {response.text}")
                return True
            else:
                logger.error(f"Failed to add pre-manage applicant. Status code: {response.status_code}")
                logger.error(f"Response: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error adding pre-manage applicant: {e}")
            return False
    
    def update_applicant_status(
        self,
        dsp_code: str,
        applicant_id: Optional[int] = None,
        current_status: str = "SENT",
        new_status: str = "INPROGRESS",
        applicant_data: Dict[str, Any] = None,
    ) -> bool:
        """
        Update the applicant status in the DSP API

        Args:
            dsp_code: The DSP short code
            applicant_id: The applicant ID (optional, will use as emp_id)
            current_status: The current status of the applicant (default: SENT)
            new_status: The new status to set (default: INPROGRESS)
            applicant_data: Additional data about the applicant (optional)

        Returns:
            True if successful, False otherwise
        """
        try:
            # Use the provided applicant_id as emp_id, or default to 75 if not provided
            emp_id = applicant_id if applicant_id is not None else 75

            logger.info(
                f"Updating applicant status for DSP code: {dsp_code} from {current_status} to {new_status} with emp_id: {emp_id}"
            )

            url = f"{self.base_url}/PreManageApplicant/UpdatePreManageApplicantStatus"

            # Prepare the payload with status information and empty answeredJSONData
            payload = {
                "appStatus": new_status,
                "empID": emp_id,
                "dspShortCode": dsp_code,
                "answeredJSONData": {"responses": {}},
            }

            # Update responses if provided
            if applicant_data and "responses" in applicant_data:
                payload["answeredJSONData"]["responses"] = applicant_data["responses"]

            logger.info(f"Sending payload: {payload}")

            # Send POST request to update the status
            response = requests.request(
                method="POST",
                url=url,
                headers=self.headers,
                data=json.dumps(payload),  # Convert to JSON string
            )

            if response.status_code == 200:
                logger.info(f"Successfully updated applicant status to {new_status}")
                
                # If the new status is PASSED, call the add_pre_manage_applicant endpoint
                if new_status == "PASSED":
                    # Get the applicant details
                    applicant_details = self.get_applicant_details(
                        dsp_code=dsp_code,
                        applicant_id=applicant_id
                    )
                    
                    if applicant_details:
                        # Extract the selected time slot from responses if available
                        selected_time_slot = None
                        if applicant_data and "responses" in applicant_data:
                            selected_time_slot = extract_time_slot_from_responses(applicant_data["responses"])
                            
                        # Extract email from responses
                        email = None
                        if isinstance(applicant_data.get("responses", {}), dict):
                            email = applicant_data["responses"].get("collected_email", None)
                            
                        # Get applicant details as dict
                        applicant_dict = applicant_details.model_dump()
                        
                        # Call the add_pre_manage_applicant endpoint
                        self.add_pre_manage_applicant(
                            applicant_details=applicant_dict,
                            time_slot=selected_time_slot,
                            email=email
                        )
                
                return True
            else:
                logger.error(
                    f"Failed to update applicant status. Status code: {response.status_code}"
                )
                logger.error(f"Response: {response.text}")
                return False

        except Exception as e:
            logger.error(f"Error updating applicant status: {e}")
            return False
