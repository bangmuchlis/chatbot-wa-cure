import os
import chromadb
from chromadb.utils import embedding_functions

CHROMA_DIR = os.path.join(os.path.dirname(__file__), "..", "chroma_db")
os.makedirs(CHROMA_DIR, exist_ok=True)

COLLECTION_NAME = "documents"

def get_chroma_collection():
    chroma_client = chromadb.PersistentClient(path=CHROMA_DIR)
    
    embedding_func = embedding_functions.DefaultEmbeddingFunction()
    
    collection = chroma_client.get_or_create_collection(
        name=COLLECTION_NAME, 
        embedding_function=embedding_func
    )
    
    return collection
