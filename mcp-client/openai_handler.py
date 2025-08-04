import json
from typing import List, Dict, Any
from openai import OpenAI
from config import TOOL_MODEL, FINAL_MODEL, OPENAI_API_KEY
from sys_prompt import SYSTEM_PROMPT

class OpenAIHandler:
    def __init__(self):
        self.client = OpenAI(api_key=OPENAI_API_KEY)
    
    def process_tool_planning(self, messages: List[Dict], available_tools: List[Dict]) -> tuple[str, List[Any]]:
        """Use the tool model to plan and execute tools"""
        llm_response = self.client.responses.create(
            model=TOOL_MODEL,
            instructions=SYSTEM_PROMPT,
            input=messages,
            tools=available_tools,
            tool_choice="auto",
        )

        tool_calls = []
        assistant_message_buffer = ""

        for event in llm_response.output:
            if event.type == "message":
                for item in event.content:
                    if getattr(item, "type", None) == "output_text":
                        text_piece = item.text
                        print(text_piece, end="", flush=True)
                        assistant_message_buffer += text_piece
            elif event.type == "function_call":
                tool_calls.append(event)

        if assistant_message_buffer:
            print("", flush=True)

        return assistant_message_buffer.strip(), tool_calls
    
    def generate_final_response(self, messages: List[Dict], available_tools: List[Dict]) -> str:
        """Use the final model to generate a comprehensive response"""
        final_response = self.client.responses.create(
            model=FINAL_MODEL,
            instructions=SYSTEM_PROMPT + "\n(The tools have already been executed and their outputs provided. Summarize the findings comprehensively without calling any more tools.)",
            input=messages,
            tools=available_tools,
            tool_choice="none",
        )

        final_answer_buffer = ""
        for event in final_response.output:
            if event.type == "message":
                for item in event.content:
                    if getattr(item, "type", None) == "output_text":
                        text_piece = item.text
                        print(text_piece, end="", flush=True)
                        final_answer_buffer += text_piece

        print("", flush=True)
        return final_answer_buffer.strip()
    
    @staticmethod
    def parse_tool_arguments(arguments_str: str) -> Dict:
        """Parse tool call arguments with error handling"""
        try:
            return json.loads(arguments_str)
        except json.JSONDecodeError:
            return {}