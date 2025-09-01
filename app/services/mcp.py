import asyncio
from contextlib import AsyncExitStack
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import nest_asyncio

# Apply nest_asyncio to allow nested event loops
nest_asyncio.apply()

class MCPClient:
    def __init__(self, server_script_path: str = "server.py", debug_logging: bool = False):
        self.server_script_path = server_script_path
        self.debug_logging = debug_logging
        self.session = None
        self.exit_stack = AsyncExitStack()
        self.stdio = None
        self.write = None

    async def connect(self):
        try:
            server_params = StdioServerParameters(
                command="python",
                args=[self.server_script_path],
            )
            stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
            self.stdio, self.write = stdio_transport
            self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))
            await self.session.initialize()
            
        except Exception as e:
            print(f"⚠️ Failed to connect to MCP server: {str(e)}")
            raise

    async def get_knowledge_base(self) -> str:
        try:
            if not self.session:
                await self.connect()
            result = await self.session.call_tool("get_knowledge_base", arguments={})
            return result.content[0].text if result.content else "No knowledge base data available."
        except Exception as e:
            print(f"⚠️ MCP error: {str(e)}")
            return "Error: Could not retrieve knowledge base."

    async def search_knowledge_base(self, query: str) -> str:
        """Memanggil tool search_knowledge_base di server MCP."""
        try:
            if not self.session: await self.connect()
            result = await self.session.call_tool(
                "search_knowledge_base", 
                arguments={"query": query}
            )
            return result.content[0].text if result.content else "Tidak ada konteks relevan ditemukan."
        except Exception as e:
            print(f"⚠️ Error MCP saat pencarian: {str(e)}")
            return "Error: Gagal mencari di knowledge base."
            
    async def cleanup(self):
        await self.exit_stack.aclose()