from pydantic_settings import BaseSettings
from functools import lru_cache
import os
from dotenv import load_dotenv
from urllib.parse import quote_plus

# Load environment variables from .env file
load_dotenv()


class Settings(BaseSettings):
    OPENAI_API_KEY: str
    LANGSMITH_TRACING: bool = True
    LANGSMITH_ENDPOINT: str = "https://api.smith.langchain.com"
    LANGSMITH_API_KEY: str = "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"
    LANGSMITH_PROJECT: str = "Report-Generation"

    # MongoDB settings
    MONGODB_PASSWORD: str = os.environ.get("MONGODB_PASSWORD", "")
    MONGODB_URI: str = (
        f"mongodb+srv://suyog:{quote_plus(os.environ.get('MONGODB_PASSWORD', ''))}@dsp-lokitech.dbvpz.mongodb.net/?retryWrites=true&w=majority&appName=dsp-lokitech"
    )
    MONGODB_DB_NAME: str = "lokitech_db"

    # Storage settings
    # Options: "mongodb" or "firebase"
    COMPANY_QUESTIONS_STORAGE: str = os.environ.get(
        "COMPANY_QUESTIONS_STORAGE", "firebase"
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings():
    return Settings()
