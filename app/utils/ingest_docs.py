import sys
import os
import pandas as pd

from langchain_community.document_loaders import DirectoryLoader, PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_ollama import OllamaEmbeddings
from langchain.schema import Document

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.append(PROJECT_ROOT)
from app.core.config import settings

CHROMA_COLLECTION_NAME = "documents"
CHROMA_PERSIST_DIR = os.path.join(PROJECT_ROOT, "chroma_db")
#CHROMA_PERSIST_DIR = "/mnt/c/Users/aiai/Documents/Development/Projects/chatbot-wwm/chroma_db"

def load_excel(file_path: str):
    df = pd.read_excel(file_path)
    documents = []

    for idx, row in df.iterrows():
        row_text = " | ".join([f"{col}: {row[col]}" for col in df.columns])
        documents.append(
            Document(page_content=row_text, metadata={"source": file_path, "row": idx})
        )
    return documents


def ingest_documents():
    print("Starting document ingestion process...")

    documents_path = os.path.join(PROJECT_ROOT, 'data', 'docs')

    if not os.path.exists(documents_path) or not os.listdir(documents_path):
        print(f"Error: Directory '{documents_path}' is empty or does not exist.")
        return

    all_documents = []

    # Load PDFs
    print(f"Loading PDF documents from: {documents_path}")
    pdf_loader = DirectoryLoader(
        documents_path,
        glob="*.pdf",
        loader_cls=PyPDFLoader,
        show_progress=True,
        use_multithreading=True
    )
    pdf_documents = pdf_loader.load()
    all_documents.extend(pdf_documents)
    print(f"Loaded {len(pdf_documents)} PDF document(s).")

    # Load Excels
    print(f"Loading Excel documents from: {documents_path}")
    excel_files = [f for f in os.listdir(documents_path) if f.endswith((".xlsx", ".xls"))]
    for file in excel_files:
        file_path = os.path.join(documents_path, file)
        excel_documents = load_excel(file_path)
        all_documents.extend(excel_documents)
    print(f"Loaded {len(excel_files)} Excel file(s).")

    if not all_documents:
        print("No documents found to ingest.")
        return

    print(f"Total {len(all_documents)} documents loaded.")

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)
    docs = text_splitter.split_documents(all_documents)
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
