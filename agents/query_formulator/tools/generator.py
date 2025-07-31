"""
Query generation tool.
"""
import sys
import os
from typing import Dict, Any

# Add parent directories to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../..'))

from shared.services import research_service, query_service
from shared.schemas import ResearchQueryCreate
from prompts.generation import QUERY_GENERATION_PROMPT
from agents.services import PromptService, ValidationService, MetricsService


class QueryGeneratorTool:
    """Tool for generating research queries"""
    
    def __init__(self, agent):
        self.agent = agent
        self.prompt_service = PromptService("query_formulator")
        self.prompt_service.register_template("generation", QUERY_GENERATION_PROMPT)
    
    def register(self, server):
        """Register tool with FastMCP server"""
        @server.tool(
            name="generate_research_queries",
            description="Generate a comprehensive set of search queries for a research brief",
        )
        def generate_research_queries(
            brief_id: int,
            num_queries: int = 8,
            strategy: str = "comprehensive"
        ) -> Dict[str, Any]:
            return self.execute(brief_id, num_queries, strategy)
    
    def execute(self, brief_id: int, num_queries: int = 8, strategy: str = "comprehensive") -> Dict[str, Any]:
        """Generate intelligent search queries for research"""
        
        try:
            # Validate inputs
            brief_id = ValidationService.validate_brief_id(brief_id)
            num_queries = ValidationService.validate_positive_int(num_queries, "num_queries")
            strategy = ValidationService.validate_choice(
                strategy, "strategy", ["quick", "standard", "comprehensive", "deep"]
            )
            
            # Get the research brief
            brief = research_service.get_brief(brief_id)
            if not brief:
                return self.agent.create_error_response("Research brief not found")
            
            # Adjust number of queries based on strategy
            strategy_configs = self.agent.config["strategies"]
            if strategy in strategy_configs:
                num_queries = strategy_configs[strategy]
            
            # Render prompt template
            prompt = self.prompt_service.render_template(
                "generation",
                topic=brief['topic'],
                angle=brief['angle'] or "comprehensive overview",
                tone=brief['tone'],
                target_length_min=brief['target_length_min'],
                num_queries=num_queries
            )
            
            # Generate queries using OpenAI
            system_prompt = self.prompt_service.get_system_message(
                "research strategist and information scientist"
            )
            
            queries = self.agent.execute_prompt_with_parsing(
                system_prompt=system_prompt,
                user_prompt=prompt,
                expected_json_type="list",
                temperature=0.3
            )
            
            # Save queries to database
            saved_queries = []
            for query_obj in queries:
                query_data = ResearchQueryCreate(
                    brief_id=brief_id,
                    query_text=query_obj.get("query", ""),
                    search_engine="brave"
                )
                saved_query = query_service.add_query(query_data)
                query_obj["id"] = saved_query['id']
                saved_queries.append(query_obj)
            
            # Analyze coverage
            coverage_analysis = MetricsService.analyze_query_coverage(saved_queries)
            
            # Log the event
            self.agent.log_event(
                brief_id=brief_id,
                event_type="queries_generated",
                message=f"Generated {len(queries)} research queries using {strategy} strategy",
                payload={
                    "num_queries": len(queries),
                    "strategy": strategy,
                    "categories": list(set(q.get("category", "unknown") for q in queries))
                }
            )
            
            return self.agent.create_success_response(
                data={
                    "brief_id": brief_id,
                    "strategy": strategy,
                    "queries": saved_queries,
                    "summary": {
                        "total_queries": len(saved_queries),
                        "categories": list(set(q.get("category", "unknown") for q in saved_queries)),
                        "coverage_analysis": coverage_analysis
                    }
                },
                message=f"Generated {len(saved_queries)} research queries using {strategy} strategy"
            )
            
        except Exception as e:
            return self.agent.create_error_response(str(e))