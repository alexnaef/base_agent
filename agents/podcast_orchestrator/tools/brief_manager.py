"""
Research brief management tool.
"""
import sys
import os
from typing import Dict, Any

# Add parent directories to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../..'))

from shared.services import research_service, event_service
from shared.schemas import ResearchBriefCreate, AgentEventCreate
from agents.services import ValidationService


class BriefManagerTool:
    """Tool for managing research briefs"""
    
    def __init__(self, agent):
        self.agent = agent
    
    def register(self, server):
        """Register tool with FastMCP server"""
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
            return self.execute(topic, angle, tone, target_length_min, additional_instructions)
    
    def execute(self, topic: str, angle: str = None, tone: str = "informative", 
               target_length_min: int = 30, additional_instructions: str = None) -> Dict[str, Any]:
        """Create a new research brief and return its details"""
        
        try:
            # Validate inputs
            topic = ValidationService.validate_string(topic, "topic", 500)
            if angle:
                angle = ValidationService.validate_string(angle, "angle", 200)
            tone = ValidationService.validate_choice(tone, "tone", ["informative", "casual", "formal", "entertaining"])
            target_length_min = ValidationService.validate_positive_int(target_length_min, "target_length_min", 5)
            
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
            self.agent.log_event(
                brief_id=brief_id,
                event_type="brief_created",
                message=f"Created research brief for topic: {topic}",
                payload={
                    "brief_id": brief_id,
                    "topic": topic,
                    "angle": angle,
                    "tone": tone,
                    "target_length_min": target_length_min
                }
            )
            
            return self.agent.create_success_response(
                data={
                    "brief_id": brief_id,
                    "topic": topic,
                    "status": "created",
                    "next_steps": [
                        "Run clarification if needed",
                        "Begin initial research planning", 
                        "Execute multi-pass research cycle"
                    ]
                },
                message=f"Research brief created successfully. Ready to begin research on: {topic}"
            )
            
        except Exception as e:
            return self.agent.create_error_response(str(e))