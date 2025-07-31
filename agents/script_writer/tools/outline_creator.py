"""
Podcast outline creation tool.
"""
import sys
import os
from typing import Dict, Any

# Add parent directories to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../..'))

from shared.services import research_service
from prompts.outline import PODCAST_OUTLINE_PROMPT
from agents.services import PromptService, ValidationService
from agents.common import AgentConfig


class OutlineCreatorTool:
    """Tool for creating podcast outlines"""
    
    def __init__(self, agent):
        self.agent = agent
        self.prompt_service = PromptService("script_writer")
        self.prompt_service.register_template("outline", PODCAST_OUTLINE_PROMPT)
    
    def register(self, server):
        """Register tool with FastMCP server"""
        @server.tool(
            name="create_podcast_outline",
            description="Generate a structured outline for a podcast episode based on research brief",
        )
        def create_podcast_outline(brief_id: int) -> Dict[str, Any]:
            return self.execute(brief_id)
    
    def execute(self, brief_id: int) -> Dict[str, Any]:
        """Create a detailed podcast outline from research brief"""
        
        try:
            # Validate inputs
            brief_id = ValidationService.validate_brief_id(brief_id)
            
            # Get the research brief
            brief = research_service.get_brief(brief_id)
            if not brief:
                return self.agent.create_error_response("Research brief not found")
            
            # Calculate target words (155 words per minute for narration)
            target_words = brief['target_length_min'] * AgentConfig.WORDS_PER_MINUTE
            
            # Create the outline prompt
            prompt = self.prompt_service.render_template(
                "outline",
                topic=brief['topic'],
                angle=brief['angle'] or "comprehensive overview",
                tone=brief['tone'],
                target_length_min=brief['target_length_min'],
                target_words=target_words
            )
            
            # Generate outline using OpenAI
            system_prompt = self.prompt_service.get_system_message(
                "podcast producer and scriptwriter"
            )
            
            outline = self.agent.execute_prompt_with_parsing(
                system_prompt=system_prompt,
                user_prompt=prompt,
                expected_json_type="dict",
                use_final_model=True,  # Use higher quality model for creative work
                temperature=0.7
            )
            
            # Log the event
            self.agent.log_event(
                brief_id=brief_id,
                event_type="outline_created",
                message="Generated podcast outline",
                payload={
                    "sections_count": len(outline.get("sections", [])), 
                    "total_duration": outline.get("total_duration_min")
                }
            )
            
            return self.agent.create_success_response(
                data={
                    "brief_id": brief_id,
                    "outline": outline,
                    "stats": {
                        "sections": len(outline.get("sections", [])),
                        "total_duration_min": outline.get("total_duration_min"),
                        "estimated_words": target_words
                    }
                },
                message="Podcast outline created successfully"
            )
            
        except Exception as e:
            return self.agent.create_error_response(str(e))