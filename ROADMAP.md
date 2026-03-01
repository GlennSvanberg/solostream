# Solostream Roadmap: Infinite Personal Radio

**Vision:** A personal AI radio station that feels always live. The full catalog (episodes + music + host) loops. When we generate new content, it joins the rotation. Music between segments. Eventually ads. One host guiding the flow.

---

## Core Principles

| Principle | Meaning |
|-----------|---------|
| **Loop over full catalog** | All content cycles. No hard "end." New content is added to the loop when generated. |
| **Feel live** | No progress bar, no episode list. Show "Now Playing" and "Up Next" only. |
| **Flow** | 30 sec music clips between episodes. Host intros. Seamless transitions. |
| **Per-user state** | Track what each user has listened to. Resume where they left off. |

### Mental Model

```
LOOP: Full catalog (episodes + music + host) cycles. No hard "end."

LISTEN STATE:
  - played: segment completed (or 80%+)
  - probably_heard: played + tab visible most of the time
  - maybe_asleep: played + long idle + late night + tab hidden

PERSONALIZATION:
  - Light questionnaires (1–2 questions, rare, skippable)
  - Use probably_heard + responses to steer future content

DON'T MISS:
  - Default: trust "played"
  - Optional: "Resume from before sleep?" when maybe_asleep
  - Optional: "Replay last" for recent segment
```

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           USER BROWSER                                    │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────────────┐  │
│  │   Player    │  │  State      │  │  UI: Now Playing / Up Next       │  │
│  │  (segments) │  │  (local or  │  │  No progress bar, no episode list │  │
│  │             │  │   Convex)   │  │                                  │  │
│  └──────┬──────┘  └──────┬──────┘  └─────────────────────────────────┘  │
└─────────┼────────────────┼──────────────────────────────────────────────┘
          │                │
          ▼                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         BACKEND (Convex)                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │
│  │   Users     │  │  Playback   │  │  Content    │  │  Generation     │  │
│  │   Sessions  │  │  Position   │  │  Queue      │  │  Triggers       │  │
│  └─────────────┘  └─────────────┘  └─────────────┘  └────────┬────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
                                                               │
          ┌───────────────────────────────────────────────────┼───────────┐
          ▼                       ▼                            ▼           ▼
┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐   ┌─────────────┐
│  Episode Gen    │   │  Music Gen       │   │  Host Segment    │   │  Ad Slots   │
│  (existing      │   │  (AI: Suno,      │   │  (ElevenLabs     │   │  (future)   │
│   pipeline)     │   │   Mubert, etc)   │   │   TTS)           │   │             │
└─────────────────┘   └─────────────────┘   └─────────────────┘   └─────────────┘
```

---

## Phase 1: Segment Model & Music (Foundation)

**Goal:** Replace episode-only playback with a segment-based stream. Add 30 sec music between episodes.

### 1.1 Data Model: Segments

Introduce a unified segment type. Each item in the stream is a segment.

```ts
type Segment =
  | { type: "episode"; id: string; title: string; url: string }
  | { type: "music"; id: string; url: string; duration: number }
  | { type: "host"; id: string; script: string; url: string }
  | { type: "ad"; id: string; url: string }  // Phase 4
