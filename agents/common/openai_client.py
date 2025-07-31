"""
Centralized OpenAI client management for all agents.
"""
import os
from typing import Optional, Dict, Any, List
from openai import OpenAI
from dotenv import load_dotenv

from .config import AgentConfig
from .exceptions import OpenAIError


class OpenAIManager:
    """Manages OpenAI client initialization and common operations"""
    
    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self.client: Optional[OpenAI] = None
        self.available = False
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize OpenAI client with proper error handling"""
        # Load environment variables
        load_dotenv(dotenv_path="../../.env", override=True)
        load_dotenv(override=True)
        
        try:
            api_key = os.getenv("OPENAI_API_KEY")
            if api_key:
                self.client = OpenAI(api_key=api_key)
                self.available = True
                print(f"✅ {self.agent_name}: OpenAI client initialized")
            else:
                print(f"❌ {self.agent_name}: OPENAI_API_KEY not found in environment")
                self.available = False
        except Exception as e:
            print(f"❌ {self.agent_name}: OpenAI client initialization failed: {e}")
            self.available = False
    
    def is_available(self) -> bool:
        """Check if OpenAI client is available"""
        return self.available
    
    def execute_prompt(
        self,
        messages: List[Dict[str, str]], 
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        **kwargs
    ) -> str:
        """Execute a prompt with the OpenAI client"""
        if not self.available:
            raise OpenAIError("OpenAI client not available")
        
        # Use default model if not specified
        if model is None:
            model = AgentConfig.OPENAI_TOOL_MODEL
        
        # Use default temperature if not specified
        if temperature is None:
            temperature = AgentConfig.DEFAULT_TEMPERATURE
        
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                **kwargs
            )
            return response.choices[0].message.content
        except Exception as e:
            raise OpenAIError(f"OpenAI API call failed: {str(e)}")
    
    def execute_tool_prompt(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """Execute a prompt using the tool model (cheaper, faster)"""
        return self.execute_prompt(
            messages=messages,
            model=AgentConfig.OPENAI_TOOL_MODEL,
            temperature=AgentConfig.DEFAULT_TEMPERATURE,
            **kwargs
        )
    
    def execute_final_prompt(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """Execute a prompt using the final model (higher quality)"""
        return self.execute_prompt(
            messages=messages,
            model=AgentConfig.OPENAI_FINAL_MODEL,
            temperature=AgentConfig.HIGH_TEMPERATURE,
            **kwargs
        )