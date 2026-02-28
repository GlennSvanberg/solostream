---
title: From pilot to practice: enabling AI in a consultancy without breaking trust
created: 2026-02-28
status: researched
episode_type: discussion
format: discussion
duration_min: 15
duration_max: 25
hosts: [nina, daniel]
---

# Narrative brief

Two-host deep dive on what it actually takes to “enable AI” inside a consultancy (strategy + delivery), beyond buying licenses. Position it as a systems-and-trust problem: client confidentiality, quality control, repeatable workflows, and measurable value.

Core beats (build the conversation in these sections):
1) Why consultancies are a special case (risk + leverage)
- Consultancies sell judgment and credibility; an AI mistake isn’t just a bug, it’s reputational damage.
- High-leverage use cases exist because work is language-heavy: proposal writing, research synthesis, meeting notes, slide narratives, coding accelerators, and analysis.

2) Start with a “use-case map,” not a tool map
- Separate work into: (a) internal-only (business development, knowledge management), (b) mixed (drafts that get human-reviewed), (c) client-facing (highest risk).
- Concrete examples to anchor: RFP/proposal first drafts; interview guide creation; summarizing discovery calls into hypotheses; generating a first pass of a comms plan; refactoring internal scripts.

3) The minimum governance kit (lightweight, but real)
- Data classification: what can go into public models vs private/enterprise vs must-never-leave (client identifiers, contract terms, M&A, regulated data).
- Model access tiers: “sandbox” for experimentation, “approved” for delivery work.
- Mandatory prompt hygiene checklist (simple, repeatable): remove client names; use placeholders; don’t paste raw contracts; cite sources; label assumptions.

4) Quality system: how to prevent plausible nonsense from shipping
- Establish a review standard for AI-assisted outputs: factual claims require sources; quantitative outputs require re-calculation; legal/HR language must be reviewed by qualified humans.
- Introduce a “red-team” step for high-stakes deliverables (someone tries to break the logic / find hallucinations).
- Concrete practice: require an “evidence table” slide for client decks—claim, source, confidence, owner.

5) Knowledge management: making work reusable without becoming a data swamp
- Build a curated internal playbook library: reusable frameworks, prompt templates, industry primers.
- Retrieval-augmented workflows: search internal knowledge first, then generate; avoid making the model the source of truth.
- Naming and versioning discipline: a lightweight taxonomy for prompts and artifacts (e.g., Client/Industry/Function/Deliverable/Date).

6) Training that sticks: behavior change for busy consultants
- 3-layer training approach: (1) 60-minute baseline (risk + basics), (2) role-based labs (analyst/manager/partner), (3) office hours + champions.
- Practice-based exercises: rewrite a slide story; create an issue tree; summarize a 45-minute call into decisions/risks/next steps; turn messy notes into a client-ready memo.

7) Measuring ROI without vanity metrics
- Track cycle-time reductions (proposal turnaround time, deck revision loops), quality metrics (rework rate, client corrections), and utilization (percent of staff using approved workflows weekly).
- Simple benchmark targets to discuss: 20–30% time saved on first drafts is plausible when the review process is tight; value comes from faster iteration, not from skipping judgment.

8) Client trust and contracting: the external conversation
- Transparency policy: when to disclose AI assistance (and how) depending on client expectations.
- Contract clauses / client security requirements: align with NDAs, data processing agreements, and client tool restrictions.
- Real-world anchor: many enterprise clients already restrict sharing data with non-approved SaaS; the consultancy needs an “AI acceptable use” addendum.

9) The operating model: who owns this?
- Define a small AI enablement team: security + legal + delivery leader + enablement lead.
- Champions network in each practice area.
- Intake process for new use cases: assess value, risk, and required controls.

10) Close with a realistic 90-day rollout plan (concrete sequence)
- Weeks 1–2: policy + data classification + approved tools.
- Weeks 3–6: 3–5 high-frequency internal workflows (proposal drafting, meeting-to-memo, research synthesis).
- Weeks 7–12: expand to client-facing drafts with review gates; publish internal playbooks; run office hours; start measuring cycle time.

Make sure the hosts keep returning to one theme: “AI capability is easy; dependable delivery is the hard part.”

# External signals (optional)

McKinsey's decision in July 2025 to bar its China practice from engaging in any generative AI–related consulting—citing both geopolitical sensitivities and client confidentiality risks—echoes the tension between innovation and discretion.([ft.com](https://www.ft.com/content/9907da48-3e6d-4208-a1d7-44a85c6a77f8?utm_source=openai))

Just 10 percent of law firms and 21 percent of corporate legal teams had actually implemented any generative AI policies as of late 2024, despite rapid AI adoption—highlighting a widespread lag in formalizing safeguards around client data and transparency.([legaltechnology.com](https://legaltechnology.com/2024/12/02/just-10-of-law-firms-have-a-genai-policy-new-thomson-reuters-report-shows/?utm_source=openai))

A 2025 Journal of Accountancy reflection argues that even where no legal requirement exists, voluntary disclosure of generative AI use to clients can preserve trust and protect against perceived deception—suggesting that transparency may be a strategic, not just ethical, imperative.([journalofaccountancy.com](https://www.journalofaccountancy.com/issues/2025/apr/should-i-disclose-my-use-of-gen-ai-to-clients/?utm_source=openai))
