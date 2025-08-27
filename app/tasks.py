from crewai import Task
from .agents import knowledge_agent

research_task = Task(
    description=(
        "Analisis pertanyaan pengguna berikut: '{question}'. "
        "Gunakan tool 'Document Search' untuk menemukan informasi yang relevan dari "
        "dokumen internal. Setelah menemukan informasinya, rangkum jawaban "
        "secara singkat, jelas, dan ramah dalam Bahasa Indonesia. "
        "Jika informasi tidak ditemukan, katakan dengan jujur bahwa Anda tidak dapat menemukannya di dokumen."
    ),
    expected_output=(
        "Jawaban akhir yang ringkas dan informatif dalam Bahasa Indonesia, "
        "disertai emoji yang sesuai untuk membuatnya lebih ramah."
    ),
    agent=knowledge_agent
)
