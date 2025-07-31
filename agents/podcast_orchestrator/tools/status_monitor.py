"""
Research status monitoring and phase management tool.
"""
import sys
import os
from typing import Dict, Any, List

# Add parent directories to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../..'))

from shared.services import research_service, event_service
from shared.models import ResearchStatus
from shared.schemas import AgentEventCreate
from agents.services import ValidationService


class StatusMonitorTool:
    """Tool for monitoring research status and managing phases"""
    
    def __init__(self, agent):
        self.agent = agent
    
    def register(self, server):
        """Register multiple tools with FastMCP server"""
        
        @server.tool(
            name="get_research_status",
            description="Get the current status and progress of a research brief",
        )
        def get_research_status(brief_id: int) -> Dict[str, Any]:
            return self.get_status(brief_id)
        
        @server.tool(
            name="advance_research_phase",
            description="Move research to the next phase based on current status and quality metrics",
        )
        def advance_research_phase(brief_id: int, force_advance: bool = False) -> Dict[str, Any]:
            return self.advance_phase(brief_id, force_advance)
    
    def get_status(self, brief_id: int) -> Dict[str, Any]:
        """Get comprehensive status of research brief"""
        
        try:
            # Validate inputs
            brief_id = ValidationService.validate_brief_id(brief_id)
            
            # Get the brief
            brief = research_service.get_brief(brief_id)
            if not brief:
                return self.agent.create_error_response("Research brief not found")
            
            # Get progress metrics
            progress = research_service.get_research_progress(brief_id)
            
            # Get recent events
            recent_events = event_service.get_events_for_brief(brief_id, limit=10)
            
            return self.agent.create_success_response(
                data={
                    "brief_id": brief_id,
                    "topic": brief['topic'],
                    "status": brief['status'],
                    "progress": progress,
                    "recent_events": [
                        {
                            "agent": event.agent_name,
                            "type": event.event_type,
                            "message": event.message,
                            "timestamp": event.created_at.isoformat()
                        } for event in recent_events[:5]  # Last 5 events
                    ],
                    "quality_metrics": {
                        "research_coverage": progress["completion_percentage"],
                        "items_verified": progress["verified_items"],
                        "claims_verified": progress["verified_claims"]
                    }
                },
                message=f"Retrieved status for research brief: {brief['topic']}"
            )
            
        except Exception as e:
            return self.agent.create_error_response(str(e))
    
    def advance_phase(self, brief_id: int, force_advance: bool = False) -> Dict[str, Any]:
        """Determine if research can advance to next phase and execute transition"""
        
        try:
            # Validate inputs
            brief_id = ValidationService.validate_brief_id(brief_id)
            
            brief = research_service.get_brief(brief_id)
            if not brief:
                return self.agent.create_error_response("Research brief not found")
            
            progress = research_service.get_research_progress(brief_id)
            current_status = brief['status']
            
            # Define phase advancement logic
            next_phase = None
            ready_to_advance = False
            requirements_met = []
            
            if current_status == ResearchStatus.PENDING:
                next_phase = ResearchStatus.IN_PROGRESS
                ready_to_advance = True
                requirements_met = ["Brief created and validated"]
                
            elif current_status == ResearchStatus.IN_PROGRESS:
                # Check if research quality meets standards for script generation
                completion_threshold = self.agent.config["completion_threshold"]
                min_verified_items = self.agent.config["min_verified_items"]
                
                if (progress["completion_percentage"] >= completion_threshold and 
                    progress["verified_items"] >= min_verified_items) or force_advance:
                    next_phase = ResearchStatus.COMPLETED
                    ready_to_advance = True
                    requirements_met = [
                        f"Query completion: {progress['completion_percentage']:.1f}%",
                        f"Verified items: {progress['verified_items']}",
                        f"Claims gathered: {progress['total_claims']}"
                    ]
                else:
                    requirements_met = [
                        f"Need {completion_threshold}% query completion (have {progress['completion_percentage']:.1f}%)",
                        f"Need {min_verified_items} verified items (have {progress['verified_items']})",
                        "Consider running more research cycles"
                    ]
            
            if ready_to_advance and next_phase:
                # Update brief status
                research_service.update_brief_status(brief_id, next_phase)
                
                # Log the phase change
                self.agent.log_event(
                    brief_id=brief_id,
                    event_type="phase_advanced",
                    message=f"Advanced from {current_status} to {next_phase}",
                    payload={
                        "old_status": current_status,
                        "new_status": next_phase,
                        "progress_metrics": progress
                    }
                )
                
                return self.agent.create_success_response(
                    data={
                        "brief_id": brief_id,
                        "phase_changed": True,
                        "old_phase": current_status,
                        "new_phase": next_phase,
                        "requirements_met": requirements_met,
                        "next_actions": self._get_next_actions(next_phase)
                    },
                    message=f"Successfully advanced to {next_phase}"
                )
            else:
                return self.agent.create_success_response(
                    data={
                        "brief_id": brief_id,
                        "phase_changed": False,
                        "current_phase": current_status,
                        "ready_to_advance": ready_to_advance,
                        "requirements_met": requirements_met
                    },
                    message="Research not ready to advance to next phase"
                )
                
        except Exception as e:
            return self.agent.create_error_response(str(e))
    
    def _get_next_actions(self, phase: str) -> List[str]:
        """Get recommended next actions for a given phase"""
        actions = {
            ResearchStatus.PENDING: [
                "Run clarification agent if needed",
                "Begin initial query formulation",
                "Start research cycle"
            ],
            ResearchStatus.IN_PROGRESS: [
                "Continue research cycles",
                "Monitor quality metrics",
                "Validate and verify sources"
            ],
            ResearchStatus.COMPLETED: [
                "Begin script generation",
                "Review and finalize manuscript", 
                "Prepare for delivery"
            ]
        }
        return actions.get(phase, ["No specific actions defined"])