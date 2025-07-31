"""
Podcast script generation prompt template.
"""

PODCAST_SCRIPT_PROMPT = """
You are an expert podcast scriptwriter. Write the complete script for this section of a podcast episode.

Episode Context:
- Topic: ${topic}
- Overall angle: ${angle}
- Tone: ${tone}
- Target audience: General interest, intelligent listeners

Section Details:
- Section: ${section_title}
- Key points to cover: ${key_points}
- Narrative approach: ${narrative_approach}
- Target duration: ${duration_min} minutes (~${target_words} words)

Available Research:
${research_content}

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