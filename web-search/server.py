import os
import re
import sys
from typing import List, Dict, Any
from datetime import datetime

import requests
from bs4 import BeautifulSoup
from mcp.server.fastmcp.server import FastMCP

from dotenv import load_dotenv
load_dotenv()

# Add project root to path to import shared modules
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

try:
    from shared.models import ResearchStatus
    from shared.schemas import ResearchItemCreate, AgentEventCreate
    from shared.services import research_service, query_service, event_service
    from shared.embeddings import embedding_manager
    DATABASE_AVAILABLE = True
    print("✅ Enhanced Web Search: Database integration available")
except ImportError as e:
    print(f"⚠️  Database integration not available: {e}")
    DATABASE_AVAILABLE = False

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
BRAVE_API_KEY = os.getenv("BRAVE_API_KEY")
if not BRAVE_API_KEY:
    raise RuntimeError(
        "Environment variable BRAVE_API_KEY is missing. "
        "Create one in the Brave Search dashboard and export it first."
    )

# ---------------------------------------------------------------------------
# FastMCP Server instance
# ---------------------------------------------------------------------------
server = FastMCP(
    name="enhanced-web-search",
    instructions="""
This is the Enhanced Web Search Server - providing comprehensive research capabilities:

Original Tools:
1. `suggest_google_searches` – generates thoughtful Google-style searches for a topic.
2. `search_brave` – queries Brave Web Search API and returns the top organic results.
3. `scrape_website` – downloads the readable text from a URL for analysis.

Enhanced Research Tools:
4. `execute_research_queries` – execute all pending queries for a research brief
5. `research_and_scrape` – perform complete research cycle: search + scrape + save
6. `get_research_summary` – get summary of collected research for a brief
7. `search_and_analyze` – search with quality analysis and relevance scoring

This server now integrates with the database to provide persistent research collection
and feeds data directly into the podcast generation pipeline.
""",
)

# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

@server.tool(
    name="suggest_google_searches",
    description="Given a topic, suggest up to `max_suggestions` Google search queries to deeply research the topic.",
)
def suggest_google_searches(topic: str, max_suggestions: int = 10) -> List[str]:
    """Generate a list of research-oriented Google search queries."""
    if not topic:
        return []

    templates = [
        f"Who is {topic}",
        f"What is {topic}'s background",  # background information
        f"{topic} latest news",
        f"{topic} controversies",
        f"{topic} achievements",
        f"{topic} timeline",
        f"{topic} impact on industry",
        f"{topic} criticisms",
        f"{topic} awards",
        f"interviews with {topic}",
        f"quotes by {topic}",
    ]
    return templates[:max_suggestions]


@server.tool(
    name="search_brave",
    description="Search the web via Brave Search API and return a list of organic results with title, url, and description.",
)
def search_brave(query: str, max_results: int = 10) -> List[Dict[str, str]]:
    """Perform a Brave Web Search and return structured results."""
    headers = {
        "Accept": "application/json",
        "X-Subscription-Token": BRAVE_API_KEY,
    }
    params = {
        "q": query,
        "count": max_results,
    }

    response = requests.get(
        "https://api.search.brave.com/res/v1/web/search",
        headers=headers,
        params=params,
        timeout=20,
    )
    response.raise_for_status()
    data = response.json()

    # Brave returns results under data["results"], but may nest under "web" etc.
    results_raw = data.get("results") or data.get("web", {}).get("results", [])
    results: List[Dict[str, str]] = []
    for item in results_raw[:max_results]:
        results.append({
            "title": item.get("title"),
            "url": item.get("url"),
            "description": item.get("description") or item.get("snippet"),
        })
    return results


@server.tool(
    name="scrape_website",
    description="Download a web page and return its cleaned text content (scripts/styles removed). Truncates to `max_chars` characters.",
)
def scrape_website(url: str, max_chars: int = 5000) -> str:
    """Retrieve readable text from the given URL."""
    headers = {"User-Agent": "Mozilla/5.0 (compatible; BaseAgent/1.0; +https://example.com)"}
    resp = requests.get(url, headers=headers, timeout=20)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")

    # Remove elements that are not useful for text extraction.
    for tag in soup(["script", "style", "noscript", "header", "footer", "nav", "aside"]):
        tag.decompose()

    text = soup.get_text(separator=" ")
    # Collapse excessive whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_chars]


