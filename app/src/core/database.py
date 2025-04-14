from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from dotenv import load_dotenv
import os
from .config import get_settings
import logging

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

settings = get_settings()

# Print connection string for debugging (without password)
connection_string = (
    settings.MONGODB_URI.replace(settings.MONGODB_PASSWORD, "****")
    if settings.MONGODB_PASSWORD
    else settings.MONGODB_URI
)
logger.info(f"MongoDB connection string: {connection_string}")
logger.info(f"MongoDB password set: {'Yes' if settings.MONGODB_PASSWORD else 'No'}")


class Database:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Database, cls).__new__(cls)
            try:
                # Configure MongoDB client with connection pooling options
                cls._instance.client = MongoClient(
                    settings.MONGODB_URI,
                    maxPoolSize=50,  # Maximum number of connections in the connection pool
                    minPoolSize=10,  # Minimum number of connections in the connection pool
                    maxIdleTimeMS=60000,  # Maximum time a connection can remain idle (1 minute)
                    connectTimeoutMS=5000,  # Connection timeout (5 seconds)
                    serverSelectionTimeoutMS=5000,  # Server selection timeout (5 seconds)
                    retryWrites=True,  # Retry write operations if they fail
                    w="majority",  # Write concern - wait for acknowledgment from a majority of replicas
                )

                # Test the connection
                cls._instance.client.admin.command("ping")
                logger.info("Successfully connected to MongoDB Atlas")

                cls._instance.db = cls._instance.client[settings.MONGODB_DB_NAME]
            except (ConnectionFailure, ServerSelectionTimeoutError) as e:
                logger.error(f"Failed to connect to MongoDB Atlas: {e}")
                # Fallback to a local MongoDB instance if available
                try:
                    logger.info("Attempting to connect to local MongoDB instance")
                    cls._instance.client = MongoClient("mongodb://localhost:27017")
                    cls._instance.client.admin.command("ping")
                    logger.info("Successfully connected to local MongoDB instance")
                    cls._instance.db = cls._instance.client[settings.MONGODB_DB_NAME]
                except Exception as local_e:
                    logger.error(
                        f"Failed to connect to local MongoDB instance: {local_e}"
                    )
                    raise Exception("Could not connect to any MongoDB instance")
            except Exception as e:
                logger.error(f"Unexpected error connecting to MongoDB: {e}")
                raise
        return cls._instance

    def get_collection(self, collection_name):
        return self.db[collection_name]

    def close(self):
        self.client.close()
        logger.info("MongoDB connection closed")


def get_db():
    return Database()
