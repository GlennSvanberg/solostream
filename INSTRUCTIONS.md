# Solostream: How to Use

This guide explains how to create episodes, sync content to the web app, and generate host segments.

---

## Prerequisites

- **Python 3** with packages from `requirements.txt`
- **Node.js** (for sync script and web app)
- **API keys** in `.env`:
  - `OPENAI_API_KEY` — required for planning, episode generation, and host segments
  - `ELEVENLABS_API_KEY` — optional, only for `generate_podcast.py` (ElevenLabs TTS)

```bash
pip install -r requirements.txt
```

---

## Workflow Overview

```
input/          →  run_planner.py     →  topics/
topics/*.md     →  generate_episode_* →  episodes/
episodes/       →  sync-episodes.js   →  web/public/episodes/
episodes.json   →  generate_host_segments.py → web/public/host/
```

---

## 1. Add Input (Optional)

Put notes, ideas, or fragments in `input/`:

- **.txt** — Raw notes
- **.md** — Markdown
- **.json** — Structured data (content extracted from `content`, `notes`, `text`)

The planner reads all supported files when proposing new topics. No special structure required.

---

## 2. Plan Topics

Generate new topic files from your input:

```bash
# Full run: plan, research, write topic files to topics/
python run_planner.py

# Dry run: see proposed topics without writing
python run_planner.py --plan-only

# Custom input/topics folders
python run_planner.py --input-dir input --topics-dir topics
```

**Output:** Topic files like `topics/2026-02-28-voice-stack-2026-top-tts-tools-and-implications.md` with:
- Frontmatter (title, format, hosts, guest, duration)
- Narrative brief (detailed content for the scriptwriter)
- Optional external signals (from web search)

---

## 3. Create an Episode

Generate audio from a topic file. Three options:

### Option A: OpenAI TTS (recommended)

Higher quality than Edge, cheaper than ElevenLabs.

```bash
python generate_episode_openai.py --topic-file topics/2026-02-28-voice-stack-2026-top-tts-tools-and-implications.md
```

**Output:** `episodes/2026-02-28-voice-stack-2026-top-tts-tools-and-implications.txt` and `*_postprocessed.mp3`

### Option B: ElevenLabs TTS

Best quality, paid API.

```bash
python generate_podcast.py --topic-file topics/2026-02-28-voice-stack-2026-top-tts-tools-and-implications.md
```

Requires `ELEVENLABS_API_KEY`.

### Option C: Edge TTS (free)

No API key. Good for testing.

```bash
python generate_episode_free.py --topic-file topics/2026-02-28-voice-stack-2026-top-tts-tools-and-implications.md
```

---

## 4. Sync Episodes to Web

Copy episodes from `episodes/` to `web/public/episodes/` and build `episodes.json`:

```bash
# From repo root (either script works)
node scripts/sync-episodes.js
# or
node web/scripts/sync-episodes.js
```

**What it does:**
- Copies all `*_postprocessed.mp3` files to `web/public/episodes/`
- Generates `web/public/episodes.json` with id, title, url for each episode
- Reads topic frontmatter from `topics/*.md` and resolves `hosts` and `guest` names via `characters.yaml`, adding them to the JSON manifest so the player can display who is in the episode

---

## 5. Generate Host Segments

Create intro/outro segments for each episode (unique scripts, OpenAI TTS):

```bash
python generate_host_segments.py
```

**When to run:** After `sync-episodes.js` when episodes change.

**Output:**
- `web/public/host/{episode-id}-intro_postprocessed.mp3`
- `web/public/host/{episode-id}-outro_postprocessed.mp3`
- `web/public/host_segments.json` (manifest for player integration)

**Options:**
```bash
# Custom paths
python generate_host_segments.py --episodes-json web/public/episodes.json --output-dir web/public/host

# Regenerate only intros or only outros
python generate_host_segments.py --slots intro
python generate_host_segments.py --slots outro
```

---

## 6. Add Transitional Music (Optional)

Short music clips play between episode blocks. Three options:

### Option A: Free static download (recommended, no API key)

Download pre-selected CC-licensed ambient clips to `web/public/music/`:

```bash
python generate_music.py --fetch-static
```

**What it does:** Fetches 2 ambient tracks from Silverman Sound (CC BY 4.0) and Kjartan Abel (CC BY-SA 4.0). Skips files that already exist. Updates `web/public/music.json` automatically.

### Option B: Manual static clips

1. Download 2–3 ambient clips from [Pixabay Music](https://pixabay.com/music/) (filter: ambient, calm, ~30 sec)
2. Save to `web/public/music/` (e.g. `calm-001.mp3`, `reflective-001.mp3`)
3. Generate manifest:

```bash
python generate_music.py --scan
```

### Option C: AI-generated (Pollinations or Replicate)

```bash
# Pollinations (free with API key from enter.pollinations.ai)
python generate_music.py --backend pollinations --mood calm --duration 30
# Add POLLINATIONS_API_KEY to .env

# Replicate MusicGen (~$0.05/clip, higher quality)
python generate_music.py --backend replicate --mood calm --duration 30
# Add REPLICATE_API_TOKEN to .env
```

**Moods:** calm, reflective, technological, ambient (or pass custom mood)

**Output:** `web/public/music/{mood}-{id}.mp3` and updates `web/public/music.json`

**Stream order (with music):** `[music] → [host intro] → [episode] → [host outro]` per episode, then repeat. Music rotates through the pool.

---

## 7. Run the Web App

```bash
cd web
npm install
npm run dev
```

Open the URL shown (e.g. `http://localhost:5173`).

---

## Quick Reference: Full Pipeline

```bash
# 1. Add notes to input/
# 2. Plan topics
python run_planner.py

# 3. Generate episode from a topic
python generate_episode_openai.py --topic-file topics/YYYY-MM-DD-your-topic-slug.md

# 4. Sync to web
node scripts/sync-episodes.js

# 5. Generate host segments
python generate_host_segments.py

# 6. (Optional) Add music: python generate_music.py --fetch-static  (free, no API key)
#    Or: download to web/public/music/ then python generate_music.py --scan
#    Or: python generate_music.py --backend replicate --mood calm

# 7. Run web app
cd web && npm run dev
```

---

## File Structure

| Path | Purpose |
|------|---------|
| `input/` | Raw notes for planner |
| `topics/` | Topic MD files (narrative briefs) |
| `episodes/` | Generated scripts and MP3s |
| `web/public/episodes/` | Episodes served by web app |
| `web/public/episodes.json` | Episode manifest |
| `web/public/host/` | Host intro/outro MP3s |
| `web/public/host_segments.json` | Host segment manifest |
| `web/public/music/` | Transitional music MP3s |
| `web/public/music.json` | Music manifest |
| `characters.yaml` | Voice config (hosts, narrator, solostream_host) |

---

## Manual Topic Creation

You can create a topic file by hand instead of using the planner. Use this structure:

```markdown
---
title: Your Topic Title
created: 2026-02-28
status: researched
episode_type: interview
format: interview
duration_min: 5
duration_max: 7
hosts: [sarah]
guest: nina
---

# Narrative brief

Detailed content for the scriptwriter. Include concrete facts, examples, and talking points.
```

**Episode types:** `short` (2–3 min solo), `interview` (5–7 min host+guest), `discussion` (15–25 min two hosts)

**Characters:** See `characters.yaml` for available `hosts` and `guest` ids (james, sarah, daniel, charlotte, george, lily, marcus, nina).
