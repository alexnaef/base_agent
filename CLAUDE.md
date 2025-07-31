# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Running the Application
```bash
# Install dependencies
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run individual MCP agent servers (for testing/inspection)
python agents/podcast_orchestrator/server.py | cat
python agents/query_formulator/server.py | cat
python agents/fact_checker/server.py | cat
python agents/script_writer/server.py | cat

# Database operations
python shared/init_db.py  # Initialize database tables
python show_manuscript.py [brief_id]  # View generated manuscript
python show_full_manuscript.py [brief_id]  # View complete manuscript with metadata
```

### Environment Setup
Required API keys:
- `OPENAI_API_KEY` - OpenAI API key for GPT models
- `BRAVE_API_KEY` - Brave Search API key for web search functionality

Optional database configuration:
- `DATABASE_URL` - Database connection string (defaults to SQLite: `sqlite:///./podcast_research.db`)

## Architecture Overview

This is a **Fast-MCP** (Model Control Protocol) multi-agent system for generating long-form podcast manuscripts. The project demonstrates both simple research tools and a complex multi-agent orchestration pattern.

### Core Components

### 1. MCP Client (`mcp-client/`)
- **Entry point**: `client.py` - Main client that spawns MCP servers and handles OpenAI integration
- **System prompt**: `sys_prompt.py` - Contains the research workflow instructions for the AI agent
- **Dependencies**: Uses OpenAI's responses API with dual-model approach:
  - `TOOL_MODEL` (default: gpt-4.1-mini) - For tool planning and execution
  - `FINAL_MODEL` (default: gpt-4.1) - For high-quality final responses

### 2. Shared Infrastructure (`shared/`)
Common data layer and services:
- **Models** (`models.py`) - SQLAlchemy models for research briefs, items, claims, events, and manuscripts
- **Database** (`database.py`) - Database connection management with SQLite default and PostgreSQL support
- **Services** (`services.py`) - Business logic layer for research operations, event logging, and data persistence
- **Embeddings** (`embeddings.py`) - OpenAI embeddings integration for semantic similarity matching

### 3. Multi-Agent Podcast System (`agents/`)
Specialized agents for deep research and manuscript generation:

- **Podcast Orchestrator** (`agents/podcast_orchestrator/`) - Master controller that manages the entire workflow, creates research briefs, monitors progress, and coordinates phase transitions
- **Query Formulator** (`agents/query_formulator/`) - Generates targeted search queries and expands research scope based on embeddings and context
- **Fact Checker** (`agents/fact_checker/`) - Cross-verifies claims, scores source credibility, and validates research quality
- **Script Writer** (`agents/script_writer/`) - Transforms research into structured podcast manuscripts with proper citations and narrative flow

### 4. Agent Infrastructure (`agents/common/` & `agents/services/`)
Shared utilities and services for all agents:
- **Base Classes** - Common agent functionality, OpenAI client management, JSON parsing
- **Services** - Prompt management, validation, metrics calculations
- **Configuration** - Centralized settings and model configurations

### Key Design Patterns

**Multi-Agent Orchestration**: The podcast orchestrator coordinates specialized agents through a shared database and event system, enabling complex multi-step workflows.

**Research Graph**: Claims and research items are linked through embeddings and verification scores, creating a knowledge graph that supports gap detection and coverage analysis.

**Phase-Based Workflow**: Research progresses through distinct phases (PENDING → IN_PROGRESS → COMPLETED) with quality gates and metric thresholds.

**Dual-Model Strategy**: Cheaper models handle tool orchestration while high-quality models generate final content.

**Shared State Management**: All agents operate on shared data models through the services layer, enabling coordination without direct communication.

## Data Models

The system uses SQLAlchemy models for persistence:
- **ResearchBrief** - Central entity containing topic, angle, tone, and target length
- **ResearchItem** - Individual pieces of research with URLs, summaries, and verification status
- **Claim** - Extracted factual claims with confidence scores and source attribution
- **AgentEvent** - Audit trail of agent actions and workflow progression
- **PodcastScript** - Final manuscript with chapters, citations, and metadata

## Model Configuration

Environment variables for model selection:
- `OPENAI_TOOL_MODEL` - Model for tool calls (default: gpt-4.1-mini)
- `OPENAI_FINAL_MODEL` - Model for final answers (default: gpt-4.1)