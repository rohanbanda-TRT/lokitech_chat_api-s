import requests
import logging
import json
from typing import Dict, Any, Optional
from pydantic import BaseModel

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
