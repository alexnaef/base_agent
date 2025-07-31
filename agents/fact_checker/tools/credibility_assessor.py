"""
Source credibility assessment tool.
"""
import sys
import os
from typing import Dict, Any

# Add parent directories to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../..'))

from prompts.credibility import SOURCE_CREDIBILITY_PROMPT
from agents.services import PromptService, ValidationService


class CredibilityAssessorTool:
    """Tool for assessing source credibility"""
    
    def __init__(self, agent):
        self.agent = agent
        self.prompt_service = PromptService("fact_checker")
        self.prompt_service.register_template("credibility", SOURCE_CREDIBILITY_PROMPT)
    
    def register(self, server):
        """Register tool with FastMCP server"""
        @server.tool(
            name="assess_source_credibility",
            description="Assess the credibility and reliability of research sources",
        )
        def assess_source_credibility(brief_id: int, max_sources: int = 10) -> Dict[str, Any]:
            return self.execute(brief_id, max_sources)
    
    def execute(self, brief_id: int, max_sources: int = 10) -> Dict[str, Any]:
        """Assess credibility of research sources"""
        
        try:
            # Validate inputs
            brief_id = ValidationService.validate_brief_id(brief_id)
            max_sources = ValidationService.validate_positive_int(max_sources, "max_sources")
            
            # Get research sources
            from shared.database import db_manager
            with db_manager.session_scope() as session:
                from shared.models import ResearchItem
                sources = session.query(ResearchItem).filter(
                    ResearchItem.brief_id == brief_id
                ).limit(max_sources).all()
            
            if not sources:
                return self.agent.create_error_response("No research sources found for credibility assessment")
            
            credibility_assessments = []
            
            for source in sources:
                try:
                    assessment = self._assess_single_source(source)
                    credibility_assessments.append(assessment)
                    
                    # Update source credibility in database
                    self._update_source_credibility(source.id, assessment.get('credibility_score', 0.5))
                    
                except Exception as source_error:
                    print(f"Failed to assess source {source.url}: {source_error}")
                    continue
            
            # Calculate statistics
            high_credibility = [a for a in credibility_assessments if a.get('credibility_level') == 'high']
            medium_credibility = [a for a in credibility_assessments if a.get('credibility_level') == 'medium']
            low_credibility = [a for a in credibility_assessments if a.get('credibility_level') in ['low', 'unreliable']]
            
            avg_credibility = sum(a.get('credibility_score', 0) for a in credibility_assessments) / len(credibility_assessments) if credibility_assessments else 0
            
            # Identify problematic sources
            problematic_sources = [
                a for a in credibility_assessments 
                if a.get('recommendation') == 'avoid' or a.get('credibility_level') == 'unreliable'
            ]
            
            return self.agent.create_success_response(
                data={
                    "brief_id": brief_id,
                    "assessments": credibility_assessments,
                    "summary": {
                        "total_sources": len(credibility_assessments),
                        "high_credibility": len(high_credibility),
                        "medium_credibility": len(medium_credibility),
                        "low_credibility": len(low_credibility),
                        "average_credibility": round(avg_credibility, 2),
                        "problematic_sources": len(problematic_sources)
                    },
                    "problematic_sources": problematic_sources,
                    "recommendations": self._generate_credibility_recommendations(credibility_assessments, avg_credibility)
                },
                message=f"Assessed {len(credibility_assessments)} sources with {avg_credibility:.1%} average credibility"
            )
            
        except Exception as e:
            return self.agent.create_error_response(str(e))
    
    def _assess_single_source(self, source) -> Dict[str, Any]:
        """Assess credibility of a single source"""
        # Extract domain
        domain = source.url.split('/')[2] if source.url and len(source.url.split('/')) > 2 else 'unknown'
        
        # Assess credibility
        prompt = self.prompt_service.render_template(
            "credibility",
            url=source.url or "N/A",
            title=source.title or "N/A",
            content=(source.content or source.description or "")[:2000],
            domain=domain
        )
        
        system_prompt = self.prompt_service.get_system_message(
            "source credibility assessment and media literacy expert"
        )
        
        assessment = self.agent.execute_prompt_with_parsing(
            system_prompt=system_prompt,
            user_prompt=prompt,
            expected_json_type="dict",
            temperature=0.2
        )
        
        # Add metadata
        assessment.update({
            "source_id": source.id,
            "title": source.title,
            "current_credibility_score": source.credibility_score
        })
        
        return assessment
    
    def _update_source_credibility(self, source_id: int, credibility_score: float):
        """Update source credibility in database"""
        from shared.database import db_manager
        with db_manager.session_scope() as update_session:
            from shared.models import ResearchItem
            update_item = update_session.query(ResearchItem).filter(
                ResearchItem.id == source_id
            ).first()
            if update_item:
                update_item.credibility_score = credibility_score
    
    def _generate_credibility_recommendations(self, assessments: list, avg_credibility: float) -> list:
        """Generate credibility-based recommendations"""
        recommendations = []
        
        low_cred = [a for a in assessments if a.get('credibility_level') in ['low', 'unreliable']]
        if low_cred:
            recommendations.append(f"Consider removing or replacing {len(low_cred)} low-credibility sources")
        
        if avg_credibility < 0.6:
            recommendations.append("Seek more authoritative sources to improve overall credibility")
        
        return recommendations