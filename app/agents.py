from crewai import Agent
from langchain_community.llms import Ollama
from app.config import settings
from app.tools.rag_tool import DocumentSearchTool

# Inisialisasi LLM
ollama_llm = Ollama(model=settings.OLLAMA_MODEL, base_url=str(settings.OLLAMA_URL))

# Definisikan Agent
knowledge_agent = Agent(
    role='Analis Dokumen Internal',
    goal='Menemukan informasi yang paling relevan dari Google Docs dan Sheets untuk menjawab pertanyaan pengguna secara akurat.',
    backstory=(
        "Anda adalah seorang analis ahli yang memiliki akses ke basis data internal perusahaan "
        "yang tersimpan di Google Drive. Anda sangat teliti dan efisien dalam menemukan "
        "jawaban yang tepat dari tumpukan dokumen dan spreadsheet."
    ),
    tools=[DocumentSearchTool()],
    llm=ollama_llm,
    verbose=settings.DEBUG_LOGGING,
    allow_delegation=False
)