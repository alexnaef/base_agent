"""
Query refinement prompt template.
"""

QUERY_REFINEMENT_PROMPT = """
You are a research quality expert. Analyze these search queries and suggest improvements.

Original queries: ${queries}
Research brief: ${brief_summary}

Evaluate each query for:
1. Specificity - Is it targeted enough to find quality sources?
2. Coverage - Does the set cover all important angles?
3. Searchability - Will search engines return good results?
4. Balance - Are multiple perspectives represented?
5. Depth - Mix of overview and detailed queries?

Identify gaps and suggest 2-3 additional queries to improve coverage.

Return JSON:
{
  "analysis": "Overall assessment of query quality and coverage",
  "gaps": ["List of missing research angles or topics"],
  "additional_queries": [
    {
      "query": "New search query",
      "category": "category",
      "rationale": "Why this fills a gap"
    }
  ],
  "refinements": [
    {
      "original": "Original query",
      "improved": "Improved version",
      "reason": "Why the improvement helps"
    }
  ]
}
"""