# ---------------------------------------------------------------------------
# Enhanced Research Tools
# ---------------------------------------------------------------------------

@server.tool(
    name="execute_research_queries",
    description="Execute all pending research queries for a brief and collect results",
)
def execute_research_queries(
    brief_id: int, 
    max_results_per_query: int = 5,
    scrape_results: bool = True
) -> Dict[str, Any]:
    """Execute all pending queries for a research brief"""
    
    if not DATABASE_AVAILABLE:
        return {"error": "Database integration not available"}
    
    try:
        # Get the research brief
        brief = research_service.get_brief(brief_id)
        if not brief:
            return {"error": "Research brief not found"}
        
        # Get pending queries
        with research_service.db_manager.session_scope() as session:
            from shared.models import ResearchQuery
            pending_queries = session.query(ResearchQuery).filter(
                ResearchQuery.brief_id == brief_id,
                ResearchQuery.status == "pending"
            ).all()
        
        if not pending_queries:
            return {"error": "No pending queries found for this brief"}
        
        executed_queries = []
        total_results = 0
        total_scraped = 0
        
        # Execute each query
        for query in pending_queries:
            try:
                # Search using Brave API
                search_results = search_brave(query.query_text, max_results_per_query)
                
                # Update query status
                query_service.update_query_status(
                    query.id, 
                    "completed", 
                    len(search_results)
                )
                
                scraped_items = []
                
                if scrape_results:
                    # Scrape each result
                    for result in search_results:
                        try:
                            content = scrape_website(result.get("url", ""), max_chars=8000)
                            
                            # Save to database as research item
                            item_data = ResearchItemCreate(
                                brief_id=brief_id,
                                title=result.get("title", ""),
                                url=result.get("url", ""),
                                description=result.get("description", ""),
                                content=content,
                                source_type="web"
                            )
                            
                            saved_item = research_service.add_research_item(item_data)
                            scraped_items.append({
                                "id": saved_item['id'],
                                "title": result.get("title"),
                                "url": result.get("url"),
                                "content_length": len(content)
                            })
                            total_scraped += 1
                            
                        except Exception as scrape_error:
                            print(f"Failed to scrape {result.get('url')}: {scrape_error}")
                            continue
                
                executed_queries.append({
                    "query": query.query_text,
                    "results_count": len(search_results),
                    "scraped_count": len(scraped_items),
                    "scraped_items": scraped_items[:3]  # Show first 3 for preview
                })
                
                total_results += len(search_results)
                
            except Exception as query_error:
                print(f"Failed to execute query '{query.query_text}': {query_error}")
                query_service.update_query_status(query.id, "failed", 0)
                continue
        
        # Log the research execution
        event_service.log_event(AgentEventCreate(
            brief_id=brief_id,
            agent_name="enhanced_web_search",
            event_type="research_executed",
            message=f"Executed {len(executed_queries)} queries, collected {total_results} results, scraped {total_scraped} items",
            payload={
                "queries_executed": len(executed_queries),
                "total_results": total_results,
                "total_scraped": total_scraped
            }
        ))
        
        return {
            "brief_id": brief_id,
            "executed_queries": executed_queries,
            "summary": {
                "queries_executed": len(executed_queries),
                "total_results": total_results,
                "total_scraped": total_scraped,
                "average_results_per_query": round(total_results / len(executed_queries), 1) if executed_queries else 0
            },
            "message": f"Successfully executed {len(executed_queries)} research queries"
        }
        
    except Exception as e:
        return {
            "error": str(e),
            "message": "Failed to execute research queries"
        }

