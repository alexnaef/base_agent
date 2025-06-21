# Base Agent – Research & Web Search Demo

This repository demonstrates how to wire up **Fast-MCP** tools with an OpenAI-powered client.

Current components:

1. `web-search` (server) – exposes three research tools:
   • `suggest_google_searches(topic, max_suggestions)`
   • `search_brave(query, max_results)`  ➡️ calls Brave Web Search API
   • `scrape_website(url, max_chars)`  ➡️ returns cleaned page text
2. `mcp-client` (client) – launches any MCP server script you point it at and lets GPT use those tools via function-calling.

---

## 1. Prerequisites

• Python 3.11+
• Git
• Two API keys:
   – **OpenAI** → `OPENAI_API_KEY`
   – **Brave Search** → `BRAVE_API_KEY` (free tier is fine – see the [Brave docs](https://api-dashboard.search.brave.com/app/documentation/web-search/get-started))

```bash
# macOS/Linux example – add your keys to shell startup or .env
export OPENAI_API_KEY="sk-..."
export BRAVE_API_KEY="brv-..."
```

---

## 2. Install dependencies

At project root:

```bash
python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
```

The `requirements.txt` already lists `openai`, `mcp`, `requests`, `beautifulsoup4`, `python-dotenv`.

---

## 3. Run the demo

The client **spawns** the server under the hood, so only one command is needed:

```bash
python mcp-client/client.py web-search/server.py
```

You should see something like:
```
Connected to server with tools: ['suggest_google_searches', 'search_brave', 'scrape_website']

MCP Client Started!
Query:
```
Now type queries such as:

* `Give me 5 queries to research SpaceX`
* `Search the web for "Elon Musk controversies"` – the model will call `search_brave`
* `Scrape_website https://example.com` (or let GPT decide when to call it)

Type `quit` to exit.

### Running the server standalone (optional)
If you'd like to just inspect the server:
```bash
python web-search/server.py | cat  # add | cat to avoid pager issues
```
But normally you let the client handle it.

---

## 4. Extending

Add more Fast-MCP servers (agents) in their own folders and point the same client at them, or modify `mcp-client/client.py` to connect to multiple servers with different toolsets.

---

## License
Add your license info here. 
