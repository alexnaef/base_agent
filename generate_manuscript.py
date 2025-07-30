#!/usr/bin/env python3
"""
Generate and display a complete podcast manuscript
"""

import asyncio
import sys
import os
import json

sys.path.append(os.path.dirname(__file__))

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from contextlib import AsyncExitStack

async def generate_and_show_manuscript():
    """Generate a complete podcast manuscript and display it"""
    
    print("📝 GENERATING COMPLETE PODCAST MANUSCRIPT")
    print("=" * 60)
    print()
    
    topic = "The Wright Brothers and the First Flight"
    print(f"🎯 Topic: {topic}")
    print("📏 Target: 20-minute podcast")
    print()
    
    # Step 1: Create brief
    print("📋 Step 1: Creating research brief...")
    
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
                "topic": topic,
                "angle": "The engineering challenges and human determination behind humanity's first powered flight",
                "tone": "inspiring",
                "target_length_min": 20
            }
        )
        
        content = result.content[0].text if result.content else "{}"
        brief_data = json.loads(content)
        brief_id = brief_data.get("brief_id")
        
        print(f"✅ Brief created (ID: {brief_id})")
    
    # Step 2: Generate complete podcast
    print("✍️  Step 2: Generating complete manuscript (this may take 60-90 seconds)...")
    print()
    
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
        
        # Generate complete podcast
        result = await script_session.call_tool(
            "generate_complete_podcast",
            {"brief_id": brief_id}
        )
        
        content = result.content[0].text if result.content else "{}"
        
        try:
            podcast_data = json.loads(content)
            
            if "error" in podcast_data:
                print(f"❌ Generation failed: {podcast_data['error']}")
                return
            
            # Extract manuscript
            manuscript = podcast_data.get('content', '')
            metrics = podcast_data.get('metrics', {})
            
            print("🎉 MANUSCRIPT GENERATED SUCCESSFULLY!")
            print("=" * 60)
            print(f"📖 Title: {podcast_data.get('title', 'N/A')}")
            print(f"📊 Word Count: {metrics.get('word_count', 'N/A')}")
            print(f"⏱️  Read Time: {metrics.get('estimated_read_time_min', 'N/A')} minutes")
            print(f"📑 Citations: {metrics.get('citation_count', 'N/A')}")
            print()
            print("📄 COMPLETE PODCAST MANUSCRIPT:")
            print("=" * 60)
            print()
            print(manuscript)
            print()
            print("=" * 60)
            print("✅ MANUSCRIPT COMPLETE")
            print()
            print("🎯 Ready for:")
            print("   • Text-to-speech conversion")
            print("   • Audio production")
            print("   • Podcast distribution")
            
        except Exception as e:
            print(f"❌ Failed to parse result: {e}")
            print("Raw content preview:")
            print(content[:500] + "..." if len(content) > 500 else content)

if __name__ == "__main__":
    print("🎙️  Generating complete podcast manuscript...")
    print("This will create a full 20-minute script with professional structure")
    print()
    asyncio.run(generate_and_show_manuscript())