import os
import sys
import json
from mcp.server.fastmcp import FastMCP

mcp = FastMCP(name="Knowledge Base")

@mcp.tool()
def get_knowledge_base() -> str:
    try:
        kb_path = os.path.join(os.path.dirname(__file__), "..", "data", "json", "data.json")
        with open(kb_path, "r", encoding="utf-8") as f:
            kb_data = json.load(f)

        kb_text = "Berikut adalah knowledge base yang ditemukan:\n\n"

        if isinstance(kb_data, list):
            for i, item in enumerate(kb_data, 1):
                if isinstance(item, dict):
                    question = item.get("question", "Pertanyaan tidak diketahui")
                    answer = item.get("answer", "Jawaban tidak diketahui")
                else:
                    question = f"Item {i}"
                    answer = str(item)

                kb_text += f"T{i}: {question}\n"
                kb_text += f"J{i}: {answer}\n\n"
        else:
            kb_text += f"Isi knowledge base: {json.dumps(kb_data, indent=2, ensure_ascii=False)}\n\n"

        return kb_text
    except FileNotFoundError:
        return "Error: File knowledge base tidak ditemukan."
    except json.JSONDecodeError:
        return "Error: Format JSON di file knowledge base tidak valid."
    except Exception as e:
        return f"Error: Terjadi kesalahan - {str(e)}"

if __name__ == "__main__":
    mcp.run(transport="stdio")

