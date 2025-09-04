import logging
from fastapi import FastAPI
from contextlib import asynccontextmanager
from .config import settings
from .services.whatsapp import WhatsAppClient
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent
from langchain_ollama import ChatOllama
import os
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Mengelola startup dan shutdown aplikasi."""
    logger.info("🚀 Starting up application...")
    
    BASE_DIR = Path(__file__).resolve().parent.parent
    QA_SERVER = str(BASE_DIR / "servers" / "qa_server.py")
    RAG_SERVER = str(BASE_DIR / "servers" / "rag_server.py")

    client = MultiServerMCPClient(
        {
            "knowledge": {
                "command": "python",
                "args": [QA_SERVER],
                "transport": "stdio",
            },
            "rag": {
                "command": "python",
                "args": [RAG_SERVER],
                "transport": "stdio",
            }
        }
    )
    tools = await client.get_tools()
    tool_names = ", ".join([t.name for t in tools])
    logger.info(f"Tools loaded: {tool_names}")

    model = ChatOllama(
        model=settings.OLLAMA_MODEL, 
        base_url=settings.OLLAMA_URL,
        temperature=0.1, 
        num_predict=512   
    )

    SYSTEM_INSTRUCTION = (
        f"ANDA ADALAH AIWA - ASISTEN AI CERDAS DARI WARNA WARNI MEDIA.\n\n"
        f"KEMAMPUAN ANDA:\n"
        f"- Tools tersedia: {tool_names}\n"
        f"- Anda memiliki kecerdasan untuk menganalisis konteks dan menentukan respons yang tepat\n"
        f"- Anda dapat membedakan berbagai jenis input: sapaan, pertanyaan, permintaan informasi\n\n"
        f"PANDUAN RESPONS DINAMIS:\n\n"
        f"UNTUK SAPAAN (halo, hai, selamat pagi, dll):\n"
        f"- Respons ramah: 'Halo! Saya Aiwa, asisten AI dari Warna Warni Media. Saya siap membantu Anda dengan semangat warna-warni. Silahkan ajukan pertanyaan Anda ☺️'\n"
        f"- JANGAN gunakan tools untuk sapaan sederhana\n\n"
        f"UNTUK PERTANYAAN INFORMASI:\n"
        f"- Gunakan tools yang tersedia untuk mencari informasi\n"
        f"- ANALISIS CERDAS: Apakah hasil tools relevan dengan pertanyaan?\n"
        f"- Jika RELEVAN: Berikan informasi dengan natural dan informatif\n"
        f"- Jika TIDAK RELEVAN/KOSONG: 'Maaf, saya tidak memiliki informasi mengenai hal tersebut.'\n\n"
        f"CONTOH ANALISIS KONTEKSTUAL:\n"
        f"Input: 'halo aiwa' → Sapaan → Respons ramah tanpa tools\n"
        f"Input: 'kebijakan cuti?' → Pertanyaan → Gunakan tools → Analisis relevansi → Respons\n"
        f"Input: 'siapa jokowi?' → Pertanyaan → Gunakan tools → Jika tidak ada info relevan → 'Tidak memiliki informasi'\n\n"
        f"PRINSIP KECERDASAN ANDA:\n"
        f"- Pahami KONTEKS dan INTENT dari setiap input\n"
        f"- Gunakan JUDGMENT untuk menentukan kapan menggunakan tools\n"
        f"- Prioritaskan AKURASI dan RELEVANSI\n"
        f"- Berikan respons yang NATURAL dan MEMBANTU\n\n"
        f"Gunakan kecerdasan Anda untuk memberikan pengalaman terbaik bagi user!"
    )   

    agent = create_react_agent(
        model,
        tools,
    )

    agent.llm = model

    whatsapp_client = WhatsAppClient(
        access_token=settings.ACCESS_TOKEN,
        phone_number_id=settings.PHONE_NUMBER_ID,
        meta_api_version=settings.META_API_VERSION,
        debug_logging=settings.DEBUG_LOGGING
    )

    app.state.client = client
    app.state.agent = agent
    app.state.whatsapp_client = whatsapp_client
    app.state.chat_histories = {}
    app.state.system_instruction = SYSTEM_INSTRUCTION
    app.state.processing_message_ids = set()

    yield

    logger.info("🛑 Shutting down MCP client...")
    await client.close()

def create_app() -> FastAPI:
    """Membuat dan mengonfigurasi instance FastAPI."""
    app = FastAPI(title="WhatsApp RAG Bot", lifespan=lifespan)

    from . import chat
    app.include_router(chat.router)
    return app