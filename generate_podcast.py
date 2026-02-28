#!/usr/bin/env python3
"""
Podcast Script Generator with ElevenLabs Integration.

Generates a podcast-style script using OpenAI, then optionally sends it to
ElevenLabs Text to Dialogue API for multi-voice audio output.

Run with: python generate_podcast.py
          python generate_podcast.py --topic-file topics/2025-02-28-scattered-day.md
Requires: OPENAI_API_KEY (if SEND_TO_OPENAI), ELEVENLABS_API_KEY (if SEND_TO_ELEVENLABS).
Keys can be in .env or environment variables.
"""

import argparse
import os
import re
from pathlib import Path

from dotenv import load_dotenv

# Load .env from project root (same directory as this script)
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

SCRIPT_DIR = Path(__file__).resolve().parent
CHARACTERS_PATH = SCRIPT_DIR / "characters.yaml"

# Episode types and default durations (overridden by topic file)
EPISODE_TYPES = {
    "short": {"duration_min": 2, "duration_max": 3},
    "interview": {"duration_min": 5, "duration_max": 7},
    "discussion": {"duration_min": 15, "duration_max": 25},
}

# =============================================================================
# CONFIG — Adjust these variables at the top of the file
# =============================================================================

LENGTH_MIN = 5  # Default when no topic file (fallback)
TOPIC = """A calm personal daily audio reflection. Single narrator. Notes from the day: feeling scattered but productive, a good conversation with a friend, wondering about the weather. Structure: opening recognition of the day, reflection on recurring ideas, gentle close. Tone: thoughtful, calm, human. Someone who has been paying attention. Not therapy, not coaching, not hype."""
NUM_SPEAKERS = 1

# ElevenLabs voice IDs — one per speaker, in order of first appearance.
# Library voices require paid plan (optimized for eleven_v3)
VOICE_IDS = [
    "EkK5I93UQWFDigLMpZcX",  # James (male, narrative)
]

# If True, generate script with OpenAI. If False, load from existing OUTPUT_SCRIPT_PATH.
SEND_TO_OPENAI = False

# If True, call ElevenLabs and save MP3. If False, only save script to file.
SEND_TO_ELEVENLABS = True

OUTPUT_SCRIPT_PATH = "podcast_script.txt"
OUTPUT_AUDIO_PATH = "podcast_output.mp3"
OUTPUT_AUDIO_POSTPROCESSED_PATH = "podcast_output_postprocessed.mp3"

# If True, add light studio polish (room tone + reverb) after ElevenLabs. Saves to OUTPUT_AUDIO_POSTPROCESSED_PATH.
APPLY_POSTPROCESSING = True

# ElevenLabs TTD stability: 0.0=Creative (most expressive), 0.5=Natural, 1.0=Robust (only 0.0,0,5 and 1.0 are allowed values)
ELEVENLABS_STABILITY = 0.0

# =============================================================================
# END CONFIG
# =============================================================================

# ElevenLabs v3 emotion tags for the OpenAI prompt
EMOTION_TAGS_REF = """
Use only these ElevenLabs v3 tags in brackets before dialogue:
- Emotional: [excited], [annoyed], [flustered], [casual], [surprised], [laughs], [sighing]
- Turn-taking: [interrupting], [overlapping], [cuts in], [starting to speak]
- Style: [whispers], [sarcastically], [fast-paced], [hesitates], [pause], [drawn out]
- Identity: [childlike tone], [deep voice], [robotic tone]
"""


def load_characters(path: Path) -> list[dict]:
    """Load characters from YAML. Returns list of dicts with id, name, voice_id, backstory, expertise."""
    import yaml

    if not path.exists():
        return []

    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data.get("characters", [])


