import uvicorn
import logging
from app import create_app
from app.core.config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    force=True         
)

logger = logging.getLogger("main")

app = create_app()

if __name__ == "__main__":
    logger.info("🚀 Starting WhatsApp Chatbot with Ollama and MCP...")
    logger.info(f"Debug logging: {settings.DEBUG_LOGGING}")
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=settings.DEBUG_LOGGING,
        log_level="info"   
    )
