import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from pathlib import Path
from app.services.llm_service import get_model
from app.services.mcp_service import init_mcp_client
from app.services.agent_service import init_agent
from app.services.whatsapp_service import WhatsAppClient
from app.core.prompt import SYSTEM_INSTRUCTION
from app.core.config import settings

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Starting up application...")

    BASE_DIR = Path(__file__).resolve().parent.parent

    client, tool_names = await init_mcp_client(BASE_DIR)
    logger.info(f"Tools loaded: {tool_names}")

    model = get_model("openrouter")

    agent = init_agent(model, await client.get_tools())

    whatsapp_client = WhatsAppClient(
        access_token=settings.ACCESS_TOKEN,
        phone_number_id=settings.PHONE_NUMBER_ID,
        meta_api_version=settings.META_API_VERSION,
        debug_logging=settings.DEBUG_LOGGING,
    )

    app.state.client = client
    app.state.agent = agent
    app.state.whatsapp_client = whatsapp_client
    app.state.chat_histories = {}
    app.state.system_instruction = SYSTEM_INSTRUCTION.format(tools=tool_names)
    app.state.processing_message_ids = set()

    yield

    logger.info("🛑 Shutting down MCP client...")
    await client.close()
