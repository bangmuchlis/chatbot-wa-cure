import requests, os

OLLAMA_URL = os.getenv("OLLAMA_URL")

def check_gpu_usage():
    try:
        r = requests.get(f"{OLLAMA_URL}/api/tags")
        if r.status_code == 200:
            return f"✅ Ollama aktif di {OLLAMA_URL}"
        else:
            return f"⚠️ Ollama tidak merespon di {OLLAMA_URL}"
    except Exception as e:
        return f"❌ Tidak bisa connect ke Ollama: {e}"