def load_topic_from_file(path: str) -> dict:
    """
    Parse a topic MD file. Returns dict with narrative_brief, format, hosts, guest.
    Expects frontmatter and a '# Narrative brief' section.
    """
    with open(path, "r", encoding="utf-8") as f:
        raw = f.read()

    result: dict = {
        "narrative_brief": "",
        "format": "solo",
        "hosts": ["james"],
        "guest": "",
        "episode_type": "interview",
        "duration_min": 5,
        "duration_max": 7,
    }

    parsed_episode_type = False
    parsed_duration = False

    # Parse frontmatter
    if raw.startswith("---"):
        end = raw.find("---", 3)
        if end != -1:
            front = raw[3:end].strip()
            body = raw[end + 3 :].lstrip()
            for line in front.splitlines():
                if line.startswith("format:"):
                    result["format"] = line.split(":", 1)[1].strip()
                elif line.startswith("hosts:"):
                    val = line.split(":", 1)[1].strip()
                    if val.startswith("[") and val.endswith("]"):
                        result["hosts"] = [x.strip().strip("'\"") for x in val[1:-1].split(",")]
                    else:
                        result["hosts"] = [val]
                elif line.startswith("guest:"):
                    result["guest"] = line.split(":", 1)[1].strip()
                elif line.startswith("episode_type:"):
                    result["episode_type"] = line.split(":", 1)[1].strip()
                    parsed_episode_type = True
                elif line.startswith("duration_min:"):
                    try:
                        result["duration_min"] = int(line.split(":", 1)[1].strip())
                        parsed_duration = True
                    except ValueError:
                        pass
                elif line.startswith("duration_max:"):
                    try:
                        result["duration_max"] = int(line.split(":", 1)[1].strip())
                        parsed_duration = True
                    except ValueError:
                        pass
        else:
            body = raw
    else:
        body = raw

    # Derive episode_type/duration from format when not explicitly set in file
    if not parsed_episode_type or not parsed_duration:
        fmt = result.get("format", "solo")
        if fmt == "solo":
            result["episode_type"] = "short"
            result["duration_min"] = 2
            result["duration_max"] = 3
        elif fmt == "discussion":
            result["episode_type"] = "discussion"
            result["duration_min"] = 15
            result["duration_max"] = 25
        else:
            result["episode_type"] = "interview"
            result["duration_min"] = 5
            result["duration_max"] = 7

    # Extract narrative brief
    match = re.search(
        r"^#\s*Narrative\s+brief\s*$(.+?)(?=^#\s|\Z)",
        body,
        re.MULTILINE | re.DOTALL | re.IGNORECASE,
    )
    if match:
        result["narrative_brief"] = match.group(1).strip()
    else:
        result["narrative_brief"] = body.strip()

    return result


