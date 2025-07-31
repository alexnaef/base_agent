"""
Query performance analysis tool.
"""
import sys
import os
from typing import Dict, Any

# Add parent directories to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../..'))

from shared.services import research_service
from agents.services import ValidationService, MetricsService


class QueryAnalyzerTool:
    """Tool for analyzing query performance"""
    
    def __init__(self, agent):
        self.agent = agent
    
    def register(self, server):
        """Register tool with FastMCP server"""
        @server.tool(
            name="analyze_query_performance",  
            description="Analyze the effectiveness of executed queries and suggest optimizations",
        )
        def analyze_query_performance(brief_id: int) -> Dict[str, Any]:
            return self.execute(brief_id)
    
    def execute(self, brief_id: int) -> Dict[str, Any]:
        """Analyze how well queries performed and suggest improvements"""
        
        try:
            # Validate inputs
            brief_id = ValidationService.validate_brief_id(brief_id)
            
            # Get query performance data
            with research_service.db_manager.session_scope() as session:
                from shared.models import ResearchQuery, ResearchItem
                
                # Get all queries for this brief
                queries = session.query(ResearchQuery).filter(
                    ResearchQuery.brief_id == brief_id
                ).all()
                
                if not queries:
                    return self.agent.create_error_response("No queries found for this brief")
                
                # Analyze performance
                performance_data = []
                total_results = 0
                completed_queries = 0
                
                for query in queries:
                    # Count research items found by this query (simplified - in real implementation would track query->item relationship)
                    items_count = session.query(ResearchItem).filter(
                        ResearchItem.brief_id == brief_id
                    ).count() // len(queries)  # Rough approximation
                    
                    performance_data.append({
                        "query": query.query_text,
                        "status": query.status,
                        "results_count": query.results_count,
                        "estimated_items": items_count
                    })
                    
                    if query.status == "completed":
                        completed_queries += 1
                        total_results += query.results_count
                
                # Calculate metrics
                completion_rate = (completed_queries / len(queries)) * 100 if queries else 0
                avg_results_per_query = total_results / completed_queries if completed_queries > 0 else 0
                
                # Generate recommendations
                avg_results, recommendations = MetricsService.analyze_performance_data(performance_data)
                
                # Identify underperforming queries
                underperforming = [
                    p for p in performance_data 
                    if p["results_count"] < 3 and p["status"] == "completed"
                ]
                
                return self.agent.create_success_response(
                    data={
                        "brief_id": brief_id,
                        "summary": {
                            "total_queries": len(queries),
                            "completed_queries": completed_queries,
                            "completion_rate": round(completion_rate, 1),
                            "total_results": total_results,
                            "avg_results_per_query": round(avg_results_per_query, 1)
                        },
                        "performance_data": performance_data,
                        "insights": {
                            "underperforming_queries": len(underperforming),
                            "top_performing": [
                                p for p in performance_data 
                                if p["results_count"] >= 5
                            ],
                            "recommendations": recommendations
                        }
                    },
                    message=f"Analyzed {len(queries)} queries: {completion_rate:.1f}% completion rate"
                )
            
        except Exception as e:
            return self.agent.create_error_response(str(e))