import asyncio
import sys
from config import validate_api_key, MAX_LOOPS
from mcp_handler import MCPHandler
from openai_handler import OpenAIHandler

validate_api_key()

class MCPClient:
    def __init__(self):
        self.mcp_handler = MCPHandler()
        self.openai_handler = OpenAIHandler()

    async def connect_to_server(self, server_script_path: str):
        """Connect to an MCP server"""
        await self.mcp_handler.connect_to_server(server_script_path)

    async def process_query(self, query: str) -> str:
        """Process a query using tool planning and final response generation"""
        messages = [{"role": "user", "content": query}]
        available_tools = await self.mcp_handler.get_available_tools()
        
        loop_counter = 0
        while loop_counter < MAX_LOOPS:
            loop_counter += 1
            
            assistant_message, tool_calls = self.openai_handler.process_tool_planning(messages, available_tools)
            
            if assistant_message:
                messages.append({"role": "assistant", "content": assistant_message})
                print("\n" + assistant_message)

            if not tool_calls:
                break

            await self._execute_tool_calls(tool_calls, messages)

        return self.openai_handler.generate_final_response(messages, available_tools)

    async def _execute_tool_calls(self, tool_calls, messages):
        """Execute tool calls and update message history"""
        for call_event in tool_calls:
            args = self.openai_handler.parse_tool_arguments(call_event.arguments)
            
            tool_output_text = await self.mcp_handler.call_tool(call_event.name, args)
            
            print(f"[Calling tool {call_event.name} with args {args}]")
            
            messages.extend([
                {
                    "type": "function_call",
                    "name": call_event.name,
                    "arguments": call_event.arguments,
                    "call_id": call_event.call_id,
                },
                {
                    "type": "function_call_output",
                    "call_id": call_event.call_id,
                    "output": tool_output_text,
                }
            ])

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
        await self.mcp_handler.cleanup()

async def main():
    if len(sys.argv) < 2:
        print("Usage: python client.py <path_to_server_script>")
        sys.exit(1)
        
    client = MCPClient()
    try:
        await client.connect_to_server(sys.argv[1])
        await client.chat_loop()
    except KeyboardInterrupt:
        print("\nShutting down...")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
    finally:
        await client.cleanup()

if __name__ == "__main__":
    asyncio.run(main())