@server.tool(
    name="research_and_scrape",
    description="Perform a single query research cycle: search, scrape, and save results",
)
def research_and_scrape(
    brief_id: int,
    query: str,
    max_results: int = 5,
    max_scrape_chars: int = 8000
) -> Dict[str, Any]:
    """Perform complete research cycle for a single query"""
    
    if not DATABASE_AVAILABLE:
        return {"error": "Database integration not available"}
    
    try:
        # Perform search
        search_results = search_brave(query, max_results)
        
        if not search_results:
            return {"error": f"No search results found for query: {query}"}
        
        # Scrape and save results
        scraped_items = []
        for result in search_results:
            try:
                content = scrape_website(result.get("url", ""), max_scrape_chars)
                
                # Calculate relevance score (simple keyword matching for now)
                relevance_score = calculate_relevance_score(query, content)
                
                # Save research item
                item_data = ResearchItemCreate(
                    brief_id=brief_id,
                    title=result.get("title", ""),
                    url=result.get("url", ""),
                    description=result.get("description", ""),
                    content=content,
                    source_type="web"
                )
                
                saved_item = research_service.add_research_item(item_data)
                
                scraped_items.append({
                    "id": saved_item['id'],
                    "title": result.get("title"),
                    "url": result.get("url"),
                    "description": result.get("description", "")[:200] + "...",
                    "content_length": len(content),
                    "relevance_score": relevance_score
                })
                
            except Exception as scrape_error:
                print(f"Failed to scrape {result.get('url')}: {scrape_error}")
                continue
        
        return {
            "brief_id": brief_id,
            "query": query,
            "search_results_count": len(search_results),
            "scraped_items": scraped_items,
            "summary": {
                "successful_scrapes": len(scraped_items),
                "average_content_length": sum(item["content_length"] for item in scraped_items) // len(scraped_items) if scraped_items else 0,
                "average_relevance": round(sum(item["relevance_score"] for item in scraped_items) / len(scraped_items), 2) if scraped_items else 0
            },
            "message": f"Successfully researched and scraped {len(scraped_items)} items for query: {query}"
        }
        
    except Exception as e:
        return {
            "error": str(e),
            "message": "Failed to perform research cycle"
        }

@server.tool(
    name="get_research_summary",
    description="Get a summary of all collected research for a brief",
)
def get_research_summary(brief_id: int) -> Dict[str, Any]:
    """Get comprehensive summary of research collected for a brief"""
    
    if not DATABASE_AVAILABLE:
        return {"error": "Database integration not available"}
    
    try:
        # Get research progress
        progress = research_service.get_research_progress(brief_id)
        
        # Get research items
        with research_service.db_manager.session_scope() as session:
            from shared.models import ResearchItem
            items = session.query(ResearchItem).filter(
                ResearchItem.brief_id == brief_id
            ).order_by(ResearchItem.created_at.desc()).limit(10).all()
        
        # Analyze content
        total_content_length = 0
        domains = set()
        sample_items = []
        
        for item in items:
            total_content_length += len(item.content or "")
            if item.url:
                domain = item.url.split('/')[2] if len(item.url.split('/')) > 2 else 'unknown'
                domains.add(domain)
            
            sample_items.append({
                "title": item.title,
                "url": item.url,
                "content_length": len(item.content or ""),
                "credibility_score": item.credibility_score,
                "relevance_score": item.relevance_score
            })
        
        return {
            "brief_id": brief_id,
            "progress": progress,
            "content_analysis": {
                "total_items": len(items),
                "total_content_length": total_content_length,
                "average_content_length": total_content_length // len(items) if items else 0,
                "unique_domains": len(domains),
                "domains": list(domains)[:10]  # Show first 10 domains
            },
            "sample_items": sample_items[:5],  # Show first 5 items
            "quality_metrics": {
                "average_credibility": round(sum(item.credibility_score for item in items) / len(items), 2) if items else 0,
                "average_relevance": round(sum(item.relevance_score for item in items) / len(items), 2) if items else 0,
                "verified_items": len([item for item in items if item.verification_status == "verified"])
            },
            "message": f"Research summary for brief {brief_id}: {len(items)} items collected"
        }
        
    except Exception as e:
        return {
            "error": str(e),
            "message": "Failed to get research summary"
        }

