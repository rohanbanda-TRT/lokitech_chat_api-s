#!/usr/bin/env python3
"""
Test script to verify MongoDB Atlas connection
"""

import os
import sys
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add the app directory to the path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))

from app.src.core.database import get_db

def test_connection():
    """Test the MongoDB connection and perform basic operations"""
    try:
        # Get database instance
        db = get_db()
        
        # Test collection access
        collection = db.get_collection("test_connection")
        
        # Insert a test document
        result = collection.insert_one({"test": "connection", "status": "success"})
        logger.info(f"Inserted document with ID: {result.inserted_id}")
        
        # Find the document
        doc = collection.find_one({"test": "connection"})
        logger.info(f"Found document: {doc}")
        
        # Delete the test document
        collection.delete_one({"_id": result.inserted_id})
        logger.info("Test document deleted")
        
        logger.info("MongoDB connection test completed successfully!")
        return True
    except Exception as e:
        logger.error(f"Error testing MongoDB connection: {e}")
        return False

if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1)
