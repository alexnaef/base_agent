# 🧠📻 Deep-Research Podcast Agent – Blueprint

## 0. Purpose
Deliver a **30-40 min podcast manuscript** of journalistic quality from any user-supplied topic.  
The result should read as a single-voice monologue, richly sourced, deeply researched, and ready to be performed aloud.

OpenAI's [Deep Research](https://openai.com/index/introducing-deep-research/) shows how multiple agents can chain tools to dig, verify, and produce knowledge.  
We adapt that idea for long-form podcast creation.

---

## 1. User Flow
1. **Prompt intake**  
   • User enters a broad topic (e.g. "Genghis Khan", "World War II", "latest CRISPR breakthroughs").
2. **Clarification loop**  
   • System asks a few smart, branching questions to focus scope (e.g. "Do you want a general overview or emphasis on military strategy?").  
   • User responses refine the *Research Brief* (goal statement, angle, desired tone, length).
3. **Research cycle (multi-pass)**  
   • Search-Agent produces queries → Scrape/Fetcher collects docs → Fact-Checker validates & enriches → Research-Planner detects gaps & issues new queries.  
   • Iterate until coverage, relevance & credibility thresholds are met.
4. **Manuscript generation**  
   • Script-Writer Agent transforms the vetted research graph into a compelling monologue (intro-body-outro, narrative hooks, segues, citations).
5. **Delivery**  
   • User receives Markdown/JSON manuscript + sources.  
   • (Future) TTS pipeline turns script into polished audio.

---

## 2. Agent Catalogue
| Agent | Responsibilities | Key Tools |
|-------|------------------|-----------|
| **Query-Formulator** | Draft Google-style search strings, expand with related concepts & entities. | LLM, embeddings, `suggest_google_searches` |
| **Fetcher / Web-Searcher** | Execute searches, scrape top N links, chunk and embed text. | Brave API, custom scraper, vector DB |
| **Fact-Checker** | Cross-verify claims, flag contradictions, score source credibility. | Web search, citation graph analyzer |
| **Research-Planner** | Maintain research map, detect knowledge gaps, request more queries or POVs. | Reasoning LLM, graph DB |
| **Script-Writer** | Craft 5-7 chapter podcast script, weave narrative, insert citations, ensure target read-time. | High-quality LLM, style prompts |
| *(Future)* Audio-Producer | Turn manuscript into narrated audio, add music beds, export MP3. | TTS, DAW pipeline |

All agents communicate via an **event bus / task queue** (e.g. Redis Pub/Sub); each publishes intermediate artefacts to Postgres + Vector store for shared context.

---

## 3. Data Artefacts
• **ResearchItem** – {id, title, url, summary, embedding, verified?}  
• **Claim** – {id, text, sources[], veracity_score}  
• **ResearchGraph** – Directed graph linking ResearchItems & Claims  
• **PodcastScript** – {chapters[], total_read_time_min, citations[]}

---

## 4. Tech Stack (MVP)
* Python 3.11  
* Fast-MCP for agent servers (tool exposure)  
* OpenAI GPT-4 / GPT-4-mini (mini for tool orchestration, full model for final prose)  
* Brave Search API + Requests/BS4 scraper  
* Postgres (metadata) + Weaviate/Pinecone (embeddings)  
* Redis (queues / pub-sub)  
* Docker-compose for local dev

---

## 5. Execution Phases
1. **P0 – Foundation _(done)_**  
   _Status: complete in codebase_
   - `web-search/` MCP server exposing `suggest_google_searches`, `search_brave`, `scrape_website`  
   - Streaming MCP client with iterative tool-call loop + dual-model strategy  
   - README & blueprint docs

2. **P1 – Clarification Agent & Brief Schema**  
   **Goal:** Capture a precise *Research Brief* before heavy research starts.  
   **Tasks:**  
   - **Data model** – Add `research_briefs` table (Postgres) + SQLAlchemy model.  
   - **Agent** – Create `clarification-agent/clarifier_server.py` (Fast-MCP) with tool `ask_user_clarification`.  
   - **Prompt design** – System prompt that asks 2-4 disambiguation questions (angle, timeframe, tone).  
   - **Workflow hook** – Orchestrator waits for brief → stores it → emits `brief.ready` event.  
   - **Client** – Show the follow-up Q&A in terminal / API.  
   - **Exit criteria:** Persisted brief JSON with `topic`, `angle`, `length_min`, `tone`.

