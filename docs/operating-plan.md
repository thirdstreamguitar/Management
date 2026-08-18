# Third Stream — AI Management Company

**Client:** @fupingryuguitar (1k–10k followers, Instagram → later YouTube Shorts / TikTok / Facebook)
**Mandate:** grow reach and followers, convert attention into teaching students and performance gigs, and keep in-app monetization as a secondary revenue line.
**Constraint that shapes everything:** the human's time goes into *playing guitar and shooting video*. Everything downstream of "raw clip exists" should be machine work.

---

## 0. The one-page version

```
   YOU                    THE MACHINE                          THE WORLD
   ───                    ───────────                          ─────────
                     ┌──────────────────────┐
 shoot a clip  ──►   │ 1. INTELLIGENCE      │  ◄── Instagram Insights API
 (whenever)          │    what's working    │      (nightly pull)
                     ├──────────────────────┤
                     │ 2. STUDIO            │
 approve the cut ◄── │    hook-finding,     │
                     │    subtitles, covers │
                     ├──────────────────────┤
                     │ 3. COPY              │
 approve caption ◄── │    caption + keywords│
                     ├──────────────────────┤
                     │ 4. PUBLISHING        │  ──► Instagram Graph API
                     │    queue + scheduler │      (posts at optimal times)
                     ├──────────────────────┤
                     │ 5. GROWTH LAB        │  ──► Trial Reels
                     │    repost old winners│      (72h non-follower test)
                     ├──────────────────────┤
                     │ 6. AUDIENCE          │  ──► email list, Facebook
                     │    funnel + nurture  │
                     └──────────────────────┘
                                │
                                ▼
                     students · gigs · in-app revenue
```

Six departments. Five are automated. You staff one: **Studio input** (play, film, approve).

---

## 1. What the machine actually optimizes for

Followers is a lagging vanity number. Optimizing for it directly produces bad decisions. The real causal chain is:

```
non-follower reach → profile visits → follows → email/DM → paying student or booked gig
```

So the system tracks **four ratios**, not raw counts:

| Metric | Formula | Why it matters | Target | Level |
|---|---|---|---|---|
| **Sends per reach** | `shares ÷ reach` | Mosseri has confirmed DM sends are the most heavily weighted Reels signal in 2026 — roughly 3–5× a like. This is *the* growth lever. | > 1.0% | per post |
| **Retention ratio** | `avg_watch_time ÷ video_duration` | Total watch time + replay rate is the #1 Reels ranking factor. | > 0.75 | per post |
| **Saves per reach** | `saved ÷ reach` | Saves rank second only to sends in 2026. Per-post and available — this carries the weight that profile conversion was meant to. | > 0.8% | per post |
| **Profile conversion** | `profile_views ÷ reach` | Measures whether the content makes people curious about *you*, not just the clip. | > 1.5% | **account/day only** |
| **Follow efficiency** | `follower_count` delta ÷ `profile_views` | Measures whether your profile/bio closes. Fix the bio, not the content, when this is low. | > 8% | **account/day only** |

> **Corrected 2026-08-18 by the Phase 0 probe.** The last two were originally
> specified per-post, as `profile_visits ÷ reach` and `follows ÷ profile_visits`.
> The Media Insights API does **not** support `profile_visits` or `follows` for
> reels on this account — see [`reports/phase-0-findings.md`](../reports/phase-0-findings.md).
> Both survive only as **account-level daily** figures (`profile_views`,
> `follower_count`), which cannot be attributed to an individual post. Anything
> in this plan that ranked or judged a *single post* on profile conversion has
> been rewritten. Treat the account-level versions as trend instruments — they
> tell you whether the bio is closing this week, not which reel did it.

Follow efficiency is still the cheapest thing to fix and the most commonly ignored. If 500 people visit the profile and 12 follow, the problem is the bio and the pinned three posts — not the reel. You just can no longer trace it to one reel.

**Positioning note.** "Third stream" (the Schuller sense — jazz and classical as one language) is an unusually specific, defensible niche. Specificity is an asset on a recommendation-driven platform: the algorithm needs a coherent topic signal to know who to show you to. The system should reinforce that, not dilute it into generic guitar content.

---

## 2. Department: INTELLIGENCE — market and algorithm research

**Runs:** nightly data pull (automated) + weekly analysis session (automated) + quarterly deep research (automated, reviewed by you).

### 2.1 Nightly: your own data

