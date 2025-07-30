import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

from typing import Dict, Any, List
import json
import re
from datetime import datetime
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv(dotenv_path="../../.env", override=True)
load_dotenv(override=True)

from mcp.server.fastmcp.server import FastMCP
from shared.models import ResearchStatus
from shared.schemas import ResearchQueryCreate, AgentEventCreate
from shared.services import research_service, query_service, event_service

# Initialize OpenAI client
try:
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        openai_client = OpenAI(api_key=api_key)
        OPENAI_AVAILABLE = True
        print("✅ Query Formulator: OpenAI client initialized")
    else:
        print("❌ OPENAI_API_KEY not found in environment")
        openai_client = None
        OPENAI_AVAILABLE = False
except Exception as e:
    print(f"Warning: OpenAI client not available: {e}")
    openai_client = None
    OPENAI_AVAILABLE = False

server = FastMCP(
    name="query-formulator",
    instructions="""
    This is the Query Formulator Agent - specialized in generating intelligent search strategies.
    
    Key responsibilities:
    1. Analyze research briefs to understand topic scope and angle
    2. Generate comprehensive search query sets covering multiple perspectives
    3. Ensure balanced coverage: facts, context, controversy, timeline, expert opinions
    4. Optimize queries for different search engines and content types
    5. Track query effectiveness and suggest refinements
    
    Query generation strategies:
    - Factual queries: "What happened", "When did", "Key facts about"
    - Contextual queries: "Background of", "Causes of", "Led to"
    - Analytical queries: "Impact of", "Consequences", "Analysis"
    - Perspective queries: "Expert opinion", "Criticism of", "Defense of"
    - Timeline queries: "Timeline", "Chronology", "Before and after"
    - Comparative queries: "Compared to", "Similar to", "Different from"
    """,
)

QUERY_GENERATION_PROMPT = """
You are an expert research strategist. Generate a comprehensive set of search queries for deep research.

Research Brief:
- Topic: {topic}  
- Angle: {angle}
- Tone: {tone}
- Target: {target_length_min}-minute podcast

Requirements:
1. Generate {num_queries} distinct, high-quality search queries
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
  {{
    "query": "Specific search query text",
    "category": "core_facts|context|events|analysis|perspectives|timeline",
    "rationale": "Why this query is important for the research",
    "expected_sources": "Type of sources this should find (news, academic, expert analysis, etc.)"
  }}
]

Generate queries that will find high-quality, credible sources for creating a compelling {target_length_min}-minute podcast.
"""

QUERY_REFINEMENT_PROMPT = """
You are a research quality expert. Analyze these search queries and suggest improvements.

Original queries: {queries}
Research brief: {brief_summary}

Evaluate each query for:
1. Specificity - Is it targeted enough to find quality sources?
2. Coverage - Does the set cover all important angles?
3. Searchability - Will search engines return good results?
4. Balance - Are multiple perspectives represented?
5. Depth - Mix of overview and detailed queries?

Identify gaps and suggest 2-3 additional queries to improve coverage.

Return JSON:
{{
  "analysis": "Overall assessment of query quality and coverage",
  "gaps": ["List of missing research angles or topics"],
  "additional_queries": [
    {{
      "query": "New search query",
      "category": "category",
      "rationale": "Why this fills a gap"
    }}
  ],
  "refinements": [
    {{
      "original": "Original query",
      "improved": "Improved version",
      "reason": "Why the improvement helps"
    }}
  ]
}}
"""

