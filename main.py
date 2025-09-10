import uvicorn
import logging

from app import create_app
from app.config import settings

logger = logging.getLogger(__name__)

app = create_app()

if __name__ == "__main__":
    logger.info("Starting WhatsApp Chatbot with Ollama and MCP...")
    logger.info(f"Model: {settings.OLLAMA_MODEL}")
    logger.info(f"Debug logging: {settings.DEBUG_LOGGING}")
    uvicorn.run(app, host="0.0.0.0", port=settings.PORT)
