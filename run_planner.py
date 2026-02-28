#!/usr/bin/env python3
"""
Solostream Topic Planner.

Reads context from input/, checks topics already covered, proposes new topics via OpenAI,
optionally researches each via web search, and writes topic MD files to topics/.

Run with: python run_planner.py
          python run_planner.py --plan-only  (dry run, no research, no write)
Requires: OPENAI_API_KEY
"""

import argparse
import json
import os
import re
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

# Paths relative to script directory
SCRIPT_DIR = Path(__file__).resolve().parent
INPUT_DIR = SCRIPT_DIR / "input"
TOPICS_DIR = SCRIPT_DIR / "topics"
CHARACTERS_PATH = SCRIPT_DIR / "characters.yaml"

# Accepted input extensions
INPUT_EXTENSIONS = {".txt", ".md", ".json"}

# JSON keys to extract text from when parsing .json files
JSON_TEXT_KEYS = ("content", "notes", "text", "body")

# Episode types: short (2-3 min solo), interview (5-7 min), discussion (15-25 min)
EPISODE_TYPES = {
    "short": {"format": "solo", "duration_min": 2, "duration_max": 3},
    "interview": {"format": "interview", "duration_min": 5, "duration_max": 7},
    "discussion": {"format": "discussion", "duration_min": 15, "duration_max": 25},
}


def load_input_folder(path: Path) -> str:
    """Read and concatenate all .txt, .md, .json files from the input folder."""
    parts: list[str] = []
    if not path.exists():
        return ""

    for f in sorted(path.iterdir()):
        if not f.is_file():
            continue
        if f.suffix.lower() not in INPUT_EXTENSIONS:
            continue
        try:
            content = f.read_text(encoding="utf-8", errors="replace")
            if f.suffix.lower() == ".json":
                try:
                    data = json.loads(content)
                    extracted = _extract_text_from_json(data)
                    if extracted:
                        parts.append(f"--- {f.name} ---\n{extracted}")
                except json.JSONDecodeError:
                    parts.append(f"--- {f.name} ---\n{content}")
            else:
                parts.append(f"--- {f.name} ---\n{content}")
        except OSError:
            continue

    return "\n\n".join(parts) if parts else ""


def _extract_text_from_json(obj: object) -> str:
    """Extract text from JSON using common keys. Recurses into nested structures."""
    if isinstance(obj, str):
        return obj
    if isinstance(obj, dict):
        for key in JSON_TEXT_KEYS:
            if key in obj:
                val = obj[key]
                if isinstance(val, str):
                    return val
                if isinstance(val, (list, dict)):
                    return _extract_text_from_json(val)
        # Fallback: concatenate string values
        texts = []
        for v in obj.values():
            t = _extract_text_from_json(v)
            if t:
                texts.append(t)
        return "\n".join(texts) if texts else ""
    if isinstance(obj, list):
        texts = [_extract_text_from_json(item) for item in obj]
        return "\n".join(t for t in texts if t)
    return ""


def list_covered_topics(path: Path) -> list[str]:
    """List topic titles/slugs from existing .md files in the topics folder."""
    covered: list[str] = []
    if not path.exists():
        return covered

    for f in path.iterdir():
        if not f.is_file() or f.suffix.lower() != ".md":
            continue
        # Extract slug from filename (e.g. 2025-02-28-scattered-day.md -> scattered-day)
        name = f.stem
        if re.match(r"\d{4}-\d{2}-\d{2}-", name):
            slug = name[11:]  # after date prefix
        else:
            slug = name
        covered.append(slug)
        # Also try to get title from frontmatter
        try:
            content = f.read_text(encoding="utf-8", errors="replace")
            if match := re.search(r"^title:\s*(.+)$", content, re.MULTILINE):
                covered.append(match.group(1).strip())
        except OSError:
            pass

    return covered


def load_characters(path: Path) -> list[dict]:
    """Load characters from YAML. Returns list of character dicts (id, name, voice_id, backstory, expertise)."""
    import yaml

    if not path.exists():
        return []

    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    return data.get("characters", [])