3. **P2 – Multi-Agent Orchestration**  
   **Goal:** Route tasks between Query-Formulator, Fetcher, Fact-Checker.  
   **Tasks:**  
   - **Infrastructure** – Dockerise Redis; publish helper `bus.py` wrapper.  
   - **Message schema** – Define `TaskMessage` (type, payload, brief_id, parent_id).  
   - **Query-Formulator Agent**  
     • Server path `agents/query_formulator/server.py` (Fast-MCP).  
     • Tool: `generate_queries(brief_id, n)` → writes `search_query` rows.  
   - **Fetcher Agent**  
     • Subscribes to `search_query.created`; calls Brave & Scraper; stores `ResearchItem`s.  
   - **Fact-Checker Agent**  
     • Listens to `research_item.created`; cross-verifies, sets `verified=True/False`.  
   - **Orchestrator Service**  
     • Cron-like loop: when ≥ X verified items → emit `research.complete`.  
   - **Observability** – Log events to stdout + Postgres table `events`.

4. **P3 – Research Graph & Planner**  
   **Goal:** Represent knowledge, detect gaps, and request more research.  
   **Tasks:**  
   - **Schema** – Create tables `claims`, `edges`, `graph_meta`; add pgvector column for embeddings.  
   - **Embedder** – Background worker that embeds `ResearchItem` content (OpenAI embeddings).  
   - **Planner Agent**  
     • Reads current graph, brief, and `coverage_threshold`.  
     • Prompt: "Identify missing aspects; output follow-up queries."  
     • Publishes `search_query.created` for new angles.  
   - **Loop control** – Stop when coverage score ≥ 0.9 or max_iterations reached.  

5. **P4 – Script-Writer Agent**  
   **Goal:** Turn vetted research into a 30-40-min script.  
   **Tasks:**  
   - **Outline prompt** – Generate 5-7 chapter outline first; user can accept/decline.  
   - **Draft prompt** – For each chapter, craft prose ≤ ≈700 words (read-time budget).  
   - **Citation injection** – Append `(Source: URL)` after fact paragraphs.  
   - **Agent implementation** – `agents/script_writer/server.py`; uses FINAL_MODEL.  
   - **Validation** – Run through Fact-Checker one last pass; fail if new contradictions.  
   - **Persistence** – Save `podcast_scripts` table (markdown + metadata).  

6. **P5 – UX & API**  
   **Goal:** Expose progress + manuscripts via Web UI / REST.  
   **Tasks:**  
   - **API** – FastAPI `backend/api.py` endpoints: `/briefs`, `/scripts/{id}`, `/events/stream`.  
   - **Web front-end** – React/Next dashboard: status timeline, agent logs, markdown preview.  
   - **Auth** – Simple API-key header for now.  
   - **CI/CD** – GitHub Actions: lint, test, docker-build.

7. **P6 – (Optional) Audio & Post-production**  
   **Goal:** Convert manuscript to studio-quality audio.  
   **Tasks:**  
   - **Voice selection** – Integrate ElevenLabs / OpenAI TTS.  
   - **Segment synthesis** – Generate per-chapter WAV, add music beds (FFmpeg).  
   - **Mixer script** – Concatenate, normalise loudness, export MP3 + chapter markers.

---

## 6. Prompts & Models Strategy
• **Tool planning** → `gpt-4.1-mini` (cheap).  
• **Writing & summarisation** → `gpt-4.1` (quality).  
• Clearly separate system prompts: *planning*, *fact-checking*, *writing*.

---

## 7. Quality Guardrails
1. Minimum 3 independent sources per key claim.  
2. Automated citation checker ensures every paragraph cites something.  
3. Fact-Checker score < 0.8 blocks script generation; Planner re-loops.

---

## 8. Future Enhancements
* Automatic translation & localisation.  
* Real-time user steering ("focus more on economic impact").  
* Fact-Checker powered by Retrieval-Augmented Generation.  
* Fine-tuned voice cloning for consistent podcast narration.

---

*Last updated: {{TBD – auto-insert commit hash/date}}* 