```

**Stream structure (loops over full catalog):**
```
[music 30s] → [host: "Coming up next..."] → [episode] → [host: "That was..."] → [music 30s] → ... → [loop]
```

### 1.2 AI Music Generation Tool

**Requirements:**
- 30 second clips
- Instrumental, ambient, or lo-fi (matches reflection tone)
- Royalty-free / commercial use
- API-driven for automation

**Options:**

| Provider | Duration | Style | API | Notes |
|----------|----------|-------|-----|-------|
| **Suno** | Configurable | Full control via prompt | REST, webhooks | Strong quality, popular |
| **Mubert** | 5s–25min | Text-to-music | REST | Royalty-free, flexible |
| **Producer AI** | ~30s | Studio quality | REST | $0.08/gen, fast |
| **Stable Audio** | Configurable | Open weights | API | Self-hostable option |

**Tool scope:**
- Script/CLI: `Generate-SolostreamMusic.ps1` or Node script
- Input: mood (e.g. "calm", "reflective"), duration (default 30s)
- Output: MP3 to `web/public/music/` or Convex file storage
- Catalog: `music.json` or DB table with id, url, mood, duration

**Suggested starting point:** Suno or Mubert API. Build a simple Node script first; integrate into pipeline later.

### 1.3 Player Changes

- **Current:** `Episode[]` → `Segment[]`
- **Logic:** On segment `ended`, advance to next segment. Loop to start when reaching end of catalog.
- **Transitions:** No crossfade initially; clean cuts. Crossfade can be Phase 2 polish.

### 1.4 Static Music for MVP

Before AI music tool is ready: use 2–3 royalty-free 30s clips (e.g. from Pixabay, Free Music Archive). Place in `web/public/music/`. Rotate between them. Proves the segment flow.

---

## Phase 2: Per-User State (Browser vs Convex)

**Goal:** Track what each user has listened to. Resume where they left off.

### 2.1 User Identity

**Option A: Anonymous (device-only)**
- Generate `deviceId` (UUID) on first visit, store in `localStorage`
- No auth. State is device-bound.
- **Pro:** Zero friction. **Con:** Lost on clear storage / new device.

**Option B: Convex Auth (recommended)**
- Email, Google, or similar
- State syncs across devices
- **Pro:** Cross-device, durable. **Con:** Sign-up friction.

**Option C: Hybrid**
- Start anonymous (localStorage). Offer "Save progress" → sign up → migrate state to Convex.

### 2.2 State to Track

| Field | Purpose |
|-------|---------|
| `userId` or `deviceId` | Who |
| `currentSegmentIndex` | Position in stream |
| `segmentId` | Which segment (for resume accuracy) |
| `playedSegmentIds` | List of completed segment IDs (for analytics, no replay) |
| `listenState` | Per-segment: `played` \| `probably_heard` \| `maybe_asleep` (see Listen Detection) |
| `lastListenAt` | Timestamp |

### 2.3 Storage Options

| Option | Pros | Cons |
|--------|------|------|
| **localStorage** | No backend, fast, simple | Device-only, ~5MB limit, no cross-device |
| **IndexedDB** | More space, async | Still device-only |
| **Convex** | Cross-device, real-time, scalable | Requires backend, auth for multi-device |

**Recommendation:** Start with **localStorage** for MVP (Phase 2a). Add **Convex** when you need cross-device or server-side logic (Phase 2b).

### 2.4 Convex Schema (when adopted)

```ts
// convex/schema.ts
defineSchema({
  users: defineTable({
    email: v.optional(v.string()),
    createdAt: v.number(),
  }),

  playbackState: defineTable({
    userId: v.id("users"),
    deviceId: v.optional(v.string()),  // for anonymous pre-auth
    currentSegmentIndex: v.number(),
    segmentId: v.string(),
    playedSegmentIds: v.array(v.string()),
    lastProbablyHeardIndex: v.optional(v.number()),  // for "resume from before sleep"
    lastListenAt: v.number(),
  }).index("by_user", ["userId"]),

  segments: defineTable({
    type: v.union(v.literal("episode"), v.literal("music"), v.literal("host"), v.literal("ad")),
    storageId: v.optional(v.id("_storage")),
    url: v.optional(v.string()),
    title: v.optional(v.string()),
    duration: v.optional(v.number()),
    order: v.number(),
  }).index("by_order", ["order"]),
});
```

---

## Listen Detection

**Goal:** Know if the user has actually listened vs. left it on, fell asleep, or walked away. Balance "don't miss content" with "doesn't require always attention."

### Listen Tiers

| Tier | Meaning | Use case |
|------|---------|----------|
| **played** | Audio ran to completion (or 80%+). | Baseline for "don't miss content." |
| **probably_heard** | Played + tab was visible most of the time. | Personalization, questionnaires. |
| **maybe_asleep** | Played + long idle + late night + tab hidden. | Offer "resume from before sleep?" |

**Default:** Trust "played." Don't punish background listening. If uncertain, treat as heard.

### Signals We Can Use

| Signal | How | Pros | Cons |
|-------|-----|------|------|
| Audio played | `timeupdate` / `ended` | Simple, reliable | No idea if they're present |
| Tab visible | `document.visibilityState` | Easy | Tab visible but user away |
| Tab focused | `window.focus` / `blur` | Easy | Same |
| Volume changes | User adjusts volume | Suggests engagement | Rare |
| Play/pause | User toggles | Strong signal | Many don't touch it |
| Interaction recency | Last click/scroll/key | Proxy for presence | Noisy |
| Time of day | When they listen | Sleep vs. active | Weak alone |

**Approach:** Combine a few cheap signals. No single perfect signal.

### Don't Miss vs. Doesn't Require Attention

| Approach | Behavior | Pros | Cons |
|----------|----------|------|------|
| **A. Trust the play** | If it played, count as heard | Simple, low friction | Overcounts sleep/away |
| **B. Visibility gate** | Only count if tab visible X% | Filters obvious "away" | Punishes background listening |
| **C. Soft markers** | "You might have missed this" vs. "You heard this" | Honest about uncertainty | More UI, logic |
| **D. Replay affordance** | "Replay last" / "Replay segment" | User controls what they missed | Adds UI, slightly breaks radio feel |
| **E. Sleep detection** | Long idle + late night → assume sleep | Targets common case | Heuristic, can be wrong |

**Recommendation:** Default to A. Add E (sleep heuristic) to downgrade when likely asleep. Avoid B (conflicts with background listening). Consider D (replay) as gentle escape hatch later.

---

## Sleep / Away Detection

**Goal:** Detect when user likely fell asleep or walked away. Don't mark content as "heard" during that window.

### Heuristics

1. **Long idle:** No interaction for 15–30+ min while audio plays.
2. **Time of day:** Late night (e.g. 11pm–6am) increases "probably asleep" likelihood.
3. **Tab state:** Tab hidden for extended period while playing.
4. **Volume:** At 0 or very low for whole segment.

### Action When "Probably Asleep"

- Don't mark segments as "heard" during that window.
- On next visit: *"Last time you might have drifted off. Pick up from [last segment before sleep] or continue from here?"*
- Or: silently resume from last "probably heard" segment.

**Caution:** Use sparingly. Don't assume sleep on every idle; require multiple signals.

---

## Questionnaires (Personalization)

**Goal:** Collect preferences for on-the-fly content generation. Light touch—not a chore.

### Timing

- After N episodes, or after a natural break (e.g. music segment), or when they pause.
- Rare: e.g. once a week. Not every session.

### Format

- 1–2 questions max.
- Easy skip; never blocking.
- Contextual: *"How was that episode?"* right after one plays.

### Example Prompts

- *"Quick one: What did you think of that?"* (thumbs up/down or 1–5)
- *"What would you like more of?"* (themes, topics, or free text)
- *"Was that the right length?"* (shorter / same / longer)

### Use

- Feed into content generation pipeline when we generate on-the-fly.
- Use `probably_heard` + responses to steer future episodes.

---

## Phase 3: UI Overhaul (Hide the Loop)

**Goal:** Radio feel. No progress bar. No episode list. Only "Now Playing" and "Up Next".

### 3.1 Remove

- [ ] Progress bar / seek bar
- [ ] Episodes popover/list
- [ ] Skip to previous/next (or keep as "tune" only if you want)
- [ ] Any indication of total duration or position in stream

### 3.2 Keep / Add

- [ ] **Now Playing:** Current segment title (episode title, or "Music" / "Solostream")
- [ ] **Up Next:** Next segment title
- [ ] Play / Pause
- [ ] Volume
- [ ] "On Air" badge
- [ ] "You're listening live" (or similar)

### 3.3 Optional: "Tune" Control

- Single "Next" to skip to next segment (like changing the dial)
- Or remove skip entirely for pure linear experience

---

## Phase 4: Content Generation Pipeline (Loop + New Content)

**Goal:** Full catalog loops. When we generate new content, it joins the rotation. No hard "end."

### 4.1 Queue Model

- **Catalog:** All segments (episodes + music + host) in rotation. Loops.
- **Generation:** New episode + music + host segments are appended to catalog when produced.
- **User position:** Each user has `currentSegmentIndex` in the catalog; advances through loop.

### 4.2 Generation Triggers

**Option A: Input-driven**
- User provides new notes → trigger episode generation
- New content joins catalog; all users eventually hear it in the loop

**Option B: Scheduled (Convex cron)**
- Cron runs daily (e.g. "reflection on yesterday" if no new input)
- Keeps catalog growing over time

**Option C: Preference-driven (later)**
- Questionnaire responses + listen state inform what to generate next
- Personalization: themes, length, tone based on feedback

**Recommendation:** Start with A (input-driven). Add B when you have a routine. C when personalization is live.

### 4.3 Generation Pipeline

1. **Episode:** Use existing topic → script → ElevenLabs pipeline
2. **Music:** Call AI music API or pick from pre-generated pool
3. **Host:** Generate "Coming up: [title]" via ElevenLabs (or template + TTS)
4. **Append** to catalog (shared loop). All users hear new content as they cycle through.

### 4.4 Input for New Episodes

- User's notes (existing flow)
- Or: "Reflection on yesterday" if no new input
- Or: Curated prompts / themes (future)

---

## Phase 5: Host Segments

**Goal:** Radio host voice that introduces "coming up" and "that was".

### 5.1 Script Templates

- `"Coming up next on Solostream: {episodeTitle}."`
- `"That was {episodeTitle}. Up next: {nextTitle}. Stay tuned."`
- `"You're listening to Solostream. Personal radio, right now."`

### 5.2 Generation

- **Option A:** Pre-record 5–10 generic phrases. Use for all.
- **Option B:** ElevenLabs TTS with dynamic `{episodeTitle}`. One host voice ID.
- **Option C:** AI-generated script (e.g. GPT) + ElevenLabs for variety.

**Recommendation:** B for MVP. One consistent host voice, template-based.

### 5.3 Placement

- Before each episode (coming up)
- After each episode (that was, up next)
- Optionally: top of "hour" or every N episodes (station ID)

---

## Phase 6: Ad Slots (Future)

**Goal:** Insert ad segments into the stream.

### 6.1 Placement

- After every 2–3 episodes
- Or: fixed intervals (e.g. every 15 min of content)

### 6.2 Segment Type

- `{ type: "ad", id: string, url: string }`
- Ads stored in Convex or CDN
- Targeting / rotation logic later

### 6.3 Skippability

- Decide: skippable after 5s, or unskippable (radio-style)

---

## Phase 7: AI Music Tool (Detailed)

**Goal:** Standalone tool to generate 30s music clips for Solostream.

### 7.1 Interface

```
# PowerShell
./scripts/Generate-Music.ps1 -Mood "calm" -Duration 30 -Output "web/public/music/calm-001.mp3"

