#!/usr/bin/env python3
"""
Generate host segments (intro/outro) for each episode in Solostream.

Uses GPT to generate unique, short scripts that add value beyond "coming up next",
then OpenAI TTS for a consistent host voice. Run after sync-episodes.js when
episodes change.

  python generate_host_segments.py
  python generate_host_segments.py --episodes-json web/public/episodes.json --output-dir web/public/host
  python generate_host_segments.py --slots intro,outro

Requires: OPENAI_API_KEY
"""

import argparse
import io
import json
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_EPISODES_JSON = SCRIPT_DIR / "web" / "public" / "episodes.json"
DEFAULT_OUTPUT_DIR = SCRIPT_DIR / "web" / "public" / "host"

OPENAI_TTS_MODEL = "gpt-4o-mini-tts"
APPLY_POSTPROCESSING = True


def load_episodes(episodes_path: Path) -> list[dict]:
    """Load episodes from JSON. Returns list of {id, title, url}."""
    if not episodes_path.exists():
        raise FileNotFoundError(f"Episodes file not found: {episodes_path}")

    with open(episodes_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("episodes", [])


def load_host_character() -> tuple[str, str]:
    """Load solostream_host from characters.yaml. Returns (voice, instructions)."""
    import yaml

    chars_path = SCRIPT_DIR / "characters.yaml"
    if not chars_path.exists():
        raise FileNotFoundError(f"characters.yaml not found: {chars_path}")

    with open(chars_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    for c in data.get("characters", []):
        if c.get("id") == "solostream_host":
            voice = c.get("openai_voice", "onyx")
            instructions = c.get("openai_instructions", "")
            return voice, instructions

    return "onyx", "Speak as a warm, thoughtful radio host. Brief, conversational, never stiff."


def generate_intro_script(
    episode_title: str,
    next_episode_title: str,
    position: int,
    total: int,
) -> str:
    """Generate a unique intro script via GPT."""
    from openai import OpenAI

    client = OpenAI()
    if not os.environ.get("OPENAI_API_KEY"):
        raise ValueError("OPENAI_API_KEY environment variable is required")

    system = """You are writing a brief radio host intro for Solostream—a personal AI radio station.
Your job: tease the upcoming episode with a micro-insight, question, or hook. Do NOT use generic phrases like "Coming up next on Solostream: [title]."
Add value: a thought-provoking angle, a connection to the listener's moment, or a subtle observation.
Output ONLY the spoken script—1 to 2 sentences, under 50 words. No stage directions, no quotes around the text."""

    user = f"""Episode coming up: "{episode_title}"
Next after that: "{next_episode_title}"
Position in rotation: {position} of {total}

Write a unique intro that teases this episode. Add a micro-insight or hook. Keep under 50 words."""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        max_tokens=150,
    )
    text = response.choices[0].message.content.strip()
    return text


def generate_outro_script(
    episode_title: str,
    next_episode_title: str,
) -> str:
    """Generate a unique outro script via GPT."""
    from openai import OpenAI

    client = OpenAI()
    if not os.environ.get("OPENAI_API_KEY"):
        raise ValueError("OPENAI_API_KEY environment variable is required")

    system = """You are writing a brief radio host outro for Solostream—a personal AI radio station.
Your job: offer a brief reflection or takeaway from what was just heard, then smoothly tease the next episode.
Do NOT use generic phrases like "That was [title]. Up next: [next]."
Add value: a light observation, a one-line takeaway, or a connection between the two episodes.
Output ONLY the spoken script—1 to 2 sentences, under 50 words. No stage directions, no quotes around the text."""

    user = f"""Episode that just played: "{episode_title}"
Next episode: "{next_episode_title}"

Write a unique outro. Add a light observation or takeaway, then tease the next. Keep under 50 words."""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        max_tokens=150,
    )
    text = response.choices[0].message.content.strip()
    return text


