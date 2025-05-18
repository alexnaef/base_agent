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
        messages = [{"role": "user", "content": query}]

        response = await self.session.list_tools()
        available_tools = []
        for tool in response.tools:
            # Ensure additionalProperties is set to False in the schema
            params = dict(tool.inputSchema)
            params["additionalProperties"] = False
            available_tools.append({
                "type": "function",
                "name": tool.name,
                "description": tool.description,
                "parameters": params,
                "strict": True
            })

        # Initial OpenAI Responses call with function calling
        response = self.openai_client.responses.create(
            model="o4-mini",
            instructions=(
                "When the user asks for weather alerts, call the get_alerts function with the two-letter state code. "
                "When the user asks for a weather forecast, call the get_forecast function with latitude and longitude. "
                "Otherwise, respond to the user normally without calling any function."),
            input=messages,
            tools=available_tools,
            tool_choice="auto"
        )

        # Process Responses API output and handle function calls
        final_text = []
        tool_call_event = None
        # Iterate over output events
        for event in response.output:
            if event.type == 'message':
                # Aggregate output_text content
                text_output = ''.join(
                    item.text for item in event.content if item.type == 'output_text'
                )
                if text_output:
                    final_text.append(text_output)
                    messages.append({"role": "assistant", "content": text_output})
            elif event.type == 'function_call':
                tool_call_event = event
        # If model called a function, execute it and call again
        if tool_call_event:
            # Extract call details
            call_args = json.loads(tool_call_event.arguments)
            # Execute MCP tool
            result = await self.session.call_tool(tool_call_event.name, call_args)
            final_text.append(f"[Calling tool {tool_call_event.name} with args {call_args}]")
            # Append the function call event to messages
            messages.append({
                "type": "function_call",
                "name": tool_call_event.name,
                "arguments": tool_call_event.arguments,
                "call_id": tool_call_event.call_id
            })
            # Extract text from the tool result and append as function_call_output
            tool_output = ''.join(
                content.text for content in result.content if hasattr(content, 'text')
            )
            messages.append({
                "type": "function_call_output",
                "call_id": tool_call_event.call_id,
                "output": tool_output
            })
            # Follow-up with function response
            response2 = self.openai_client.responses.create(
                model='o4-mini',
                input=messages,
                tools=available_tools
            )
            final_text.append(response2.output_text)
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