import firebase_admin
from firebase_admin import credentials, firestore
import os
import logging
from dotenv import load_dotenv
from functools import lru_cache

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

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
                    # Initialize Firebase app
                    # For production, use a service account key file
                    # For development, we'll use the application default credentials
                    if os.path.exists("firebase-credentials.json"):
                        cred = credentials.Certificate("firebase-credentials.json")
                        firebase_admin.initialize_app(cred)
                        logger.info("Firebase initialized with service account")
                    else:
                        # Use application default credentials
                        firebase_admin.initialize_app()
                        logger.info("Firebase initialized with application default credentials")
                
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