# Or Node
node scripts/generate-music.js --mood calm --duration 30
```

### 7.2 Integration Points

- **Manual:** Run when you want new music in the pool
- **Automated:** Convex action or cron calls API when music pool is low
- **Per-user:** (Advanced) Generate mood-matched music based on user's recent themes

### 7.3 Music Pool

- Directory: `web/public/music/` or Convex file storage
- Manifest: `music.json` or DB with `{ id, url, mood, duration }`
- Player picks randomly from pool when inserting music segment

---

## Implementation Order

| Phase | Scope | Deps |
|-------|-------|------|
| **1a** | Segment model + static music (2–3 clips) | None |
| **1b** | AI music generation script (Suno/Mubert) | API key |
| **2a** | localStorage playback state | None |
| **2b** | Convex + auth + migration | Convex account |
| **2c** | Listen detection (signals, tiers) | 2a |
| **2d** | Sleep/away heuristics + "resume from before sleep?" | 2c |
| **3** | UI: remove progress/list, add Up Next | 1a |
| **3b** | Questionnaires (1–2 questions, rare, skippable) | 2c |
| **4** | Generation trigger + pipeline (adds to catalog loop) | 2b, existing episode gen |
| **5** | Host segments (template + TTS) | ElevenLabs |
| **6** | Ad slots | 4 |
| **7** | Music tool polish + automation | 1b |

---

## Open Questions

1. **Host voice:** Same as narrator or distinct "announcer" voice?
2. **Music mood:** Single mood (calm) or vary by episode theme?
3. **Skip control:** Allow "Next" to skip segment, or strict linear?
4. **Auth timing:** Require sign-up from day 1, or start anonymous?
5. **Sleep detection threshold:** How long idle + what time window = "maybe asleep"?
6. **Replay affordance:** Add "Replay last segment" or keep strict linear?
7. **Questionnaire frequency:** Once per week? After every N episodes?

---

## Success Metrics (Updated)

| Metric | Target |
|--------|--------|
| Day-2 return rate | ≥30% |
| Completion rate (per segment) | ≥70% |
| Catalog grows over time | New content added when input available |
| Cross-device resume | Works when Convex adopted |
| Questionnaire completion | Track; aim for non-intrusive, useful response rate |

---

## References

- [Suno API](https://docs.sunoapi.org/)
- [Mubert Text-to-Music](https://github.com/MubertAI/Mubert-Text-to-Music)
- [Producer AI](https://aimusicapi.ai/)
- [Convex Docs](https://docs.convex.dev)
- [ElevenLabs TTS](https://elevenlabs.io/docs) (existing)
