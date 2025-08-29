import uvicorn
import logging
from app import create_app
from app.config import settings

# Get the logger
logger = logging.getLogger(__name__)

# Create the app instance using the factory function
app = create_app()

if __name__ == "__main__":
    """
    This is the main entry point for running the application.
    """
    logger.info("Starting WhatsApp Chatbot with Ollama and MCP...")
    logger.info(f"Model: {settings.OLLAMA_MODEL}")
    logger.info(f"Debug logging: {settings.DEBUG_LOGGING}")
    
    # Run the app with Uvicorn
    uvicorn.run(app, host="0.0.0.0", port=settings.PORT)