def plan_topics(context: str, covered: list[str], characters: list[dict]) -> list[dict]:
    """Call OpenAI to propose new topics. Returns list of topic dicts."""
    from openai import OpenAI

    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    if not client.api_key:
        raise ValueError("OPENAI_API_KEY environment variable is required")

    schema = {
        "type": "object",
        "properties": {
            "topics": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string", "description": "Short topic title"},
                        "slug": {
                            "type": "string",
                            "description": "URL-safe slug, lowercase, hyphens (e.g. scattered-day)",
                        },
                        "episode_type": {
                            "type": "string",
                            "enum": ["short", "interview", "discussion"],
                            "description": "short=2-3 min solo, one insight; interview=5-7 min host+guest; discussion=15-25 min two hosts deep dive",
                        },
                        "narrative_brief": {
                            "type": "string",
                            "description": "Narrative brief for scriptwriter. Content depth must match episode_type: short=brief punchy single insight; interview=Q&A structure medium depth; discussion=deep exploration multiple angles.",
                        },
                        "research_query": {
                            "type": "string",
                            "description": "Optional web search query for 1 external signal (news, cultural reference). Empty string if not needed.",
                        },
                        "host_selection": {
                            "type": "object",
                            "properties": {
                                "format": {
                                    "type": "string",
                                    "enum": ["solo", "interview", "discussion"],
                                    "description": "solo=1 host, interview=host+guest, discussion=2 hosts",
                                },
                                "hosts": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "Character ids. One for solo, one for interview, two for discussion.",
                                },
                                "guest": {
                                    "type": "string",
                                    "description": "Character id for guest. Only for interview format. Empty string otherwise.",
                                },
                            },
                            "required": ["format", "hosts", "guest"],
                            "additionalProperties": False,
                        },
                    },
                    "required": ["title", "slug", "episode_type", "narrative_brief", "research_query", "host_selection"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["topics"],
        "additionalProperties": False,
    }

    char_summary = "\n".join(
        f"- {c['id']} ({c['name']}): expertise in {', '.join(c.get('expertise', []))}"
        for c in characters
    ) if characters else "(no characters loaded)"

    instructions = """You are a producer for Solostream—a personal AI radio station that turns daily notes into narrated audio reflections.

Given user context (notes, fragments, ideas), topics already covered, and the available characters, propose 1–5 NEW episode topics. Each topic must:

EPISODE TYPES (pick one per topic):
- short (2–3 min): Solo format. One person, one sharp insight or observation. Brief, punchy, focused. No deep exploration. Content: a single idea that can be delivered in 2–3 minutes.
- interview (5–7 min): Host + guest. Q&A structure. Medium depth. One topic explored through questions and responses. Content: one theme with room for back-and-forth.
- discussion (15–25 min): Two hosts. Deep dive. Multiple angles, building on each other. Content: rich enough for sustained exploration, nuance, and reflection.

RULES:
- Be distinct from already-covered topics
- narrative_brief content depth MUST match episode_type (short=brief, interview=medium, discussion=deep)
- Follow Solostream tone: thoughtful, human, not therapy/coaching/hype
- Optionally include research_query for 1 external signal. Use empty string if not needed.
- host_selection must match episode_type: short=solo (1 host), interview=host+guest, discussion=2 hosts. Use character ids exactly as listed.

Output valid JSON matching the schema."""

    covered_str = ", ".join(covered) if covered else "(none yet)"
    user_input = f"""Context from user input folder:
{context if context.strip() else "(no input files or empty)"}

Already covered topics (do not repeat): {covered_str}

Available characters (use their id in host_selection):
{char_summary}

Propose new topics as JSON."""

    response = client.responses.create(
        model="gpt-5.2",
        instructions=instructions,
        input=user_input,
        text={
            "format": {
                "type": "json_schema",
                "name": "topics",
                "schema": schema,
            }
        },
    )

    for item in response.output:
        if getattr(item, "type", None) == "message":
            for content in getattr(item, "content", []):
                if getattr(content, "type", None) == "output_text":
                    data = json.loads(content.text)
                    return data.get("topics", [])

    raise RuntimeError("No text in OpenAI response")


def research_topic(query: str) -> str:
    """Call OpenAI with web search to get 1–2 external signals. Returns summary text."""
    from openai import OpenAI

    if not query or not query.strip():
        return ""

    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    if not client.api_key:
        raise ValueError("OPENAI_API_KEY environment variable is required")

    response = client.responses.create(
        model="gpt-4.1",
        input=f"Find a brief, relevant external signal (news, cultural moment, or idea) for: {query}. Return 1–3 sentences that could mirror or contrast a personal reflection on this theme. No preamble.",
        tools=[{"type": "web_search"}],
    )

    for item in reversed(response.output):
        if getattr(item, "type", None) == "message" and getattr(item, "role", None) == "assistant":
            for content in getattr(item, "content", []):
                if getattr(content, "type", None) == "output_text":
                    return content.text

    return ""


