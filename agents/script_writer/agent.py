"""
Script Writer Agent - core business logic.
"""
import sys
import os
from typing import List, Any

# Add parent directories to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

from agents.common import BaseAgent
from config import AGENT_INSTRUCTIONS
from tools import OutlineCreatorTool, ScriptWriterTool, CompleteGeneratorTool


class ScriptWriterAgent(BaseAgent):
    """Agent specialized in podcast script writing and content creation"""
    
    def __init__(self):
        super().__init__(
            name="script-writer",
            instructions=AGENT_INSTRUCTIONS
        )
        
        # Initialize tools
        self.outline_creator_tool = OutlineCreatorTool(self)
        self.script_writer_tool = ScriptWriterTool(self)
        self.complete_generator_tool = CompleteGeneratorTool(self)
    
    def get_tools(self) -> List[Any]:
        """Return list of tools this agent provides"""
        return [
            self.outline_creator_tool,
            self.script_writer_tool,
            self.complete_generator_tool
        ]