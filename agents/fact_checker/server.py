import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

from typing import Dict, Any, List
import json
import re
from datetime import datetime
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv(dotenv_path="../../.env", override=True)
load_dotenv(override=True)

from mcp.server.fastmcp.server import FastMCP
from shared.models import ResearchStatus, VerificationStatus
from shared.schemas import AgentEventCreate
from shared.services import research_service, event_service, query_service

# Initialize OpenAI client
try:
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        openai_client = OpenAI(api_key=api_key)
        OPENAI_AVAILABLE = True
        print("✅ Fact Checker: OpenAI client initialized")
    else:
        print("❌ OPENAI_API_KEY not found in environment")
        openai_client = None
        OPENAI_AVAILABLE = False
except Exception as e:
    print(f"Warning: OpenAI client not available: {e}")
    openai_client = None
    OPENAI_AVAILABLE = False

server = FastMCP(
    name="fact-checker",
    instructions="""
    This is the Fact Checker Agent - specialized in verifying claims and assessing source credibility.
    
    Key responsibilities:
    1. Extract factual claims from research content and manuscripts
    2. Cross-verify claims against multiple sources
    3. Assess source credibility and reliability
    4. Identify contradictions and inconsistencies
    5. Flag unsupported or potentially false claims
    6. Generate credibility scores for content and sources
    
    Verification methodology:
    - Source triangulation: Verify claims across multiple independent sources
    - Authority assessment: Evaluate source expertise and reputation
    - Recency validation: Check if information is current and accurate
    - Context analysis: Ensure claims are not taken out of context
    - Bias detection: Identify potential source bias or agenda
    """,
)

CLAIM_EXTRACTION_PROMPT = """
You are a fact-checking expert. Extract verifiable factual claims from this content.

Content: {content}

Extract specific, factual claims that can be verified. Focus on:
- Dates, numbers, statistics
- Names of people, places, organizations
- Specific events and their details
- Cause-and-effect relationships
- Technical or scientific facts

Return JSON array of claims:
[
  {{
    "claim": "Specific factual statement",
    "category": "date|statistic|person|event|technical|other",
    "confidence": "high|medium|low",
    "importance": "critical|important|minor",
    "context": "Brief context for the claim"
  }}
]

Only extract claims that are:
1. Specific and verifiable
2. Important to the content's credibility
3. Can be fact-checked against reliable sources
"""

FACT_VERIFICATION_PROMPT = """
You are a fact-checking expert. Verify this claim against the provided sources.

Claim to verify: {claim}
Context: {context}

Sources to check against:
{sources}

Analyze the claim and return a verification assessment:

{{
  "claim": "{claim}",
  "verification_status": "verified|disputed|unverified|needs_more_sources",
  "confidence_score": 0.0-1.0,
  "evidence_found": "What evidence supports or refutes the claim",
  "contradictions": ["List any contradictory information found"],
  "supporting_sources": ["URLs or descriptions of sources that support the claim"],
  "reliability_assessment": "Assessment of source reliability for this claim",
  "recommendation": "accept|flag|investigate_further|reject",
  "notes": "Additional context or concerns"
}}

Be thorough but concise. Focus on factual accuracy and source reliability.
"""

SOURCE_CREDIBILITY_PROMPT = """
You are a source credibility expert. Assess the reliability of this source.

Source URL: {url}
Source Title: {title}
Source Content: {content}
Domain: {domain}

Evaluate credibility based on:
1. Domain authority and reputation
2. Author expertise and credentials
3. Editorial standards and fact-checking
4. Bias and potential agenda
5. Currency and accuracy of information
6. Citation of other reliable sources

Return assessment:
{{
  "url": "{url}",
  "domain": "{domain}",
  "credibility_score": 0.0-1.0,
  "credibility_level": "high|medium|low|unreliable",
  "strengths": ["What makes this source credible"],
  "weaknesses": ["Potential credibility concerns"],
  "bias_assessment": "left|right|center|unknown",
  "bias_strength": "strong|moderate|slight|minimal",
  "domain_type": "academic|news|government|commercial|blog|other",
  "recommendation": "primary_source|secondary_source|cross_verify|avoid",
  "notes": "Additional credibility considerations"
}}
"""

