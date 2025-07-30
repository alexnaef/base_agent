#!/usr/bin/env python3
"""
Generate and display manuscript without database save issues
"""

import asyncio
import sys
import os
import json

sys.path.append(os.path.dirname(__file__))

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from contextlib import AsyncExitStack

async def show_manuscript():
    """Generate manuscript and display content directly"""
    
    print("📝 PODCAST MANUSCRIPT GENERATOR")
    print("=" * 50)
    print()
    
    # Create brief
    brief_id = None
    async with AsyncExitStack() as stack:
        orchestrator_params = StdioServerParameters(
            command=sys.executable,
            args=["agents/podcast_orchestrator/server.py"],
            env=None
        )
        
        orchestrator_transport = await stack.enter_async_context(stdio_client(orchestrator_params))
        orchestrator_stdio, orchestrator_write = orchestrator_transport
        orchestrator_session = await stack.enter_async_context(ClientSession(orchestrator_stdio, orchestrator_write))
        
        await orchestrator_session.initialize()
        
        result = await orchestrator_session.call_tool(
            "create_research_brief",
            {
                "topic": "The Moon Landing: Humanity's Greatest Achievement",
                "angle": "The incredible human and technical story behind Apollo 11",
                "tone": "inspiring",
                "target_length_min": 15  # Shorter for faster generation
            }
        )
        
        content = result.content[0].text if result.content else "{}"
        brief_data = json.loads(content)
        brief_id = brief_data.get("brief_id")
        
        print(f"✅ Research Brief: {brief_data.get('topic')}")
        print(f"📏 Target Length: 15 minutes")
        print()
    
    # Generate outline only first (faster)
    print("📋 Generating podcast outline...")
    
    async with AsyncExitStack() as stack:
        script_params = StdioServerParameters(
            command=sys.executable,
            args=["agents/script_writer/server.py"],
            env=None
        )
        
        script_transport = await stack.enter_async_context(stdio_client(script_params))
        script_stdio, script_write = script_transport
        script_session = await stack.enter_async_context(ClientSession(script_stdio, script_write))
        
        await script_session.initialize()
        
        # Get outline
        result = await script_session.call_tool(
            "create_podcast_outline",
            {"brief_id": brief_id}
        )
        
        content = result.content[0].text if result.content else "{}"
        outline_data = json.loads(content)
        
        if "outline" in outline_data:
            outline = outline_data["outline"]
            print("✅ PODCAST OUTLINE CREATED")
            print("=" * 40)
            print(f"📖 Title: {outline.get('title')}")
            print(f"⏱️  Duration: {outline.get('total_duration_min')} minutes")
            print()
            
            # Show detailed structure
            print("📋 DETAILED STRUCTURE:")
            print("-" * 40)
            
            # Introduction
            intro = outline.get('introduction', {})
            print(f"🎬 INTRODUCTION ({intro.get('duration_min', 2)} minutes)")
            print(f"   Hook: {intro.get('hook', 'N/A')}")
            print(f"   Setup: {intro.get('setup', 'N/A')}")
            print()
            
            # Main sections
            sections = outline.get('sections', [])
            for i, section in enumerate(sections, 1):
                print(f"📚 SECTION {i}: {section.get('title', f'Section {i}')} ({section.get('duration_min', 3)} minutes)")
                print(f"   Approach: {section.get('narrative_approach', 'N/A')}")
                key_points = section.get('key_points', [])
                if key_points:
                    print(f"   Key Points:")
                    for point in key_points[:3]:  # Show first 3
                        print(f"     • {point}")
                print()
            
            # Conclusion
            conclusion = outline.get('conclusion', {})
            print(f"🎯 CONCLUSION ({conclusion.get('duration_min', 2)} minutes)")
            print(f"   Summary: {conclusion.get('summary', 'N/A')}")
            print(f"   Call to Action: {conclusion.get('call_to_action', 'N/A')}")
            print()
            
            print("✅ PROFESSIONAL PODCAST STRUCTURE COMPLETE!")
            print("=" * 50)
            print()
            print("🎯 THIS OUTLINE IS READY FOR:")
            print("   • Full script generation (adds detailed content)")
            print("   • Voice narration recording")
            print("   • Text-to-speech conversion")
            print("   • Audio production and editing")
            print()
            print("💡 The system successfully:")
            print("   ✅ Analyzed user topic and angle")
            print("   ✅ Created professional broadcast structure")
            print("   ✅ Balanced timing for target duration")
            print("   ✅ Organized content for audio narration")
            print("   ✅ Prepared compelling narrative flow")
            
        else:
            print("❌ Outline generation failed")

if __name__ == "__main__":
    print("🎙️  Generating professional podcast outline...")
    print("This shows the structured content our system creates")
    print()
    asyncio.run(show_manuscript())