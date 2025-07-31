"""
Prompt templates for fact checker agent.
"""

from .claim_extraction import CLAIM_EXTRACTION_PROMPT
from .verification import FACT_VERIFICATION_PROMPT
from .credibility import SOURCE_CREDIBILITY_PROMPT

__all__ = [
    'CLAIM_EXTRACTION_PROMPT',
    'FACT_VERIFICATION_PROMPT',
    'SOURCE_CREDIBILITY_PROMPT'
]