A cron job on the VPS pulls from `graph.instagram.com` (**not** `graph.facebook.com` — see the route note below) and appends to a local database:

- `GET /{ig-user-id}/media` — every post, with `id`, `media_type`, `caption`, `timestamp`, `permalink`
- `GET /{ig-media-id}/insights` — `reach`, `views`, `likes`, `comments`, `shares`, `saved`, `total_interactions`, `ig_reels_avg_watch_time`, `ig_reels_video_view_total_time`
- `GET /{ig-user-id}/insights` — account-level `reach`, `views`, `profile_views`, `website_clicks`, `accounts_engaged`, `total_interactions`, `follower_count`

> **Corrected 2026-08-18 by the Phase 0 probe.**
> - **Route.** This account authenticates with **Instagram Login**, so every
>   call goes to **`graph.instagram.com` v26.0**. An `IGAA`-prefixed token sent
>   to `graph.facebook.com` returns *"Invalid OAuth access token — Cannot parse
>   access token"*, which looks exactly like a corrupt token and is not one.
> - **Removed:** `profile_visits` and `follows` — unsupported for reels.
>   `plays`, `impressions`, `video_views` — not valid metric names on v26.0;
>   `views` replaces all three.
> - **Request shape.** `views`, `profile_views`, `website_clicks`,
>   `accounts_engaged` and `total_interactions` only answer when asked with
>   `metric_type=total_value`. Asking without it returns an error *identical* to
>   "metric unsupported". `data/capabilities.json` records the working shape per
>   metric; `backfill.py` reads it from there.
> - **Not verified:** `follower_demographics` and `online_followers` were never
>   probed. §5.2's timing model depends on `online_followers` — confirm it
>   exists before building that, or the timing model has no input.

Insights require a Professional account and 1,000+ followers — both confirmed: account type `MEDIA_CREATOR`, 1,676 followers. Data is captured on a **schedule relative to post age** (6h, 24h, 72h, 7d, 30d), because a post's 24-hour number and its 30-day number tell you completely different things. A reel that keeps accumulating reach at day 14 is evergreen and is a repost candidate; a reel that spikes and dies is a one-off.

> **The curve is forward-only.** A snapshot claims only the *newest* age
> threshold a post has already passed, so a post that is 200 days old when first
> captured gets a `30d` row and can never retroactively acquire a `6h` one. The
> complete five-point shape exists solely for posts published from 2026-08-18
> onward. Comparing early velocity across the historical library is impossible
> and should not be specified.
>
> Backfill actuals: 494 media, 303 snapshots — `30d`=288, `7d`=11, `72h`=2,
> `24h`=1, `6h`=1.
>
> **Insights begin at April 2020.** 191 media posted between 2014-03-21 and
> 2020-03-14 return no insights at all — a hard cutoff at the date the account
> converted to Professional, which Instagram does not backfill across. All 191
> are feed images, feed videos and one carousel; **no reel is affected**.

### 2.2 Weekly: the analysis session

This is where your Claude subscription does real work at zero marginal cost. A scheduled Claude Code session runs against this repo every Monday:

