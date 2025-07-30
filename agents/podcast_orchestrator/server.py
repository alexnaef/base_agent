import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

from typing import Dict, Any, List
import json
from datetime import datetime

from mcp.server.fastmcp.server import FastMCP
from shared.models import ResearchStatus
from shared.schemas import ResearchBriefCreate, AgentEventCreate
from shared.services import research_service, event_service

server = FastMCP(
    name="podcast-orchestrator",
    instructions="""
    This is the Podcast Orchestrator Agent - the master controller for the deep research podcast system.
    
    Key responsibilities:
    1. Create and manage research briefs from user queries
    2. Coordinate workflow between all specialized agents
    3. Monitor research progress and quality metrics
    4. Determine when research is complete and ready for script generation
    5. Provide status updates and manage the overall podcast generation process
    
    The orchestrator follows this workflow:
    1. User Query → Research Brief creation
    2. Clarification phase (if needed)
    3. Research execution coordination
    4. Quality validation
    5. Script generation coordination
    6. Final delivery
    """,
)

@server.tool(
    name="create_research_brief",
    description="Create a new research brief from a user query. This starts the podcast generation process.",
)
def create_research_brief(
    topic: str,
    angle: str = None,
    tone: str = "informative",
    target_length_min: int = 30,
    additional_instructions: str = None
) -> Dict[str, Any]:
    """Create a new research brief and return its details"""
    
    try:
        # Create the research brief
        brief_data = ResearchBriefCreate(
            topic=topic,
            angle=angle,
            tone=tone,
            target_length_min=target_length_min,
            additional_instructions=additional_instructions
        )
        
        brief = research_service.create_brief(brief_data)
        brief_id = brief['id'] if isinstance(brief, dict) else brief.id
        
        # Log the creation event
        event_service.log_event(AgentEventCreate(
            brief_id=brief_id,
            agent_name="podcast_orchestrator",
            event_type="brief_created",
            message=f"Created research brief for topic: {topic}",
            payload={
                "brief_id": brief_id,
                "topic": topic,
                "angle": angle,
                "tone": tone,
                "target_length_min": target_length_min
            }
        ))
        
        return {
            "brief_id": brief_id,
            "topic": topic,
            "status": "created",
            "message": f"Research brief created successfully. Ready to begin research on: {topic}",
            "next_steps": [
                "Run clarification if needed",
                "Begin initial research planning",
                "Execute multi-pass research cycle"
            ]
        }
        
    except Exception as e:
        return {
            "error": str(e),
            "message": "Failed to create research brief"
        }

@server.tool(
    name="get_research_status",
    description="Get the current status and progress of a research brief",
)
def get_research_status(brief_id: int) -> Dict[str, Any]:
    """Get comprehensive status of research brief"""
    
    try:
        # Get the brief
        brief = research_service.get_brief(brief_id)
        if not brief:
            return {"error": "Research brief not found"}
        
        # Get progress metrics
        progress = research_service.get_research_progress(brief_id)
        
        # Get recent events
        recent_events = event_service.get_events_for_brief(brief_id, limit=10)
        
        return {
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
        }
        
    except Exception as e:
        return {
            "error": str(e),
            "message": "Failed to get research status"
        }

@server.tool(
    name="advance_research_phase",
    description="Move research to the next phase based on current status and quality metrics",
)
def advance_research_phase(brief_id: int, force_advance: bool = False) -> Dict[str, Any]:
    """Determine if research can advance to next phase and execute transition"""
    
    try:
        brief = research_service.get_brief(brief_id)
        if not brief:
            return {"error": "Research brief not found"}
        
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
            completion_threshold = 80.0  # 80% of queries completed
            min_verified_items = 5  # At least 5 verified sources
            
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
            event_service.log_event(AgentEventCreate(
                brief_id=brief_id,
                agent_name="podcast_orchestrator",
                event_type="phase_advanced",
                message=f"Advanced from {current_status} to {next_phase}",
                payload={
                    "old_status": current_status,
                    "new_status": next_phase,
                    "progress_metrics": progress
                }
            ))
            
            return {
                "brief_id": brief_id,
                "phase_changed": True,
                "old_phase": current_status,
                "new_phase": next_phase,
                "requirements_met": requirements_met,
                "message": f"Successfully advanced to {next_phase}",
                "next_actions": get_next_actions(next_phase)
            }
        else:
            return {
                "brief_id": brief_id,
                "phase_changed": False,
                "current_phase": current_status,
                "ready_to_advance": ready_to_advance,
                "requirements_met": requirements_met,
                "message": "Research not ready to advance to next phase"
            }
            
    except Exception as e:
        return {
            "error": str(e),
            "message": "Failed to advance research phase"
        }

@server.tool(
    name="orchestrate_research_cycle",
    description="Coordinate a complete research cycle: planning → querying → scraping → validation",
)
def orchestrate_research_cycle(brief_id: int, cycle_type: str = "comprehensive") -> Dict[str, Any]:
    """Orchestrate a multi-agent research cycle"""
    
    try:
        brief = research_service.get_brief(brief_id)
        if not brief:
            return {"error": "Research brief not found"}
        
        # Log cycle start
        event_service.log_event(AgentEventCreate(
            brief_id=brief_id,
            agent_name="podcast_orchestrator",
            event_type="research_cycle_started",
            message=f"Starting {cycle_type} research cycle",
            payload={"cycle_type": cycle_type}
        ))
        
        # Define cycle parameters based on type
        cycle_config = {
            "quick": {"queries": 3, "items_per_query": 2, "depth": "surface"},
            "comprehensive": {"queries": 6, "items_per_query": 3, "depth": "deep"},
            "targeted": {"queries": 4, "items_per_query": 4, "depth": "focused"}
        }
        
        config = cycle_config.get(cycle_type, cycle_config["comprehensive"])
        
        # Return orchestration plan - actual execution would be handled by individual agents
        return {
            "brief_id": brief_id,
            "cycle_type": cycle_type,
            "config": config,
            "orchestration_plan": {
                "phase_1": "Query formulation and planning",
                "phase_2": f"Execute {config['queries']} search queries",
                "phase_3": f"Scrape {config['queries'] * config['items_per_query']} research items",
                "phase_4": "Fact-check and verify sources",
                "phase_5": "Extract and validate claims"
            },
            "estimated_duration_min": 5 + (config['queries'] * 2),  # Rough estimate
            "message": f"Research cycle plan created. Ready to execute {cycle_type} research.",
            "next_step": "Execute individual agent tasks in sequence"
        }
        
    except Exception as e:
        return {
            "error": str(e),
            "message": "Failed to orchestrate research cycle"
        }

def get_next_actions(phase: str) -> List[str]:
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

if __name__ == "__main__":
    server.run()