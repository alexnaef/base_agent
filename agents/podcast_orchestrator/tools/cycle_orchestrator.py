"""
Research cycle orchestration tool.
"""
import sys
import os
from typing import Dict, Any

# Add parent directories to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../..'))

from shared.services import research_service, event_service
from shared.schemas import AgentEventCreate
from agents.services import ValidationService


class CycleOrchestratorTool:
    """Tool for orchestrating research cycles"""
    
    def __init__(self, agent):
        self.agent = agent
    
    def register(self, server):
        """Register tool with FastMCP server"""
        @server.tool(
            name="orchestrate_research_cycle",
            description="Coordinate a complete research cycle: planning → querying → scraping → validation",
        )
        def orchestrate_research_cycle(brief_id: int, cycle_type: str = "comprehensive") -> Dict[str, Any]:
            return self.execute(brief_id, cycle_type)
    
    def execute(self, brief_id: int, cycle_type: str = "comprehensive") -> Dict[str, Any]:
        """Orchestrate a multi-agent research cycle"""
        
        try:
            # Validate inputs
            brief_id = ValidationService.validate_brief_id(brief_id)
            cycle_type = ValidationService.validate_choice(
                cycle_type, "cycle_type", ["quick", "comprehensive", "targeted"]
            )
            
            brief = research_service.get_brief(brief_id)
            if not brief:
                return self.agent.create_error_response("Research brief not found")
            
            # Log cycle start
            self.agent.log_event(
                brief_id=brief_id,
                event_type="research_cycle_started",
                message=f"Starting {cycle_type} research cycle",
                payload={"cycle_type": cycle_type}
            )
            
            # Define cycle parameters based on type
            cycle_config = self.agent.config["cycle_configs"][cycle_type]
            
            # Return orchestration plan - actual execution would be handled by individual agents
            return self.agent.create_success_response(
                data={
                    "brief_id": brief_id,
                    "cycle_type": cycle_type,
                    "config": cycle_config,
                    "orchestration_plan": {
                        "phase_1": "Query formulation and planning",
                        "phase_2": f"Execute {cycle_config['queries']} search queries",
                        "phase_3": f"Scrape {cycle_config['queries'] * cycle_config['items_per_query']} research items",
                        "phase_4": "Fact-check and verify sources",
                        "phase_5": "Extract and validate claims"
                    },
                    "estimated_duration_min": 5 + (cycle_config['queries'] * 2),  # Rough estimate
                    "next_step": "Execute individual agent tasks in sequence"
                },
                message=f"Research cycle plan created. Ready to execute {cycle_type} research."
            )
            
        except Exception as e:
            return self.agent.create_error_response(str(e))