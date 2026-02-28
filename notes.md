# solostream — MVP Context

Solostream is a personal AI radio station that turns your daily notes into a short narrated audio reflection. It produces one daily episode (~5–7 min) from your raw thoughts, using ElevenLabs for natural narration. The MVP tests whether people will voluntarily come back to listen again, unprompted.

## What this is

solostream is an experiment in **personal audio reflection**.

The goal is to test whether people will **voluntarily listen to a short, daily audio narration of their own life** — created from their raw notes and lightly contextualized with the outside world.

This is not a podcast app, a music app, or a productivity tool.

It is a **personal AI radio station**, starting in its simplest possible form:
→ one user  
→ one daily episode  
→ one voice  
→ ~5–7 minutes

The only thing this MVP must prove:
**Will a user come back tomorrow to listen again, unprompted?**

---

## Core Hypothesis

> People are overwhelmed by input but under-supported in reflection.  
> A calm, narrated daily audio reflection can become a habit.

If this is false, nothing else matters.

---

## MVP Scope (Strict)

### Included
- One daily, pre-generated audio episode (~5–7 min)
- Single narrator voice (ElevenLabs)
- Input via raw text (manual paste or message dump)
- Simple producer logic (theme detection + light external context)
- Manual or semi-manual generation is acceptable

### Explicitly Excluded
- No 24/7 stream
- No live generation
- No background music
- No ads
- No HLS / streaming illusion
- No multi-user support
- No UI beyond basic input/output
- No scaling concerns

If it’s not required to test **return-to-listen behavior**, it does not belong in the MVP.

---

## User Loop (v0.1)

1. **Ingest**
   - User provides raw thoughts:
     - short texts
     - fragments
     - ideas
     - voice-note transcripts
   - No formatting, no editing, no “content creation”

2. **Produce (Once per day)**
   - Extract:
     - dominant themes
     - emotional tone
     - contradictions or tension
   - Optionally pull **1–2 external signals**:
     - news
     - cultural reference
     - idea that validates or challenges the user’s thinking
   - No deep browsing, no rabbit holes

3. **Narrate**
   - Generate a spoken script designed for listening
   - Structure:
     1. Opening recognition of the day
     2. Reflection on recurring ideas
     3. External mirror or contrast
     4. Gentle close (no CTA)

4. **Deliver**
   - Output as a single audio file (MP3)
   - User listens passively

---

## Tone & Voice Rules

- Calm, confident, human
- Not therapy
- Not coaching
- Not hype
- Not summarizing like meeting notes
- No productivity advice
- No calls to action

The voice should feel like:
> “Someone thoughtful who has been paying attention.”

Slight discomfort is acceptable. Manipulation is not.

---

## TTS Choice

**Text-to-Speech Engine:** ElevenLabs

Reasons:
- Best-in-class emotional nuance
- Natural prosody for long-form narration
- Supports consistent narrator voice
- Suitable for podcast-quality output

Latency is irrelevant. Quality and emotional realism are the priority.

---

## Success Metrics (Only These)

1. **Day-2 Return Rate**
   - Did the user listen again the next day without prompting?
   - Target: ≥30%

2. **Completion Rate**
   - Did the user finish the episode?
   - Target: ≥70%

3. **Voluntary Input**
   - Did the user send thoughts without being asked?

Ignore all other metrics.

---

## What This Is NOT (Important)

- Not a feed
- Not social
- Not a journal
- Not an assistant
- Not content discovery

solostream is about **continuity**, not consumption.

---

## Future (Out of Scope for MVP)

Only considered if MVP succeeds:
- Background music
- Live / pseudo-live streaming
- Dynamic HLS
- Tribe/shared segments
- Ad-supported personalization
- Multiple voices / hosts

None of these matter until daily listening is proven.

---

## Build Philosophy

- Optimize for emotional truth, not technical elegance
- Manual steps are acceptable early
- If it doesn’t work when handcrafted, automation won’t save it
- Stop immediately if users don’t return
