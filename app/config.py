from pydantic_settings import BaseSettings
from pydantic import HttpUrl, ConfigDict
from typing import List

class Settings(BaseSettings):
    # Pengaturan Meta WhatsApp
    ACCESS_TOKEN: str
    PHONE_NUMBER_ID: str
    VERIFY_TOKEN: str
    META_API_VERSION: str = "v20.0"

    # Pengaturan Ollama & LLM
    OLLAMA_MODEL: str = "mistral"
    OLLAMA_URL: HttpUrl = "http://localhost:11434"

    # Pengaturan Aplikasi
    PORT: int = 8000
    DEBUG_LOGGING: bool = False
    LOG_LEVEL: str = "INFO"

    # Pengaturan Google Drive RAG
    GOOGLE_SHEET_IDS: List[str] = []
    GOOGLE_DOC_IDS: List[str] = []
    
    # Path ke file kredensial Google
    GOOGLE_CREDENTIALS_PATH: str = "credentials.json"
    
    # Direktori untuk menyimpan indeks LlamaIndex
    INDEX_PERSIST_DIR: str = "./storage"

    model_config = ConfigDict(extra='ignore')

settings = Settings()