import os
import sys
import json

from mcp.server.fastmcp import FastMCP
from langchain_community.vectorstores import Chroma
from langchain_ollama import OllamaEmbeddings
from dotenv import load_dotenv

PROJECT_ROOT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
load_dotenv(os.path.join(PROJECT_ROOT_PATH, '.env'))

OLLAMA_EMBEDDING_MODEL = os.getenv("OLLAMA_EMBEDDING", "nomic-embed-text")

CHROMA_PERSIST_DIR = os.path.join(PROJECT_ROOT_PATH, "chroma_db")
CHROMA_COLLECTION_NAME = "documents"

mcp = FastMCP(name="RAG")

@mcp.tool()
def rag_query(query: str, top_k: int = 5) -> str:
    try:
        embedding_function = OllamaEmbeddings(model=OLLAMA_EMBEDDING_MODEL)
        
        vectordb = Chroma(
            collection_name=CHROMA_COLLECTION_NAME,
            persist_directory=CHROMA_PERSIST_DIR,
            embedding_function=embedding_function
        )
        results = vectordb.similarity_search(query, k=top_k)
        
        if not results:
            return "Tidak ada dokumen relevan yang ditemukan di RAG."

        rag_text = "Berikut adalah dokumen yang relevan dari RAG:\n\n"
        for i, doc in enumerate(results, 1):
            rag_text += f"Dokumen {i}:\n"
            rag_text += f"Konten: {doc.page_content}\n"
            metadata_str = json.dumps(doc.metadata, indent=2, ensure_ascii=False)
            rag_text += f"Metadata: {metadata_str}\n\n"

        return rag_text
    except Exception as e:
        return f"Error saat melakukan query RAG: {str(e)}"

if __name__ == "__main__":
    if PROJECT_ROOT_PATH not in sys.path:
        sys.path.append(PROJECT_ROOT_PATH)
        
    mcp.run(transport="stdio")

