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
    """Mencari dokumen yang relevan dari vector store Chroma."""
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
    # --- Blok Debugging ---
    # python servers/rag_server.py test

    # if len(sys.argv) > 1 and sys.argv[1] == 'test':
    #     print("--- Menjalankan dalam Mode Tes Chroma ---")
    #     try:
    #         if not os.path.exists(CHROMA_PERSIST_DIR):
    #             print(f"Error: Direktori Chroma tidak ditemukan di '{CHROMA_PERSIST_DIR}'")
    #             sys.exit(1)

    #         vectordb = Chroma(
    #             collection_name=CHROMA_COLLECTION_NAME,
    #             persist_directory=CHROMA_PERSIST_DIR,
    #             embedding_function=OllamaEmbeddings(model=OLLAMA_EMBEDDING_MODEL) # Perlu embedding untuk load
    #         )
            
    #         retrieved_docs = vectordb.get()
            
    #         if not retrieved_docs or not retrieved_docs.get('documents'):
    #              print("Tidak ada dokumen yang ditemukan di dalam koleksi.")
    #         else:
    #             print(f"Ditemukan {len(retrieved_docs['documents'])} dokumen di koleksi '{CHROMA_COLLECTION_NAME}':\n")
    #             for i, doc_content in enumerate(retrieved_docs['documents']):
    #                 print("-" * 30)
    #                 print(f"Dokumen {i+1}")
    #                 print(f"Konten: {doc_content[:500]}...") # Tampilkan 500 karakter pertama
    #                 if retrieved_docs['metadatas']:
    #                      print(f"Metadata: {retrieved_docs['metadatas'][i]}")
    #                 print("-" * 30 + "\n")

    #     except Exception as e:
    #         print(f"Terjadi error saat mencoba mengakses Chroma: {e}")
        
    #     print("--- Tes Chroma Selesai ---")
    #     sys.exit(0)

    if PROJECT_ROOT_PATH not in sys.path:
        sys.path.append(PROJECT_ROOT_PATH)
        
    mcp.run(transport="stdio")