@server.tool(
    name="search_and_analyze",
    description="Search with advanced analysis: quality scoring, source diversity, content analysis",
)
def search_and_analyze(
    query: str,
    max_results: int = 10,
    analyze_content: bool = True
) -> Dict[str, Any]:
    """Perform search with quality analysis"""
    
    try:
        # Perform search
        search_results = search_brave(query, max_results)
        
        if not search_results:
            return {"error": f"No search results found for query: {query}"}
        
        analyzed_results = []
        domains = set()
        total_quality_score = 0
        
        for result in search_results:
            url = result.get("url", "")
            title = result.get("title", "")
            description = result.get("description", "")
            
            # Extract domain
            domain = url.split('/')[2] if len(url.split('/')) > 2 else 'unknown'
            domains.add(domain)
            
            # Calculate quality score based on various factors
            quality_score = calculate_source_quality(url, title, description)
            total_quality_score += quality_score
            
            analyzed_result = {
                "title": title,
                "url": url,
                "description": description,
                "domain": domain,
                "quality_score": quality_score
            }
            
            # Optional content analysis
            if analyze_content:
                try:
                    content = scrape_website(url, max_chars=3000)  # Smaller sample for analysis
                    analyzed_result.update({
                        "content_preview": content[:300] + "..." if len(content) > 300 else content,
                        "content_length": len(content),
                        "relevance_score": calculate_relevance_score(query, content)
                    })
                except:
                    analyzed_result.update({
                        "content_preview": "Failed to scrape content",
                        "content_length": 0,
                        "relevance_score": 0
                    })
            
            analyzed_results.append(analyzed_result)
        
        # Calculate diversity and quality metrics
        diversity_score = len(domains) / len(search_results) * 100 if search_results else 0
        average_quality = total_quality_score / len(search_results) if search_results else 0
        
        return {
            "query": query,
            "results": analyzed_results,
            "analysis": {
                "total_results": len(search_results),
                "unique_domains": len(domains),
                "diversity_score": round(diversity_score, 1),
                "average_quality_score": round(average_quality, 2),
                "domains": list(domains)
            },
            "recommendations": generate_search_recommendations(analyzed_results, diversity_score, average_quality),
            "message": f"Analyzed {len(search_results)} search results for query: {query}"
        }
        
    except Exception as e:
        return {
            "error": str(e),
            "message": "Failed to perform search analysis"
        }

# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------

def calculate_relevance_score(query: str, content: str) -> float:
    """Calculate relevance score based on keyword matching"""
    if not query or not content:
        return 0.0
    
    query_words = set(query.lower().split())
    content_words = set(content.lower().split())
    
    # Simple relevance scoring
    matches = len(query_words.intersection(content_words))
    max_possible = len(query_words)
    
    return round(matches / max_possible, 2) if max_possible > 0 else 0.0

def calculate_source_quality(url: str, title: str, description: str) -> float:
    """Calculate source quality score based on various factors"""
    score = 0.5  # Base score
    
    # Domain quality indicators (simplified)
    domain = url.split('/')[2] if len(url.split('/')) > 2 else ''
    
    # Boost for known quality domains
    quality_domains = [
        'wikipedia.org', 'britannica.com', 'smithsonianmag.com',
        'nationalgeographic.com', 'bbc.com', 'reuters.com',
        'ap.org', 'pbs.org', 'npr.org', 'history.com'
    ]
    
    if any(domain.endswith(qd) for qd in quality_domains):
        score += 0.3
    
    # Boost for .edu and .gov domains
    if domain.endswith('.edu') or domain.endswith('.gov'):
        score += 0.2
    
    # Title quality (length and keywords)
    if title and len(title) > 20:
        score += 0.1
    
    # Description quality
    if description and len(description) > 50:
        score += 0.1
    
    return min(1.0, score)  # Cap at 1.0

def generate_search_recommendations(results: List[Dict], diversity_score: float, quality_score: float) -> List[str]:
    """Generate recommendations based on search analysis"""
    recommendations = []
    
    if diversity_score < 50:
        recommendations.append("Consider broadening search terms to get more diverse sources")
    
    if quality_score < 0.6:
        recommendations.append("Try more specific queries to find higher quality sources")
    
    if len(results) < 5:
        recommendations.append("Consider alternative search terms to find more results")
    
    # Check for academic/authoritative sources
    quality_sources = [r for r in results if r.get('quality_score', 0) > 0.7]
    if len(quality_sources) < 2:
        recommendations.append("Look for more authoritative sources (academic, government, established media)")
    
    if not recommendations:
        recommendations.append("Search quality looks good - diverse sources with reasonable quality scores")
    
    return recommendations

# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    server.run() 