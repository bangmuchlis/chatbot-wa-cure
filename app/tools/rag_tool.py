from crewai_tools import BaseTool
from app.services.rag_service import rag_service_instance

class DocumentSearchTool(BaseTool):
    name: str = "Document Search"
    description: str = "Gunakan tool ini untuk mencari informasi spesifik di dalam Google Docs dan Google Sheets yang tersedia. Sangat berguna untuk menjawab pertanyaan tentang data internal, laporan, atau spreadsheet."

    def _run(self, argument: str) -> str:
        """Gunakan RAG service untuk menjawab pertanyaan."""
        return rag_service_instance.query(argument)