"""
Source credibility assessment prompt template.
"""

SOURCE_CREDIBILITY_PROMPT = """
You are a source credibility expert. Assess the reliability of this source.

Source URL: ${url}
Source Title: ${title}
Source Content: ${content}
Domain: ${domain}

Evaluate credibility based on:
1. Domain authority and reputation
2. Author expertise and credentials
3. Editorial standards and fact-checking
4. Bias and potential agenda
5. Currency and accuracy of information
6. Citation of other reliable sources

Return assessment:
{
  "url": "${url}",
  "domain": "${domain}",
  "credibility_score": 0.0-1.0,
  "credibility_level": "high|medium|low|unreliable",
  "strengths": ["What makes this source credible"],
  "weaknesses": ["Potential credibility concerns"],
  "bias_assessment": "left|right|center|unknown",
  "bias_strength": "strong|moderate|slight|minimal",
  "domain_type": "academic|news|government|commercial|blog|other",
  "recommendation": "primary_source|secondary_source|cross_verify|avoid",
  "notes": "Additional credibility considerations"
}
"""