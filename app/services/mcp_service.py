from pathlib import Path
from langchain_mcp_adapters.client import MultiServerMCPClient

async def init_mcp_client(base_dir: Path) -> tuple[MultiServerMCPClient, str]:
    project_root = base_dir.parent

    QA_SERVER = str(project_root / "servers" / "qa_server.py")
    VECTORDB_SERVER = str(project_root / "servers" / "vectordb_server.py")

    client = MultiServerMCPClient({
        "qa": {
            "command": "python", 
            "args": [QA_SERVER], 
            "transport": "stdio"
            },
        "vectordb": {
            "command": "python", 
            "args": [VECTORDB_SERVER], 
            "transport": "stdio"},
    })

    tools = await client.get_tools()
    tool_names = ", ".join([t.name for t in tools])

    return client, tool_names
 