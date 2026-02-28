#!/usr/bin/env python3
"""
Free podcast episode generator using Edge TTS (no API key required).

Reuses script generation and parsing from generate_podcast. Uses Edge TTS for
multi-voice audio output. Use for testing and low-stakes episodes; use
generate_podcast.py with ElevenLabs for high-stakes episodes.

Run with: python generate_episode_free.py --topic-file topics/2025-02-28-scattered-day.md

With --topic-file: saves to episodes/{topic-filename}.txt and .mp3.
Without: uses podcast_script.txt and podcast_output.mp3.
Requires: OPENAI_API_KEY only if SEND_TO_OPENAI is True.
"""

import io
import os
import re
from pathlib import Path

from dotenv import load_dotenv

# Load .env from project root
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

# Import shared logic from generate_podcast
from generate_podcast import (
    APPLY_POSTPROCESSING,
    CHARACTERS_PATH,
    EPISODES_DIR,
    OUTPUT_AUDIO_PATH,
    OUTPUT_AUDIO_POSTPROCESSED_PATH,
    OUTPUT_SCRIPT_PATH,
    SCRIPT_DIR,
    apply_studio_polish,
    generate_script,
    load_characters,
    load_topic_from_file,
    parse_script,
)

# =============================================================================
# CONFIG
# =============================================================================

# If True, generate script with OpenAI. If False, load from existing script.
SEND_TO_OPENAI = False

# If True, add light studio polish after Edge TTS.
APPLY_POSTPROCESSING = True

# Regex to strip ElevenLabs emotion tags (Edge TTS does not support them)
EMOTION_TAG_RE = re.compile(r"^(\[[^\]]+\]\s*)+", re.IGNORECASE)


def _strip_emotion_tags(text: str) -> str:
    """Remove leading ElevenLabs emotion tags from text."""
    return EMOTION_TAG_RE.sub("", text).strip()


