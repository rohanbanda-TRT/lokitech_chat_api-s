from typing import List, Dict, Any, Optional
import json
import logging
from pymongo import IndexModel, ASCENDING
from pymongo.errors import PyMongoError
from datetime import datetime
from ..core.database import get_db

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class DriverScreeningManager:
    """
    Manager class for driver screening responses
    """

    def __init__(self):
        self.db = get_db()
        self.collection = self.db.get_collection("drivers")

        # Create indexes for better query performance
        try:
            self.collection.create_index("driver_id")
            self.collection.create_index(
                [
                    ("screenings.dsp_code", ASCENDING),
                    ("screenings.session_id", ASCENDING),
                ]
            )
            logger.info("Created indexes on driver_id and screenings fields")
        except PyMongoError as e:
            logger.warning(f"Index creation warning (may already exist): {e}")

        logger.info("DriverScreeningManager initialized")

    def create_driver(
        self, driver_id: str, driver_name: str, contact_info: Dict[str, str]
    ) -> bool:
        """
        Create a new driver record in the database

        Args:
            driver_id: Unique identifier for the driver
            driver_name: Name of the driver
            contact_info: Dictionary containing email and phone

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            logger.info(f"Creating new driver record for driver_id: {driver_id}")

            # Check if driver already exists
            existing = self.collection.find_one({"driver_id": driver_id})

            if existing:
                logger.info(f"Driver with id {driver_id} already exists")
                return True

            # Create new driver document
            driver_doc = {
                "driver_id": driver_id,
                "driver_name": driver_name,
                "contact_info": contact_info,
                "screenings": [],
            }

            result = self.collection.insert_one(driver_doc)

            logger.info(f"Driver created with id: {result.inserted_id}")
            return result.acknowledged

        except Exception as e:
            logger.error(f"Error creating driver: {e}")
            return False

    def add_screening_session(
        self, driver_id: str, dsp_code: str, session_id: str
    ) -> bool:
        """
        Initialize a new screening session for a driver

        Args:
            driver_id: Unique identifier for the driver
            dsp_code: The DSP code for the company
            session_id: Unique identifier for the screening session

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            logger.info(
                f"Initializing screening session for driver_id: {driver_id}, dsp_code: {dsp_code}, session_id: {session_id}"
            )

            # Check if driver exists
            existing = self.collection.find_one({"driver_id": driver_id})

            if not existing:
                logger.error(f"Driver with id {driver_id} does not exist")
                return False

            # Check if this session already exists
            for screening in existing.get("screenings", []):
                if (
                    screening.get("session_id") == session_id
                    and screening.get("dsp_code") == dsp_code
                ):
                    logger.info(
                        f"Screening session already exists for driver_id: {driver_id}, dsp_code: {dsp_code}, session_id: {session_id}"
                    )
                    return True

            # Create new screening session
            new_screening = {
                "dsp_code": dsp_code,
                "session_id": session_id,
                "screening_date": datetime.now(),
                "responses": [],
                "overall_result": {"pass": None, "evaluation_summary": ""},
            }

            # Add new screening to driver's screenings array
            result = self.collection.update_one(
                {"driver_id": driver_id}, {"$push": {"screenings": new_screening}}
            )

            logger.info(
                f"Screening session initialized: {result.modified_count} documents modified"
            )
            return result.modified_count > 0

        except Exception as e:
            logger.error(f"Error initializing screening session: {e}")
            return False

    def add_screening_response(
        self,
        driver_id: str,
        dsp_code: str,
        session_id: str,
        question_id: int,
        question_text: str,
        response_text: str,
    ) -> bool:
        """
        Add a response to a screening session

        Args:
            driver_id: Unique identifier for the driver
            dsp_code: The DSP code for the company
            session_id: Unique identifier for the screening session
            question_id: The ID of the question
            question_text: The text of the question
            response_text: The driver's response to the question

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            logger.info(
                f"Adding response for driver_id: {driver_id}, dsp_code: {dsp_code}, session_id: {session_id}"
            )

            # Find the driver and the specific screening session
            driver = self.collection.find_one(
                {
                    "driver_id": driver_id,
                    "screenings": {
                        "$elemMatch": {"dsp_code": dsp_code, "session_id": session_id}
                    },
                }
            )

            if not driver:
                logger.error(
                    f"Driver with id {driver_id} or screening session not found"
                )
                return False

            # Create response object
            response = {
                "question_id": question_id,
                "question_text": question_text,
                "response_text": response_text,
            }

            # Add response to the specific screening session
            result = self.collection.update_one(
                {
                    "driver_id": driver_id,
                    "screenings.dsp_code": dsp_code,
                    "screenings.session_id": session_id,
                },
                {"$push": {"screenings.$.responses": response}},
            )

            logger.info(f"Response added: {result.modified_count} documents modified")
            return result.modified_count > 0

        except Exception as e:
            logger.error(f"Error adding response: {e}")
            return False

    def update_screening_result(
        self,
        driver_id: str,
        dsp_code: str,
        session_id: str,
        pass_result: bool,
        evaluation_summary: str,
    ) -> bool:
        """
        Update the overall result of a screening session

        Args:
            driver_id: Unique identifier for the driver
            dsp_code: The DSP code for the company
            session_id: Unique identifier for the screening session
            pass_result: Whether the driver passed the screening
            evaluation_summary: Summary of the evaluation

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            logger.info(
                f"Updating screening result for driver_id: {driver_id}, dsp_code: {dsp_code}, session_id: {session_id}"
            )

            # Update the overall result for the specific screening session
            result = self.collection.update_one(
                {
                    "driver_id": driver_id,
                    "screenings.dsp_code": dsp_code,
                    "screenings.session_id": session_id,
                },
                {
                    "$set": {
                        "screenings.$.overall_result.pass": pass_result,
                        "screenings.$.overall_result.evaluation_summary": evaluation_summary,
                    }
                },
            )

            logger.info(
                f"Screening result updated: {result.modified_count} documents modified"
            )
            return result.modified_count > 0

        except Exception as e:
            logger.error(f"Error updating screening result: {e}")
            return False

    def get_driver_screenings(self, driver_id: str) -> List[Dict[str, Any]]:
        """
        Get all screening sessions for a driver

        Args:
            driver_id: Unique identifier for the driver

        Returns:
            List of screening session objects
        """
        try:
            logger.info(f"Retrieving screenings for driver_id: {driver_id}")

            driver = self.collection.find_one(
                {"driver_id": driver_id}, {"_id": 0, "screenings": 1}
            )

            if driver and "screenings" in driver:
                screenings = driver["screenings"]
                logger.info(
                    f"Found {len(screenings)} screenings for driver_id: {driver_id}"
                )
                return screenings
            else:
                logger.info(f"No screenings found for driver_id: {driver_id}")
                return []

        except Exception as e:
            logger.error(f"Error retrieving screenings: {e}")
            return []

    def get_screening_session(
        self, driver_id: str, dsp_code: str, session_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get a specific screening session

        Args:
            driver_id: Unique identifier for the driver
            dsp_code: The DSP code for the company
            session_id: Unique identifier for the screening session

        Returns:
            Screening session object or None if not found
        """
        try:
            logger.info(
                f"Retrieving screening session for driver_id: {driver_id}, dsp_code: {dsp_code}, session_id: {session_id}"
            )

            driver = self.collection.find_one(
                {"driver_id": driver_id},
                {
                    "_id": 0,
                    "screenings": {
                        "$elemMatch": {"dsp_code": dsp_code, "session_id": session_id}
                    },
                },
            )

            if driver and "screenings" in driver and len(driver["screenings"]) > 0:
                screening = driver["screenings"][0]
                logger.info(
                    f"Found screening session for driver_id: {driver_id}, dsp_code: {dsp_code}, session_id: {session_id}"
                )
                return screening
            else:
                logger.info(
                    f"No screening session found for driver_id: {driver_id}, dsp_code: {dsp_code}, session_id: {session_id}"
                )
                return None

        except Exception as e:
            logger.error(f"Error retrieving screening session: {e}")
            return None

    def add_interview_details(
        self,
        driver_id: str,
        dsp_code: str,
        session_id: str,
        interview_data: Dict[str, Any],
    ) -> bool:
        """
        Add interview details to a screening session

        Args:
            driver_id: Unique identifier for the driver
            dsp_code: The DSP code for the company
            session_id: Unique identifier for the screening session
            interview_data: Dictionary containing interview details (scheduled, date, time, etc.)

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            logger.info(
                f"Adding interview details for driver_id: {driver_id}, dsp_code: {dsp_code}, session_id: {session_id}"
            )

            # Update the interview details for the specific screening session
            result = self.collection.update_one(
                {
                    "driver_id": driver_id,
                    "screenings.dsp_code": dsp_code,
                    "screenings.session_id": session_id,
                },
                {"$set": {"screenings.$.interview_details": interview_data}},
            )

            logger.info(
                f"Interview details added: {result.modified_count} documents modified"
            )
            return result.modified_count > 0

        except Exception as e:
            logger.error(f"Error adding interview details: {e}")
            return False

    def get_driver(self, driver_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a driver by driver_id

        Args:
            driver_id: Unique identifier for the driver

        Returns:
            Driver document or None if not found
        """
        try:
            logger.info(f"Retrieving driver with driver_id: {driver_id}")

            driver = self.collection.find_one(
                {"driver_id": driver_id}, {"_id": 0}  # Exclude MongoDB _id field
            )

            if driver:
                logger.info(f"Found driver with driver_id: {driver_id}")
                return driver
            else:
                logger.info(f"No driver found with driver_id: {driver_id}")
                return None

        except Exception as e:
            logger.error(f"Error retrieving driver: {e}")
            return None
