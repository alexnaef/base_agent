"""
Claim extraction prompt template.
"""

CLAIM_EXTRACTION_PROMPT = """
You are a fact-checking expert. Extract verifiable factual claims from this content.

Content: ${content}

Extract specific, factual claims that can be verified. Focus on:
- Dates, numbers, statistics
- Names of people, places, organizations
- Specific events and their details
- Cause-and-effect relationships
- Technical or scientific facts

Return JSON array of claims:
[
  {
    "claim": "Specific factual statement",
    "category": "date|statistic|person|event|technical|other",
    "confidence": "high|medium|low",
    "importance": "critical|important|minor",
    "context": "Brief context for the claim"
  }
]

Only extract claims that are:
1. Specific and verifiable
2. Important to the content's credibility
3. Can be fact-checked against reliable sources
"""