import json
import logging
import asyncio
import aiohttp

from langchain.prompts import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
)

logger = logging.getLogger(__name__)


def build_aiwa_prompt(knowledge_base: str):
    """
    Membuat system prompt Aiwa dengan aturan RAG menggunakan LangChain.
    """
    if not knowledge_base or knowledge_base.strip() == "":
        # Fallback jika knowledge_base kosong
        system_rules = """
Anda adalah Aiwa, asisten AI dari Warna Warni Media.

PERATURAN:
- Karena KNOWLEDGE BASE kosong, Anda WAJIB menjawab semua pertanyaan hanya dengan:
  "Maaf, saya tidak memiliki informasi mengenai hal tersebut."
"""
        prompt = ChatPromptTemplate.from_messages([
            SystemMessagePromptTemplate.from_template(system_rules),
            HumanMessagePromptTemplate.from_template("{user_message}")
        ])
        return prompt

    system_rules = """
    Anda adalah Aiwa, asisten AI dari Warna Warni Media.

    ⚠️ ATURAN PALING PENTING:
    - Jika pertanyaan pengguna TIDAK BISA dijawab menggunakan "KNOWLEDGE BASE", balas HANYA dengan:
    "Maaf, saya tidak memiliki informasi mengenai hal tersebut."
    - Jangan memberikan informasi lain, penjelasan tambahan, atau sapaan. Ini adalah aturan mutlak.

    ⚠️ ATURAN UNTUK SAPAAN:
    - Jika pesan pengguna HANYA berupa sapaan sederhana (contoh: "halo", "hai", "selamat pagi"),
    balas HANYA dengan:
    "Halo! Saya Aiwa, asisten AI dari Warna Warni Media. Saya siap membantu Anda dengan semangat warna-warni. Silahkan ajukan pertanyaan Anda ☺️"

    ⚠️ ATURAN UNTUK PERTANYAAN DENGAN JAWABAN DI KNOWLEDGE BASE:
    - Berikan HANYA jawaban yang relevan dari KNOWLEDGE BASE.
    - Jangan ulangi pertanyaan pengguna.
    - Jangan tambahkan sapaan pembuka.
    - Jangan tambahkan penutup.
    - Jawaban HARUS langsung dimulai dengan isi dari knowledge base.
    - Jika jawaban terdiri dari beberapa poin, cukup tampilkan apa adanya sesuai KB.

    Dengan kata lain:
    - Pertanyaan → Jawaban langsung (tanpa pengulangan, tanpa sapaan)
    - Salam → Salam khusus di atas
    - Pertanyaan di luar KB → Balas dengan kalimat "Maaf, saya tidak memiliki informasi mengenai hal tersebut."
    """



    knowledge_section = f"""
                        --- KNOWLEDGE BASE ---
                        {knowledge_base}
                        ----------------------
                        """

    system_prompt = system_rules + "\n" + knowledge_section

    prompt = ChatPromptTemplate.from_messages([
        SystemMessagePromptTemplate.from_template(system_prompt),
        HumanMessagePromptTemplate.from_template("{user_message}")
    ])
    return prompt


def lc_messages_to_ollama(messages):
    converted = []
    for msg in messages:
        if msg.type == "system":
            converted.append({"role": "system", "content": msg.content})
        elif msg.type == "human":
            converted.append({"role": "user", "content": msg.content})
        elif msg.type == "ai":
            converted.append({"role": "assistant", "content": msg.content})
        else:
            # fallback generic
            converted.append({"role": msg.type, "content": msg.content})
    return converted


class OllamaClient:
    """
    Client untuk berinteraksi dengan Ollama API, difokuskan pada RAG.
    """

    def __init__(self, url: str, model: str, debug_logging: bool = False):
        self.url = url
        self.model = model
        self.debug_logging = debug_logging
        self.api_endpoint = f"{url}/api/chat"

    async def get_response(self, user_message: str, knowledge_base: str) -> str:
        prompt = build_aiwa_prompt(knowledge_base)
        formatted_prompt = prompt.format_prompt(user_message=user_message)

        # Konversi LangChain message → dict agar bisa di-JSON
        ollama_messages = lc_messages_to_ollama(formatted_prompt.to_messages())

        payload = {
            "model": self.model,
            "messages": ollama_messages,
            "stream": False,
            "options": {
                "temperature": 0.1,
                "num_predict": 1000,
            },
        }

        if self.debug_logging:
            logger.debug(f"Ollama payload: {json.dumps(payload, indent=2, ensure_ascii=False)}")

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.api_endpoint, json=payload, timeout=30) as response:
                    if response.status == 200:
                        result = await response.json()
                        ollama_reply = result.get('message', {}).get('content', '').strip()
                        return ollama_reply
                    else:
                        error_text = await response.text()
                        logger.error(f"Ollama API error: {response.status} - {error_text}")
                        return "Maaf, saya sedang mengalami masalah teknis. Silahkan coba lagi nanti!"
        except asyncio.TimeoutError:
            logger.error("Ollama request timed out.")
            return "Maaf, respons terlalu lama. Coba ulangi pertanyaan anda."
        except aiohttp.ClientConnectorError:
            logger.error(f"Cannot connect to Ollama at {self.url}.")
            return "Maaf, saya sedang offline. Pastikan sistem sedang berjalan."
        except Exception as e:
            logger.error(f"An unexpected error occurred with Ollama: {e}", exc_info=self.debug_logging)
            return "Maaf, terjadi kesalahan sistem. Silahkan coba lagi nanti!"
