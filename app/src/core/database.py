from pymongo import MongoClient
from .config import get_settings

settings = get_settings()

class Database:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Database, cls).__new__(cls)
            cls._instance.client = MongoClient(settings.MONGODB_URI)
            cls._instance.db = cls._instance.client[settings.MONGODB_DB_NAME]
        return cls._instance
    
    def get_collection(self, collection_name):
        return self.db[collection_name]
    
    def close(self):
        self.client.close()

def get_db():
    return Database()
