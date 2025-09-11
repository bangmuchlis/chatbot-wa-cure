# test_mcp.py
from langchain_mcp_adapters.client import MultiServerMCPClient
from pathlib import Path
import asyncio
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    BASE_DIR = Path(__file__).resolve().parent
    QA_SERVER = str(BASE_DIR / "servers" / "qa_server.py")
    RAG_SERVER = str(BASE_DIR / "servers" / "rag_server.py")

    client = MultiServerMCPClient({
        "knowledge": {"command": "python", "args": [QA_SERVER], "transport": "stdio"},
        "rag": {"command": "python", "args": [RAG_SERVER], "transport": "stdio"}
    })
    tools = await client.get_tools()
    logger.info(f"Tools loaded: {', '.join(t.name for t in tools)}")
    
    # Tes rag_query
    rag_tool = next(t for t in tools if t.name == "rag_query")
    result = await rag_tool.ainvoke({"query": "apa visi dari bgm advertising?"})
    logger.info(f"RAG Output: {result}")
    print("RAG Output:", result)
    
    # Tes get_knowledge_base
    kb_tool = next(t for t in tools if t.name == "get_knowledge_base")
    result = await kb_tool.ainvoke({"query": "visi bgm advertising"})
    logger.info(f"KB Output: {result}")
    print("KB Output:", result)

asyncio.run(main())