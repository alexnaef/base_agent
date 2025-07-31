"""
Prompt templates for query formulator agent.
"""

from .generation import QUERY_GENERATION_PROMPT
from .refinement import QUERY_REFINEMENT_PROMPT

__all__ = [
    'QUERY_GENERATION_PROMPT',
    'QUERY_REFINEMENT_PROMPT'
]