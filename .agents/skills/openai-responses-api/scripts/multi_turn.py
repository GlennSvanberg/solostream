#!/usr/bin/env python3
"""
Multi-turn conversation using OpenAI Responses API.
Run with: OPENAI_API_KEY=your_key python multi_turn.py
"""

import os
from openai import OpenAI

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# First turn
response1 = client.responses.create(
    model="gpt-4o-mini",
    input="My favorite color is blue. Remember that.",
)

# Second turn - context is preserved via previous_response_id
response2 = client.responses.create(
    model="gpt-4o-mini",
    input="What is my favorite color?",
    previous_response_id=response1.id,
)

def get_output_text(response):
    for item in reversed(response.output):
        if getattr(item, "type", None) == "message" and getattr(item, "role", None) == "assistant":
            for content in getattr(item, "content", []):
                if getattr(content, "type", None) == "output_text":
                    return content.text
    return None

print("Turn 1:", get_output_text(response1))
print("Turn 2:", get_output_text(response2))
