"""
Podcast outline generation prompt template.
"""

PODCAST_OUTLINE_PROMPT = """
You are an expert podcast scriptwriter. Create a detailed outline for a ${target_length_min}-minute podcast episode.

Topic: ${topic}
Angle: ${angle}
Tone: ${tone}

Requirements:
- Target length: ${target_length_min} minutes (~${target_words} words)
- Create 6-8 main sections with clear narrative flow
- Each section should have 2-4 subsections
- Include estimated time allocation for each section
- Design for single-voice narration
- Ensure compelling introduction and strong conclusion

Return a JSON structure with:
{
  "title": "Engaging episode title",
  "introduction": {
    "hook": "Opening hook or question",
    "setup": "Context and episode preview",
    "duration_min": 2
  },
  "sections": [
    {
      "title": "Section title",
      "key_points": ["Point 1", "Point 2", "Point 3"],
      "narrative_approach": "How to present this section",
      "duration_min": 4
    }
  ],
  "conclusion": {
    "summary": "Key takeaways",
    "call_to_action": "Ending thought or question",
    "duration_min": 2
  },
  "total_duration_min": ${target_length_min}
}
"""