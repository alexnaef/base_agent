"""
Fact Checker MCP Server - FastMCP integration only.
"""
from agent import FactCheckerAgent

def main():
    """Main entry point for the fact checker agent"""
    agent = FactCheckerAgent()
    
    if not agent.is_ready():
        print("❌ Fact Checker Agent: Not ready (OpenAI client unavailable)")
        return
    
    print("🚀 Fact Checker Agent: Starting server...")
    agent.run()

if __name__ == "__main__":
    main()