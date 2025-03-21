import logging
from functools import lru_cache
from ..core.config import get_settings
from .company_questions_manager import CompanyQuestionsManager
from .firebase_company_questions_manager import FirebaseCompanyQuestionsManager

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@lru_cache()
def get_company_questions_manager():
    """
    Factory function to get the appropriate company questions manager based on configuration
    
    Returns:
        CompanyQuestionsManager or FirebaseCompanyQuestionsManager
    """
    settings = get_settings()
    storage_type = settings.COMPANY_QUESTIONS_STORAGE.lower()
    
    if storage_type == "firebase":
        logger.info("Using Firebase for company questions storage")
        return FirebaseCompanyQuestionsManager()
    else:
        # Default to MongoDB
        logger.info("Using MongoDB for company questions storage")
        return CompanyQuestionsManager()
