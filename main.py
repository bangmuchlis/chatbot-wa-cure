import uvicorn
from app import app
from app.config import settings

if __name__ == '__main__':
    print("🚀 Memulai RAG Chatbot dengan CrewAI, FastAPI, dan Ollama...")
    print(f"🤖 Model LLM: {settings.OLLAMA_MODEL}")
    print(f"🔧 Mode Debug: {settings.DEBUG_LOGGING}")

    uvicorn.run(
        "main:app", 
        host="0.0.0.0", 
        port=settings.PORT, 
        reload=True
    )