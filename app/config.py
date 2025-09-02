import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    ACCESS_TOKEN: str = os.getenv('ACCESS_TOKEN')
    PHONE_NUMBER_ID: str = os.getenv('PHONE_NUMBER_ID')
    VERIFY_TOKEN: str = os.getenv('VERIFY_TOKEN')
    META_API_VERSION: str = os.getenv('META_API_VERSION')
    OLLAMA_MODEL: str = os.getenv('OLLAMA_MODEL')
    OLLAMA_URL: str = os.getenv('OLLAMA_URL')
    OLLAMA_EMBEDDING: str = os.getenv('OLLAMA_EMBEDDING')
    ALLOWED_CONTACT: str = os.getenv('ALLOWED_CONTACT')
    DEBUG_LOGGING: bool = os.getenv('DEBUG_LOGGING')
    PORT: int = int(os.getenv('PORT', 5000))
    META_API_URL: str = f"https://graph.facebook.com/{META_API_VERSION}/{PHONE_NUMBER_ID}/messages"

settings = Settings()