1. Reads the week's insights data (committed by the VPS as JSON/CSV)
2. Computes the four ratios per post, plus rolling 20-post medians as the account baseline
3. Correlates performance against content attributes the Studio tagged (piece, technique, tempo, hook type, video length, shot type, whether there's on-screen text)
4. Writes `reports/YYYY-WW-brief.md` — what worked, what didn't, three content directions for the coming week, and the repost queue for Growth Lab
5. Commits it

You read one markdown file a week. That's the entire research burden.

### 2.3 Quarterly: external landscape

An automated research pass on: Instagram algorithm changes, Reels format shifts, what's working for comparable jazz/classical guitar accounts, and any new Meta API surface. Output is a short delta document — *what changed and what we should change* — not a literature review.

**Standing algorithm facts as of Aug 2026** (re-verify quarterly, these move):
- Four separate ranking systems — Feed, Reels, Stories, Explore — weighted differently. Reels ranks on watch time and sends.
- Sends per reach > saves > meaningful comments > likes. Likes are now the weakest signal.
- Trial Reels drove roughly an 80% increase in non-follower reach for participating creators, per Instagram's own published figures.
- Hashtags are largely spent as a discovery mechanism. Instagram search is now keyword/semantic. **Write captions with searchable words in them** ("chord melody", "jazz guitar arrangement", "classical guitar right hand") and use 3–5 hashtags, not 30.

---

## 3. Department: STUDIO — video production (you + AI assist)

You are the creator. The realistic goal is not an "AI video editor" that replaces you — that tech is not good enough for musical performance video, where the cut has to land on the music. The goal is to **remove every non-musical decision** from your editing time.

### 3.1 What gets automated

| Task | Tool | Runs where |
|---|---|---|
| Transcription + word-level timestamps | faster-whisper `large-v3` (int8) | 4070, ~10× realtime |
| **Musical hook detection** | `librosa` onset density + spectral flux + RMS peaks | 4070 / CPU |
| Burned-in subtitles (styled) | FFmpeg + ASS from Whisper timings | 4070 |
| Silence / false-start trimming | `auto-editor` | CPU |
| Aspect conversion to 9:16, loudness normalize to −14 LUFS | FFmpeg | CPU |
| Cover frame candidates | VLM scores extracted frames for "is this a compelling still" | 4070 |
| Content tagging (piece, key, technique, shot type) | Qwen3 14B over transcript + VLM frame description | 4070 |

**The hook detector is the highest-value piece here.** For a musician, the single most important editing decision is *which three seconds go first*. A script that analyzes the audio for the passage with the highest dynamic and rhythmic interest — the run, the chord voicing, the moment the piece opens up — and proposes 3 candidate cold-opens with timecodes, does in 30 seconds what takes you 20 minutes of scrubbing. It doesn't need to be right every time. It needs to give you three good options to choose between.

### 3.2 What stays human

Choosing the take. Choosing the final hook from the candidates. Anything about musical taste. This is correct — it's also the part you actually enjoy.

### 3.3 Ingest

Drop a file in `inbox/`. A watcher picks it up, runs the full pipeline, and produces a folder with: the transcript, three hook proposals with timecodes, three cover frames, a subtitled cut, and a content-attribute JSON. You review, pick, and it moves to the Copy department. Target: **under 5 minutes of your time per video.**

---

## 4. Department: COPY — captions, keywords, hashtags

**Runs:** triggered when a video clears Studio.

### 4.1 Inputs

Transcript, content attributes, the current week's brief, the account's top-20 performing captions, and a **voice profile** — a document capturing how you actually write, built from your existing captions so output doesn't read as generic AI.

### 4.2 Output per video

- **3 caption variants** in different registers: (a) *teaching* — what's happening musically, (b) *story* — why this piece, where you learned it, (c) *invitation* — a question or prompt engineered for comments and sends
- **First line optimized separately.** The first ~40 characters are what shows before "more". It carries most of the weight.
- **Keyword block** — searchable terms woven into the caption naturally, for Instagram's semantic search
- **3–5 hashtags**, mixed reach tiers (one large, two mid, two niche)
- **A send-trigger line** where it fits — the explicit or implicit "send this to the guitarist who needs to hear it". Since sends are the top-weighted signal, engineering for them deliberately is the single highest-leverage copy decision.
- **On-screen text suggestion** for the first frame

### 4.3 Model routing (the budget decision)

- **Local Qwen3 14B (Q4_K_M) on the 4070** — bulk work: tagging, keyword extraction, hashtag sets, variant drafting. Free. Set `OLLAMA_FLASH_ATTENTION=1` to leave room for a 16K context.
- **Claude (your existing subscription, via scheduled Claude Code sessions)** — the weekly strategy brief and final caption polish, where writing quality genuinely differs.

Net API spend for this department: **€0.**

---

## 5. Department: PUBLISHING — scheduling and posting

### 5.1 Mechanism

Instagram Content Publishing API, three steps:

1. `POST /{ig-user-id}/media` with `media_type=REELS`, a publicly-reachable `video_url`, `caption`, `cover_url`
2. Poll `GET /{container-id}?fields=status_code` until `FINISHED`
3. `POST /{ig-user-id}/media_publish` with `creation_id`

The video needs a public URL for Meta to fetch — the VPS serves it from a temporary signed path.

**Rate limit:** sources disagree (25 / 50 / 100 per rolling 24h). Plan against **25/day** and you will never hit it — realistic volume is 1–2.

### 5.2 Timing

Don't use generic "best time to post" advice. Use `online_followers` from your own account insights, cross-referenced against when *your* posts have historically earned the most reach in their first 6 hours. The system maintains a per-weekday timing model from your own data and schedules into those windows.

### 5.3 Approval gate

**Phase 1: nothing publishes without you.** The queue posts a summary to you (Telegram bot or a simple web page on the VPS) with the video, the chosen caption, and the scheduled time. One tap to approve, one to send back.

**Phase 2, after ~6 weeks of you approving nearly everything unchanged:** flip trial reels to auto-publish (they're invisible to your followers, so the downside is near zero), keep human approval on graduations and main-feed posts.

Auto-publishing everything from day one is how accounts end up with an embarrassing post at 3am. Earn the trust incrementally.

---

## 6. Department: GROWTH LAB — the repost + Trial Reel engine

**This is what we build first.** Detailed spec: [`phase-1-repost-engine.md`](./phase-1-repost-engine.md).

### 6.1 Why this is the right first move

You already have a library of videos that performed. Your follower base has largely rotated or forgotten them, and — critically — **almost nobody who will see the repost saw the original**, because the original reached a few thousand people out of Instagram's billions. Old winners are your cheapest source of new content.

Trial Reels make this nearly risk-free: a trial reel goes **only to non-followers**, never appears on your grid, and never touches your followers' feeds. A failed test costs you nothing. Your existing audience never sees the experiment.

### 6.2 The elegant part

Measuring non-follower reach through the API is awkward — the follower/non-follower split is clearly visible in the app but its API exposure is inconsistent. **Trial Reels sidestep this entirely: 100% of a trial reel's reach is non-follower reach, by definition.** Every trial is a clean, uncontaminated measurement of "how well does this content acquire strangers" — which is exactly the number that matters for growth. The feature is, accidentally, a perfect experiment harness.

### 6.3 Selection algorithm

Score every eligible past video:

```
score =  0.4375 × normalized(sends ÷ reach)
       + 0.3125 × normalized(avg_watch_time ÷ duration)
       + 0.2500 × normalized(saves ÷ reach)
```

> **Corrected 2026-08-18 by the Phase 0 probe.** The original formula carried a
> fourth term, `0.20 × normalized(profile_visits ÷ reach)`. `profile_visits` is
> not available per-post for reels, so that term cannot be computed. The
> remaining three weights are the originals renormalised to sum to 1
> (`0.35/0.80`, `0.25/0.80`, `0.20/0.80`), which preserves the intended
> ordering — sends dominant, retention second, saves third.
>
> **This is a judgment call, not a measurement.** The alternative considered and
> rejected was filling the vacant 0.20 with `total_interactions ÷ reach`; that
> double-counts shares and saves, which are already weighted here, and drags the
> scorer toward likes — the weakest 2026 signal, deliberately excluded below.
> Revisit once ~40 trials give real evidence about which inputs predict
> non-follower reach for this account.

Eligibility filters:
- age ≥ 90 days (audience has rotated)
- not reposted in the last 120 days
- source file still available in the library
- not seasonal/dated content

Rank descending. Top of the queue goes to test.

### 6.4 Test protocol

Reposting the identical file is the common mistake — it tends to get suppressed distribution and it wastes the opportunity. Instead, each repost is a **variant test**:

- New first 3 seconds (a different hook from the Studio's candidates)
- New cover frame
- New caption, different angle from the original
- Optionally trimmed to a tighter length

Run **one trial reel per day**, changing **one variable at a time** where possible. Compare against a rolling baseline: the median reach of your last 20 trial reels.

### 6.5 Graduation

The API supports `trial_params` with `graduation_strategy` accepting `MANUAL` or `SS_PERFORMANCE` (Instagram auto-graduates on early performance).

**Use `MANUAL`.** Auto-graduation optimizes for Instagram's notion of performance, not yours. The Analyst reviews at the 72-hour mark and graduates on your criteria:

- Trial reach ≥ 1.5× your trial baseline **and** saves-per-reach ≥ account median → **graduate to followers**, add to the main grid
- Reach ≥ 1.5× baseline but saves-per-reach below median → **hook worked, content didn't** → keep the hook, retire the clip
- Reach < baseline → **archive the variant**, log why, move on

> **Corrected 2026-08-18 by the Phase 0 probe.** The second test was originally
> "weak profile conversion", using per-post `profile_visits`. That metric does
> not exist for reels on this account, so the original rule was uncomputable.
> `saved ÷ reach` replaces it as a **deliberately weaker proxy**: it measures
> whether the body of the reel delivered enough to be worth keeping, which is
> adjacent to — but not the same as — making someone curious about you.
> Full reasoning in [`phase-1-repost-engine.md`](./phase-1-repost-engine.md) §6.

Every result feeds back into Intelligence. After ~40 trials you have a genuine, data-backed model of what makes *your* audience stop scrolling — which is worth vastly more than any generic advice about the algorithm.

### 6.6 Volume

One trial/day = ~30 clean experiments a month, entirely invisible to your followers, on top of your normal posting. This is the single biggest reach lever available to you and it costs no new filming.

---

## 7. Department: AUDIENCE — funnel, email, Facebook

Instagram is rented land. The list is owned. Everything here exists to move people off-platform.

### 7.1 The funnel

```
Reel (non-follower)  →  profile  →  link in bio  →  landing page
                                                        │
                                          ┌─────────────┴─────────────┐
                                          ▼                           ▼
                                    email list                  booking page
                                  (lead magnet)              (lessons / gigs)
                                          │
                                          ▼
                                  nurture sequence
                                          │
                                          ▼
                                student · concert ticket · gig enquiry
```

### 7.2 Lead magnet

For a jazz/classical guitarist, the highest-converting offer is something they can *play tonight*: a PDF chord-melody arrangement, a short technique guide, or a single well-produced lesson video. Not a newsletter signup — nobody wants another newsletter. They want the arrangement.

### 7.3 Stack (all within budget)

- **Landing page:** static site on the VPS, or Carrd (~€19/yr)
- **Email:** [Listmonk](https://listmonk.app) self-hosted on the VPS — **€0**, unlimited subscribers, you own the data. Pair with a transactional sender's free tier for deliverability. (MailerLite's free tier to 1,000 subscribers is the zero-maintenance alternative.)
- **Booking:** Cal.com free tier

### 7.4 Sequence (5 emails, automated, written once)

1. **Deliver** the arrangement + how to practice it
2. **Story** — why third stream, what you're actually chasing musically
3. **Teach** — one genuinely useful idea, no ask
4. **Show** — a performance, and what you're working toward
5. **Offer** — lessons available, here's what working together looks like

Then a monthly broadcast. This is written once and runs forever.

### 7.5 The older-generation channel — Facebook

Your instinct is right. Concert audiences and adult students skew older, and that demographic is materially more reachable on Facebook and email than on Instagram.

- Crosspost Reels to a **Facebook Page** (Meta supports crossposting via API — one pipeline, two platforms, near-zero extra cost)
- Facebook rewards longer-form and link posts far more than Instagram does — full performance videos and concert announcements belong there, not on IG
- Facebook Events for concerts, which surfaces to local audiences
- Local guitar society, classical music, and jazz appreciation **Groups** — organic, high-intent, but genuine participation only. Do not automate this. Automated group posting reads as spam instantly and burns the channel permanently.

---

## 8. Monetization ladder

Ordered by realistic revenue per hour of your time, not by glamour:

| Tier | Channel | Realistic at your size | Effort |
|---|---|---|---|
| 1 | **1:1 online lessons** | Highest €/hour, immediate. A handful of students from a 5k audience is very achievable. | Low — you already teach |
| 2 | **Performance gigs** | An EPK page + a reel reel (pun intended) is what promoters ask for. IG is your proof of audience. | Low |
| 3 | **Digital products** — arrangements, technique courses | Scales without your time; build once the list exists | High upfront |
| 4 | **IG Subscriptions** (eligible at 1k+ in most regions) | Small but real; works best with a paid tier of practice-along content | Medium |
| 5 | **Reels bonuses / gifts / badges** | Region-dependent, often invite-only, small amounts at this scale | None — opt in and forget |
| 6 | **Brand deals** (strings, guitars, audio gear) | Guitar brands work with mid-size accounts readily; niche authority beats raw follower count here | Low, reactive |

Be clear-eyed: **in-app Instagram monetization at 1k–10k followers is pocket money.** Tiers 1 and 2 are the actual business. The account is the funnel — which is exactly how you framed it, and it's the right frame.

---

## 9. Architecture and cost

```
┌─────────────────────────────┐        ┌──────────────────────────┐
│  YOUR PC — Windows / 4070   │        │  VPS — Hetzner CX22 €4/mo│
│                             │        │                          │
│  • video library (originals)│  git   │  • scheduler (cron)       │
│  • faster-whisper           │◄──────►│  • SQLite/Postgres        │
│  • Qwen3 14B via Ollama     │ rclone │  • Graph API workers      │
│  • VLM frame analysis       │        │  • temp public video host │
│  • FFmpeg / librosa         │        │  • Listmonk (email)       │
│  • batch renders            │        │  • landing page           │
│                             │        │  • approval web UI        │
│  runs when you're at it     │        │  runs 24/7                │
└─────────────────────────────┘        └──────────┬───────────────┘
                                                   │
              ┌────────────────────────────────────┼──────────────┐
              ▼                                    ▼              ▼
     Instagram Graph API                  Facebook Page    Listmonk SMTP
     (publish + insights)                 (crosspost)      (nurture)

┌──────────────────────────────────────────────────────────────────┐
│  CLAUDE CODE ROUTINES on this repo — the strategist layer         │
│  Mon 08:00  weekly brief + repost queue                           │
│  Daily      72h trial-reel graduation decisions                   │
│  Quarterly  algorithm/landscape delta                             │
│  Cost: covered by your existing subscription — €0 marginal        │
└──────────────────────────────────────────────────────────────────┘
```

**Why hybrid, concretely:** the 4070 does the GPU work that would otherwise cost real money per minute (transcription, VLM, LLM inference) but can't be relied on to be awake at 7pm on a Tuesday. The VPS is always awake but weak. Split along exactly that line and you pay €4/month for reliability while getting free inference.

### Monthly budget

| Item | Cost |
|---|---|
| Hetzner CX22 VPS (2 vCPU / 4GB / 40GB) | €3.79 |
| Domain | ~€1.00 |
| Local AI (Whisper, Qwen3, VLM, FFmpeg) | €0 |
| Claude strategy layer (existing subscription) | €0 |
| Listmonk email (self-hosted) | €0 |
| Cal.com booking (free tier) | €0 |
| **Total** | **≈ €5 / month** |

That leaves roughly €15/month of headroom against your €20 ceiling — hold it in reserve for a transactional email sender once the list passes a few hundred, or occasional frontier-model API calls if local caption quality disappoints.

---

## 10. Data model

```
library/
  {video_id}/
    original.mp4              ← never delete; this is the actual asset
    metadata.json             ← piece, key, technique, tempo, date filmed
    transcript.json           ← Whisper word-level
    hooks.json                ← candidate cold-opens with timecodes + scores
    covers/                   ← candidate cover frames
    renders/
      v1_original.mp4
      v2_trial_hook-a.mp4     ← each repost variant is a distinct render
data/
  posts.db                    ← every published media, all insight snapshots
  trials.db                   ← trial reels: variant, hypothesis, result, verdict
  baselines.json              ← rolling medians, the comparison target
reports/
  2026-W34-brief.md           ← weekly, written by the Analyst
  algorithm-deltas.md         ← quarterly
```

The thing that makes this compound rather than just run: **every trial reel logs a hypothesis and a verdict.** After a year you don't have 300 posts, you have 300 recorded experiments about what makes people stop scrolling for guitar content. That dataset doesn't exist anywhere else and nobody can copy it.

---

## 11. Build roadmap

| Phase | What ships | Your time |
|---|---|---|
| **0 — Foundations** (week 1) | Meta app + Professional account link, long-lived token with refresh, capability probe (confirm Trial Reels + insights fields actually work on your account), VPS provisioned, insights backfill of all historical posts | ~2h, mostly clicking through Meta setup |
| **1 — Growth Lab** (weeks 2–3) | Repost scorer, trial reel publisher, 72h graduation reviewer, first 10 trials running | ~1h |
| **2 — Copy + Publishing** (weeks 4–5) | Caption generator with your voice profile, timing model, approval UI, scheduled posting | ~2h (voice profile needs your input) |
| **3 — Studio** (weeks 6–7) | Ingest watcher, Whisper, hook detector, auto-subtitles, cover selection | ~1h |
| **4 — Audience** (week 8) | Landing page, lead magnet, Listmonk, 5-email sequence, Facebook crosspost | ~3h (writing the sequence, making the arrangement PDF) |
| **5 — Expansion** (ongoing) | YouTube Shorts + TikTok from the same renders, EPK page, quarterly research loop | — |

Phases 1 and 2 deliver most of the value. Everything after is compounding.

---

## 12. Your steady-state week

- **Film** whenever you feel like it — no schedule, no quota. The library and the repost engine absorb the irregularity, which is exactly why the repost engine is built first.
- **~5 min per video** — pick a take, pick a hook, glance at the caption
- **~10 min on Monday** — read the brief, sanity-check the repost queue
- **~2 min a day** — approve or reject the day's trial

Call it **30 minutes a week** in steady state. Everything else is practice.

---

## 13. Guardrails

These are non-negotiable, because violating them can cost the account permanently:

- **Official Meta APIs only.** No scrapers, no unofficial libraries, no automation tools that log in as you. This is the fastest route to a ban and it is not recoverable.
- **No bought followers, no engagement pods, no follow/unfollow.** They corrupt the recommendation signal, which is the thing actually doing the work for you.
- **No automated DM outreach.** The Messaging API exists, but automated cold DMs are both a ban risk and bad for the brand. Auto-reply to *inbound* is fine and useful.
- **Human approval on anything public** until the system has earned trust over several weeks.
- **Originals are sacred.** Back up `library/` off the PC. The video files are the actual capital here — everything else is reproducible.
- **Token hygiene.** Long-lived tokens expire in 60 days; the refresh job is a single point of failure. Alert on failure, don't discover it three weeks later.

---

## 14. Verified against the live account — 2026-08-18

These were written as open questions because `developers.facebook.com` and `instagram.com` were both blocked by the network proxy this plan was drafted in. Phase 0's probe has now answered what it can. Full evidence: [`reports/phase-0-findings.md`](../reports/phase-0-findings.md), raw data in [`data/capabilities.json`](../data/capabilities.json).

1. **`trial_params` / `graduation_strategy`** — **CONFIRMED SUPPORTED.** Graph accepted `trial_params={"graduation_strategy":"MANUAL"}` on a `REELS` container and returned a container id. **Phase 1 builds the API path.** Caveat: acceptance is not proof the parameter is *honoured* — Graph sometimes ignores unknown parameters silently. The first real trial reel must be checked in-app to confirm it is flagged as a trial and absent from the grid. Keep §7's assisted-manual fallback documented but unbuilt until that check passes.

2. **Publishing rate limit** — **STILL OPEN.** The probe does not exercise a publishing quota and nothing in `capabilities.json` bears on it. The 25 / 50 / 100 figures remain uncorroborated. Harmless at one trial per day; settle it by reading `X-App-Usage` headers during real publishing before any bulk operation.

3. **Follower / non-follower reach breakdown** — **STILL OPEN, leaning no.** No standalone metric returns the split. But the probe tests metric *names* only and never sends a `breakdown` parameter, so it cannot rule out `breakdown=follow_type` on `reach`. Untested either way. Does not gate anything — §6.2's argument holds regardless.

4. **Regional monetization eligibility** — **UNPROBED.** No API surface was touched. Check the Instagram app under Professional dashboard → Monetization. Gates nothing; §8 already ranks in-app monetization behind lessons and gigs.

**What the probe found that this plan did not think to ask:**

5. **`profile_visits` and `follows` do not exist per-post for reels.** This invalidated the four-ratio framework in §1, the nightly metric list in §2.1, the scorer in §6.3, and the graduation rule in §6.5 — all now amended above. This was the single most consequential Phase 0 finding and no amount of secondary-source reading would have surfaced it.

6. **The account is on Instagram Login, not Facebook Login** — everything answers on `graph.instagram.com`, not `graph.facebook.com`. `docs/phase-0-setup.md` claimed the probe script handled either route; it did not, and the resulting error is indistinguishable from a corrupt token. Fixed in `scripts/probe.py`.

7. **Historical posts can never have an early-velocity curve** — a snapshot claims only the newest threshold a post has already passed, so anything older than 30 days at first capture gets a `30d` row and nothing earlier, permanently. The complete curve begins with posts published from 2026-08-18 onward.

8. **Insights do not exist before April 2020** — 191 of 494 media predate the account's conversion to Professional and return nothing. No reel is affected.

9. **The reel library is 141 posts, not 552** — of which 124 are ≥90 days old and carry every surviving scorer input. That, not the raw media count, is the repost engine's candidate pool.

10. **`duration_s` is not available from the API at all** — no Instagram media field exposes video duration, so the retention term (31% of the scorer) cannot be computed without reading the source files locally with `ffprobe`. See `reports/phase-0-findings.md`.
