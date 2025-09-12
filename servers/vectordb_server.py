import os
import sys
import json
import logging

from mcp.server.fastmcp import FastMCP
from langchain_community.vectorstores import Chroma
from langchain_ollama import OllamaEmbeddings
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

PROJECT_ROOT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
load_dotenv(os.path.join(PROJECT_ROOT_PATH, '.env'))

OLLAMA_EMBEDDING_MODEL = os.getenv("OLLAMA_EMBEDDING")
CHROMA_PERSIST_DIR = os.path.join(PROJECT_ROOT_PATH, "chroma_db")
CHROMA_COLLECTION_NAME = "documents"

mcp = FastMCP(name="VectorDB_Server")

@mcp.tool()
def vectordb_query(query: str, top_k: int = 5) -> str:
    """
    Perform semantic similarity search on company documents using vector embeddings.
    Use this tool ONLY when the user asks open-ended, vague, or complex questions that are NOT explicitly listed in the static Q&A database.
    
    Examples of questions suitable for this tool:
    - "Tell me about our company culture."
    - "What do employees say about remote work?"
    - "Summarize the latest updates on IT policies."
    - "Find documents mentioning employee wellness programs."

    This tool DOES NOT know exact answers — it finds similar text snippets from uploaded documents.
    Always analyze if the results contain the exact answer before responding.

    Args:
        query: The natural language question to search for.
        top_k: Number of top matching documents to retrieve (default: 5).

    Returns:
        Formatted string with retrieved document content and metadata, or error message.
    """
    try:
        logging.info(f"Initializing embeddings with model: {OLLAMA_EMBEDDING_MODEL}")
        embedding_function = OllamaEmbeddings(model=OLLAMA_EMBEDDING_MODEL)
        
        logging.info(f"Connecting to ChromaDB collection '{CHROMA_COLLECTION_NAME}' at '{CHROMA_PERSIST_DIR}'")
        vectordb = Chroma(
            collection_name=CHROMA_COLLECTION_NAME,
            persist_directory=CHROMA_PERSIST_DIR,
            embedding_function=embedding_function
        )
        
        logging.info(f"Performing similarity search for query: '{query}' with top_k={top_k}")
        results = vectordb.similarity_search(query, k=top_k)
        
        if not results:
            logging.warning("No relevant documents were found for the query.")
            return "No relevant documents were found in the RAG system."

        logging.info(f"Found {len(results)} relevant document(s). Formatting output.")
        rag_text = "The following relevant documents were found by the RAG system:\n\n"
        for i, doc in enumerate(results, 1):
            rag_text += f"--- Document {i} ---\n"
            rag_text += f"Content: {doc.page_content}\n"

            metadata_str = json.dumps(doc.metadata, indent=2, ensure_ascii=False)
            rag_text += f"Metadata: {metadata_str}\n\n"

        return rag_text
    except Exception as e:
        logging.error(f"An error occurred during the RAG query: {e}", exc_info=True)
        return f"An error occurred while querying the RAG system: {str(e)}"

if __name__ == "__main__":
    if PROJECT_ROOT_PATH not in sys.path:
        sys.path.append(PROJECT_ROOT_PATH)
        
    logging.info("Starting FastMCP server with stdio transport...")
    mcp.run(transport="stdio")
