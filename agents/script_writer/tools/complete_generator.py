"""
Complete podcast generation tool.
"""
import sys
import os
from typing import Dict, Any

# Add parent directories to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../..'))

from agents.services import ValidationService


class CompleteGeneratorTool:
    """Tool for end-to-end podcast generation"""
    
    def __init__(self, agent):
        self.agent = agent
    
    def register(self, server):
        """Register tool with FastMCP server"""
        @server.tool(
            name="generate_complete_podcast",
            description="End-to-end podcast generation: create outline and write full script",
        )
        def generate_complete_podcast(brief_id: int) -> Dict[str, Any]:
            return self.execute(brief_id)
    
    def execute(self, brief_id: int) -> Dict[str, Any]:
        """Generate a complete podcast from research brief in one step"""
        
        try:
            # Validate inputs
            brief_id = ValidationService.validate_brief_id(brief_id)
            
            # Step 1: Create outline
            from .outline_creator import OutlineCreatorTool
            outline_creator = OutlineCreatorTool(self.agent)
            outline_result = outline_creator.execute(brief_id)
            
            if "error" in outline_result:
                return outline_result
            
            outline = outline_result["outline"]
            
            # Step 2: Write script
            from .script_writer import ScriptWriterTool
            script_writer = ScriptWriterTool(self.agent)
            script_result = script_writer.execute(brief_id, outline)
            
            if "error" in script_result:
                return script_result
            
            # Combine results
            return self.agent.create_success_response(
                data={
                    "brief_id": brief_id,
                    "script_id": script_result["script_id"],
                    "title": script_result["title"],
                    "content": script_result["content"],
                    "outline": outline,
                    "metrics": script_result["metrics"],
                    "workflow": [
                        "✅ Outline created",
                        "✅ Introduction written", 
                        f"✅ {len(outline.get('sections', []))} main sections written",
                        "✅ Conclusion written",
                        "✅ Script saved to database"
                    ]
                },
                message="Complete podcast generated successfully"
            )
            
        except Exception as e:
            return self.agent.create_error_response(str(e))