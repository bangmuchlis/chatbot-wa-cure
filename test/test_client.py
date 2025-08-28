import asyncio
import json
from contextlib import AsyncExitStack
from typing import Any, Dict, List
import aiohttp
import nest_asyncio
from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Apply nest_asyncio to allow nested event loops (needed for Jupyter/IPython)
nest_asyncio.apply()

# Load environment variables
load_dotenv("../.env")

# Global variables to store session state
session = None
exit_stack = AsyncExitStack()
ollama_base_url = "http://localhost:11434"  # Default Ollama URL
model = "llama3.2"  # Example Ollama model (adjust as needed)
stdio = None
write = None

class OllamaClient:
    """Simple async client for Ollama API."""
    
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url
    
    async def chat_completions_create(self, model: str, messages: List[Dict],
                                      tools: List[Dict] = None, tool_choice: str = "auto"):
        """Create chat completion with Ollama."""
        async with aiohttp.ClientSession() as session:
            # Prepare the request payload
            payload = {
                "model": model,
                "messages": messages,
                "stream": False,
                "format": "json" if tools else None
            }
            
            # Add tool information to system message if tools are available
            if tools and tool_choice != "none":
                tool_descriptions = []
                for tool in tools:
                    func_info = tool["function"]
                    tool_desc = f"- {func_info['name']}: {func_info['description']}"
                    if "parameters" in func_info:
                        tool_desc += f"\n  Parameters: {json.dumps(func_info['parameters'])}"
                    tool_descriptions.append(tool_desc)
                
                system_message = {
                    "role": "system",
                    "content": f"""You are a helpful assistant with access to the following tools:

{chr(10).join(tool_descriptions)}

When you need to use a tool, respond with JSON in this format:
{{
    "tool_calls": [
        {{
            "id": "call_1",
            "function": {{
                "name": "tool_name",
                "arguments": "{{\"param\": \"value\"}}"
            }}
        }}
    ]
}}

If you don't need to use any tools, respond normally."""
                }
                
                # Insert system message at the beginning
                if messages and messages[0]["role"] == "system":
                    messages[0]["content"] = system_message["content"]
                else:
                    messages.insert(0, system_message)
            
            async with session.post(f"{self.base_url}/api/chat", json=payload) as response:
                if response.status != 200:
                    raise Exception(f"Ollama API error: {response.status}")
                
                result = await response.json()
                content = result["message"]["content"]
                
                # Try to parse as JSON for tool calls
                if tools and tool_choice != "none":
                    try:
                        parsed_content = json.loads(content)
                        if "tool_calls" in parsed_content:
                            # Create a mock response similar to OpenAI format
                            return type('Response', (), {
                                'choices': [type('Choice', (), {
                                    'message': type('Message', (), {
                                        'content': None,
                                        'tool_calls': [
                                            type('ToolCall', (), {
                                                'id': tc["id"],
                                                'function': type('Function', (), {
                                                    'name': tc["function"]["name"],
                                                    'arguments': tc["function"]["arguments"]
                                                })()
                                            })() for tc in parsed_content["tool_calls"]
                                        ]
                                    })()
                                })()]
                            })()
                    except (json.JSONDecodeError, KeyError):
                        pass
                
                # Regular response
                return type('Response', (), {
                    'choices': [type('Choice', (), {
                        'message': type('Message', (), {
                            'content': content,
                            'tool_calls': None
                        })()
                    })()]
                })()

ollama_client = OllamaClient(ollama_base_url)

async def connect_to_server(server_script_path: str = "server.py"):
    """Connect to an MCP server.

    Args:
        server_script_path: Path to the server script.
    """
    global session, stdio, write, exit_stack

    # Server configuration
    server_params = StdioServerParameters(
        command="python",
        args=[server_script_path],
    )

    # Connect to the server
    stdio_transport = await exit_stack.enter_async_context(stdio_client(server_params))
    stdio, write = stdio_transport
    session = await exit_stack.enter_async_context(ClientSession(stdio, write))

    # Initialize the connection
    await session.initialize()

    # List available tools
    tools_result = await session.list_tools()
    print("\nConnected to server with tools:")
    for tool in tools_result.tools:
        print(f"  - {tool.name}: {tool.description}")

async def get_mcp_tools() -> List[Dict[str, Any]]:
    """Get available tools from the MCP server in Ollama-compatible format.

    Returns:
        A list of tools in Ollama-compatible format.
    """
    global session

    tools_result = await session.list_tools()
    return [
        {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.inputSchema,
            },
        }
        for tool in tools_result.tools
    ]

async def process_query(query: str) -> str:
    """Process a query using Ollama and available MCP tools.

    Args:
        query: The user query.

    Returns:
        The response from Ollama.
    """
    global session, ollama_client, model

    # Get available tools
    tools = await get_mcp_tools()

    # Initial Ollama API call
    response = await ollama_client.chat_completions_create(
        model=model,
        messages=[{"role": "user", "content": query}],
        tools=tools,
        tool_choice="auto",
    )

    # Get assistant's response
    assistant_message = response.choices[0].message

    # Initialize conversation with user query and assistant response
    messages = [
        {"role": "user", "content": query},
    ]
    
    # Add assistant message to conversation
    if assistant_message.content:
        messages.append({"role": "assistant", "content": assistant_message.content})
    else:
        messages.append({"role": "assistant", "content": "Using tools to help answer your question."})

    # Handle tool calls if present
    if assistant_message.tool_calls:
        # Process each tool call
        for tool_call in assistant_message.tool_calls:
            try:
                # Execute tool call
                result = await session.call_tool(
                    tool_call.function.name,
                    arguments=json.loads(tool_call.function.arguments),
                )

                # Add tool response to conversation
                tool_result = result.content[0].text if result.content else "Tool executed successfully"
                messages.append(
                    {
                        "role": "user",  # Ollama treats tool results as user messages
                        "content": f"Tool '{tool_call.function.name}' result: {tool_result}. Please provide a comprehensive answer based on this information.",
                    }
                )
            except Exception as e:
                messages.append(
                    {
                        "role": "user",
                        "content": f"Tool '{tool_call.function.name}' failed with error: {str(e)}. Please provide an alternative answer.",
                    }
                )

        # Get final response from Ollama with tool results
        final_response = await ollama_client.chat_completions_create(
            model=model,
            messages=messages,
            tools=None,  # Don't provide tools for final response
            tool_choice="none",  # Don't allow more tool calls
        )

        return final_response.choices[0].message.content

    # No tool calls, just return the direct response
    return assistant_message.content

async def cleanup():
    """Clean up resources."""
    global exit_stack
    await exit_stack.aclose()

async def main():
    """Main entry point for the client."""
    await connect_to_server("server.py")

    # Example: Ask about company vacation policy
    query = "Bagaimana cara bermain layang-layang?"
    print(f"\nQuery: {query}")

    response = await process_query(query)
    print(f"\nResponse: {response}")

    await cleanup()

if __name__ == "__main__":
    asyncio.run(main())