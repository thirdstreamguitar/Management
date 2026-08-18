# Third Stream — AI Management Company

Automated social media management for **@fupingryuguitar** (jazz/classical guitar).
Instagram first, then Facebook, YouTube Shorts and TikTok.

**Operating principle:** the human plays guitar and shoots video. Everything downstream of "raw clip exists" is machine work. Target steady-state human time: **~30 minutes per week.**

## Documents

| Doc | What it covers |
|---|---|
| [`docs/operating-plan.md`](docs/operating-plan.md) | The full workflow — six departments, architecture, budget, roadmap, guardrails |
| [`docs/phase-0-setup.md`](docs/phase-0-setup.md) | **Start here.** What you click once (~15 min), then a paste-able prompt that hands the rest to an agent |
| [`docs/phase-1-repost-engine.md`](docs/phase-1-repost-engine.md) | Buildable spec for the first thing to ship: repost old winners as Trial Reels |

## Scripts

| Script | What it does |
|---|---|
| `scripts/probe.py` | Asks the live account what it can actually do — supported metrics, `trial_params`, token expiry — and writes `data/capabilities.json`. Stdlib only, no install. |
| `scripts/backfill.py` | Pulls every post plus age-bucketed insight snapshots into `data/posts.db`. Reads `capabilities.json`, so it never requests a metric this account doesn't support. |

## The six departments

1. **Intelligence** — nightly insights pull, weekly analysis brief, quarterly algorithm research
2. **Studio** — human filming + AI assist (musical hook detection, subtitles, covers, tagging)
3. **Copy** — captions, searchable keywords, 3–5 hashtags, send-triggers
4. **Publishing** — timing model from own data, approval gate, Graph API posting
5. **Growth Lab** — the repost + Trial Reel experiment engine ← **build this first**
6. **Audience** — link-in-bio funnel, email list, Facebook for the older demographic

## What it optimizes for

Not followers. Followers is a lagging metric. The system tracks four ratios:

- **sends ÷ reach** — the most heavily weighted Reels signal in 2026
- **avg watch time ÷ duration** — retention
- **profile visits ÷ reach** — does the content make people curious about you
- **follows ÷ profile visits** — does your profile close

## Architecture

Hybrid. GPU work (Whisper, Qwen3 14B, VLM, FFmpeg) runs on the Windows/4070 box for free.
A €4/mo VPS handles the always-on scheduler, database, email and approval UI.
Claude Code Routines against this repo do the weekly strategy at no marginal cost.

**Total running cost: ≈ €5/month.**

## Status

Planning complete; Phase 0 tooling written and ready to run.

**Next step:** [`docs/phase-0-setup.md`](docs/phase-0-setup.md) — ~15 minutes of Meta console
setup by hand, then paste the prompt in Part B into a Claude Code or Cowork tab and the agent
takes it from there.

Run the scripts **on your PC or the VPS**, not in a hosted web session — `graph.facebook.com`
is blocked by egress policy in most sandboxed environments. The probe detects this and reports
it as a network problem rather than blaming your token.

The four open questions in [§14 of the operating plan](docs/operating-plan.md#14-to-verify-before-building)
are what `probe.py` exists to answer. Until it runs, treat those four as unverified.
