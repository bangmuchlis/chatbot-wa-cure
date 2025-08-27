from fastapi import FastAPI
from .routes import webhook, health
from .utils.logger import setup_logger

setup_logger()

app = FastAPI(
    title="WhatsApp RAG Chatbot with CrewAI",
    description="Chatbot yang didukung oleh RAG dari Google Drive dan diorkestrasi oleh CrewAI.",
    version="1.0.0"
)

app.include_router(webhook.router, prefix="/api", tags=["Webhook"])
app.include_router(health.router, prefix="/api", tags=["Health Check"])

@app.get("/", tags=["Root"])
def read_root():
    return {"status": "✅ RAG Chatbot Service is running."}
