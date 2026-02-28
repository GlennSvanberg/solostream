#!/usr/bin/env python3
"""
Minimal OpenAI Responses API example.
Run with: OPENAI_API_KEY=your_key python basic_response.py
"""

import os
from openai import OpenAI

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

response = client.responses.create(
    model="gpt-4o-mini",
    input="Tell me a short joke in one sentence.",
)

for item in response.output:
    if getattr(item, "type", None) == "message":
        for content in getattr(item, "content", []):
            if getattr(content, "type", None) == "output_text":
                print(content.text)
                break
        break
