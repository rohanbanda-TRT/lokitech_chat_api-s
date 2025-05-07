import firebase_admin
from firebase_admin import credentials, firestore
import os
import logging
from dotenv import load_dotenv
from functools import lru_cache
from enum import Enum
from typing import Optional

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# Define environment types
class Environment(str, Enum):
    DEVELOPMENT = "development"
    LOCAL = "local"
    PRODUCTION = "production"


# Get current environment
def get_environment() -> Environment:
    env = os.environ.get("FIREBASE_ENV", "local").lower()
    if env == "production" or env == "prod":
        return Environment.PRODUCTION
    elif env == "development" or env == "dev":
        return Environment.DEVELOPMENT
    else:
        return Environment.LOCAL


# Get credentials file path based on environment
def get_credentials_file(environment: Environment) -> Optional[str]:
    # Default credential file
    default_cred_file = "firebase-credentials.json"
    
    # Environment-specific credential files
    env_cred_files = {
        Environment.PRODUCTION: "firebase-credentials-prod.json",
        Environment.DEVELOPMENT: "firebase-credentials-dev.json",
        Environment.LOCAL: "firebase-credentials-local.json"
    }
    
    # Check for environment-specific credential file first
    env_file = env_cred_files[environment]
    if os.path.exists(env_file):
        logger.info(f"Using environment-specific credentials file: {env_file}")
        return env_file
    
    # Fall back to default credential file
    if os.path.exists(default_cred_file):
        logger.info(f"Using default credentials file: {default_cred_file}")
        return default_cred_file
    
    # No credential file found
    return None


class FirebaseDB:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(FirebaseDB, cls).__new__(cls)
            try:
                # Check if the app is already initialized
                try:
                    firebase_admin.get_app()
                    logger.info("Firebase app already initialized")
                except ValueError:
                    # Get current environment
                    environment = get_environment()
                    logger.info(f"Initializing Firebase for environment: {environment}")
                    
                    # Get credentials file for current environment
                    cred_file = get_credentials_file(environment)
                    
                    # Initialize Firebase app
                    if cred_file:
                        cred = credentials.Certificate(cred_file)
                        firebase_admin.initialize_app(cred)
                        logger.info(f"Firebase initialized with service account from {cred_file}")
                    else:
                        # Use application default credentials
                        firebase_admin.initialize_app()
                        logger.info(
                            "Firebase initialized with application default credentials"
                        )

                # Get Firestore client
                cls._instance.db = firestore.client()
                logger.info("Successfully connected to Firebase Firestore")

            except Exception as e:
                logger.error(f"Failed to initialize Firebase: {e}")
                import traceback

                logger.error(f"Traceback: {traceback.format_exc()}")
                cls._instance.db = None

        return cls._instance

    def get_firestore_db(self):
        """
        Get the Firestore database client

        Returns:
            Firestore client or None if initialization failed
        """
        return self.db


@lru_cache()
def get_firestore_db():
    """
    Get the Firestore database client (cached)

    Returns:
        Firestore client
    """
    firebase_db = FirebaseDB()
    return firebase_db.get_firestore_db()
