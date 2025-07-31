"""
Fact verification prompt template.
"""

FACT_VERIFICATION_PROMPT = """
You are a fact-checking expert. Verify this claim against the provided sources.

Claim to verify: ${claim}
Context: ${context}

Sources to check against:
${sources}

Analyze the claim and return a verification assessment:

{
  "claim": "${claim}",
  "verification_status": "verified|disputed|unverified|needs_more_sources",
  "confidence_score": 0.0-1.0,
  "evidence_found": "What evidence supports or refutes the claim",
  "contradictions": ["List any contradictory information found"],
  "supporting_sources": ["URLs or descriptions of sources that support the claim"],
  "reliability_assessment": "Assessment of source reliability for this claim",
  "recommendation": "accept|flag|investigate_further|reject",
  "notes": "Additional context or concerns"
}

Be thorough but concise. Focus on factual accuracy and source reliability.
"""