@server.tool(
    name="extract_claims_from_content",
    description="Extract verifiable factual claims from research content or manuscripts",
)
def extract_claims_from_content(
    brief_id: int,
    content_source: str = "research_items",  # research_items, manuscript, or custom
    custom_content: str = None
) -> Dict[str, Any]:
    """Extract factual claims from content for verification"""
    
    if not OPENAI_AVAILABLE:
        return {"error": "OpenAI client not available"}
    
    try:
        # Get content to analyze
        content_to_analyze = ""
        
        if content_source == "research_items":
            # Extract from research items
            from shared.database import db_manager
            with db_manager.session_scope() as session:
                from shared.models import ResearchItem
                items = session.query(ResearchItem).filter(
                    ResearchItem.brief_id == brief_id
                ).limit(10).all()  # Analyze top 10 items
                
                content_pieces = []
                for item in items:
                    if item.content:
                        content_pieces.append(f"Source: {item.title}\n{item.content[:2000]}")
                
                content_to_analyze = "\n\n---\n\n".join(content_pieces)
        
        elif content_source == "manuscript":
            # Extract from generated manuscript
            from shared.database import db_manager
            with db_manager.session_scope() as session:
                from shared.models import PodcastScript
                script = session.query(PodcastScript).filter(
                    PodcastScript.brief_id == brief_id
                ).first()
                
                if script and script.content:
                    content_to_analyze = script.content
                else:
                    return {"error": "No manuscript found for this brief"}
        
        elif content_source == "custom" and custom_content:
            content_to_analyze = custom_content
        
        else:
            return {"error": "Invalid content source or no custom content provided"}
        
        if not content_to_analyze.strip():
            return {"error": "No content available for claim extraction"}
        
        # Extract claims using OpenAI
        prompt = CLAIM_EXTRACTION_PROMPT.format(content=content_to_analyze[:8000])  # Limit for API
        
        response = openai_client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": "You are an expert fact-checker specialized in extracting verifiable claims."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2
        )
        
        claims_text = response.choices[0].message.content
        
        # Parse JSON response
        try:
            if claims_text.strip().startswith('['):
                claims = json.loads(claims_text)
            else:
                json_match = re.search(r'```(?:json)?\s*(\[.*?\])\s*```', claims_text, re.DOTALL)
                if json_match:
                    claims = json.loads(json_match.group(1))
                else:
                    return {"error": "Failed to parse claims JSON", "raw_response": claims_text}
        except json.JSONDecodeError as e:
            return {"error": f"JSON parsing failed: {e}", "raw_response": claims_text}
        
        # Categorize claims by importance and type
        critical_claims = [c for c in claims if c.get("importance") == "critical"]
        important_claims = [c for c in claims if c.get("importance") == "important"]
        high_confidence = [c for c in claims if c.get("confidence") == "high"]
        
        # Log the extraction
        event_service.log_event(AgentEventCreate(
            brief_id=brief_id,
            agent_name="fact_checker",
            event_type="claims_extracted",
            message=f"Extracted {len(claims)} factual claims from {content_source}",
            payload={
                "total_claims": len(claims),
                "critical_claims": len(critical_claims),
                "important_claims": len(important_claims),
                "high_confidence_claims": len(high_confidence),
                "content_source": content_source
            }
        ))
        
        return {
            "brief_id": brief_id,
            "content_source": content_source,
            "claims": claims,
            "summary": {
                "total_claims": len(claims),
                "critical_claims": len(critical_claims),
                "important_claims": len(important_claims),
                "high_confidence_claims": len(high_confidence),
                "categories": list(set(c.get("category", "other") for c in claims))
            },
            "message": f"Extracted {len(claims)} factual claims for verification"
        }
        
    except Exception as e:
        return {
            "error": str(e),
            "message": "Failed to extract claims from content"
        }