@server.tool(
    name="generate_research_queries",
    description="Generate a comprehensive set of search queries for a research brief",
)
def generate_research_queries(
    brief_id: int,
    num_queries: int = 8,
    strategy: str = "comprehensive"
) -> Dict[str, Any]:
    """Generate intelligent search queries for research"""
    
    if not OPENAI_AVAILABLE:
        return {"error": "OpenAI client not available"}
    
    try:
        # Get the research brief
        brief = research_service.get_brief(brief_id)
        if not brief:
            return {"error": "Research brief not found"}
        
        # Adjust number of queries based on strategy
        strategy_configs = {
            "quick": 4,
            "standard": 6, 
            "comprehensive": 8,
            "deep": 12
        }
        
        if strategy in strategy_configs:
            num_queries = strategy_configs[strategy]
        
        # Generate queries using OpenAI
        prompt = QUERY_GENERATION_PROMPT.format(
            topic=brief['topic'],
            angle=brief['angle'] or "comprehensive overview",
            tone=brief['tone'],
            target_length_min=brief['target_length_min'],
            num_queries=num_queries
        )
        
        response = openai_client.chat.completions.create(
            model="gpt-4.1-mini",  # Use cheaper model for query generation
            messages=[
                {"role": "system", "content": "You are an expert research strategist and information scientist."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3  # Lower temperature for more focused queries
        )
        
        queries_text = response.choices[0].message.content
        
        # Parse JSON from response
        try:
            if queries_text.strip().startswith('['):
                queries = json.loads(queries_text)
            else:
                # Extract JSON from markdown code block
                json_match = re.search(r'```(?:json)?\s*(\[.*?\])\s*```', queries_text, re.DOTALL)
                if json_match:
                    queries = json.loads(json_match.group(1))
                else:
                    return {"error": "Failed to parse queries JSON", "raw_response": queries_text}
        except json.JSONDecodeError as e:
            return {"error": f"JSON parsing failed: {e}", "raw_response": queries_text}
        
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
        
        # Log the event
        event_service.log_event(AgentEventCreate(
            brief_id=brief_id,
            agent_name="query_formulator",
            event_type="queries_generated",
            message=f"Generated {len(queries)} research queries using {strategy} strategy",
            payload={
                "num_queries": len(queries),
                "strategy": strategy,
                "categories": list(set(q.get("category", "unknown") for q in queries))
            }
        ))
        
        return {
            "brief_id": brief_id,
            "strategy": strategy,
            "queries": saved_queries,
            "summary": {
                "total_queries": len(saved_queries),
                "categories": list(set(q.get("category", "unknown") for q in saved_queries)),
                "coverage_analysis": analyze_query_coverage(saved_queries)
            },
            "message": f"Generated {len(saved_queries)} research queries using {strategy} strategy"
        }
        
    except Exception as e:
        return {
            "error": str(e),
            "message": "Failed to generate research queries"
        }

@server.tool(
    name="refine_query_set",
    description="Analyze and improve an existing set of research queries",
)
def refine_query_set(brief_id: int) -> Dict[str, Any]:
    """Analyze existing queries and suggest improvements"""
    
    if not OPENAI_AVAILABLE:
        return {"error": "OpenAI client not available"}
    
    try:
        # Get the research brief and existing queries
        brief = research_service.get_brief(brief_id)
        if not brief:
            return {"error": "Research brief not found"}
        
        # Get existing queries from database
        with research_service.db_manager.session_scope() as session:
            from shared.models import ResearchQuery
            existing_queries = session.query(ResearchQuery).filter(
                ResearchQuery.brief_id == brief_id
            ).all()
        
        if not existing_queries:
            return {"error": "No existing queries found for this brief"}
        
        # Format queries for analysis
        query_list = [
            {
                "query": q.query_text,
                "id": q.id,
                "status": q.status
            } for q in existing_queries
        ]
        
        brief_summary = f"Topic: {brief['topic']}, Angle: {brief['angle']}, Length: {brief['target_length_min']}min"
        
        # Generate refinement suggestions
        prompt = QUERY_REFINEMENT_PROMPT.format(
            queries=json.dumps(query_list, indent=2),
            brief_summary=brief_summary
        )
        
        response = openai_client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": "You are an expert research quality analyst."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2
        )
        
        refinement_text = response.choices[0].message.content
        
        # Parse JSON response
        try:
            if refinement_text.strip().startswith('{'):
                refinement = json.loads(refinement_text)
            else:
                json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', refinement_text, re.DOTALL)
                if json_match:
                    refinement = json.loads(json_match.group(1))
                else:
                    return {"error": "Failed to parse refinement JSON", "raw_response": refinement_text}
        except json.JSONDecodeError as e:
            return {"error": f"Refinement JSON parsing failed: {e}", "raw_response": refinement_text}
        
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
        event_service.log_event(AgentEventCreate(
            brief_id=brief_id,
            agent_name="query_formulator",
            event_type="queries_refined",
            message=f"Refined query set: identified {len(refinement.get('gaps', []))} gaps, added {len(refinement.get('additional_queries', []))} queries",
            payload={
                "gaps_identified": len(refinement.get('gaps', [])),
                "additional_queries": len(refinement.get('additional_queries', [])),
                "refinements_suggested": len(refinement.get('refinements', []))
            }
        ))
        
        return {
            "brief_id": brief_id,
            "analysis": refinement.get("analysis", ""),
            "gaps": refinement.get("gaps", []),
            "additional_queries": refinement.get("additional_queries", []),
            "refinements": refinement.get("refinements", []),
            "new_query_ids": new_query_ids,
            "message": f"Query refinement complete: {len(refinement.get('additional_queries', []))} new queries added"
        }
        
    except Exception as e:
        return {
            "error": str(e),
            "message": "Failed to refine query set"
        }

@server.tool(
    name="analyze_query_performance",  
    description="Analyze the effectiveness of executed queries and suggest optimizations",
)
def analyze_query_performance(brief_id: int) -> Dict[str, Any]:
    """Analyze how well queries performed and suggest improvements"""
    
    try:
        # Get query performance data
        with research_service.db_manager.session_scope() as session:
            from shared.models import ResearchQuery, ResearchItem
            
            # Get all queries for this brief
            queries = session.query(ResearchQuery).filter(
                ResearchQuery.brief_id == brief_id
            ).all()
            
            if not queries:
                return {"error": "No queries found for this brief"}
            
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
            
            # Identify underperforming queries
            underperforming = [
                p for p in performance_data 
                if p["results_count"] < 3 and p["status"] == "completed"
            ]
            
            return {
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
                    "recommendations": generate_performance_recommendations(performance_data, avg_results_per_query)
                },
                "message": f"Analyzed {len(queries)} queries: {completion_rate:.1f}% completion rate"
            }
        
    except Exception as e:
        return {
            "error": str(e),
            "message": "Failed to analyze query performance"
        }