def send_to_edge_tts(inputs: list[dict], output_path: str | None = None) -> None:
    """
    Call Edge TTS for each segment and concatenate audio.
    Strips ElevenLabs emotion tags before sending (Edge does not support them).
    """
    import edge_tts
    from pydub import AudioSegment

    path = output_path or OUTPUT_AUDIO_PATH

    combined = AudioSegment.empty()
    for i, seg in enumerate(inputs):
        text = _strip_emotion_tags(seg["text"])
        if not text:
            continue
        voice = seg["voice_id"]  # Overloaded as Edge voice name
        communicate = edge_tts.Communicate(text, voice)
        audio_bytes = b""
        for chunk in communicate.stream_sync():
            if chunk.get("type") == "audio":
                audio_bytes += chunk["data"]
        if audio_bytes:
            segment_audio = AudioSegment.from_mp3(io.BytesIO(audio_bytes))
            combined += segment_audio
        if (i + 1) % 50 == 0:
            print(f"  Processed {i + 1}/{len(inputs)} segments...")

    combined.export(path, format="mp3", bitrate="128k")
    print(f"Audio saved to {path}")


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate Solostream podcast episode (free, Edge TTS)"
    )
    parser.add_argument(
        "--topic-file",
        type=str,
        metavar="PATH",
        help="Path to topic MD file. Uses narrative brief and hosts.",
    )
    args = parser.parse_args()

    topic_data: dict | None = None
    speaker_to_edge_voice: dict[str, str] | None = None

    script_path = OUTPUT_SCRIPT_PATH
    audio_path = OUTPUT_AUDIO_PATH
    postprocessed_path = OUTPUT_AUDIO_POSTPROCESSED_PATH

    if args.topic_file:
        topic_data = load_topic_from_file(args.topic_file)
        ep = topic_data.get("episode_type", "interview")
        d_min, d_max = topic_data.get("duration_min", 5), topic_data.get("duration_max", 7)
        print(f"Loaded topic from {args.topic_file} ({ep} {d_min}-{d_max} min)")

        episode_name = Path(args.topic_file).stem
        episodes_dir = SCRIPT_DIR / EPISODES_DIR
        episodes_dir.mkdir(parents=True, exist_ok=True)
        script_path = str(episodes_dir / f"{episode_name}.txt")
        audio_path = str(episodes_dir / f"{episode_name}.mp3")
        postprocessed_path = str(episodes_dir / f"{episode_name}_postprocessed.mp3")
        print(f"  Episode output: episodes/{episode_name}.*")

        characters = load_characters(CHARACTERS_PATH)
        char_by_id = {c["id"]: c for c in characters}

        format_val = topic_data.get("format", "solo")
        hosts = topic_data.get("hosts", ["james"])
        guest = topic_data.get("guest", "")

        character_list: list[dict] = []
        if format_val == "solo" and hosts:
            for hid in hosts[:1]:
                if hid in char_by_id:
                    character_list.append(char_by_id[hid])
        elif format_val == "interview" and hosts and guest:
            if hosts[0] in char_by_id:
                character_list.append(char_by_id[hosts[0]])
            if guest in char_by_id:
                character_list.append(char_by_id[guest])
        elif format_val == "discussion" and len(hosts) >= 2:
            for hid in hosts[:2]:
                if hid in char_by_id:
                    character_list.append(char_by_id[hid])

        if character_list:
            topic_data["character_list"] = character_list
            missing = [c["name"] for c in character_list if not c.get("edge_voice")]
            if missing:
                raise ValueError(
                    f"Characters missing edge_voice in characters.yaml: {missing}. "
                    "Add edge_voice (e.g. en-US-GuyNeural) for each character."
                )
            speaker_to_edge_voice = {c["name"]: c["edge_voice"] for c in character_list}
            print(f"  Hosts: {', '.join(c['name'] for c in character_list)}")
        else:
            # Fallback: build map from all characters + Narrator for scripts without topic
            characters = load_characters(CHARACTERS_PATH)
            speaker_to_edge_voice = {}
            default_voice = None
            for c in characters:
                if c.get("edge_voice"):
                    speaker_to_edge_voice[c["name"]] = c["edge_voice"]
                    if default_voice is None:
                        default_voice = c["edge_voice"]
            if default_voice:
                speaker_to_edge_voice.setdefault("Narrator", default_voice)
            if not speaker_to_edge_voice:
                raise ValueError(
                    "No characters with edge_voice in characters.yaml. "
                    "Add edge_voice to at least one character."
                )
            print("  No characters matched; using default narrator mapping")
    else:
        # No topic file: build fallback speaker->Edge voice map from all characters
        characters = load_characters(CHARACTERS_PATH)
        speaker_to_edge_voice = {}
        default_voice = None
        for c in characters:
            if c.get("edge_voice"):
                speaker_to_edge_voice[c["name"]] = c["edge_voice"]
                if default_voice is None:
                    default_voice = c["edge_voice"]
        if default_voice:
            speaker_to_edge_voice.setdefault("Narrator", default_voice)
        if not speaker_to_edge_voice:
            raise ValueError(
                "No characters with edge_voice in characters.yaml. "
                "Add edge_voice to at least one character."
            )

    if SEND_TO_OPENAI or topic_data is not None:
        print("Generating podcast script with OpenAI...")
        script = generate_script(topic_data=topic_data)
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(script)
        print(f"Script saved to {script_path}")
    else:
        print(f"Loading existing script from {script_path}...")
        with open(script_path, "r", encoding="utf-8") as f:
            script = f.read()

    inputs = parse_script(script, speaker_to_voice=speaker_to_edge_voice)
    print(f"Parsed {len(inputs)} dialogue segments")

    print("Sending to Edge TTS...")
    send_to_edge_tts(inputs, output_path=audio_path)

    if APPLY_POSTPROCESSING:
        print("Applying post-processing...")
        apply_studio_polish(audio_path, postprocessed_path)


if __name__ == "__main__":
    main()
