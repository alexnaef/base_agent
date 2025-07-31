"""
Fact checking report generation tool.
"""
import sys
import os
from typing import Dict, Any
from datetime import datetime

# Add parent directories to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../..'))

from shared.services import research_service
from agents.services import MetricsService


class ReportGeneratorTool:
    """Tool for generating comprehensive fact-checking reports"""
    
    def __init__(self, agent):
        self.agent = agent
    
    def register(self, server):
        """Register tool with FastMCP server"""
        @server.tool(
            name="generate_fact_check_report",
            description="Generate comprehensive fact-checking report for a research brief",
        )
        def generate_fact_check_report(brief_id: int) -> Dict[str, Any]:
            return self.execute(brief_id)
    
    def execute(self, brief_id: int) -> Dict[str, Any]:
        """Generate comprehensive fact-checking report"""
        
        try:
            # Get research brief
            brief = research_service.get_brief(brief_id)
            if not brief:
                return self.agent.create_error_response("Research brief not found")
            
            # Perform claim extraction
            from .claim_extractor import ClaimExtractorTool
            claim_extractor = ClaimExtractorTool(self.agent)
            claims_result = claim_extractor.execute(brief_id, "research_items")
            
            # Perform claim verification
            from .verifier import VerifierTool
            verifier = VerifierTool(self.agent)
            verification_result = verifier.execute(brief_id)
            
            # Assess source credibility
            from .credibility_assessor import CredibilityAssessorTool
            credibility_assessor = CredibilityAssessorTool(self.agent)
            credibility_result = credibility_assessor.execute(brief_id)
            
            # Compile comprehensive report
            report = {
                "brief_id": brief_id,
                "topic": brief['topic'],
                "report_generated": datetime.now().isoformat(),
                
                "claim_analysis": claims_result.get("summary", {}),
                "verification_analysis": verification_result.get("summary", {}),
                "credibility_analysis": credibility_result.get("summary", {}),
                
                "high_risk_items": {
                    "disputed_claims": verification_result.get("high_risk_claims", []),
                    "low_credibility_sources": credibility_result.get("problematic_sources", [])
                },
                
                "overall_assessment": {
                    "content_reliability": self._calculate_content_reliability(
                        verification_result.get("summary", {}),
                        credibility_result.get("summary", {})
                    ),
                    "research_quality": self._assess_research_quality(
                        claims_result.get("summary", {}),
                        verification_result.get("summary", {}),
                        credibility_result.get("summary", {})
                    )
                },
                
                "recommendations": self._compile_all_recommendations(
                    verification_result.get("recommendations", []),
                    credibility_result.get("recommendations", [])
                )
            }
            
            # Log report generation
            self.agent.log_event(
                brief_id=brief_id,
                event_type="fact_check_report_generated",
                message="Generated comprehensive fact-checking report",
                payload={
                    "overall_reliability": report["overall_assessment"]["content_reliability"],
                    "research_quality": report["overall_assessment"]["research_quality"],
                    "high_risk_items": len(report["high_risk_items"]["disputed_claims"]) + len(report["high_risk_items"]["low_credibility_sources"])
                }
            )
            
            return self.agent.create_success_response(
                data=report,
                message="Generated comprehensive fact-checking report"
            )
            
        except Exception as e:
            return self.agent.create_error_response(str(e))
    
    def _calculate_content_reliability(self, verification_summary: Dict, credibility_summary: Dict) -> str:
        """Calculate overall content reliability assessment"""
        verification_score = verification_summary.get("average_confidence", 0)
        credibility_score = credibility_summary.get("average_credibility", 0)
        
        return MetricsService.calculate_content_reliability(verification_score, credibility_score)
    
    def _assess_research_quality(self, claims_summary: Dict, verification_summary: Dict, credibility_summary: Dict) -> str:
        """Assess overall research quality"""
        factors = [
            claims_summary.get("high_confidence_claims", 0) / max(claims_summary.get("total_claims", 1), 1),
            verification_summary.get("verified_count", 0) / max(verification_summary.get("total_verified", 1), 1),
            credibility_summary.get("high_credibility", 0) / max(credibility_summary.get("total_sources", 1), 1)
        ]
        
        avg_quality = sum(factors) / len(factors)
        
        if avg_quality >= 0.7:
            return "excellent"
        elif avg_quality >= 0.5:
            return "good"
        elif avg_quality >= 0.3:
            return "fair"
        else:
            return "poor"
    
    def _compile_all_recommendations(self, verification_recs: list, credibility_recs: list) -> list:
        """Compile all recommendations into a single list"""
        all_recs = verification_recs + credibility_recs
        
        if not all_recs:
            all_recs.append("Research quality meets standards for publication")
        
        return all_recs