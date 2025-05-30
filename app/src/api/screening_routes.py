from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from ..agents import DriverScreeningAgent
from ..core.config import get_settings
from typing import Optional
import logging
import uuid

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Screening"])
settings = get_settings()
driver_screening_agent = DriverScreeningAgent(settings.OPENAI_API_KEY)


class DriverScreeningRequest(BaseModel):
    message: str

    session_id: str = Field(
        ...,
        min_length=1,
        description="Unique session identifier for screening conversation",
    )
    dsp_code: Optional[str] = Field(
        None, description="Optional DSP code to use company-specific questions"
    )
    station_code: Optional[str] = Field(
        None, description="Station code for the DSP location"
    )
    applicant_id: Optional[int] = Field(
        None, description="Applicant ID for the driver being screened"
    )


@router.post(
    "/driver-screening",
    summary="Screen potential drivers",
    description="Conducts an interactive screening conversation with potential drivers"
)
async def driver_screening(request: DriverScreeningRequest):
    try:
        # Validate session_id
        session_id = request.session_id
        if not session_id or session_id.strip() == "":
            # Generate a unique session ID if none provided
            session_id = str(uuid.uuid4())
            logger.info(f"Generated new session_id: {session_id}")

        # Validate dsp_code
        dsp_code = request.dsp_code
        if not dsp_code or dsp_code.strip() == "":
            dsp_code = "DEMO"  # Use a default DSP code
            logger.info(f"Using default dsp_code: {dsp_code}")

        # Get station_code and applicant_id
        station_code = request.station_code
        applicant_id = request.applicant_id

        # Validate message
        default_message = f"Start [DSP: {dsp_code}, Session: {session_id}, Station Code: {station_code}, Applicant ID: {applicant_id}]"
        message = (
            default_message
            if not request.message or request.message.strip() == ""
            else request.message
        )

        # Process message using driver screening agent with dsp_code if provided
        try:
            # Get applicant details first if this is a new session
            applicant_details = None
            if message.startswith("Start [DSP:") or message == default_message:
                # This is likely the first message, try to get applicant details
                from ..tools.dsp_api_client import DSPApiClient

                api_client = DSPApiClient()

                # Use provided station_code and applicant_id if available, otherwise use defaults
                station_code_to_use = station_code if station_code else "DJE1"
                applicant_id_to_use = applicant_id if applicant_id is not None else 5

                applicant_details_obj = api_client.get_applicant_details(
                    dsp_code=dsp_code,
                    station_code=station_code_to_use,
                    applicant_id=applicant_id_to_use,
                )

                if applicant_details_obj:
                    applicant_details = applicant_details_obj.model_dump()
                    logger.info(f"Retrieved applicant details: {applicant_details}")

            # Get company contact information
            _, contact_info, _, = driver_screening_agent._get_company_time_slots_and_contact_info(dsp_code)
            logger.info(f"Retrieved company contact info: {contact_info}")

            result = driver_screening_agent.process_message(
                message, session_id, dsp_code, station_code, applicant_id
            )

            response_data = {
                "response": result,
                "session_id": session_id,
                "dsp_code": dsp_code,
                "station_code": station_code,
                "applicant_id": applicant_id,
                "contact_info": contact_info,
            }

            # Include applicant details in the response if available
            if applicant_details:
                response_data["applicant_details"] = applicant_details

            return response_data
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            raise HTTPException(
                status_code=500, detail=f"Error processing message: {str(e)}"
            )

    except Exception as e:
        logger.error(f"Unexpected error in driver_screening endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")