def analyze_query_coverage(queries: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze how well queries cover different research angles"""
    
    categories = {}
    for query in queries:
        category = query.get("category", "unknown")
        if category not in categories:
            categories[category] = 0
        categories[category] += 1
    
    total_queries = len(queries)
    coverage_score = len(categories) / 6 * 100  # 6 main categories expected
    
    return {
        "categories_covered": list(categories.keys()),
        "category_distribution": categories,
        "coverage_score": round(coverage_score, 1),
        "balance_assessment": "balanced" if max(categories.values()) <= total_queries * 0.4 else "unbalanced"
    }

def generate_performance_recommendations(performance_data: List[Dict], avg_results: float) -> List[str]:
    """Generate recommendations based on query performance"""
    
    recommendations = []
    
    underperforming = [p for p in performance_data if p["results_count"] < avg_results * 0.7]
    if underperforming:
        recommendations.append(f"Consider refining {len(underperforming)} underperforming queries")
    
    zero_results = [p for p in performance_data if p["results_count"] == 0]
    if zero_results:
        recommendations.append(f"Replace {len(zero_results)} queries that returned no results")
    
    if avg_results < 3:
        recommendations.append("Overall query specificity may be too high - consider broader terms")
    elif avg_results > 10:
        recommendations.append("Queries may be too broad - consider more specific targeting")
    
    if not recommendations:
        recommendations.append("Query performance looks good - maintain current strategy")
    
    return recommendations

if __name__ == "__main__":
    server.run()