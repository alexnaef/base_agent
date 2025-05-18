# Base Agent OpenAI

This repository contains two main components:

- `weather` (server): A FastMCP-based weather server providing weather alerts and forecasts.
- `mcp-client` (client): A client that connects to the MCP server and processes queries using OpenAI chat completions.

## Prerequisites

- Python 3.11 or higher
- Git
- An OpenAI API key

## Clone the repository

```bash
git clone https://github.com/username/base_agent.git
cd base_agent
```

## Setup and run the Weather Server

1. Navigate to the `weather` directory:
    ```bash
    cd weather
    ```

2. Create and activate a virtual environment:
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    ```

3. Install dependencies:
    ```bash
    pip install httpx>=0.28.1 'mcp[cli]>=1.9.0'
    ```

4. Run the server:
    ```bash
    python weather.py
    ```

The server will start and listen for tool calls over standard I/O.

## Setup and run the MCP client

1. Open a new terminal window/tab (keep the server running), and navigate to the `mcp-client` directory:
    ```bash
    cd mcp-client
    ```

2. Create and activate a virtual environment:
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    ```

3. Install dependencies:
    ```bash
    pip install openai>=0.27.0 mcp>=1.9.0 python-dotenv>=1.1.0
    ```

4. Create a `.env` file in the `mcp-client` directory with your OpenAI API key:
    ```
    OPENAI_API_KEY=your_api_key_here
    ```

5. Run the client, pointing it to the server script:
    ```bash
    python client.py ../weather/weather.py
    ```

## Usage

Once the client is running, type your queries at the `Query:` prompt. Available tools on the server include:

- `get_alerts(state: str)`: Fetch active weather alerts for a given two-letter US state code.
- `get_forecast(latitude: float, longitude: float)`: Fetch weather forecast for a given location.

Type `quit` to exit the client.

## License

Add your license information here. 
