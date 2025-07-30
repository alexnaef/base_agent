import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

from typing import Dict, Any, List
import json
import re
from datetime import datetime
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv(dotenv_path="../../.env", override=True)
load_dotenv(override=True)

from mcp.server.fastmcp.server import FastMCP
from shared.models import ResearchStatus
from shared.schemas import PodcastScriptCreate, AgentEventCreate
from shared.services import research_service, script_service, event_service

# Initialize OpenAI client
try:
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        openai_client = OpenAI(api_key=api_key)
        OPENAI_AVAILABLE = True
        print("✅ OpenAI client initialized successfully")
    else:
        print("❌ OPENAI_API_KEY not found in environment")
        openai_client = None
        OPENAI_AVAILABLE = False
except Exception as e:
    print(f"Warning: OpenAI client not available: {e}")
    openai_client = None
    OPENAI_AVAILABLE = False

server = FastMCP(
    name="script-writer",
    instructions="""
    This is the Script Writer Agent - specialized in creating compelling podcast manuscripts.
    
    Key responsibilities:
    1. Generate structured outlines for 30-minute podcast episodes
    2. Transform research data into engaging narrative prose
    3. Ensure proper citation integration and fact attribution
    4. Optimize content for audio narration (clear structure, smooth transitions)
    5. Meet target word count and estimated read time requirements
    
    Writing style guidelines:
    - Conversational yet authoritative tone
    - Clear narrative arc with intro, development, and conclusion
    - Smooth transitions between topics and sections
    - Strategic use of hooks, tension, and payoffs
    - Proper attribution and citation integration
    """,
)

PODCAST_OUTLINE_PROMPT = """
You are an expert podcast scriptwriter. Create a detailed outline for a {target_length_min}-minute podcast episode.

Topic: {topic}
Angle: {angle}
Tone: {tone}

Requirements:
- Target length: {target_length_min} minutes (~{target_words} words)
- Create 6-8 main sections with clear narrative flow
- Each section should have 2-4 subsections
- Include estimated time allocation for each section
- Design for single-voice narration
- Ensure compelling introduction and strong conclusion

Return a JSON structure with:
{{
  "title": "Engaging episode title",
  "introduction": {{
    "hook": "Opening hook or question",
    "setup": "Context and episode preview",
    "duration_min": 2
  }},
  "sections": [
    {{
      "title": "Section title",
      "key_points": ["Point 1", "Point 2", "Point 3"],
      "narrative_approach": "How to present this section",
      "duration_min": 4
    }}
  ],
  "conclusion": {{
    "summary": "Key takeaways",
    "call_to_action": "Ending thought or question",
    "duration_min": 2
  }},
  "total_duration_min": {target_length_min}
}}
"""

PODCAST_SCRIPT_PROMPT = """
You are an expert podcast scriptwriter. Write the complete script for this section of a podcast episode.

Episode Context:
- Topic: {topic}
- Overall angle: {angle}
- Tone: {tone}
- Target audience: General interest, intelligent listeners

Section Details:
- Section: {section_title}
- Key points to cover: {key_points}
- Narrative approach: {narrative_approach}
- Target duration: {duration_min} minutes (~{target_words} words)

Available Research:
{research_content}

Instructions:
1. Write in a conversational, engaging style suitable for audio
2. Use "I" or "we" perspective to create connection with listeners
3. Include smooth transitions and natural speech patterns
4. Integrate research findings with proper attribution: "(Source: [URL])"
5. Use rhetorical questions and hooks to maintain engagement
6. Write exactly for the target word count
7. End with a natural transition to the next section

Write the complete script for this section:
"""

