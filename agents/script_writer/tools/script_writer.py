"""
Podcast script writing tool.
"""
import sys
import os
import re
from typing import Dict, Any

# Add parent directories to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../..'))

from shared.services import research_service, script_service
from shared.schemas import PodcastScriptCreate
from prompts.script import PODCAST_SCRIPT_PROMPT
from agents.services import PromptService, ValidationService, MetricsService
from agents.common import AgentConfig


class ScriptWriterTool:
    """Tool for writing podcast scripts"""
    
    def __init__(self, agent):
        self.agent = agent
        self.prompt_service = PromptService("script_writer")
        self.prompt_service.register_template("script", PODCAST_SCRIPT_PROMPT)
    
    def register(self, server):
        """Register tool with FastMCP server"""
        @server.tool(
            name="write_podcast_script",
            description="Generate the complete podcast manuscript from outline and research data",
        )
        def write_podcast_script(brief_id: int, outline: Dict[str, Any]) -> Dict[str, Any]:
            return self.execute(brief_id, outline)
    
    def execute(self, brief_id: int, outline: Dict[str, Any]) -> Dict[str, Any]:
        """Write the complete podcast script from outline and available research"""
        
        try:
            # Validate inputs
            brief_id = ValidationService.validate_brief_id(brief_id)
            
            # Get the research brief
            brief = research_service.get_brief(brief_id)
            if not brief:
                return self.agent.create_error_response("Research brief not found")
            
            # Get available research content
            research_content = self._get_research_content(brief_id, brief['topic'])
            
            # Generate script sections
            script_sections = {}
            full_script = []
            total_words = 0
            
            # Write introduction
            intro_script, intro_words = self._write_section(
                brief=brief,
                section_title="Introduction",
                key_points=outline.get("introduction", {}).get("setup", "Episode introduction"),
                narrative_approach="Engaging hook and episode preview",
                duration_min=outline.get("introduction", {}).get("duration_min", 2),
                research_content=research_content
            )
            
            script_sections["introduction"] = intro_script
            full_script.append(f"## Introduction\n\n{intro_script}")
            total_words += intro_words
            
            # Write main sections
            for i, section in enumerate(outline.get("sections", [])):
                section_script, section_words = self._write_section(
                    brief=brief,
                    section_title=section.get("title", f"Section {i+1}"),
                    key_points=", ".join(section.get("key_points", [])),
                    narrative_approach=section.get("narrative_approach", "Informative discussion"),
                    duration_min=section.get("duration_min", 4),
                    research_content=research_content
                )
                
                script_sections[f"section_{i+1}"] = section_script
                full_script.append(f"## {section.get('title', f'Section {i+1}')}\n\n{section_script}")
                total_words += section_words
            
            # Write conclusion
            conclusion_script, conclusion_words = self._write_section(
                brief=brief,
                section_title="Conclusion",
                key_points=outline.get("conclusion", {}).get("summary", "Episode summary"),
                narrative_approach="Wrap up with key takeaways and final thoughts",
                duration_min=outline.get("conclusion", {}).get("duration_min", 2),
                research_content=research_content
            )
            
            script_sections["conclusion"] = conclusion_script
            full_script.append(f"## Conclusion\n\n{conclusion_script}")
            total_words += conclusion_words
            
            # Combine full script
            complete_script = "\n\n".join(full_script)
            
            # Calculate metrics
            estimated_read_time = MetricsService.calculate_read_time(complete_script)
            citation_count = MetricsService.count_citations(complete_script)
            
            # Save to database
            script_data = PodcastScriptCreate(
                brief_id=brief_id,
                title=outline.get("title", f"Podcast: {brief['topic']}"),
                outline=outline,
                content=complete_script
            )
            
            saved_script = script_service.create_script(script_data)
            
            # Update with quality metrics
            script_service.update_script_quality(
                saved_script.id if hasattr(saved_script, 'id') else saved_script['id'],
                quality_score=0.85,  # Would be calculated based on various factors
                citation_count=citation_count
            )
            
            # Log the event
            self.agent.log_event(
                brief_id=brief_id,
                event_type="script_completed", 
                message="Generated complete podcast script",
                payload={
                    "word_count": total_words,
                    "estimated_read_time_min": estimated_read_time,
                    "citation_count": citation_count
                }
            )
            
            return self.agent.create_success_response(
                data={
                    "brief_id": brief_id,
                    "script_id": saved_script.id if hasattr(saved_script, 'id') else saved_script['id'],
                    "title": outline.get("title"),
                    "content": complete_script,
                    "metrics": {
                        "word_count": total_words,
                        "estimated_read_time_min": round(estimated_read_time, 1),
                        "citation_count": citation_count,
                        "sections": len(outline.get("sections", [])) + 2  # +2 for intro and conclusion
                    }
                },
                message="Podcast script generated successfully"
            )
            
        except Exception as e:
            return self.agent.create_error_response(str(e))
    
    def _get_research_content(self, brief_id: int, topic: str) -> str:
        """Get research content for script generation"""
        # For now, we'll simulate this with a placeholder
        # In a full implementation, this would gather actual research
        return f"""
Research Summary for: {topic}

Note: This is a demonstration with simulated research content.
In the full implementation, this would contain:
- Verified research items from web scraping
- Fact-checked claims and statistics  
- Expert quotes and citations
- Historical data and context
- Multiple perspective sources

For now, we'll generate a high-quality script based on general knowledge
while maintaining the proper structure and citation format.
"""
    
    def _write_section(self, brief: Dict, section_title: str, key_points: str, 
                      narrative_approach: str, duration_min: int, research_content: str) -> tuple:
        """Write a single script section"""
        target_words = duration_min * AgentConfig.WORDS_PER_MINUTE
        
        prompt = self.prompt_service.render_template(
            "script",
            topic=brief['topic'],
            angle=brief['angle'] or "comprehensive overview",
            tone=brief['tone'],
            section_title=section_title,
            key_points=key_points,
            narrative_approach=narrative_approach,
            duration_min=duration_min,
            target_words=target_words,
            research_content=research_content
        )
        
        system_prompt = self.prompt_service.get_system_message(
            "podcast scriptwriter who writes engaging, conversational content"
        )
        
        section_script = self.agent.openai.execute_final_prompt(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )
        
        word_count = MetricsService.calculate_word_count(section_script)
        return section_script, word_count