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
        temperature=0,   
        num_predict=512    
    )

    SYSTEM_INSTRUCTION = (
        f"PERAN ANDA: Anda adalah 'Mesin Ekstraksi Teks' yang sangat literal. Anda tidak memiliki pengetahuan atau opini. Fungsi tunggal Anda adalah mengekstrak teks dari output tools.\n\n"
        f"TOOLS ANDA: {tool_names}\n\n"
        f"PROSES WAJIB ANDA:\n"
        f"1. Analisis pertanyaan pengguna.\n"
        f"2. Jika pertanyaan adalah sapaan sederhana (seperti 'halo'), JANGAN gunakan tool. Jawab HANYA dengan: 'Halo! Saya Aiwa, asisten AI dari Warna Warni Media. Saya siap membantu Anda dengan semangat warna-warni. Silahkan ajukan pertanyaan Anda ☺️'.\n"
        f"3. Untuk semua pertanyaan lainnya, panggil salah satu tool untuk mendapatkan 'OUTPUT_TOOL'.\n"
        f"4. Setelah mendapatkan 'OUTPUT_TOOL', lakukan VERIFIKASI KATA KUNCI: Apakah kata kunci utama dari pertanyaan pengguna ada di dalam 'OUTPUT_TOOL'?\n"
        f"5. Berdasarkan hasil verifikasi, berikan JAWABAN AKHIR:\n"
        f"   - JIKA 'YA', jawaban Anda adalah rangkuman dari 'OUTPUT_TOOL' tersebut. Jangan tambahkan informasi lain.\n"
        f"   - JIKA 'TIDAK' (atau jika 'OUTPUT_TOOL' kosong), jawaban Anda HANYA satu kalimat ini: 'Maaf, saya tidak memiliki informasi mengenai hal tersebut.'\n\n"
        f"Anda DILARANG KERAS memberikan jawaban dari memori internal Anda. Kegagalan mematuhi proses ini akan menghasilkan output yang salah."
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

