#!/usr/bin/env python3
"""
Generate and display full manuscript content without database save
"""

import asyncio
import sys
import os
import json
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv(dotenv_path=".env", override=True)

sys.path.append(os.path.dirname(__file__))

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from contextlib import AsyncExitStack

# Initialize OpenAI client
try:
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        openai_client = OpenAI(api_key=api_key)
        print("✅ OpenAI client ready")
    else:
        print("❌ OPENAI_API_KEY not found")
        exit(1)
except Exception as e:
    print(f"❌ OpenAI setup failed: {e}")
    exit(1)

SCRIPT_PROMPT = """
You are an expert podcast scriptwriter. Write a complete, engaging podcast script for this topic.

Topic: {topic}
Angle: {angle}  
Target Length: {target_length_min} minutes (~{target_words} words)

Create a complete, word-for-word script that:
1. Is conversational and engaging for audio
2. Has smooth transitions between ideas
3. Uses "I" or "we" to connect with listeners
4. Includes compelling hooks and narrative elements
5. Is exactly the target word count for proper timing
6. Ready to be read aloud as a complete podcast episode

Write the COMPLETE SCRIPT with full content, not just an outline.
Include engaging storytelling, specific details, and a compelling narrative flow.
"""

async def generate_full_manuscript():
    """Generate complete manuscript content"""
    
    print("📝 FULL PODCAST MANUSCRIPT GENERATOR")
    print("=" * 60)
    print()
    
    topic = "The Titanic Disaster: Lessons in Hubris and Heroism"
    angle = "Human stories of courage and failure from history's most famous shipwreck"
    target_length = 12  # Shorter for demonstration
    target_words = target_length * 155  # 155 words per minute
    
    print(f"🎯 Topic: {topic}")
    print(f"📐 Angle: {angle}")
    print(f"📏 Target: {target_length} minutes (~{target_words} words)")
    print()
    
    print("✍️  Generating complete manuscript...")
    print("   (This takes 30-60 seconds for a full script)")
    print()
    
    # Generate the complete script
    prompt = SCRIPT_PROMPT.format(
        topic=topic,
        angle=angle,
        target_length_min=target_length,
        target_words=target_words
    )
    
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4.1",  # High-quality model for content
            messages=[
                {"role": "system", "content": "You are an expert podcast scriptwriter who creates engaging, conversational content for audio narration."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )
        
        manuscript = response.choices[0].message.content
        word_count = len(manuscript.split())
        estimated_time = word_count / 155
        
        print("🎉 COMPLETE PODCAST MANUSCRIPT GENERATED!")
        print("=" * 60)
        print(f"📊 Word Count: {word_count}")
        print(f"⏱️  Estimated Read Time: {estimated_time:.1f} minutes")
        print()
        print("📄 FULL MANUSCRIPT:")
        print("=" * 60)
        print()
        print(manuscript)
        print()
        print("=" * 60)
        print("✅ MANUSCRIPT COMPLETE - READY FOR AUDIO PRODUCTION!")
        print()
        print("🎯 Next Steps:")
        print("   • Copy this text to a text-to-speech service")
        print("   • Record with a human narrator")
        print("   • Add intro/outro music and editing")
        print("   • Publish as podcast episode")
        
    except Exception as e:
        print(f"❌ Generation failed: {e}")

if __name__ == "__main__":
    asyncio.run(generate_full_manuscript())