@server.tool(
    name="create_podcast_outline",
    description="Generate a structured outline for a podcast episode based on research brief",
)
def create_podcast_outline(brief_id: int) -> Dict[str, Any]:
    """Create a detailed podcast outline from research brief"""
    
    if not OPENAI_AVAILABLE:
        return {"error": "OpenAI client not available"}
    
    try:
        # Get the research brief
        brief = research_service.get_brief(brief_id)
        if not brief:
            return {"error": "Research brief not found"}
        
        # Calculate target words (155 words per minute for narration)
        target_words = brief['target_length_min'] * 155
        
        # Create the outline prompt
        prompt = PODCAST_OUTLINE_PROMPT.format(
            topic=brief['topic'],
            angle=brief['angle'] or "comprehensive overview",
            tone=brief['tone'],
            target_length_min=brief['target_length_min'],
            target_words=target_words
        )
        
        # Generate outline using OpenAI
        response = openai_client.chat.completions.create(
            model="gpt-4.1",
            messages=[
                {"role": "system", "content": "You are an expert podcast producer and scriptwriter."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )
        
        outline_text = response.choices[0].message.content
        
        # Parse JSON from response
        try:
            outline = json.loads(outline_text)
        except json.JSONDecodeError:
            # If JSON parsing fails, extract JSON from markdown code block
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', outline_text, re.DOTALL)
            if json_match:
                outline = json.loads(json_match.group(1))
            else:
                return {"error": "Failed to parse outline JSON", "raw_response": outline_text}
        
        # Log the event
        event_service.log_event(AgentEventCreate(
            brief_id=brief_id,
            agent_name="script_writer",
            event_type="outline_created",
            message="Generated podcast outline",
            payload={"sections_count": len(outline.get("sections", [])), "total_duration": outline.get("total_duration_min")}
        ))
        
        return {
            "brief_id": brief_id,
            "outline": outline,
            "message": "Podcast outline created successfully",
            "stats": {
                "sections": len(outline.get("sections", [])),
                "total_duration_min": outline.get("total_duration_min"),
                "estimated_words": target_words
            }
        }
        
    except Exception as e:
        return {
            "error": str(e),
            "message": "Failed to create podcast outline"
        }

@server.tool(
    name="write_podcast_script",
    description="Generate the complete podcast manuscript from outline and research data",
)
def write_podcast_script(brief_id: int, outline: Dict[str, Any]) -> Dict[str, Any]:
    """Write the complete podcast script from outline and available research"""
    
    if not OPENAI_AVAILABLE:
        return {"error": "OpenAI client not available"}
    
    try:
        # Get the research brief
        brief = research_service.get_brief(brief_id)
        if not brief:
            return {"error": "Research brief not found"}
        
        # Get available research items (for now, we'll simulate this)
        # In a full implementation, this would gather actual research
        research_content = f"""
Research Summary for: {brief['topic']}

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
        
        # Generate script sections
        script_sections = {}
        full_script = []
        total_words = 0
        
        # Write introduction
        intro_prompt = PODCAST_SCRIPT_PROMPT.format(
            topic=brief['topic'],
            angle=brief['angle'] or "comprehensive overview", 
            tone=brief['tone'],
            section_title="Introduction",
            key_points=outline.get("introduction", {}).get("setup", "Episode introduction"),
            narrative_approach="Engaging hook and episode preview",
            duration_min=outline.get("introduction", {}).get("duration_min", 2),
            target_words=outline.get("introduction", {}).get("duration_min", 2) * 155,
            research_content=research_content
        )
        
        intro_response = openai_client.chat.completions.create(
            model="gpt-4.1",
            messages=[
                {"role": "system", "content": "You are an expert podcast scriptwriter. Write engaging, conversational content."},
                {"role": "user", "content": intro_prompt}
            ],
            temperature=0.7
        )
        
        intro_script = intro_response.choices[0].message.content
        script_sections["introduction"] = intro_script
        full_script.append(f"## Introduction\n\n{intro_script}")
        total_words += len(intro_script.split())
        
        # Write main sections
        for i, section in enumerate(outline.get("sections", [])):
            section_prompt = PODCAST_SCRIPT_PROMPT.format(
                topic=brief['topic'],
                angle=brief['angle'] or "comprehensive overview",
                tone=brief['tone'], 
                section_title=section.get("title", f"Section {i+1}"),
                key_points=", ".join(section.get("key_points", [])),
                narrative_approach=section.get("narrative_approach", "Informative discussion"),
                duration_min=section.get("duration_min", 4),
                target_words=section.get("duration_min", 4) * 155,
                research_content=research_content
            )
            
            section_response = openai_client.chat.completions.create(
                model="gpt-4.1",
                messages=[
                    {"role": "system", "content": "You are an expert podcast scriptwriter. Write engaging, conversational content."},
                    {"role": "user", "content": section_prompt}
                ],
                temperature=0.7
            )
            
            section_script = section_response.choices[0].message.content
            script_sections[f"section_{i+1}"] = section_script
            full_script.append(f"## {section.get('title', f'Section {i+1}')}\n\n{section_script}")
            total_words += len(section_script.split())
        
        # Write conclusion
        conclusion_prompt = PODCAST_SCRIPT_PROMPT.format(
            topic=brief['topic'],
            angle=brief['angle'] or "comprehensive overview",
            tone=brief['tone'],
            section_title="Conclusion",
            key_points=outline.get("conclusion", {}).get("summary", "Episode summary"),
            narrative_approach="Wrap up with key takeaways and final thoughts",
            duration_min=outline.get("conclusion", {}).get("duration_min", 2),
            target_words=outline.get("conclusion", {}).get("duration_min", 2) * 155,
            research_content=research_content
        )
        
        conclusion_response = openai_client.chat.completions.create(
            model="gpt-4.1",
            messages=[
                {"role": "system", "content": "You are an expert podcast scriptwriter. Write engaging, conversational content."},
                {"role": "user", "content": conclusion_prompt}
            ],
            temperature=0.7
        )
        
        conclusion_script = conclusion_response.choices[0].message.content
        script_sections["conclusion"] = conclusion_script
        full_script.append(f"## Conclusion\n\n{conclusion_script}")
        total_words += len(conclusion_script.split())
        
        # Combine full script
        complete_script = "\n\n".join(full_script)
        
        # Calculate metrics
        estimated_read_time = total_words / 155  # 155 words per minute
        citation_count = len(re.findall(r'\(Source:', complete_script))
        
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
        event_service.log_event(AgentEventCreate(
            brief_id=brief_id,
            agent_name="script_writer",
            event_type="script_completed", 
            message="Generated complete podcast script",
            payload={
                "word_count": total_words,
                "estimated_read_time_min": estimated_read_time,
                "citation_count": citation_count
            }
        ))
        
        return {
            "brief_id": brief_id,
            "script_id": saved_script.id if hasattr(saved_script, 'id') else saved_script['id'],
            "title": outline.get("title"),
            "content": complete_script,
            "metrics": {
                "word_count": total_words,
                "estimated_read_time_min": round(estimated_read_time, 1),
                "citation_count": citation_count,
                "sections": len(outline.get("sections", [])) + 2  # +2 for intro and conclusion
            },
            "message": "Podcast script generated successfully"
        }
        
    except Exception as e:
        return {
            "error": str(e),
            "message": "Failed to write podcast script"
        }

@server.tool(
    name="generate_complete_podcast",
    description="End-to-end podcast generation: create outline and write full script",
)
def generate_complete_podcast(brief_id: int) -> Dict[str, Any]:
    """Generate a complete podcast from research brief in one step"""
    
    try:
        # Step 1: Create outline
        outline_result = create_podcast_outline(brief_id)
        
        if "error" in outline_result:
            return outline_result
        
        outline = outline_result["outline"]
        
        # Step 2: Write script
        script_result = write_podcast_script(brief_id, outline)
        
        if "error" in script_result:
            return script_result
        
        # Combine results
        return {
            "brief_id": brief_id,
            "script_id": script_result["script_id"],
            "title": script_result["title"],
            "content": script_result["content"],
            "outline": outline,
            "metrics": script_result["metrics"],
            "message": "Complete podcast generated successfully",
            "workflow": [
                "✅ Outline created",
                "✅ Introduction written", 
                f"✅ {len(outline.get('sections', []))} main sections written",
                "✅ Conclusion written",
                "✅ Script saved to database"
            ]
        }
        
    except Exception as e:
        return {
            "error": str(e),
            "message": "Failed to generate complete podcast"
        }

if __name__ == "__main__":
    server.run()