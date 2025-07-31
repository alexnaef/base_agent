"""
Centralized configuration for all agents.
"""
import os
from typing import Dict, Any

class AgentConfig:
    """Centralized configuration for all agents"""
    
    # OpenAI Configuration
    OPENAI_TOOL_MODEL = os.getenv("OPENAI_TOOL_MODEL", "gpt-4.1-mini")
    OPENAI_FINAL_MODEL = os.getenv("OPENAI_FINAL_MODEL", "gpt-4.1")
    
    # General Configuration
    WORDS_PER_MINUTE = 155  # For podcast script timing
    MAX_PROMPT_LENGTH = 8000
    DEFAULT_TEMPERATURE = 0.3
    LOW_TEMPERATURE = 0.1
    HIGH_TEMPERATURE = 0.7
    
    # Query Formulator Configuration
    QUERY_FORMULATOR = {
        "strategies": {
            "quick": 4,
            "standard": 6, 
            "comprehensive": 8,
            "deep": 12
        },
        "max_sources": 15,
        "performance_threshold": 3  # Minimum results per query
    }
    
    # Fact Checker Configuration
    FACT_CHECKER = {
        "verification_depths": {
            "quick": 5,
            "standard": 10,
            "thorough": 20
        },
        "credibility_threshold": 0.6,
        "confidence_threshold": 0.8,
        "max_sources_to_assess": 10
    }
    
    # Script Writer Configuration
    SCRIPT_WRITER = {
        "min_sections": 6,
        "max_sections": 8,
        "intro_duration_min": 2,
        "conclusion_duration_min": 2,
        "section_duration_min": 4
    }
    
    # Podcast Orchestrator Configuration
    ORCHESTRATOR = {
        "completion_threshold": 80.0,  # Percentage
        "min_verified_items": 5,
        "cycle_configs": {
            "quick": {"queries": 3, "items_per_query": 2, "depth": "surface"},
            "comprehensive": {"queries": 6, "items_per_query": 3, "depth": "deep"},
            "targeted": {"queries": 4, "items_per_query": 4, "depth": "focused"}
        }
    }
    
    @classmethod
    def get_agent_config(cls, agent_name: str) -> Dict[str, Any]:
        """Get configuration for a specific agent"""
        config_map = {
            "query_formulator": cls.QUERY_FORMULATOR,
            "fact_checker": cls.FACT_CHECKER,
            "script_writer": cls.SCRIPT_WRITER,
            "podcast_orchestrator": cls.ORCHESTRATOR
        }
        return config_map.get(agent_name, {})