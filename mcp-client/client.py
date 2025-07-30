import asyncio
from typing import Optional
from contextlib import AsyncExitStack
import os

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from openai import OpenAI
import json
import sys
from dotenv import load_dotenv
from sys_prompt import SYSTEM_PROMPT

load_dotenv(dotenv_path="../.env", override=True)

# ---------------------------------------------------------------------------
# Model configuration
# ---------------------------------------------------------------------------
TOOL_MODEL = os.getenv("OPENAI_TOOL_MODEL", "gpt-4.1-mini")  # cheaper model for planning/tool calls
FINAL_MODEL = os.getenv("OPENAI_FINAL_MODEL", "gpt-4.1")     # higher-quality model for final answer
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Debug: Print first few characters of API key to verify it's loaded
if OPENAI_API_KEY:
    print(f"API key loaded")
else:
    print("WARNING: No OPENAI_API_KEY found in environment variables")

class MCPClient:
    def __init__(self):
        # Initialize session and client objects
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.openai_client = OpenAI(api_key=OPENAI_API_KEY)

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
        """Process a query by repeatedly chatting with the LLM and executing tool calls
        until the model returns a normal assistant message with **no** function calls.
        """
        # Prepare conversation messages
        messages = [{"role": "user", "content": query}]

        # Build tool schema list once
        tool_list_response = await self.session.list_tools()
        available_tools = []
        for tool in tool_list_response.tools:
            schema = dict(tool.inputSchema)
            schema["additionalProperties"] = False
            if "properties" in schema:
                schema["required"] = list(schema["properties"].keys())
            available_tools.append({
                "type": "function",
                "name": tool.name,
                "description": tool.description,
                "parameters": schema,
                "strict": True,
            })

        final_chunks: list[str] = []
        max_loops = 25  # generous cap to allow multi-step plans
        loop_counter = 0
        while loop_counter < max_loops:
            loop_counter += 1
            
            llm_response = self.openai_client.responses.create(
                model=TOOL_MODEL,
                instructions=SYSTEM_PROMPT,
                input=messages,
                tools=available_tools,
                tool_choice="auto",
            )

            tool_calls = []
            assistant_message_buffer = ""

            # Parse streaming events
            for event in llm_response.output:
                if event.type == "message":
                    # Stream any output_text pieces in real time
                    for item in event.content:
                        if getattr(item, "type", None) == "output_text":
                            text_piece = item.text
                            print(text_piece, end="", flush=True)
                            assistant_message_buffer += text_piece
                elif event.type == "function_call":
                    tool_calls.append(event)

            # Ensure a newline after streaming the assistant message when the chunk finishes
            if assistant_message_buffer:
                print("", flush=True)

            # Append assistant's textual part (if any)
            if assistant_message_buffer.strip():
                final_chunks.append(assistant_message_buffer.strip())
                messages.append({"role": "assistant", "content": assistant_message_buffer.strip()})
                # Stream progress to the terminal for the user
                print("\n" + assistant_message_buffer.strip())

            # If no tool calls were requested, we're done
            if not tool_calls:
                break  # Exit while loop

            # Execute each tool call sequentially
            for call_event in tool_calls:
                try:
                    args = json.loads(call_event.arguments)
                except json.JSONDecodeError:
                    args = {}

                # Call the MCP tool
                tool_result = await self.session.call_tool(call_event.name, args)

                # For transparency in terminal, show that we called it
                final_chunks.append(f"[Calling tool {call_event.name} with args {args}]")
                print(f"[Calling tool {call_event.name} with args {args}]")

                # Add function_call message for the LLM context
                messages.append({
                    "type": "function_call",
                    "name": call_event.name,
                    "arguments": call_event.arguments,
                    "call_id": call_event.call_id,
                })

                # Convert tool result content to plain text
                tool_output_text = "".join(
                    c.text for c in tool_result.content if hasattr(c, "text")
                )

                messages.append({
                    "type": "function_call_output",
                    "call_id": call_event.call_id,
                    "output": tool_output_text,
                })

        # After tool loop, craft the final, high-quality answer using FINAL_MODEL
        final_answer_buffer = ""
        final_response = self.openai_client.responses.create(
            model=FINAL_MODEL,
            instructions=SYSTEM_PROMPT + "\n(The tools have already been executed and their outputs provided. Summarize the findings comprehensively without calling any more tools.)",
            input=messages,
            tools=available_tools,
            tool_choice="none",  # disable further tool use
        )

        for event in final_response.output:
            if event.type == "message":
                for item in event.content:
                    if getattr(item, "type", None) == "output_text":
                        text_piece = item.text
                        print(text_piece, end="", flush=True)
                        final_answer_buffer += text_piece

        print("", flush=True)  # ensure newline

        return final_answer_buffer.strip()

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