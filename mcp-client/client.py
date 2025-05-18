import asyncio
from typing import Optional
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from openai import OpenAI
import json
import sys
from dotenv import load_dotenv

load_dotenv()  # load environment variables from .env

class MCPClient:
    def __init__(self):
        # Initialize session and client objects
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.openai_client = OpenAI()

    async def connect_to_server(self, server_script_path: str):
        """Connect to an MCP server
        
        Args:
            server_script_path: Path to the server script (.py or .js)
        """
        is_python = server_script_path.endswith('.py')
        is_js = server_script_path.endswith('.js')
        if not (is_python or is_js):
            raise ValueError("Server script must be a .py or .js file")
            
        command = sys.executable if is_python else "node"
        server_params = StdioServerParameters(
            command=command,
            args=[server_script_path],
            env=None
        )
        
        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        self.stdio, self.write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))
        
        await self.session.initialize()
        
        # List available tools
        response = await self.session.list_tools()
        tools = response.tools
        print("\nConnected to server with tools:", [tool.name for tool in tools])

    async def process_query(self, query: str) -> str:
        """Process a query using Claude and available tools"""
        # Prepare messages for OpenAI
        messages = [
            {"role": "user", "content": query}
        ]

        response = await self.session.list_tools()
        available_tools = [
            {"name": tool.name, "description": tool.description, "parameters": tool.inputSchema}
            for tool in response.tools
        ]

        # Initial OpenAI ChatCompletion call with function calling
        response = self.openai_client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            functions=available_tools,
            function_call="auto",
        )

        # Process OpenAI response and handle function calls
        final_text = []
        msg = response.choices[0].message
        # Append text if present
        if msg.content:
            final_text.append(msg.content)
        # Handle function call
        if hasattr(msg, "function_call") and msg.function_call:
            tool_name = msg.function_call.name
            tool_args = json.loads(msg.function_call.arguments)
            # Execute tool call
            result = await self.session.call_tool(tool_name, tool_args)
            final_text.append(f"[Calling tool {tool_name} with args {tool_args}]")
            # Add assistant function_call message and function response
            messages.append({
                "role": "assistant",
                "content": None,
                "function_call": {"name": tool_name, "arguments": msg.function_call.arguments}
            })
            messages.append({
                "role": "function",
                "name": tool_name,
                "content": result.content
            })
            # Second OpenAI call with function result
            response2 = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
            )
            final_text.append(response2.choices[0].message.content)
        return "\n".join(final_text)

    async def chat_loop(self):
        """Run an interactive chat loop"""
        print("\nMCP Client Started!")
        print("Type your queries or 'quit' to exit.")
        
        while True:
            try:
                query = input("\nQuery: ").strip()
                
                if query.lower() == 'quit':
                    break
                    
                response = await self.process_query(query)
                print("\n" + response)
                    
            except Exception as e:
                print(f"\nError: {str(e)}")
    
    async def cleanup(self):
        """Clean up resources"""
        await self.exit_stack.aclose()

async def main():
    if len(sys.argv) < 2:
        print("Usage: python client.py <path_to_server_script>")
        sys.exit(1)
        
    client = MCPClient()
    try:
        await client.connect_to_server(sys.argv[1])
        await client.chat_loop()
    finally:
        await client.cleanup()

if __name__ == "__main__":
    asyncio.run(main())