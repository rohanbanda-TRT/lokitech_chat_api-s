from typing import Dict, Any, List, Optional
import json
import logging
from pydantic import BaseModel, Field
from .dsp_api_client import DSPApiClient, ApplicantDetails

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

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
                return json.dumps({
                    "success": False,
                    "message": "Missing required field: dsp_code"
                })
                
            if not applicant_id:
                return json.dumps({
                    "success": False,
                    "message": "Missing required field: applicant_id"
                })
                
            if not new_status:
                return json.dumps({
                    "success": False,
                    "message": "Missing required field: new_status"
                })
            
            # Prepare applicant data with responses only
            applicant_data = {
                "responses": responses
            }
            
            # Update the applicant status
            status_updated = self.dsp_api_client.update_applicant_status(
                dsp_code=dsp_code,
                applicant_id=applicant_id,
                current_status=current_status,
                new_status=new_status,
                applicant_data=applicant_data
            )
            
            if status_updated:
                return json.dumps({
                    "success": True,
                    "message": f"Successfully updated applicant status to {new_status}"
                })
            else:
                return json.dumps({
                    "success": False,
                    "message": f"Failed to update applicant status to {new_status}"
                })
                
        except Exception as e:
            logger.error(f"Error updating applicant status: {e}")
            return json.dumps({
                "success": False,
                "message": f"Error: {str(e)}"
            })
