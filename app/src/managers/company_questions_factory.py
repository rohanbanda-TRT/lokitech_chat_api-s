import logging
from functools import lru_cache
from .firebase_company_questions_manager import FirebaseCompanyQuestionsManager

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@lru_cache()
def get_company_questions_manager():
    """
    Factory function to get the company questions manager

    Returns:
        FirebaseCompanyQuestionsManager
    """
    logger.info("Using Firebase for company questions storage")
    return FirebaseCompanyQuestionsManager()
