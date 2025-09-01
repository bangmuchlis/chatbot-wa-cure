import os
import sys
import json
from mcp.server.fastmcp import FastMCP
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
from app.utils.chroma_utils import get_chroma_collection

mcp = FastMCP(
    name="Knowledge Base",
    host="0.0.0.0",
    port=8050, 
)

@mcp.tool()
def get_knowledge_base() -> str:
    try:
        kb_path = os.path.join(os.path.dirname(__file__), "data", "data.json")
        with open(kb_path, "r") as f:
            kb_data = json.load(f)

        kb_text = "Here is the retrieved knowledge base:\n\n"

        if isinstance(kb_data, list):
            for i, item in enumerate(kb_data, 1):
                if isinstance(item, dict):
                    question = item.get("question", "Unknown question")
                    answer = item.get("answer", "Unknown answer")
                else:
                    question = f"Item {i}"
                    answer = str(item)

                kb_text += f"Q{i}: {question}\n"
                kb_text += f"A{i}: {answer}\n\n"
        else:
            kb_text += f"Knowledge base content: {json.dumps(kb_data, indent=2)}\n\n"

        return kb_text
    except FileNotFoundError:
        return "Error: Knowledge base file not found"
    except json.JSONDecodeError:
        return "Error: Invalid JSON in knowledge base file"
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
def search_knowledge_base(query: str) -> str:
    try:
        collection = get_chroma_collection()
        
        # Lakukan pencarian di ChromaDB. Ambil 3 hasil teratas.
        results = collection.query(query_texts=[query], n_results=3)

        documents = results.get('documents')
        if not documents or not documents[0]:
            return "Tidak ada informasi yang ditemukan di knowledge base."

        # Format hasil pencarian menjadi satu string konteks
        context = "Berdasarkan knowledge base, berikut informasi yang relevan:\n\n"
        for i, doc in enumerate(documents[0], 1):
            context += f"--- Konteks Relevan {i} ---\n{doc}\n\n"
            
        return context.strip()
    except Exception as e:
        print(f"Error saat mencari di ChromaDB: {e}")
        return f"Error: Terjadi kesalahan saat mencari di knowledge base."
    
if __name__ == "__main__":
    mcp.run(transport="stdio")