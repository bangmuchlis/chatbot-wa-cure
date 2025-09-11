import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # Meta 
    ACCESS_TOKEN: str = os.getenv('ACCESS_TOKEN')
    PHONE_NUMBER_ID: str = os.getenv('PHONE_NUMBER_ID')
    VERIFY_TOKEN: str = os.getenv('VERIFY_TOKEN')
    META_API_VERSION: str = os.getenv('META_API_VERSION')
    META_API_URL: str = f"https://graph.facebook.com/{META_API_VERSION}/{PHONE_NUMBER_ID}/messages"
    ALLOWED_CONTACT: str = os.getenv('ALLOWED_CONTACT')
    
    # Ollama
    OLLAMA_MODEL: str = os.getenv('OLLAMA_MODEL')
    OLLAMA_URL: str = os.getenv('OLLAMA_URL')
    OLLAMA_EMBEDDING: str = os.getenv('OLLAMA_EMBEDDING')
    
    # API key
    OPENROUTER_API_KEY: bool = os.getenv('OPENROUTER_API_KEY')
    GEMINI_API_KEY: bool = os.getenv('GEMINI_API_KEY')
    GROQ_API_KEY: bool = os.getenv('GROQ_API_KEY')

    # Database
    DATABASE_URL: bool = os.getenv('DATABASE_URL')
    DEBUG_LOGGING: bool = os.getenv('LOGGING')
    PORT: int = int(os.getenv('PORT', 5000))

settings = Settings()