def generate_script(
    topic: str | None = None,
    topic_data: dict | None = None,
) -> str:
    """Generate podcast script using OpenAI. topic_data can include format, hosts, guest, character_list."""
    from openai import OpenAI

    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    if not client.api_key:
        raise ValueError("OPENAI_API_KEY environment variable is required")

    content = ""
    if topic_data and topic_data.get("narrative_brief"):
        content = topic_data["narrative_brief"].strip()
    elif topic is not None:
        content = topic.strip()
    else:
        content = TOPIC.strip()

    # Duration from topic or default
    if topic_data:
        d_min = topic_data.get("duration_min", 5)
        d_max = topic_data.get("duration_max", 7)
        duration_min = (d_min + d_max) // 2  # Use midpoint
    else:
        duration_min = LENGTH_MIN
    target_words = duration_min * 150  # ~150 words per minute

    # Build character context for multi-speaker
    character_list = topic_data.get("character_list", []) if topic_data else []
    format_val = topic_data.get("format", "solo") if topic_data else "solo"
    episode_type = topic_data.get("episode_type", "interview") if topic_data else "interview"

    # Content depth hint by episode type
    if episode_type == "short":
        depth_hint = "SHORT episode (2-3 min): One sharp insight only. Brief, punchy, focused. No deep exploration. Land the idea and close."
    elif episode_type == "interview":
        depth_hint = "INTERVIEW episode (5-7 min): Medium depth. Q&A structure. One theme explored through host questions and guest responses."
    elif episode_type == "discussion":
        depth_hint = "DISCUSSION episode (15-25 min): Deep dive. Multiple angles. Two hosts build on each other, explore nuance, sustain reflection."
    else:
        depth_hint = "Reflective narration. Match content depth to the suggested length."

    if format_val == "solo" or not character_list:
        # Single narrator - use character name if available, else "Narrator"
        narrator_name = character_list[0]["name"] if character_list else "Narrator"
        system_prompt = f"""You are a scriptwriter for Solostream—a personal AI radio station that turns daily notes into a narrated audio reflection.

Format: Each line must be {narrator_name}: [optional tag] text
- Single narrator only. Use the name "{narrator_name}" for every line. No stage directions, notes, or text outside the Name: [tag] format.

Tone: Calm, confident, human. Someone thoughtful who has been paying attention.
- NOT therapy, NOT coaching, NOT hype, NOT summarizing like meeting notes.
- Slight discomfort is acceptable. Manipulation is not.

{depth_hint}

Structure the script as:
1. Opening recognition of the day
2. Reflection on recurring ideas or themes
3. Gentle close (no call to action)

Emotion tags ({EMOTION_TAGS_REF}): Use tags that fit reflective narration—[casual], [thoughtful], [pause], [drawn out], [hesitates], [sighing]. Avoid debate tags like [interrupting], [overlapping]. Use tags on ~40-60% of lines.
- MINIMIZE punctuation that slows delivery: avoid ellipses, em dashes, excessive commas.
- Write like someone speaking calmly to a listener. Natural flow, not polished prose."""

        user_prompt = f"""Write a Solostream-style narrated reflection with these specs:
- Content: {content}
- Single narrator: {narrator_name}
- Target length: approximately {target_words} words ({duration_min} minutes at ~150 words/min)
- Format: {narrator_name}: [optional tag] text
- Calm, thoughtful, human. Sound like someone paying attention."""
    else:
        # Multi-speaker: interview or discussion
        names = [c["name"] for c in character_list]
        char_desc = "\n".join(
            f"- {c['name']}: {c.get('backstory', '')}" for c in character_list
        )

        if format_val == "interview":
            host_name = names[0]
            guest_name = names[1] if len(names) > 1 else ""
            format_instruction = f"Interview format: {host_name} is the host (leads, asks questions), {guest_name} is the guest (responds, shares perspective). {host_name} opens and closes."
        elif format_val == "discussion":
            format_instruction = f"Discussion format: {names[0]} and {names[1]} are co-hosts. They trade ideas, build on each other, reflect together. Natural back-and-forth."
        else:
            format_instruction = f"Solo: {names[0]} narrates alone."

        system_prompt = f"""You are a scriptwriter for Solostream—a personal AI radio station with recurring characters on the air.

Format: Each line must be SpeakerName: [optional tag] text
- Use ONLY these speaker names: {', '.join(names)}
- No stage directions, notes, or text outside the Name: [tag] format.
- Each line starts with the character's name followed by colon.

Tone: Calm, confident, human. Thoughtful people who have been paying attention.
- NOT therapy, NOT coaching, NOT hype, NOT summarizing like meeting notes.
- Slight discomfort is acceptable. Manipulation is not.

{depth_hint}

{format_instruction}

Character backstories (use to inform voice and perspective):
{char_desc}

Emotion tags ({EMOTION_TAGS_REF}): Use tags that fit reflective conversation—[casual], [thoughtful], [pause], [drawn out], [hesitates], [sighing]. For interview/discussion you may use [interrupting], [overlapping] sparingly.
- MINIMIZE punctuation that slows delivery.
- Write like people speaking calmly. Natural flow."""

        user_prompt = f"""Write a Solostream-style episode with these specs:
- Content: {content}
- Format: {format_val}. Speakers: {', '.join(names)}
- Target length: approximately {target_words} words ({duration_min} minutes at ~150 words/min)
- Format each line as: Name: [optional tag] text
- Calm, thoughtful, human. Sound like people paying attention."""

    response = client.responses.create(
        model="gpt-5.2",
        instructions=system_prompt,
        input=user_prompt,
    )

    for item in response.output:
        if getattr(item, "type", None) == "message":
            for content in getattr(item, "content", []):
                if getattr(content, "type", None) == "output_text":
                    return content.text
    raise RuntimeError("No text in OpenAI response")


def parse_script(script: str, speaker_to_voice: dict[str, str] | None = None) -> list[dict]:
    """
    Parse script lines like "SpeakerName: [tag] text" into dialogue inputs.
    If speaker_to_voice is provided, use it to map speaker names to voice_ids.
    Otherwise maps by order of first appearance using VOICE_IDS.
    Merges consecutive lines from the same speaker into longer segments.
    """
    # Pattern: SpeakerName: [optional tag] rest of line
    line_re = re.compile(r"^([^:]+):\s*(?:\[([^\]]+)\]\s*)?(.+)$", re.MULTILINE)

    voice_map: dict[str, str] = {}
    if speaker_to_voice:
        voice_map = dict(speaker_to_voice)

    inputs_list: list[dict] = []
    current_segment: dict | None = None

    lines = script.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        match = line_re.match(line)
        if match:
            speaker = match.group(1).strip()
            tag = match.group(2)
            text = match.group(3).strip()

            if not text:
                i += 1
                continue

            # Map speaker to voice_id
            if speaker not in voice_map:
                if speaker_to_voice is not None:
                    raise ValueError(
                        f"Unknown speaker '{speaker}' in script. Expected one of: {list(speaker_to_voice.keys())}"
                    )
                idx = len(voice_map)
                if idx >= len(VOICE_IDS):
                    raise ValueError(
                        f"More unique speakers ({idx + 1}) than VOICE_IDS ({len(VOICE_IDS)}). "
                        "Add more voice IDs or provide speaker_to_voice map."
                    )
                voice_map[speaker] = VOICE_IDS[idx]

            voice_id = voice_map[speaker]
            if tag:
                segment_text = f"[{tag}] {text}"
            else:
                segment_text = text

            # Merge with previous segment if same speaker (smoother audio flow)
            if current_segment and current_segment["voice_id"] == voice_id:
                current_segment["text"] = current_segment["text"] + " " + segment_text
            else:
                current_segment = {"text": segment_text, "voice_id": voice_id}
                inputs_list.append(current_segment)
        elif current_segment and line.strip():
            # Multi-line: append to previous segment
            current_segment["text"] = current_segment["text"] + " " + line.strip()
        i += 1

    return inputs_list


