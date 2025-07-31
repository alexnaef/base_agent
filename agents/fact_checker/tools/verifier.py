"""
Claim verification tool.
"""
import sys
import os
from typing import Dict, Any, List

# Add parent directories to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../..'))

from prompts.verification import FACT_VERIFICATION_PROMPT
from agents.services import PromptService, ValidationService, MetricsService


class VerifierTool:
    """Tool for verifying claims against sources"""
    
    def __init__(self, agent):
        self.agent = agent
        self.prompt_service = PromptService("fact_checker")
        self.prompt_service.register_template("verification", FACT_VERIFICATION_PROMPT)
    
    def register(self, server):
        """Register tool with FastMCP server"""
        @server.tool(
            name="verify_claims_against_sources",
            description="Verify extracted claims against available research sources",
        )
        def verify_claims_against_sources(
            brief_id: int,
            claims: List[Dict[str, Any]] = None,
            verification_depth: str = "standard"
        ) -> Dict[str, Any]:
            return self.execute(brief_id, claims, verification_depth)
    
    def execute(self, brief_id: int, claims: List[Dict[str, Any]] = None, verification_depth: str = "standard") -> Dict[str, Any]:
        """Verify claims against research sources"""
        
        try:
            # Validate inputs
            brief_id = ValidationService.validate_brief_id(brief_id)
            verification_depth = ValidationService.validate_choice(
                verification_depth, "verification_depth", ["quick", "standard", "thorough"]
            )
            
            # Get claims to verify
            if not claims:
                # Import claim extractor to get fresh claims
                from .claim_extractor import ClaimExtractorTool
                extractor = ClaimExtractorTool(self.agent)
                extraction_result = extractor.execute(brief_id, "research_items")
                if "error" in extraction_result:
                    return extraction_result
                claims = extraction_result.get("claims", [])
            
            if not claims:
                return self.agent.create_error_response("No claims to verify")
            
            # Get research sources
            sources_text = self._get_sources_content(brief_id)
            if not sources_text:
                return self.agent.create_error_response("No research sources available for verification")
            
            # Verify claims based on depth setting
            depth_limits = self.agent.config["verification_depths"]
            claims_to_verify = claims[:depth_limits.get(verification_depth, 10)]
            verified_claims = []
            
            for claim in claims_to_verify:
                try:
                    verification = self._verify_single_claim(claim, sources_text)
                    verified_claims.append(verification)
                except Exception as claim_error:
                    print(f"Failed to verify claim: {claim_error}")
                    continue
            
            # Calculate verification statistics
            verified_count = len([c for c in verified_claims if c.get("verification_status") == "verified"])
            disputed_count = len([c for c in verified_claims if c.get("verification_status") == "disputed"])
            unverified_count = len([c for c in verified_claims if c.get("verification_status") == "unverified"])
            
            avg_confidence = sum(c.get("confidence_score", 0) for c in verified_claims) / len(verified_claims) if verified_claims else 0
            
            # Identify high-risk claims
            high_risk_claims = [
                c for c in verified_claims 
                if c.get("recommendation") in ["flag", "reject"] or c.get("verification_status") == "disputed"
            ]
            
            # Log verification results
            self.agent.log_event(
                brief_id=brief_id,
                event_type="claims_verified",
                message=f"Verified {len(verified_claims)} claims: {verified_count} verified, {disputed_count} disputed, {unverified_count} unverified",
                payload={
                    "claims_verified": len(verified_claims),
                    "verified_count": verified_count,
                    "disputed_count": disputed_count,
                    "unverified_count": unverified_count,
                    "high_risk_claims": len(high_risk_claims),
                    "average_confidence": round(avg_confidence, 2),
                    "verification_depth": verification_depth
                }
            )
            
            return self.agent.create_success_response(
                data={
                    "brief_id": brief_id,
                    "verification_results": verified_claims,
                    "summary": {
                        "total_verified": len(verified_claims),
                        "verified_count": verified_count,
                        "disputed_count": disputed_count,
                        "unverified_count": unverified_count,
                        "average_confidence": round(avg_confidence, 2),
                        "verification_depth": verification_depth
                    },
                    "high_risk_claims": high_risk_claims,
                    "recommendations": self._generate_verification_recommendations(verified_claims, avg_confidence)
                },
                message=f"Verified {len(verified_claims)} claims with {avg_confidence:.1%} average confidence"
            )
            
        except Exception as e:
            return self.agent.create_error_response(str(e))
    
    def _get_sources_content(self, brief_id: int) -> str:
        """Get research sources content for verification"""
        from shared.database import db_manager
        with db_manager.session_scope() as session:
            from shared.models import ResearchItem
            sources = session.query(ResearchItem).filter(
                ResearchItem.brief_id == brief_id
            ).all()
        
        if not sources:
            return ""
        
        source_content = []
        for source in sources[:15]:  # Limit to 15 sources for performance
            source_content.append(f"Source: {source.title} (URL: {source.url})\n{source.content[:1500] if source.content else source.description}")
        
        return "\n\n---\n\n".join(source_content)
    
    def _verify_single_claim(self, claim: Dict[str, Any], sources_text: str) -> Dict[str, Any]:
        """Verify a single claim against sources"""
        prompt = self.prompt_service.render_template(
            "verification",
            claim=claim.get("claim", ""),
            context=claim.get("context", ""),
            sources=sources_text[:6000]  # Limit for API
        )
        
        system_prompt = self.prompt_service.get_system_message(
            "fact-checker with deep knowledge of verification methodology"
        )
        
        verification = self.agent.execute_prompt_with_parsing(
            system_prompt=system_prompt,
            user_prompt=prompt,
            expected_json_type="dict",
            use_final_model=True,  # Use higher quality model for verification
            temperature=0.1
        )
        
        # Add original claim metadata
        verification.update({
            "original_category": claim.get("category"),
            "original_importance": claim.get("importance"),
            "original_confidence": claim.get("confidence")
        })
        
        return verification
    
    def _generate_verification_recommendations(self, verified_claims: List[Dict], avg_confidence: float) -> List[str]:
        """Generate recommendations based on verification results"""
        recommendations = []
        
        high_risk = [c for c in verified_claims if c.get("recommendation") in ["flag", "reject"]]
        if high_risk:
            recommendations.append(f"Review {len(high_risk)} high-risk claims before publication")
        
        if avg_confidence < 0.6:
            recommendations.append("Overall claim confidence is low - consider additional research")
        
        disputed = [c for c in verified_claims if c.get("verification_status") == "disputed"]
        if disputed:
            recommendations.append(f"Investigate {len(disputed)} disputed claims with contradictory evidence")
        
        return recommendations