def text_to_speech(text: str, voice: str, instructions: str, output_path: Path) -> None:
    """Render text to MP3 using OpenAI TTS."""
    from openai import OpenAI
    from pydub import AudioSegment

    client = OpenAI()
    kwargs = {
        "model": OPENAI_TTS_MODEL,
        "voice": voice,
        "input": text,
    }
    if instructions and OPENAI_TTS_MODEL.startswith("gpt-4o-mini"):
        kwargs["instructions"] = instructions

    response = client.audio.speech.create(**kwargs)
    audio_bytes = response.read()
    if not audio_bytes:
        raise RuntimeError("OpenAI TTS returned empty audio")

    segment = AudioSegment.from_mp3(io.BytesIO(audio_bytes))
    segment.export(str(output_path), format="mp3", bitrate="128k")


def apply_studio_polish(input_path: Path, output_path: Path) -> None:
    """Add subtle room tone for consistency with episodes."""
    from pydub import AudioSegment
    from pydub.generators import WhiteNoise

    voice = AudioSegment.from_mp3(str(input_path))
    noise = WhiteNoise().to_audio_segment(duration=len(voice)).apply_gain(-54)
    mixed = voice.overlay(noise)
    mixed.export(str(output_path), format="mp3", bitrate="128k")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate host segments (intro/outro) for Solostream episodes"
    )
    parser.add_argument(
        "--episodes-json",
        type=Path,
        default=DEFAULT_EPISODES_JSON,
        help="Path to episodes.json",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory for host MP3s and manifest",
    )
    parser.add_argument(
        "--slots",
        type=str,
        default="intro,outro",
        help="Comma-separated: intro, outro",
    )
    args = parser.parse_args()

    slots = [s.strip() for s in args.slots.split(",") if s.strip()]
    if not slots:
        slots = ["intro", "outro"]

    episodes = load_episodes(args.episodes_json)
    if not episodes:
        print("No episodes found. Run sync-episodes.js first.")
        return

    voice, instructions = load_host_character()
    print(f"Host voice: {voice}")
    print(f"Episodes: {len(episodes)}")
    print(f"Slots: {', '.join(slots)}")

    args.output_dir.mkdir(parents=True, exist_ok=True)

    manifest_segments: list[dict] = []

    for i, ep in enumerate(episodes):
        ep_id = ep["id"]
        ep_title = ep["title"]
        next_ep = episodes[(i + 1) % len(episodes)]
        next_title = next_ep["title"]

        if "intro" in slots:
            print(f"  Intro for {ep_id}...")
            script = generate_intro_script(
                episode_title=ep_title,
                next_episode_title=next_title,
                position=i + 1,
                total=len(episodes),
            )
            intro_path = args.output_dir / f"{ep_id}-intro.mp3"
            text_to_speech(script, voice, instructions, intro_path)

            if APPLY_POSTPROCESSING:
                polished = args.output_dir / f"{ep_id}-intro_postprocessed.mp3"
                apply_studio_polish(intro_path, polished)
                intro_path.unlink()
                intro_path = polished
                final_filename = intro_path.name
            else:
                final_filename = f"{ep_id}-intro.mp3"

            manifest_segments.append({
                "id": f"{ep_id}-intro",
                "type": "host",
                "episodeId": ep_id,
                "slot": "intro",
                "url": f"/host/{final_filename}",
                "script": script,
            })

        if "outro" in slots:
            print(f"  Outro for {ep_id}...")
            script = generate_outro_script(
                episode_title=ep_title,
                next_episode_title=next_title,
            )
            outro_path = args.output_dir / f"{ep_id}-outro.mp3"
            text_to_speech(script, voice, instructions, outro_path)

            if APPLY_POSTPROCESSING:
                polished = args.output_dir / f"{ep_id}-outro_postprocessed.mp3"
                apply_studio_polish(outro_path, polished)
                outro_path.unlink()
                outro_path = polished
                final_filename = outro_path.name
            else:
                final_filename = f"{ep_id}-outro.mp3"

            manifest_segments.append({
                "id": f"{ep_id}-outro",
                "type": "host",
                "episodeId": ep_id,
                "slot": "outro",
                "url": f"/host/{final_filename}",
                "script": script,
            })

    manifest_path = args.output_dir.parent / "host_segments.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump({"segments": manifest_segments}, f, indent=2)

    print(f"Done. {len(manifest_segments)} segments saved to {args.output_dir}")
    print(f"Manifest: {manifest_path}")


if __name__ == "__main__":
    main()
