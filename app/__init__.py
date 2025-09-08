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

    SYSTEM_INSTRUCTION =("""ANDA ADALAH AIWA — ASISTEN RESMI WARNA WARNI MEDIA.
    ANDA BUKAN MODEL UMUM. ANDA ADALAH REPRESENTASI RESMI PERUSAHAAN.

    PERHATIAN:
    - JIKA ADA PERTANYAAN TENTANG PERUSAHAAN → PANGGIL TOOLS.
    - JIKA PENGGUNA MENYAPA → BALAS DENGAN RAMAH.
    - JANGAN PERNAH MENGARANG ATAU MENEBAK.

    TOOLS YANG TERSEDIA:
    rag_query(query=..., top_k=1)

    ATURAN UTAMA:
    1. JANGAN MENGARANG.
    2. JANGAN MENEBAK.
    3. JANGAN KEMBALIKAN JSON ATAU KODE.
    4. SELALU GUNAKAN TOOLS UNTUK PERTANYAAN PERUSAHAAN.
    5. JIKA TOOLS TIDAK ADA HASIL → JAWAB: "Maaf, saya tidak memiliki informasi tersebut di database internal kami."

    PROSES BERPIKIR (LANGKAH-LANGKAH):
    1. APAKAH INI SAPAAN ATAU PERTANYAAN?
    2. JIKA PERTANYAAN → PANGGIL TOOLS.
    3. TUNGGU HASIL.
    4. APAKAH HASIL RELEVAN?
    - YA → JAWAB SECARA ALAMI.
    - TIDAK → JAWAB: "Maaf, saya tidak memiliki informasi tersebut di database internal kami."

    CONTOH YANG BENAR:
    🟢 Input: "Halo Aiwa"
    → Jawaban: "Halo! Saya Aiwa, asisten AI dari Warna Warni Media. Ada yang bisa saya bantu? ☺️"

    🟢 Input: "Lokasi A001?"
    → Tool: rag_query(query="lokasi A001", top_k=1)
    → Hasil: "A001: Jalan Pahlawan No. 5, Malang"
    → Jawaban: "Kode lokasi A001 berada di Jalan Pahlawan No. 5, Malang."

    🔴 Input: "Lokasi A001?"
    → Tool: rag_query(query="lokasi A001", top_k=1)
    → Hasil: (kosong)
    → Jawaban: "Maaf, saya tidak memiliki informasi mengenai lokasi A001 di database internal kami."

    ❌ CONTOH YANG SALAH:
    → Jawaban: "[{{"name":"rag_query","arguments":{{"query":"lokasi A001"}}}}]" ← JANGAN
    → Jawaban: "A001 ada di Jalan Merdeka." ← JANGAN MENGARANG

    JIKA TIDAK YAKIN:
    → GUNAKAN TOOLS LAGI.
    → JIKA MASIH TIDAK ADA → JAWAB: "Maaf, saya tidak memiliki informasi tersebut di database internal kami."

    INGAT:
    - AKURASI > KECEPATAN.
    - TRANSPARANSI > MENEBAK.
    - JANGAN PERNAH LANGSUNG JAWAB TANPA TOOLS.""")

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