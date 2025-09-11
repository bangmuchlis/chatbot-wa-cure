import os
import sys
import json
import logging
from mcp.server.fastmcp import FastMCP

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

mcp = FastMCP(name="QA_Server")

@mcp.tool()
def get_knowledge_base() -> str:
    """
    Reads a JSON file from a predefined path and formats its content into a readable string.

    This tool expects the JSON file to be a list of question-answer dictionaries.
    If the format is different, it will fall back to a raw JSON dump.

    Returns:
        A formatted string containing the knowledge base content, or an error message.
    """
    try:
        kb_path = os.path.join(os.path.dirname(__file__), "..", "data", "json", "data.json")
        logging.info(f"Attempting to read knowledge base from: {kb_path}")
        
        with open(kb_path, "r", encoding="utf-8") as f:
            kb_data = json.load(f)

        kb_text = "The following knowledge base was found:\n\n"

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
            kb_text += f"Knowledge base content: {json.dumps(kb_data, indent=2, ensure_ascii=False)}\n\n"

        return kb_text
        
    except FileNotFoundError:
        logging.error(f"Knowledge base file not found at path: {kb_path}")
        return "Error: The knowledge base file was not found."
    except json.JSONDecodeError:
        logging.error("Failed to decode JSON from the knowledge base file.")
        return "Error: The JSON format in the knowledge base file is invalid."
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}", exc_info=True)
        return f"Error: An unexpected error occurred - {str(e)}"

if __name__ == "__main__":
    logging.info("Starting FastMCP server with stdio transport...")
    mcp.run(transport="stdio")
