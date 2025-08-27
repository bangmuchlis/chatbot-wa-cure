from crewai import Crew, Process
from .agents import knowledge_agent
from .tasks import research_task
import logging

logger = logging.getLogger(__name__)

def run_crew(question: str) -> str:
    """Menjalankan CrewAI untuk memproses pertanyaan."""
    logger.info(f"CrewAI memulai proses untuk pertanyaan: '{question}'")
    
    knowledge_crew = Crew(
        agents=[knowledge_agent],
        tasks=[research_task],
        process=Process.sequential,
        verbose=2 
    )
    
    result = knowledge_crew.kickoff(inputs={'question': question})
    logger.info(f"CrewAI selesai dengan hasil: {result}")
    return result