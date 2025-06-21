import os
import re
from typing import List, Dict

import requests
from bs4 import BeautifulSoup
from mcp.server.fastmcp.server import FastMCP

from dotenv import load_dotenv
load_dotenv()

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
    name="web-search",
    instructions="""
This server provides three tools that assist research agents:

1. `suggest_google_searches` – generates thoughtful Google-style searches for a topic.
2. `search_brave` – queries Brave Web Search API and returns the top organic results.
3. `scrape_website` – downloads the readable text from a URL for analysis.
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
# Entrypoint
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    server.run() 