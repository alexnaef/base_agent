"""
Base agent class providing common functionality for all agents.
"""
import sys
import os
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional

# Add parent directories to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

from mcp.server.fastmcp.server import FastMCP
from shared.services import event_service
from shared.schemas import AgentEventCreate

from .openai_client import OpenAIManager
from .json_parser import JSONParser
from .config import AgentConfig
from .exceptions import AgentError


class BaseAgent(ABC):
    """Abstract base class for all agents"""
    
    def __init__(self, name: str, instructions: str):
        self.name = name
        self.instructions = instructions
        self.config = AgentConfig.get_agent_config(name)
        
        # Initialize OpenAI manager
        self.openai = OpenAIManager(name)
        
        # Initialize JSON parser
        self.json_parser = JSONParser()
        
        # Initialize FastMCP server
        self.server = FastMCP(name=name, instructions=instructions)
    
    def is_ready(self) -> bool:
        """Check if agent is ready to process requests"""
        return self.openai.is_available()
    
    def log_event(
        self, 
        brief_id: int, 
        event_type: str, 
        message: str, 
        payload: Optional[Dict[str, Any]] = None
    ):
        """Log an agent event"""
        try:
            event_service.log_event(AgentEventCreate(
                brief_id=brief_id,
                agent_name=self.name,
                event_type=event_type,
                message=message,
                payload=payload or {}
            ))
        except Exception as e:
            print(f"Warning: Failed to log event for {self.name}: {e}")
    
    def execute_prompt_with_parsing(
        self,
        system_prompt: str,
        user_prompt: str,
        expected_json_type: str = "auto",
        use_final_model: bool = False,
        **openai_kwargs
    ) -> Any:
        """
        Execute a prompt and parse the JSON response
        
        Args:
            system_prompt: System message content
            user_prompt: User message content  
            expected_json_type: "dict", "list", or "auto"
            use_final_model: Whether to use the final (higher quality) model
            **openai_kwargs: Additional OpenAI parameters
            
        Returns:
            Parsed JSON response
            
        Raises:
            AgentError: If prompt execution or parsing fails
        """
        if not self.is_ready():
            raise AgentError(f"{self.name}: OpenAI client not available")
        
        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            if use_final_model:
                response_text = self.openai.execute_final_prompt(messages, **openai_kwargs)
            else:
                response_text = self.openai.execute_tool_prompt(messages, **openai_kwargs)
            
            return self.json_parser.parse_response(response_text, expected_json_type)
            
        except Exception as e:
            raise AgentError(f"{self.name}: Prompt execution failed: {str(e)}")
    
    def create_error_response(self, error_message: str) -> Dict[str, Any]:
        """Create standardized error response"""
        return {
            "error": error_message,
            "agent": self.name,
            "message": f"{self.name} operation failed"
        }
    
    def create_success_response(
        self, 
        data: Dict[str, Any], 
        message: str
    ) -> Dict[str, Any]:
        """Create standardized success response"""
        return {
            "agent": self.name,
            "message": message,
            **data
        }
    
    @abstractmethod
    def get_tools(self) -> List[Any]:
        """Return list of tools this agent provides"""
        pass
    
    def register_tools(self):
        """Register all tools with the FastMCP server"""
        tools = self.get_tools()
        for tool in tools:
            if hasattr(tool, 'register'):
                tool.register(self.server)
    
    def run(self):
        """Start the agent server"""
        self.register_tools()
        self.server.run()