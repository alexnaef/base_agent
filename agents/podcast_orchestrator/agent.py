"""
Podcast Orchestrator Agent - core business logic.
"""
import sys
import os
from typing import List, Any

# Add parent directories to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

from agents.common import BaseAgent
from config import AGENT_INSTRUCTIONS
from tools import BriefManagerTool, StatusMonitorTool, CycleOrchestratorTool


class PodcastOrchestratorAgent(BaseAgent):
    """Agent specialized in orchestrating the entire podcast generation workflow"""
    
    def __init__(self):
        super().__init__(
            name="podcast-orchestrator",
            instructions=AGENT_INSTRUCTIONS
        )
        
        # Initialize tools
        self.brief_manager_tool = BriefManagerTool(self)
        self.status_monitor_tool = StatusMonitorTool(self)
        self.cycle_orchestrator_tool = CycleOrchestratorTool(self)
    
    def get_tools(self) -> List[Any]:
        """Return list of tools this agent provides"""
        return [
            self.brief_manager_tool,
            self.status_monitor_tool,
            self.cycle_orchestrator_tool
        ]