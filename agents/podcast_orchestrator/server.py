"""
Podcast Orchestrator MCP Server - FastMCP integration only.
"""
from agent import PodcastOrchestratorAgent

def main():
    """Main entry point for the podcast orchestrator agent"""
    agent = PodcastOrchestratorAgent()
    
    if not agent.is_ready():
        print("❌ Podcast Orchestrator Agent: Not ready (OpenAI client unavailable)")
        return
    
    print("🚀 Podcast Orchestrator Agent: Starting server...")
    agent.run()

if __name__ == "__main__":
    main()