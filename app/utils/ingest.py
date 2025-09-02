import sys
import os

from langchain_community.document_loaders import DirectoryLoader, PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_ollama import OllamaEmbeddings


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.append(PROJECT_ROOT)
from app.config import settings

CHROMA_COLLECTION_NAME = "documents"
CHROMA_PERSIST_DIR = os.path.join(PROJECT_ROOT, "chroma_db")


def ingest_documents():
    """Loads documents, splits them, and stores them in Chroma with BGE-M3 embeddings."""
    print("Starting document ingestion process...")

    documents_path = os.path.join(PROJECT_ROOT, 'data', 'docs')

    if not os.path.exists(documents_path) or not os.listdir(documents_path):
        print(f"Error: Directory '{documents_path}' is empty or does not exist.")
        return

    print(f"Loading documents from: {documents_path}")
    loader = DirectoryLoader(
        documents_path,
        glob="*.pdf",
        loader_cls=PyPDFLoader,
        show_progress=True,
        use_multithreading=True
    )

    documents = loader.load()
    if not documents:
        print("No PDF documents found to ingest.")
        return

    print(f"Loaded {len(documents)} document(s).")

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    docs = text_splitter.split_documents(documents)
    print(f"Documents split into {len(docs)} text chunks.")

    embedding_function = OllamaEmbeddings(model=settings.OLLAMA_EMBEDDING)
    print("Using BGE-M3 embeddings...")

    print(f"Storing data in Chroma collection: '{CHROMA_COLLECTION_NAME}'...")
    vectordb = Chroma.from_documents(
        docs,
        embedding=embedding_function,
        collection_name=CHROMA_COLLECTION_NAME,
        persist_directory=CHROMA_PERSIST_DIR
    )

    print("-" * 50)
    print("✅ Ingestion Complete!")
    print(f"Data stored in Chroma collection: '{CHROMA_COLLECTION_NAME}'")
    print(f"Persist directory: '{CHROMA_PERSIST_DIR}'")
    print("-" * 50)


if __name__ == '__main__':
    ingest_documents()
