"""
Query generation prompt template.
"""

QUERY_GENERATION_PROMPT = """
You are an expert research strategist. Generate a comprehensive set of search queries for deep research.

Research Brief:
- Topic: ${topic}  
- Angle: ${angle}
- Tone: ${tone}
- Target: ${target_length_min}-minute podcast

Requirements:
1. Generate ${num_queries} distinct, high-quality search queries
2. Cover multiple research angles: facts, context, analysis, perspectives, timeline
3. Ensure queries are specific enough to find quality sources
4. Optimize for web search engines (Google/Brave style)
5. Include both broad overview and specific detail queries
6. Consider controversial aspects and multiple viewpoints

Query Categories to Cover:
- Core Facts: Essential information and key details
- Historical Context: Background, causes, setting
- Key Events: Specific incidents, turning points, milestones  
- Analysis & Impact: Consequences, significance, expert analysis
- Multiple Perspectives: Different viewpoints, criticism, defense
- Timeline: Chronological development, before/after comparisons

Return a JSON array of query objects:
[
  {
    "query": "Specific search query text",
    "category": "core_facts|context|events|analysis|perspectives|timeline",
    "rationale": "Why this query is important for the research",
    "expected_sources": "Type of sources this should find (news, academic, expert analysis, etc.)"
  }
]

Generate queries that will find high-quality, credible sources for creating a compelling ${target_length_min}-minute podcast.
"""