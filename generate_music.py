#!/usr/bin/env python3
"""
Generate short transitional music clips for Solostream.

Supports Pollinations (free) and Replicate MusicGen (~$0.05/clip).
Output: web/public/music/{mood}-{id}.mp3 and updates music.json.

  python generate_music.py --backend pollinations --mood calm --duration 30
  python generate_music.py --backend replicate --mood reflective --duration 30
  python generate_music.py --scan  # Generate music.json from existing files in web/public/music/
  python generate_music.py --fetch-static  # Download free ambient clips (CC-licensed) to web/public/music/

Requires: No API key for Pollinations (basic). REPLICATE_API_TOKEN for Replicate.
"""

import argparse
import json
import os
import re
import urllib.parse
import urllib.request
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_OUTPUT_DIR = SCRIPT_DIR / "web" / "public" / "music"
DEFAULT_MUSIC_JSON = SCRIPT_DIR / "web" / "public" / "music.json"

# Free static clips (CC-licensed, royalty-free). Used by --fetch-static.
# Sources: Silverman Sound (CC BY 4.0), Kjartan Abel (CC BY-SA 4.0)
STATIC_MUSIC_URLS = [
    ("calm-001", "https://www.silvermansound.com/wp-content/uploads/ascension.mp3", "calm"),
    ("ambient-001", "https://usercontent.one/wp/kjartan-abel.com/wp-content/uploads/2024/01/Winterstorm-I-by-Kjartan-Abel.mp3", "ambient"),
]

MOOD_PROMPTS = {
    "calm": "calm ambient instrumental 30 seconds, no vocals, lo-fi, peaceful, soft pads",
    "reflective": "reflective ambient instrumental 30 seconds, no vocals, thoughtful, gentle piano",
    "technological": "subtle electronic ambient 30 seconds, no vocals, minimal, tech feel",
    "ambient": "ambient instrumental 30 seconds, no vocals, atmospheric, ethereal",
}


def generate_pollinations(prompt: str, output_path: Path, duration: int) -> None:
    """Generate music via Pollinations API. Requires POLLINATIONS_API_KEY for audio generation."""
    encoded = urllib.parse.quote(prompt)
    url = f"https://gen.pollinations.ai/audio/{encoded}"
    headers = {"User-Agent": "Solostream/1.0"}
    if key := os.environ.get("POLLINATIONS_API_KEY"):
        headers["Authorization"] = f"Bearer {key}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = resp.read()
    output_path.write_bytes(data)


def generate_replicate(prompt: str, output_path: Path, duration: int) -> None:
    """Generate music via Replicate MusicGen (~$0.05/clip)."""
    import replicate

    if not os.environ.get("REPLICATE_API_TOKEN"):
        raise ValueError("REPLICATE_API_TOKEN environment variable is required for Replicate backend")

    output = replicate.run(
        "meta/musicgen",
        input={
            "prompt": prompt,
            "duration": min(duration, 30),
            "model_version": "melody",
        },
    )
    if isinstance(output, str):
        url = output
    else:
        url = str(output) if output else ""
    if not url:
        raise RuntimeError("Replicate returned no output")

    req = urllib.request.Request(url, headers={"User-Agent": "Solostream/1.0"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = resp.read()
    output_path.write_bytes(data)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate transitional music for Solostream")
    parser.add_argument(
        "--backend",
        choices=["pollinations", "replicate"],
        default="pollinations",
        help="Backend: pollinations (free) or replicate (~$0.05/clip)",
    )
    parser.add_argument(
        "--mood",
        type=str,
        default="calm",
        help="Mood: calm, reflective, technological, ambient (or custom prompt)",
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=30,
        help="Duration in seconds (max 30 for most APIs)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Output directory for MP3s",
    )
    parser.add_argument(
        "--music-json",
        type=Path,
        default=DEFAULT_MUSIC_JSON,
        help="Path to music.json manifest",
    )
    parser.add_argument(
        "--scan",
        action="store_true",
        help="Scan output dir and regenerate music.json from existing MP3s (no generation)",
    )
    parser.add_argument(
        "--fetch-static",
        action="store_true",
        help="Download free ambient clips from known CC-licensed URLs (no API key)",
    )
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)

    if args.scan:
        tracks = []
        for f in sorted(args.output_dir.glob("*.mp3")):
            stem = f.stem
            mood = stem.split("-")[0] if "-" in stem else "ambient"
            tracks.append({
                "id": stem,
                "url": f"/music/{f.name}",
                "mood": mood,
                "duration": 30,
            })
        with open(args.music_json, "w", encoding="utf-8") as out:
            json.dump({"tracks": tracks}, out, indent=2)
        print(f"Scanned {len(tracks)} track(s). Updated {args.music_json}")
        return

    if args.fetch_static:
        tracks = []
        for track_id, url, mood in STATIC_MUSIC_URLS:
            output_path = args.output_dir / f"{track_id}.mp3"
            if output_path.exists():
                print(f"Skipping {track_id} (already exists)")
                tracks.append({"id": track_id, "url": f"/music/{track_id}.mp3", "mood": mood, "duration": 30})
                continue
            print(f"Downloading {track_id} from {url[:50]}...")
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "Solostream/1.0"})
                with urllib.request.urlopen(req, timeout=60) as resp:
                    data = resp.read()
                output_path.write_bytes(data)
                tracks.append({"id": track_id, "url": f"/music/{track_id}.mp3", "mood": mood, "duration": 30})
                print(f"  Saved {output_path.name}")
            except Exception as e:
                print(f"  Failed: {e}")
        with open(args.music_json, "w", encoding="utf-8") as out:
            json.dump({"tracks": tracks}, out, indent=2)
        print(f"Updated {args.music_json}. Total tracks: {len(tracks)}")
        return

    prompt = MOOD_PROMPTS.get(args.mood.lower())
    if not prompt:
        prompt = f"{args.mood} instrumental 30 seconds, no vocals, ambient"

    existing = [f.stem for f in args.output_dir.glob("*.mp3")]
    base_id = re.sub(r"[^a-z0-9-]", "", args.mood.lower()) or "ambient"
    counter = 1
    while f"{base_id}-{counter:03d}" in existing:
        counter += 1
    track_id = f"{base_id}-{counter:03d}"
    output_path = args.output_dir / f"{track_id}.mp3"

    print(f"Generating {track_id} ({args.backend}, {args.mood})...")
    if args.backend == "pollinations":
        generate_pollinations(prompt, output_path, args.duration)
    else:
        generate_replicate(prompt, output_path, args.duration)

    print(f"Saved to {output_path}")

    tracks = []
    if args.music_json.exists():
        with open(args.music_json, "r", encoding="utf-8") as f:
            data = json.load(f)
            tracks = data.get("tracks", [])

    tracks.append({
        "id": track_id,
        "url": f"/music/{track_id}.mp3",
        "mood": base_id,
        "duration": args.duration,
    })

    with open(args.music_json, "w", encoding="utf-8") as f:
        json.dump({"tracks": tracks}, f, indent=2)

    print(f"Updated {args.music_json}. Total tracks: {len(tracks)}")


if __name__ == "__main__":
    main()
