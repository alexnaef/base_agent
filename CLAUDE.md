# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Running the Application
```bash
# Install dependencies
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run the MCP client with web-search server
python mcp-client/client.py web-search/server.py

# Run server standalone (optional for inspection)
python web-search/server.py | cat
```

### Environment Setup
Required API keys:
- `OPENAI_API_KEY` - OpenAI API key for GPT models
- `BRAVE_API_KEY` - Brave Search API key for web search functionality

## Architecture Overview

This is a **Fast-MCP** (Model Control Protocol) demonstration project consisting of two main components:

### 1. MCP Client (`mcp-client/`)
- **Entry point**: `client.py` - Main client that spawns MCP servers and handles OpenAI integration
- **System prompt**: `sys_prompt.py` - Contains the research workflow instructions for the AI agent
- **Dependencies**: Uses OpenAI's new responses API with dual-model approach:
  - `TOOL_MODEL` (default: gpt-4.1-mini) - For tool planning and execution
  - `FINAL_MODEL` (default: gpt-4.1) - For high-quality final responses

### 2. Web Search Server (`web-search/`)
- **Entry point**: `server.py` - FastMCP server exposing three research tools
- **Available tools**:
  - `suggest_google_searches(topic, max_suggestions)` - Generates research queries
  - `search_brave(query, max_results)` - Performs web search via Brave API
  - `scrape_website(url, max_chars)` - Extracts clean text from web pages

### Key Design Patterns

**Dual-Model Architecture**: The client uses a cheaper model for tool execution and planning, then switches to a higher-quality model for final answer synthesis.

**Streaming Response Handling**: The client processes OpenAI's streaming responses in real-time, handling both text content and function calls.

**Research Workflow**: The system prompt in `sys_prompt.py` defines a specific 4-step research methodology:
1. Generate search queries
2. Search for each query
3. Scrape all found URLs
4. Synthesize findings

**MCP Protocol**: Uses Fast-MCP for tool registration and execution, allowing the server to expose Python functions as tools that the OpenAI client can call.

## Model Configuration

The system supports environment variable configuration:
- `OPENAI_TOOL_MODEL` - Model for tool calls (default: gpt-4.1-mini)
- `OPENAI_FINAL_MODEL` - Model for final answers (default: gpt-4.1)

## Extending the System

To add new MCP servers:
1. Create a new directory with a server script
2. Use `@server.tool()` decorator to expose functions
3. Point the client at your new server: `python mcp-client/client.py your-server/server.py`

The client architecture supports connecting to any MCP-compatible server that exposes tools via the protocol.