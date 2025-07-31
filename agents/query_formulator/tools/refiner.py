"""
Query refinement tool.
"""
import sys
import os
import json
from typing import Dict, Any

# Add parent directories to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../..'))

from shared.services import research_service, query_service
from shared.schemas import ResearchQueryCreate
from prompts.refinement import QUERY_REFINEMENT_PROMPT
from agents.services import PromptService, ValidationService


class QueryRefinerTool:
    """Tool for refining existing query sets"""
    
    def __init__(self, agent):
        self.agent = agent
        self.prompt_service = PromptService("query_formulator")
        self.prompt_service.register_template("refinement", QUERY_REFINEMENT_PROMPT)
    
    def register(self, server):
        """Register tool with FastMCP server"""
        @server.tool(
            name="refine_query_set",
            description="Analyze and improve an existing set of research queries",
        )
        def refine_query_set(brief_id: int) -> Dict[str, Any]:
            return self.execute(brief_id)
    
    def execute(self, brief_id: int) -> Dict[str, Any]:
        """Analyze existing queries and suggest improvements"""
        
        try:
            # Validate inputs
            brief_id = ValidationService.validate_brief_id(brief_id)
            
            # Get the research brief and existing queries
            brief = research_service.get_brief(brief_id)
            if not brief:
                return self.agent.create_error_response("Research brief not found")
            
            # Get existing queries from database
            with research_service.db_manager.session_scope() as session:
                from shared.models import ResearchQuery
                existing_queries = session.query(ResearchQuery).filter(
                    ResearchQuery.brief_id == brief_id
                ).all()
            
            if not existing_queries:
                return self.agent.create_error_response("No existing queries found for this brief")
            
            # Format queries for analysis
            query_list = [
                {
                    "query": q.query_text,
                    "id": q.id,
                    "status": q.status
                } for q in existing_queries
            ]
            
            brief_summary = f"Topic: {brief['topic']}, Angle: {brief['angle']}, Length: {brief['target_length_min']}min"
            
            # Render refinement prompt
            prompt = self.prompt_service.render_template(
                "refinement",
                queries=json.dumps(query_list, indent=2),
                brief_summary=brief_summary
            )
            
            # Generate refinement suggestions
            system_prompt = self.prompt_service.get_system_message("research quality analyst")
            
            refinement = self.agent.execute_prompt_with_parsing(
                system_prompt=system_prompt,
                user_prompt=prompt,
                expected_json_type="dict",
                temperature=0.2
            )
            
            # Add new suggested queries to database
            new_query_ids = []
            for additional_query in refinement.get("additional_queries", []):
                query_data = ResearchQueryCreate(
                    brief_id=brief_id,
                    query_text=additional_query.get("query", ""),
                    search_engine="brave"
                )
                saved_query = query_service.add_query(query_data)
                additional_query["id"] = saved_query['id']
                new_query_ids.append(additional_query["id"])
            
            # Log the refinement event
            self.agent.log_event(
                brief_id=brief_id,
                event_type="queries_refined",
                message=f"Refined query set: identified {len(refinement.get('gaps', []))} gaps, added {len(refinement.get('additional_queries', []))} queries",
                payload={
                    "gaps_identified": len(refinement.get('gaps', [])),
                    "additional_queries": len(refinement.get('additional_queries', [])),
                    "refinements_suggested": len(refinement.get('refinements', []))
                }
            )
            
            return self.agent.create_success_response(
                data={
                    "brief_id": brief_id,
                    "analysis": refinement.get("analysis", ""),
                    "gaps": refinement.get("gaps", []),
                    "additional_queries": refinement.get("additional_queries", []),
                    "refinements": refinement.get("refinements", []),
                    "new_query_ids": new_query_ids
                },
                message=f"Query refinement complete: {len(refinement.get('additional_queries', []))} new queries added"
            )
            
        except Exception as e:
            return self.agent.create_error_response(str(e))