def send_to_elevenlabs(inputs: list[dict]) -> None:
    """Call ElevenLabs Text to Dialogue API and save audio to OUTPUT_AUDIO_PATH."""
    from elevenlabs import ElevenLabs, ModelSettingsResponseModel

    if not os.environ.get("ELEVENLABS_API_KEY"):
        raise ValueError("ELEVENLABS_API_KEY environment variable is required for ElevenLabs")

    client = ElevenLabs()

    audio = client.text_to_dialogue.convert(
        inputs=inputs,
        model_id="eleven_v3",
        output_format="mp3_44100_128",
        settings=ModelSettingsResponseModel(stability=ELEVENLABS_STABILITY),
    )

    with open(OUTPUT_AUDIO_PATH, "wb") as f:
        for chunk in audio:
            f.write(chunk)

    print(f"Audio saved to {OUTPUT_AUDIO_PATH}")


def apply_studio_polish(input_path: str, output_path: str) -> None:
    """Add very subtle room tone only. Reverb was removed—it caused a 'can' effect."""
    from pydub import AudioSegment
    from pydub.generators import WhiteNoise

    voice = AudioSegment.from_mp3(input_path)

    # Room tone: very quiet white noise (-54 dB) — barely perceptible
    noise = WhiteNoise().to_audio_segment(duration=len(voice)).apply_gain(-54)
    mixed = voice.overlay(noise)

    mixed.export(output_path, format="mp3", bitrate="128k")
    print(f"Post-processed audio saved to {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Solostream podcast episode")
    parser.add_argument(
        "--topic-file",
        type=str,
        metavar="PATH",
        help="Path to topic MD file (from run_planner.py). Uses narrative brief and hosts.",
    )
    args = parser.parse_args()

    topic_data: dict | None = None
    speaker_to_voice: dict[str, str] | None = None

    if args.topic_file:
        topic_data = load_topic_from_file(args.topic_file)
        ep = topic_data.get("episode_type", "interview")
        d_min, d_max = topic_data.get("duration_min", 5), topic_data.get("duration_max", 7)
        print(f"Loaded topic from {args.topic_file} ({ep} {d_min}-{d_max} min)")

        # Load characters and build character_list + speaker_to_voice
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
            speaker_to_voice = {c["name"]: c["voice_id"] for c in character_list}
            print(f"  Hosts: {', '.join(c['name'] for c in character_list)}")
        else:
            print("  No characters matched; using default solo narrator")

    if SEND_TO_OPENAI or topic_data is not None:
        print("Generating podcast script with OpenAI...")
        script = generate_script(topic_data=topic_data)
        with open(OUTPUT_SCRIPT_PATH, "w", encoding="utf-8") as f:
            f.write(script)
        print(f"Script saved to {OUTPUT_SCRIPT_PATH}")
    else:
        print(f"Loading existing script from {OUTPUT_SCRIPT_PATH}...")
        with open(OUTPUT_SCRIPT_PATH, "r", encoding="utf-8") as f:
            script = f.read()

    inputs = parse_script(script, speaker_to_voice=speaker_to_voice)
    print(f"Parsed {len(inputs)} dialogue segments")

    if SEND_TO_ELEVENLABS:
        print("Sending to ElevenLabs...")
        send_to_elevenlabs(inputs)

        if APPLY_POSTPROCESSING:
            print("Applying post-processing...")
            apply_studio_polish(OUTPUT_AUDIO_PATH, OUTPUT_AUDIO_POSTPROCESSED_PATH)
    else:
        print("SEND_TO_ELEVENLABS is False. Set to True to generate audio.")


if __name__ == "__main__":
    main()
