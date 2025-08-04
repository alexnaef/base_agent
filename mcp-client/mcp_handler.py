import sys
from typing import Optional, List, Dict
from contextlib import AsyncExitStack
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

class MCPHandler:
    def __init__(self):
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.stdio = None
        self.write = None

    async def connect_to_server(self, server_script_path: str):
        """Connect to an MCP server"""
        command = self._get_command_for_script(server_script_path)
        
        server_params = StdioServerParameters(
            command=command,
            args=[server_script_path],
            env=None
        )
        
        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        self.stdio, self.write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))
        
        await self.session.initialize()
        
        response = await self.session.list_tools()
        tools = response.tools
        print("\nConnected to server with tools:", [tool.name for tool in tools])

    def _get_command_for_script(self, server_script_path: str) -> str:
        """Determine the command to run based on script extension"""
        is_python = server_script_path.endswith('.py')
        is_js = server_script_path.endswith('.js')
        
        if not (is_python or is_js):
            raise ValueError("Server script must be a .py or .js file")
            
        return sys.executable if is_python else "node"

    async def get_available_tools(self) -> List[Dict]:
        """Get list of available tools with their schemas"""
        if not self.session:
            raise RuntimeError("Not connected to any server")
            
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
        
        return available_tools

    async def call_tool(self, tool_name: str, args: Dict):
        """Call an MCP tool and return the result"""
        if not self.session:
            raise RuntimeError("Not connected to any server")
            
        tool_result = await self.session.call_tool(tool_name, args)
        return "".join(c.text for c in tool_result.content if hasattr(c, "text"))

    async def cleanup(self):
        """Clean up resources"""
        await self.exit_stack.aclose()