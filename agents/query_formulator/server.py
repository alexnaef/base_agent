"""
Query Formulator MCP Server - FastMCP integration only.
"""
from agent import QueryFormulatorAgent

def main():
    """Main entry point for the query formulator agent"""
    agent = QueryFormulatorAgent()
    
    if not agent.is_ready():
        print("❌ Query Formulator Agent: Not ready (OpenAI client unavailable)")
        return
    
    print("🚀 Query Formulator Agent: Starting server...")
    agent.run()

if __name__ == "__main__":
    main()