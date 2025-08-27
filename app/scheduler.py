from apscheduler.schedulers.background import BackgroundScheduler
from app.services.rag_service import RAGService
from app.config import settings
import logging

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler(daemon=True)

def update_rag_index_job():
    """Tugas yang akan dijalankan oleh scheduler."""
    logger.info("Scheduler memicu tugas pembaruan indeks RAG.")
    RAGService.refresh_index()

# Menambahkan tugas ke scheduler
scheduler.add_job(
    update_rag_index_job,
    'interval',
    minutes=settings.RAG_UPDATE_INTERVAL_MINUTES
)