@server.tool(
    name="verify_claims_against_sources",
    description="Verify extracted claims against available research sources",
)
def verify_claims_against_sources(
    brief_id: int,
    claims: List[Dict[str, Any]] = None,
    verification_depth: str = "standard"  # quick, standard, thorough
) -> Dict[str, Any]:
    """Verify claims against research sources"""
    
    if not OPENAI_AVAILABLE:
        return {"error": "OpenAI client not available"}
    
    try:
        # Get claims to verify
        if not claims:
            # Get previously extracted claims - for now, extract fresh ones
            extraction_result = extract_claims_from_content(brief_id, "research_items")
            if "error" in extraction_result:
                return extraction_result
            claims = extraction_result.get("claims", [])
        
        if not claims:
            return {"error": "No claims to verify"}
        
        # Get research sources
        from shared.database import db_manager
        with db_manager.session_scope() as session:
            from shared.models import ResearchItem
            sources = session.query(ResearchItem).filter(
                ResearchItem.brief_id == brief_id
            ).all()
        
        if not sources:
            return {"error": "No research sources available for verification"}
        
        # Prepare source content for verification
        source_content = []
        for source in sources[:15]:  # Limit to 15 sources for performance
            source_content.append(f"Source: {source.title} (URL: {source.url})\n{source.content[:1500] if source.content else source.description}")
        
        sources_text = "\n\n---\n\n".join(source_content)
        
        # Verify claims based on depth setting
        depth_limits = {
            "quick": 5,
            "standard": 10,
            "thorough": len(claims)
        }
        
        claims_to_verify = claims[:depth_limits.get(verification_depth, 10)]
        verified_claims = []
        
        for claim in claims_to_verify:
            try:
                # Verify individual claim
                prompt = FACT_VERIFICATION_PROMPT.format(
                    claim=claim.get("claim", ""),
                    context=claim.get("context", ""),
                    sources=sources_text[:6000]  # Limit for API
                )
                
                response = openai_client.chat.completions.create(
                    model="gpt-4.1",  # Use higher quality model for verification
                    messages=[
                        {"role": "system", "content": "You are an expert fact-checker with deep knowledge of verification methodology."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.1  # Low temperature for factual analysis
                )
                
                verification_text = response.choices[0].message.content
                
                # Parse verification result
                try:
                    if verification_text.strip().startswith('{'):
                        verification = json.loads(verification_text)
                    else:
                        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', verification_text, re.DOTALL)
                        if json_match:
                            verification = json.loads(json_match.group(1))
                        else:
                            verification = {
                                "claim": claim.get("claim", ""),
                                "verification_status": "unverified",
                                "confidence_score": 0.0,
                                "evidence_found": "Failed to parse verification response",
                                "recommendation": "investigate_further"
                            }
                except:
                    verification = {
                        "claim": claim.get("claim", ""),
                        "verification_status": "unverified", 
                        "confidence_score": 0.0,
                        "evidence_found": "Verification parsing failed",
                        "recommendation": "investigate_further"
                    }
                
                # Add original claim metadata
                verification.update({
                    "original_category": claim.get("category"),
                    "original_importance": claim.get("importance"),
                    "original_confidence": claim.get("confidence")
                })
                
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
        event_service.log_event(AgentEventCreate(
            brief_id=brief_id,
            agent_name="fact_checker",
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
        ))
        
        return {
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
            "recommendations": generate_verification_recommendations(verified_claims, avg_confidence),
            "message": f"Verified {len(verified_claims)} claims with {avg_confidence:.1%} average confidence"
        }
        
    except Exception as e:
        return {
            "error": str(e),
            "message": "Failed to verify claims against sources"
        }

@server.tool(
    name="assess_source_credibility",
    description="Assess the credibility and reliability of research sources",
)
def assess_source_credibility(brief_id: int, max_sources: int = 10) -> Dict[str, Any]:
    """Assess credibility of research sources"""
    
    if not OPENAI_AVAILABLE:
        return {"error": "OpenAI client not available"}
    
    try:
        # Get research sources
        from shared.database import db_manager
        with db_manager.session_scope() as session:
            from shared.models import ResearchItem
            sources = session.query(ResearchItem).filter(
                ResearchItem.brief_id == brief_id
            ).limit(max_sources).all()
        
        if not sources:
            return {"error": "No research sources found for credibility assessment"}
        
        credibility_assessments = []
        
        for source in sources:
            try:
                # Extract domain
                domain = source.url.split('/')[2] if source.url and len(source.url.split('/')) > 2 else 'unknown'
                
                # Assess credibility
                prompt = SOURCE_CREDIBILITY_PROMPT.format(
                    url=source.url or "N/A",
                    title=source.title or "N/A",
                    content=(source.content or source.description or "")[:2000],
                    domain=domain
                )
                
                response = openai_client.chat.completions.create(
                    model="gpt-4.1-mini",
                    messages=[
                        {"role": "system", "content": "You are an expert in source credibility assessment and media literacy."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.2
                )
                
                assessment_text = response.choices[0].message.content
                
                # Parse assessment
                try:
                    if assessment_text.strip().startswith('{'):
                        assessment = json.loads(assessment_text)
                    else:
                        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', assessment_text, re.DOTALL)
                        if json_match:
                            assessment = json.loads(json_match.group(1))
                        else:
                            assessment = {
                                "url": source.url,
                                "domain": domain,
                                "credibility_score": 0.5,
                                "credibility_level": "unknown",
                                "recommendation": "cross_verify"
                            }
                except:
                    assessment = {
                        "url": source.url,
                        "domain": domain,
                        "credibility_score": 0.5,
                        "credibility_level": "unknown",
                        "recommendation": "cross_verify"
                    }
                
                # Add metadata
                assessment.update({
                    "source_id": source.id,
                    "title": source.title,
                    "current_credibility_score": source.credibility_score
                })
                
                credibility_assessments.append(assessment)
                
                # Update source credibility in database
                if hasattr(assessment, 'credibility_score'):
                    from shared.database import db_manager
                    with db_manager.session_scope() as update_session:
                        update_item = update_session.query(ResearchItem).filter(
                            ResearchItem.id == source.id
                        ).first()
                        if update_item:
                            update_item.credibility_score = assessment.get('credibility_score', 0.5)
                
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
        
        return {
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
            "recommendations": generate_credibility_recommendations(credibility_assessments, avg_credibility),
            "message": f"Assessed {len(credibility_assessments)} sources with {avg_credibility:.1%} average credibility"
        }
        
    except Exception as e:
        return {
            "error": str(e),
            "message": "Failed to assess source credibility"
        }

@server.tool(
    name="generate_fact_check_report",
    description="Generate comprehensive fact-checking report for a research brief",
)
def generate_fact_check_report(brief_id: int) -> Dict[str, Any]:
    """Generate comprehensive fact-checking report"""
    
    try:
        # Get research brief
        brief = research_service.get_brief(brief_id)
        if not brief:
            return {"error": "Research brief not found"}
        
        # Perform claim extraction
        claims_result = extract_claims_from_content(brief_id, "research_items")
        
        # Perform claim verification
        verification_result = verify_claims_against_sources(brief_id)
        
        # Assess source credibility
        credibility_result = assess_source_credibility(brief_id)
        
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
                "content_reliability": calculate_content_reliability(
                    verification_result.get("summary", {}),
                    credibility_result.get("summary", {})
                ),
                "research_quality": assess_research_quality(
                    claims_result.get("summary", {}),
                    verification_result.get("summary", {}),
                    credibility_result.get("summary", {})
                )
            },
            
            "recommendations": compile_all_recommendations(
                verification_result.get("recommendations", []),
                credibility_result.get("recommendations", [])
            )
        }
        
        # Log report generation
        event_service.log_event(AgentEventCreate(
            brief_id=brief_id,
            agent_name="fact_checker",
            event_type="fact_check_report_generated",
            message="Generated comprehensive fact-checking report",
            payload={
                "overall_reliability": report["overall_assessment"]["content_reliability"],
                "research_quality": report["overall_assessment"]["research_quality"],
                "high_risk_items": len(report["high_risk_items"]["disputed_claims"]) + len(report["high_risk_items"]["low_credibility_sources"])
            }
        ))
        
        return report
        
    except Exception as e:
        return {
            "error": str(e),
            "message": "Failed to generate fact-checking report"
        }

# Helper functions
def generate_verification_recommendations(verified_claims: List[Dict], avg_confidence: float) -> List[str]:
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

def generate_credibility_recommendations(assessments: List[Dict], avg_credibility: float) -> List[str]:
    recommendations = []
    
    low_cred = [a for a in assessments if a.get('credibility_level') in ['low', 'unreliable']]
    if low_cred:
        recommendations.append(f"Consider removing or replacing {len(low_cred)} low-credibility sources")
    
    if avg_credibility < 0.6:
        recommendations.append("Seek more authoritative sources to improve overall credibility")
    
    return recommendations

def calculate_content_reliability(verification_summary: Dict, credibility_summary: Dict) -> str:
    """Calculate overall content reliability assessment"""
    verification_score = verification_summary.get("average_confidence", 0)
    credibility_score = credibility_summary.get("average_credibility", 0)
    
    combined_score = (verification_score + credibility_score) / 2
    
    if combined_score >= 0.8:
        return "high"
    elif combined_score >= 0.6:
        return "medium"
    else:
        return "low"

def assess_research_quality(claims_summary: Dict, verification_summary: Dict, credibility_summary: Dict) -> str:
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

def compile_all_recommendations(verification_recs: List[str], credibility_recs: List[str]) -> List[str]:
    """Compile all recommendations into a single list"""
    all_recs = verification_recs + credibility_recs
    
    if not all_recs:
        all_recs.append("Research quality meets standards for publication")
    
    return all_recs

if __name__ == "__main__":
    server.run()