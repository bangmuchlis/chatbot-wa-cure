from fastapi import APIRouter
from app.config import settings
import httpx

router = APIRouter()

@router.get("/health", summary="Pemeriksaan Kesehatan Layanan")
async def health_check():
    """
    Menyediakan pemeriksaan kesehatan dasar layanan.
    """
    return {"status": "ok", "service": "WhatsApp Chatbot"}

@router.get("/test-ollama", summary="Tes Koneksi Ollama")
async def test_ollama():
    """
    Menguji koneksi ke layanan Ollama.
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(str(settings.OLLAMA_URL))
        if response.status_code == 200:
            return {"status": "sukses", "ollama_response": "Ollama sedang berjalan."}
        else:
            return {"status": "gagal", "details": f"Menerima status code {response.status_code}"}
    except httpx.ConnectError as e:
        return {"status": "gagal", "details": f"Koneksi ke Ollama gagal: {e}"}
