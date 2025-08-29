import logging
from fastapi import FastAPI
from .config import settings
from .services.mcp import MCPClient
from .services.ollama import OllamaClient
from .services.whatsapp import WhatsAppClient

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def create_app() -> FastAPI:
    """
    Application factory to create and configure the FastAPI application.
    This pattern helps in organizing the application setup.
    """
    app = FastAPI(title="WhatsApp RAG Bot")

    # Initialize clients using the centralized settings
    mcp_client = MCPClient(server_script_path="server.py", debug_logging=settings.DEBUG_LOGGING)
    ollama_client = OllamaClient(url=settings.OLLAMA_URL, model=settings.OLLAMA_MODEL, debug_logging=settings.DEBUG_LOGGING)
    whatsapp_client = WhatsAppClient(
        access_token=settings.ACCESS_TOKEN,
        phone_number_id=settings.PHONE_NUMBER_ID,
        meta_api_version=settings.META_API_VERSION,
        debug_logging=settings.DEBUG_LOGGING
    )

    # Store clients in the app's state to make them accessible from API routes
    app.state.mcp_client = mcp_client
    app.state.ollama_client = ollama_client
    app.state.whatsapp_client = whatsapp_client

    @app.on_event("startup")
    async def startup_event():
        """Initialize MCP connection when the application starts."""
        logger.info("Starting MCP client connection...")
        await app.state.mcp_client.connect()

    @app.on_event("shutdown")
    async def shutdown_event():
        """Clean up MCP connection when the application stops."""
        logger.info("Shutting down MCP client...")
        await app.state.mcp_client.cleanup()

    # Import and include the router from the chat module
    from . import chat
    app.include_router(chat.router)

    return app
