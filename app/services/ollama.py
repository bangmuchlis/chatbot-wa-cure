import json
import logging
import asyncio
import aiohttp

logger = logging.getLogger(__name__)

class OllamaClient:
    """
    Client untuk berinteraksi dengan Ollama API, difokuskan pada RAG.
    """
    def __init__(self, url: str, model: str, debug_logging: bool = False):
        self.url = url
        self.model = model
        self.debug_logging = debug_logging
        self.api_endpoint = f"{url}/api/generate"

    async def get_response(self, user_message: str, knowledge_base: str) -> str:
        """
        Mengirim pesan ke Ollama dengan konteks knowledge base yang ketat.
        Bot hanya akan menjawab berdasarkan informasi yang diberikan.
        """
        system_prompt = f"""Anda adalah asisten AI yang bertugas menjawab pertanyaan HANYA berdasarkan informasi yang ada di dalam "KNOWLEDGE BASE".
        Aturan ketat:
        1. JAWAB HANYA DARI KNOWLEDGE BASE. Jangan gunakan pengetahuan umum Anda sama sekali.
        2. Jika jawaban atas pertanyaan pengguna TIDAK ADA di dalam knowledge base, jawab dengan: "Maaf, saya tidak memiliki informasi mengenai hal tersebut."
        3. Jangan mengarang atau menyimpulkan informasi di luar konteks yang diberikan.
        4. Jawaban harus singkat, jelas, dan sopan dalam Bahasa Indonesia.

        --- KNOWLEDGE BASE ---
        {knowledge_base}
        --------------------------

        Pertanyaan Pengguna: {user_message}

        Jawaban Anda:"""

        payload = {
            "model": self.model,
            "prompt": system_prompt,
            "stream": False,
            "options": {
                "temperature": 0.1, 
                "top_p": 0.8,
            }
        }

        if self.debug_logging:
            logger.debug(f"Ollama payload: {json.dumps(payload, indent=2, ensure_ascii=False)}")

        try:
            # Menggunakan aiohttp untuk menjaga operasi tetap asynchronous
            async with aiohttp.ClientSession() as session:
                async with session.post(self.api_endpoint, json=payload, timeout=30) as response:
                    if response.status == 200:
                        result = await response.json()
                        ollama_reply = result.get('response', '').strip()
                        logger.info("Successfully received response from Ollama.")
                        return ollama_reply
                    else:
                        error_text = await response.text()
                        logger.error(f"Ollama API error: {response.status} - {error_text}")
                        return "Maaf, saya sedang mengalami masalah teknis. Coba lagi nanti ya! 😅"
        except asyncio.TimeoutError:
            logger.error("Ollama request timed out.")
            return "Maaf, respons terlalu lama. Coba dengan pertanyaan yang lebih singkat ya! ⏰"
        except aiohttp.ClientConnectorError:
            logger.error(f"Cannot connect to Ollama at {self.url}.")
            return "Maaf, saya tidak dapat terhubung ke sistem AI saat ini. 🔧"
        except Exception as e:
            logger.error(f"An unexpected error occurred with Ollama: {e}", exc_info=self.debug_logging)
            return "Maaf, terjadi kesalahan tak terduga pada sistem. 🙏"
