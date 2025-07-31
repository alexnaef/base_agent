"""
Claim extraction tool.
"""
import sys
import os
from typing import Dict, Any

# Add parent directories to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../..'))

from prompts.claim_extraction import CLAIM_EXTRACTION_PROMPT
from agents.services import PromptService, ValidationService


class ClaimExtractorTool:
    """Tool for extracting factual claims from content"""
    
    def __init__(self, agent):
        self.agent = agent
        self.prompt_service = PromptService("fact_checker")
        self.prompt_service.register_template("claim_extraction", CLAIM_EXTRACTION_PROMPT)
    
    def register(self, server):
        """Register tool with FastMCP server"""
        @server.tool(
            name="extract_claims_from_content",
            description="Extract verifiable factual claims from research content or manuscripts",
        )
        def extract_claims_from_content(
            brief_id: int,
            content_source: str = "research_items",
            custom_content: str = None
        ) -> Dict[str, Any]:
            return self.execute(brief_id, content_source, custom_content)
    
    def execute(self, brief_id: int, content_source: str = "research_items", custom_content: str = None) -> Dict[str, Any]:
        """Extract factual claims from content for verification"""
        
        try:
            # Validate inputs
            brief_id = ValidationService.validate_brief_id(brief_id)
            content_source = ValidationService.validate_choice(
                content_source, "content_source", ["research_items", "manuscript", "custom"]
            )
            
            # Get content to analyze
            content_to_analyze = self._get_content(brief_id, content_source, custom_content)
            
            if not content_to_analyze.strip():
                return self.agent.create_error_response("No content available for claim extraction")
            
            # Extract claims using OpenAI
            prompt = self.prompt_service.render_template(
                "claim_extraction",
                content=content_to_analyze[:8000]  # Limit for API
            )
            
            system_prompt = self.prompt_service.get_system_message(
                "fact-checker specialized in extracting verifiable claims"
            )
            
            claims = self.agent.execute_prompt_with_parsing(
                system_prompt=system_prompt,
                user_prompt=prompt,
                expected_json_type="list",
                temperature=0.2
            )
            
            # Categorize claims by importance and type
            critical_claims = [c for c in claims if c.get("importance") == "critical"]
            important_claims = [c for c in claims if c.get("importance") == "important"]
            high_confidence = [c for c in claims if c.get("confidence") == "high"]
            
            # Log the extraction
            self.agent.log_event(
                brief_id=brief_id,
                event_type="claims_extracted",
                message=f"Extracted {len(claims)} factual claims from {content_source}",
                payload={
                    "total_claims": len(claims),
                    "critical_claims": len(critical_claims),
                    "important_claims": len(important_claims),
                    "high_confidence_claims": len(high_confidence),
                    "content_source": content_source
                }
            )
            
            return self.agent.create_success_response(
                data={
                    "brief_id": brief_id,
                    "content_source": content_source,
                    "claims": claims,
                    "summary": {
                        "total_claims": len(claims),
                        "critical_claims": len(critical_claims),
                        "important_claims": len(important_claims),
                        "high_confidence_claims": len(high_confidence),
                        "categories": list(set(c.get("category", "other") for c in claims))
                    }
                },
                message=f"Extracted {len(claims)} factual claims for verification"
            )
            
        except Exception as e:
            return self.agent.create_error_response(str(e))
    
    def _get_content(self, brief_id: int, content_source: str, custom_content: str = None) -> str:
        """Get content based on source type"""
        if content_source == "research_items":
            return self._get_research_items_content(brief_id)
        elif content_source == "manuscript":
            return self._get_manuscript_content(brief_id)
        elif content_source == "custom" and custom_content:
            return custom_content
        else:
            return ""
    
    def _get_research_items_content(self, brief_id: int) -> str:
        """Extract content from research items"""
        from shared.database import db_manager
        with db_manager.session_scope() as session:
            from shared.models import ResearchItem
            items = session.query(ResearchItem).filter(
                ResearchItem.brief_id == brief_id
            ).limit(10).all()
            
            content_pieces = []
            for item in items:
                if item.content:
                    content_pieces.append(f"Source: {item.title}\n{item.content[:2000]}")
            
            return "\n\n---\n\n".join(content_pieces)
    
    def _get_manuscript_content(self, brief_id: int) -> str:
        """Extract content from generated manuscript"""
        from shared.database import db_manager
        with db_manager.session_scope() as session:
            from shared.models import PodcastScript
            script = session.query(PodcastScript).filter(
                PodcastScript.brief_id == brief_id
            ).first()
            
            return script.content if script and script.content else ""