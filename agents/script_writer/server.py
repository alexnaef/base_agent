"""
Script Writer MCP Server - FastMCP integration only.
"""
from agent import ScriptWriterAgent

def main():
    """Main entry point for the script writer agent"""
    agent = ScriptWriterAgent()
    
    if not agent.is_ready():
        print("❌ Script Writer Agent: Not ready (OpenAI client unavailable)")
        return
    
    print("🚀 Script Writer Agent: Starting server...")
    agent.run()

if __name__ == "__main__":
    main()