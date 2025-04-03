from typing import Dict, Any, List, Optional
import json
import logging
from pydantic import BaseModel, Field
from ..managers.driver_screening_manager import DriverScreeningManager
from .dsp_api_client import DSPApiClient, ApplicantDetails

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Input models for validation
class ContactInfo(BaseModel):
    email: str
    phone: str

class ResponseItem(BaseModel):
    question_id: int
    question_text: str
    response_text: str

class OverallResult(BaseModel):
    pass_result: bool
    evaluation_summary: str

class InterviewDetails(BaseModel):
    scheduled: bool
    date: Optional[str] = None
    time: Optional[str] = None
    calendar_event_id: Optional[str] = None
    event_link: Optional[str] = None
    meet_link: Optional[str] = None

class StoreDriverScreeningInput(BaseModel):
    driver_id: str
    driver_name: str
    contact_info: ContactInfo
    dsp_code: str
    session_id: str
    responses: List[ResponseItem]
    overall_result: OverallResult
    interview_details: Optional[InterviewDetails] = None

class DriverScreeningTools:
    """
    Tools for driver screening operations
    """
    def __init__(self):
        self.screening_manager = DriverScreeningManager()
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
                applicant_id=5  # Static for now
            )
            
            if applicant_details:
                return json.dumps({
                    "success": True,
                    "data": applicant_details.model_dump()
                })
            else:
                return json.dumps({
                    "success": False,
                    "message": f"Failed to retrieve applicant details for DSP code: {dsp_code}"
                })
                
        except Exception as e:
            logger.error(f"Error retrieving applicant details: {e}")
            return json.dumps({
                "success": False,
                "message": f"Error: {str(e)}"
            })
    
    def _store_driver_screening(self, input_str: str) -> str:
        """
        Store complete driver screening data in one operation
        
        Args:
            input_str: JSON string containing all driver screening data
            
        Returns:
            Success or error message
        """
        try:
            logger.info(f"Storing complete driver screening data: {input_str}")
            
            # Parse input
            input_data = StoreDriverScreeningInput.model_validate_json(input_str)
            
            # Handle case when session_id is 'unknown'
            session_id = input_data.session_id
            if session_id == 'unknown':
                # Generate a unique session ID based on driver_id and timestamp
                import time
                timestamp = int(time.time())
                session_id = f"{input_data.driver_id}-{timestamp}"
                logger.info(f"Generated new session_id: {session_id} to replace 'unknown'")
            
            # 1. Ensure driver exists
            driver_created = self.screening_manager.create_driver(
                input_data.driver_id,
                input_data.driver_name,
                input_data.contact_info.model_dump()
            )
            
            if not driver_created:
                return json.dumps({
                    "success": False,
                    "message": "Failed to create driver record"
                })
            
            # 2. Create screening session
            session_created = self.screening_manager.add_screening_session(
                input_data.driver_id,
                input_data.dsp_code,
                session_id
            )
            
            if not session_created:
                return json.dumps({
                    "success": False,
                    "message": "Failed to create screening session"
                })
            
            # 3. Add all responses
            all_responses_added = True
            for response in input_data.responses:
                success = self.screening_manager.add_screening_response(
                    input_data.driver_id,
                    input_data.dsp_code,
                    session_id,
                    response.question_id,
                    response.question_text,
                    response.response_text
                )
                if not success:
                    all_responses_added = False
                    logger.error(f"Failed to add response for question_id: {response.question_id}")
            
            # 4. Update overall result
            result_updated = self.screening_manager.update_screening_result(
                input_data.driver_id,
                input_data.dsp_code,
                session_id,
                input_data.overall_result.pass_result,
                input_data.overall_result.evaluation_summary
            )
            
            # 5. Store interview details if available
            interview_details_stored = True
            if input_data.interview_details:
                # Store interview details in the database
                # Note: This assumes the manager has a method to store interview details
                # If not, you would need to implement it in the DriverScreeningManager
                try:
                    interview_data = input_data.interview_details.model_dump()
                    # Add interview details to the session metadata or as a separate record
                    # This is a placeholder - implement according to your database schema
                    logger.info(f"Storing interview details: {interview_data}")
                    interview_details_stored = self.screening_manager.add_interview_details(
                        input_data.driver_id,
                        input_data.dsp_code,
                        session_id,
                        interview_data
                    )
                except Exception as e:
                    interview_details_stored = False
                    logger.error(f"Failed to store interview details: {e}")
            
            # Return overall status
            if all_responses_added and result_updated and interview_details_stored:
                return json.dumps({
                    "success": True,
                    "message": "Driver screening data stored successfully",
                    "session_id": session_id
                })
            else:
                return json.dumps({
                    "success": False,
                    "message": "Some parts of the driver screening data could not be stored",
                    "session_id": session_id,
                    "responses_added": all_responses_added,
                    "result_updated": result_updated,
                    "interview_details_stored": interview_details_stored
                })
                
        except Exception as e:
            logger.error(f"Error storing driver screening data: {e}")
            return json.dumps({
                "success": False,
                "message": f"Error: {str(e)}"
            })