def write_topic_file(topic: dict, base_path: Path) -> Path:
    """Write a topic MD file with frontmatter. Returns the path written."""
    today = date.today().isoformat()
    slug = topic.get("slug", "topic").lower().replace(" ", "-")
    slug = re.sub(r"[^a-z0-9-]", "", slug) or "topic"

    filename = f"{today}-{slug}.md"
    filepath = base_path / filename

    # Avoid overwrite: append -2, -3, etc.
    counter = 2
    while filepath.exists():
        filename = f"{today}-{slug}-{counter}.md"
        filepath = base_path / filename
        counter += 1

    title = topic.get("title", slug)
    narrative = topic.get("narrative_brief", "")
    external = topic.get("external_signals", "")

    episode_type = topic.get("episode_type", "interview")
    ep_config = EPISODE_TYPES.get(episode_type, EPISODE_TYPES["interview"])
    format_val = ep_config["format"]
    duration_min = ep_config["duration_min"]
    duration_max = ep_config["duration_max"]

    host_sel = topic.get("host_selection", {})
    hosts_list = host_sel.get("hosts", ["james"])
    guest_val = host_sel.get("guest", "")

    # Override format from episode_type; validate hosts
    if not hosts_list:
        hosts_list = ["james"]
    if format_val == "interview" and not guest_val and len(hosts_list) >= 2:
        guest_val = hosts_list[1]
        hosts_list = hosts_list[:1]
    elif format_val == "discussion" and len(hosts_list) < 2:
        extra = next((c for c in ["sarah", "daniel", "charlotte"] if c not in hosts_list), "sarah")
        hosts_list = hosts_list + [extra]

    hosts_yaml = "[" + ", ".join(hosts_list) + "]"

    body_parts = [f"# Narrative brief\n\n{narrative}"]
    if external:
        body_parts.append(f"\n# External signals (optional)\n\n{external}")

    frontmatter_lines = [
        f"title: {title}",
        f"created: {today}",
        f"status: researched",
        f"episode_type: {episode_type}",
        f"format: {format_val}",
        f"duration_min: {duration_min}",
        f"duration_max: {duration_max}",
        f"hosts: {hosts_yaml}",
    ]
    if format_val == "interview" and guest_val:
        frontmatter_lines.append(f"guest: {guest_val}")

    content = "---\n" + "\n".join(frontmatter_lines) + "\n---\n\n" + "\n".join(body_parts) + "\n"

    base_path.mkdir(parents=True, exist_ok=True)
    filepath.write_text(content, encoding="utf-8")
    return filepath


def main() -> None:
    parser = argparse.ArgumentParser(description="Plan and research Solostream topics")
    parser.add_argument(
        "--plan-only",
        action="store_true",
        help="Plan only, no research, no write (dry run)",
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=INPUT_DIR,
        help="Input folder path",
    )
    parser.add_argument(
        "--topics-dir",
        type=Path,
        default=TOPICS_DIR,
        help="Topics output folder path",
    )
    args = parser.parse_args()

    print("Loading input folder...")
    context = load_input_folder(args.input_dir)
    print(f"  Loaded {len(context)} chars from input/")

    print("Listing covered topics...")
    covered = list_covered_topics(args.topics_dir)
    print(f"  Found {len(covered)} covered topics")

    print("Loading characters...")
    characters = load_characters(CHARACTERS_PATH)
    if not characters:
        # Fallback if characters.yaml missing: use default ids so planner can still select
        characters = [
            {"id": "james", "name": "James", "expertise": ["reflection", "daily life"]},
            {"id": "sarah", "name": "Sarah", "expertise": ["conversations", "relationships"]},
            {"id": "daniel", "name": "Daniel", "expertise": ["ideas", "culture"]},
            {"id": "charlotte", "name": "Charlotte", "expertise": ["learning", "curiosity"]},
            {"id": "george", "name": "George", "expertise": ["storytelling", "memory"]},
            {"id": "lily", "name": "Lily", "expertise": ["creativity", "emotion"]},
            {"id": "marcus", "name": "Marcus", "expertise": ["rhythm", "discipline"]},
            {"id": "nina", "name": "Nina", "expertise": ["synthesis", "technology"]},
        ]
        print("  Using default character ids (characters.yaml not found)")
    else:
        print(f"  Loaded {len(characters)} characters")

    print("Planning new topics...")
    topics = plan_topics(context, covered, characters)
    print(f"  Proposed {len(topics)} new topics")

    if not topics:
        print("No new topics proposed. Done.")
        return

    if args.plan_only:
        for i, t in enumerate(topics, 1):
            print(f"  {i}. {t.get('title', '?')} (slug: {t.get('slug', '?')})")
        print("--plan-only: skipping research and write.")
        return

    for i, topic in enumerate(topics, 1):
        title = topic.get("title", "?")
        print(f"  {i}. {title}...")
        research_query = topic.get("research_query", "").strip()
        if research_query:
            try:
                external = research_topic(research_query)
                topic["external_signals"] = external
            except Exception as e:
                print(f"      Research failed: {e}")
                topic["external_signals"] = ""
        else:
            topic["external_signals"] = ""

        filepath = write_topic_file(topic, args.topics_dir)
        print(f"      Wrote {filepath.name}")

    print("Done.")


if __name__ == "__main__":
    main()
