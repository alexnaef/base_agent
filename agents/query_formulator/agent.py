"""
Query Formulator Agent - core business logic.
"""
import sys
import os
from typing import List, Any

# Add parent directories to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

from agents.common import BaseAgent
from config import AGENT_INSTRUCTIONS
from tools import QueryGeneratorTool, QueryRefinerTool, QueryAnalyzerTool


class QueryFormulatorAgent(BaseAgent):
    """Agent specialized in generating and refining search queries"""
    
    def __init__(self):
        super().__init__(
            name="query-formulator",
            instructions=AGENT_INSTRUCTIONS
        )
        
        # Initialize tools
        self.generator_tool = QueryGeneratorTool(self)
        self.refiner_tool = QueryRefinerTool(self)
        self.analyzer_tool = QueryAnalyzerTool(self)
    
    def get_tools(self) -> List[Any]:
        """Return list of tools this agent provides"""
        return [
            self.generator_tool,
            self.refiner_tool,
            self.analyzer_tool
        ]