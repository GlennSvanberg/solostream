---
name: openai-responses-api
description: Interact with the OpenAI Responses API in Python. Use when generating model responses, building multi-turn conversations, using hosted tools (web search, file search), function calling, or structured JSON outputs. Covers client.responses.create(), stateful conversations, and tool-augmented responses.
compatibility: Requires openai Python package and OPENAI_API_KEY.
metadata: {"openclaw": {"requires": {"env": ["OPENAI_API_KEY"]}, "primaryEnv": "OPENAI_API_KEY"}}
---

# OpenAI Responses API

The Responses API is a stateful, tool-augmented way to interact with OpenAI models. Unlike Chat Completions, it handles multi-turn conversations, hosted tools (web search, file search), and multimodal inputs in a single API call.

## Quick Start

```python
import os
from openai import OpenAI

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

response = client.responses.create(
    model="gpt-4o-mini",
    input="Tell me a joke",
)

# Extract text from output (output is a list of items: messages, tool calls, etc.)
for item in response.output:
    if getattr(item, "type", None) == "message":
        for content in item.content:
            if getattr(content, "type", None) == "output_text":
                print(content.text)
                break
```

Or use the convenience property when available:

```python
print(response.output_text)  # SDK convenience - may not exist in all versions
```

## Input Formats

**Simple string** (user role implied):

```python
response = client.responses.create(model="gpt-4o-mini", input="Hello")
```

**Message list** with explicit structure:

```python
response = client.responses.create(
    model="gpt-4o-mini",
    input=[
        {"role": "user", "content": [{"type": "input_text", "text": "What is Python?"}]}
    ],
)
```

**Multimodal** (text + image):

```python
response = client.responses.create(
    model="gpt-4o",
    input=[
        {
            "role": "user",
            "content": [
                {"type": "input_text", "text": "Describe this image"},
                {"type": "input_image", "image_url": "https://example.com/image.jpg"},
            ],
        }
    ],
)
```

**System/developer instructions**:

```python
response = client.responses.create(
    model="gpt-4o-mini",
    instructions="You are a helpful assistant that responds concisely.",
    input="Explain recursion in one sentence",
)
```

## Multi-Turn Conversations

The API is stateful. Use `previous_response_id` to continue:

```python
# First turn
response1 = client.responses.create(
    model="gpt-4o-mini",
    input="My name is Alice",
)

# Second turn - context is preserved
response2 = client.responses.create(
    model="gpt-4o-mini",
    input="What's my name?",
    previous_response_id=response1.id,
)
```

**Forking**: Use the same `previous_response_id` with different `input` to explore alternative paths without affecting the original thread.

## Hosted Tools

**Web search**:

```python
response = client.responses.create(
    model="gpt-4o",
    input="What's the latest news about AI?",
    tools=[{"type": "web_search"}],
)
```

**File search** (requires a vector store):

```python
response = client.responses.create(
    model="gpt-4o",
    input="Summarize the uploaded documents",
    tools=[{"type": "file_search", "vector_store_ids": ["vs_abc123"]}],
)
```

**Tool choice**: `tool_choice="auto"` (default), `"required"`, or `"none"`.

**Output parsing**: The `output` array contains items like `web_search_call`, `file_search_call`, and `message`. Iterate to find the final assistant message:

```python
def get_output_text(response):
    for item in reversed(response.output):
        if getattr(item, "type", None) == "message" and getattr(item, "role", None) == "assistant":
            for content in getattr(item, "content", []):
                if getattr(content, "type", None) == "output_text":
                    return content.text
    return None
```

## Function Calling

Define tools and handle tool calls in a loop:

```python
import json

def get_weather(city: str) -> dict:
    # Implement your function logic
    return {"city": city, "temp": 72, "conditions": "sunny"}

tools = [
    {
        "type": "function",
        "name": "get_weather",
        "description": "Get weather for a city",
        "parameters": {
            "type": "object",
            "properties": {"city": {"type": "string"}},
            "required": ["city"],
        },
    }
]

response = client.responses.create(
    model="gpt-4o-mini",
    input="What's the weather in Tokyo?",
    tools=tools,
)

# Check for function_call in output, execute, then continue
for item in response.output:
    if getattr(item, "type", None) == "function_call":
        args = json.loads(item.arguments)
        result = get_weather(city=args["city"])
        response = client.responses.create(
            model="gpt-4o-mini",
            input=[{"type": "function_call_output", "call_id": item.call_id, "output": json.dumps(result)}],
            previous_response_id=response.id,
        )
        break
```

## Structured Outputs

**JSON schema** (preferred for gpt-4o+):

```python
response = client.responses.create(
    model="gpt-4o-mini",
    input="List 2 fruits with their colors",
    text={
        "format": {
            "type": "json_schema",
            "name": "fruits",
            "schema": {
                "type": "object",
                "properties": {
                    "fruits": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {"name": {"type": "string"}, "color": {"type": "string"}},
                        },
                    }
                },
            },
        }
    },
)
```

**JSON object** (legacy):

```python
response = client.responses.create(
    model="gpt-4o-mini",
    input="Return a JSON object with keys 'greeting' and 'count'",
    text={"format": {"type": "json_object"}},
)
```

## Key Parameters

| Parameter | Description |
|-----------|--------------|
| `model` | Model ID (e.g. `gpt-4o`, `gpt-4o-mini`) |
| `max_output_tokens` | Max tokens to generate |
| `temperature` | 0-2, randomness (use with `top_p` but not both) |
| `top_p` | Nucleus sampling alternative to temperature |
| `truncation` | `"auto"` (truncate to fit) or `"disabled"` (fail if over limit) |
| `prompt_cache_key` | Stable ID for caching (replaces deprecated `user`) |
| `stream` | `True` for streaming (returns iterator) |

## Error Handling

```python
response = client.responses.create(model="gpt-4o-mini", input="Hello")

if response.error:
    print(f"Error: {response.error.code} - {response.error.message}")

# Check status: completed, failed, in_progress, cancelled, queued, incomplete
if response.status != "completed":
    print(f"Status: {response.status}")
```

Common errors: `rate_limit_exceeded`, `invalid_prompt`, `invalid_image`, `invalid_image_url`.

## Other Operations

- **Retrieve**: `client.responses.retrieve(response_id=response.id)`
- **Delete**: `client.responses.delete(response_id=response.id)`

## Advanced (See Official Docs)

- **Streaming**: Set `stream=True`; iterate over events
- **Background mode**: `background=True` for async processing
- **MCP tools, code interpreter, computer use**: [Built-in tools](https://platform.openai.com/docs/guides/tools)
- **Reasoning models** (o1, o3): `reasoning={"effort": "medium"}` etc.

## Resources

- [API Reference](https://platform.openai.com/docs/api-reference/responses)
- [Responses API Guide](https://platform.openai.com/docs/guides/text)
