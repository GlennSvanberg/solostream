#!/usr/bin/env python3
"""
OpenAI Responses API with web search tool.
Run with: OPENAI_API_KEY=your_key python with_tools.py
"""

import os
from openai import OpenAI

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

response = client.responses.create(
    model="gpt-4o",
    input="What are the top 2 headlines about AI today? Summarize briefly.",
    tools=[{"type": "web_search"}],
)

def get_output_text(response):
    for item in reversed(response.output):
        if getattr(item, "type", None) == "message" and getattr(item, "role", None) == "assistant":
            for content in getattr(item, "content", []):
                if getattr(content, "type", None) == "output_text":
                    return content.text
    return None

text = get_output_text(response)
if text:
    print(text)
else:
    print("No text output found. Response output:", response.output)
