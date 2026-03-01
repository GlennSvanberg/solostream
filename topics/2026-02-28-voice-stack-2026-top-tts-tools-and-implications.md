---
title: "The voice stack in 2026: top TTS tools, what they enable, and what to watch for"
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

Host + guest conversation that maps the current voice-generation landscape into a usable “stack” (capture → synthesis → editing → deployment), then explores the new powers and the risks. Make it concrete: name tools, typical use cases, and operational considerations.

Key themes / questions (with angles and facts/examples the script can use):
1) “If someone says ‘AI voice,’ what do they actually mean?”
   - Distinguish: text-to-speech (TTS), voice conversion, cloning, dubbing/translation, and full voice agents.
   - Anchor examples: audiobook-style narration, customer support IVR, podcast voice intros, multilingual product videos.
2) “Who are the major tool categories and recognizable players right now?”
   - Name widely discussed vendors/tools in each category (keep as examples, not endorsements):
     - High-quality TTS / voice libraries: ElevenLabs; OpenAI TTS; Google Cloud Text-to-Speech; Amazon Polly; Microsoft Azure Neural TTS.
     - Dubbing / localization workflows: e.g., tools positioned for dubbing/translation such as ElevenLabs dubbing and similar platforms.
     - Editing/cleanup around voice: Descript for podcast-style editing; Adobe Audition as a classic DAW reference; Whisper-style transcription as the companion layer.
   - Keep claims modest: “commonly used,” “widely referenced,” rather than “best.”
3) “What new powers does this unlock—specifically?”
   - Concrete unlocks:
     - Rapid iteration: generate multiple reads (serious, playful, short) without re-recording.
     - Localization at scale: same script in multiple languages with consistent cadence.
     - Accessibility: create audio versions of internal docs and newsletters.
     - Personal radio / daily reflections (tie back to Solostream concept): turn notes into narrated audio.
   - Provide 2–3 real workflow mini-stories the host can ask about:
     - A small team producing weekly product updates in 5 languages.
     - A consultancy producing client-ready “audio memos” after workshops.
     - An educator converting lesson notes into short audio summaries.
4) “What’s the catch: rights, consent, and trust?”
   - Practical checkpoints:
     - Consent for voice cloning and clear labeling when synthetic voice is used.
     - Data handling: where voice samples and transcripts are stored; retention policies.
     - Brand risk: deepfake concerns and the need for verification steps.
   - Mention public, broadly understood context: synthetic media/deepfakes have increased misinformation concerns; many platforms and jurisdictions are moving toward disclosure norms.
5) “How do you choose a tool for a real deployment?”
   - A selection checklist:
     - Quality: natural prosody, pronunciation controls (SSML), emotion/stability.
     - Operations: API availability, latency, batching, uptime, pricing.
     - Governance: admin controls, audit logs, user permissions.
     - Legal: licensing terms for commercial use; voice actor agreements if using a commissioned voice.
   - Host should ask for a simple decision tree (prototype → pilot → production).

Include at least two concrete demonstrations the guest can describe verbally:
- A/B: same paragraph rendered with (a) generic voice and (b) custom voice, noting differences (pacing, breathiness, sibilance, mispronounced names).
- “Pronunciation edge cases”: company names, acronyms, and multilingual names; show how SSML or pronunciation dictionaries matter.

Close with: one practical recommendation for listeners to try this week (e.g., pick a 200-word memo, generate 3 voices, measure which one people actually listen to).


# External signals (optional)

“EmergentTTS‑Eval’s new benchmark reveals that while ElevenLabs often wins in emotional prosody, OpenAI’s GPT‑4o‑mini‑TTS can outperform it on nuanced pronunciation accuracy and expressiveness—even though it still trails in raw prosody scores.” ([arxiv.org](https://arxiv.org/abs/2505.23009?utm_source=openai))

“Meanwhile, VoXtream’s breakthrough streaming TTS launches speech from the first word with just about 102 ms latency, dramatically undercutting ElevenLabs’ roughly 400 ms while preserving high-quality voice—an elegant contrast between immediacy and artistry.” ([arxiv.org](https://arxiv.org/abs/2509.15969?utm_source=openai))
