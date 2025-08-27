import os
import logging
import shutil
from llama_index.core import VectorStoreIndex, StorageContext, load_index_from_storage
from llama_index.readers.google import GoogleDocsReader, GoogleSheetsReader
from app.config import settings

logger = logging.getLogger(__name__)

class RAGService:
    _instance = None
    _query_engine = None
    _index = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RAGService, cls).__new__(cls)
            cls.initialize_index()
        return cls._instance

    @classmethod
    def initialize_index(cls):
        """Menginisialisasi atau memuat indeks dari penyimpanan."""
        try:
            if not os.path.exists(settings.INDEX_PERSIST_DIR):
                logger.info("Membuat indeks baru dari Google Drive...")
                cls.refresh_index()
            else:
                logger.info(f"Memuat indeks dari {settings.INDEX_PERSIST_DIR}...")
                storage_context = StorageContext.from_defaults(persist_dir=settings.INDEX_PERSIST_DIR)
                cls._index = load_index_from_storage(storage_context)
                cls._query_engine = cls._index.as_query_engine(similarity_top_k=3)
                logger.info("Indeks berhasil dimuat.")
        except Exception as e:
            logger.error(f"Gagal menginisialisasi RAGService: {e}")

    @classmethod
    def refresh_index(cls):
        """Memuat ulang dokumen dan membangun kembali indeks."""
        logger.info("Memulai proses pembaruan indeks RAG...")
        try:
            if os.path.exists(settings.INDEX_PERSIST_DIR):
                shutil.rmtree(settings.INDEX_PERSIST_DIR)
                logger.info(f"Direktori indeks lama '{settings.INDEX_PERSIST_DIR}' telah dihapus.")
            
            os.makedirs(settings.INDEX_PERSIST_DIR)

            documents = cls._load_documents()
            if not documents:
                logger.warning("Tidak ada dokumen yang dimuat. Proses pembaruan indeks dibatalkan.")
                cls._query_engine = None
                return

            cls._index = VectorStoreIndex.from_documents(documents)
            cls._index.storage_context.persist(persist_dir=settings.INDEX_PERSIST_DIR)
            cls._query_engine = cls._index.as_query_engine(similarity_top_k=3)
            logger.info("Pembaruan indeks RAG berhasil diselesaikan.")

        except Exception as e:
            logger.error(f"Gagal memperbarui indeks RAG: {e}", exc_info=True)

    @classmethod
    def _load_documents(cls):
        """Memuat dokumen dari Google Docs dan Sheets."""
        try:
            docs_loader = GoogleDocsReader()
            sheets_loader = GoogleSheetsReader()
            
            all_docs = []
            if settings.GOOGLE_DOC_IDS:
                all_docs.extend(docs_loader.load_data(document_ids=settings.GOOGLE_DOC_IDS))
            if settings.GOOGLE_SHEET_IDS:
                all_docs.extend(sheets_loader.load_data(spreadsheet_ids=settings.GOOGLE_SHEET_IDS))
            
            logger.info(f"Total {len(all_docs)} dokumen berhasil dimuat dari Google Drive.")
            return all_docs
        except Exception as e:
            logger.error(f"Gagal memuat dokumen dari Google Drive: {e}")
            logger.error("Pastikan file 'credentials.json' Anda valid dan memiliki akses ke Google Drive API.")
            return []

    def query(self, question: str) -> str:
        """Melakukan query ke indeks dan mengembalikan jawaban."""
        if self._query_engine is None:
            return "Maaf, sistem pencarian dokumen saat ini tidak tersedia."
        
        logger.info(f"Melakukan query RAG untuk pertanyaan: '{question}'")
        response = self._query_engine.query(question)
        return str(response)

# Inisialisasi singleton instance saat modul dimuat
rag_service_instance = RAGService()
