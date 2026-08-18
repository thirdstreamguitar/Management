# Phase 0 — Setup and handoff

Phase 0 produces two things: a working long-lived access token, and
`data/capabilities.json` — the file that replaces every assumption in the
operating plan with a fact from your live account.

Two parts. **You do Part A once (~15 minutes). An agent does Part B and
everything after it, forever.**

---

## Why the split

The obvious move is to hand a browser agent your Meta Business login and let it
click through. Three reasons not to:

1. **Your login lives in your browser, not in an agent's container.** A cloud
   agent session starts with no cookies of yours. It would have to log in as
   you, from scratch.
2. **Meta flags datacenter logins.** Signing into Meta Business from a cloud IP
   is one of the most reliable ways to trigger a security checkpoint. On the
   account your entire funnel runs through, that is a bad trade for 15 minutes.
3. **Part A is mostly agreeing to legal terms** — Meta Platform Terms and
   Developer Policies. You should actually agree to those, not have something
   click through them on your behalf.

Part A is also the *only* manual step in the whole system. Everything downstream
— tokens, refresh, probing, backfill, scoring, publishing, review — is Part B.

> If you still want browser automation, the safe place for it is Claude Code
> running **locally on your Windows box**, driving your own Chrome profile over
> `--remote-debugging-port`. Same IP, same cookies, no credentials handed to
> anything. Not needed for any of this, but that's the shape that doesn't risk
> the account.

---

## Part A — what you click (~15 min)

Meta reorganizes this console regularly, so these are named by *what you're
looking for* rather than by exact button position.

### 1. Instagram account → Professional
In the Instagram app: **Settings → Account type and tools → Switch to
professional account**. Choose **Creator**.
*Required for: Insights API, Content Publishing, Trial Reels. All three are
dead without it.*

### 2. Link a Facebook Page
Same menu, connect (or create) a Facebook Page.
*Not needed for Phase 1. Needed for the Facebook crossposting in the plan's
Audience department, and it makes the never-expiring token route available
later — so do it now while you're in here.*

### 3. Create a Meta app
[developers.facebook.com/apps](https://developers.facebook.com/apps) →
**Create App** → use case **Other** → type **Business**.
Name it anything; it is never user-facing.

### 4. Add the Instagram product
In the app: **Add product → Instagram → API setup with Instagram login**.

Take the **Instagram login** route, not Facebook Login for Business. It's
substantially fewer steps and it's what Meta is steering new apps toward. The
probe script handles either, so this isn't a lock-in.

> **Corrected 2026-08-18.** "The probe script handles either" was false when
> written, and it cost a full setup session. `probe.py` sent every request to
> `graph.facebook.com`, which **cannot parse an Instagram-Login token**. The
> failure is:
>
> ```
> Invalid OAuth access token - Cannot parse access token   (code 190, no subcode)
> ```
>
> — wording that is indistinguishable from a truncated or corrupt token, so the
> obvious response is to regenerate the token, which does not help.
>
> The routes do not share a host:
>
> | Route | Token prefix | Host |
> |---|---|---|
> | Instagram API with Instagram Login | `IGAA` | `graph.instagram.com` |
> | Instagram API with Facebook Login | `EAA` | `graph.facebook.com` |
>
> `probe.py` now picks the host from the token prefix and falls back to trying
> both, and records the winner in `capabilities.json` so every later script
> follows it. If you ever see "Cannot parse access token" again, run
> `python scripts/diagnose.py` — it separates a malformed token from a
> wrong-host token in one call.

### 5. Generate the token
In that same panel: add your Instagram account, then **Generate token**.

Grant these scopes — the probe will tell you if one is missing, but getting them
right now saves a round trip:

| Scope | Needed for |
|---|---|
| `instagram_business_basic` | reading your media list |
| `instagram_business_manage_insights` | every metric the scorer runs on |
| `instagram_business_content_publish` | publishing reels and trial reels |
| `instagram_business_manage_comments` | later — auto-reply to inbound |

### 6. Put the token in `.env`

```bash
cp .env.example .env
# paste the token after IG_ACCESS_TOKEN=
```

**Do not paste the token into a chat window or a prompt.** It is equivalent to
account access and chat transcripts persist. `.env` is gitignored; agents read
it from there. That's the whole reason the file exists.

**Token lifetime is 60 days.** The probe reports days remaining. Automating the
refresh is the first thing Part B does — an expired token silently kills the
whole system, and you'd find out weeks later.

---

## Part B — paste this into a Claude Code or Cowork tab

Run it **on your Windows PC or your VPS**, not in a sandboxed web session —
`graph.facebook.com` is blocked by egress policy in most hosted environments
(it is blocked in the one this plan was written in). The scripts detect this and
say so explicitly rather than blaming your token.

```
Work in the thirdstreamguitar/Management repo, branch
claude/instagram-ai-management-workflow-9vl8sv.

Read docs/operating-plan.md and docs/phase-1-repost-engine.md first — they
explain what we're building and why the metric choices are what they are.

I've completed Part A of docs/phase-0-setup.md: a Meta app exists and a
long-lived token is in .env as IG_ACCESS_TOKEN. Never print that token, never
commit it, never paste it into a message.

Do this:

1. Load .env, run `python scripts/probe.py`, and show me the verdict block.
2. If the probe reports a network failure, stop and tell me — that means this
   machine can't reach graph.facebook.com and nothing else will work.
3. If any required scope is missing, tell me exactly which one and which Meta
   console screen grants it. Don't work around it.
4. Run `python scripts/backfill.py --full`. Expect one snapshot row per
   (post, age bucket).
5. Write reports/phase-0-findings.md answering the four open questions from
   section 14 of the operating plan, each with the evidence from
   data/capabilities.json that settles it. Where the probe came back
   INCONCLUSIVE, say so — do not guess.
6. Amend docs/operating-plan.md and docs/phase-1-repost-engine.md wherever the
   real capabilities contradict what those documents assume. The plan was
   written from secondary sources because Meta's docs were unreachable; your
   probe results are primary evidence and win.
7. Commit and push (data/capabilities.json yes, .env and *.db no — .gitignore
   already handles this).

Then tell me, in a short summary:
- whether trial_params works on my account, and therefore whether Phase 1 is
  the API path or the assisted-manual fallback
- which of the four scorer inputs (shares, saved, profile_visits,
  ig_reels_avg_watch_time, reach) are actually available
- how many posts and snapshots landed in the database
- how many days until my token expires

Don't start building Phase 1 yet. Phase 0 is just about replacing assumptions
with facts.
```

---

## Part C — what you get back

`data/capabilities.json`, committed, containing:

- the Graph API version this account answers on (the probe walks v26 → v21 until one responds)
- your resolved IG user id, account type, follower count, and which login route the token uses
- token scopes and exact expiry
- **every media metric probed one at a time** — so you get the real supported list, not a batch request that fails as a unit because of one bad name
- the `trial_params` verdict

### How the trial_params check stays safe

It sends a deliberately unreachable `video_url`. Two outcomes, and they're
distinguishable, which is the entire point:

- Graph rejects `trial_params` by name → **not supported**, build the fallback
- Graph accepts the params and fails fetching the video → **supported**

Either way no container is created and nothing is published.

---

## Then what

With `capabilities.json` in the repo, Phase 1 is unblocked and every later
script reads facts from it instead of carrying a hardcoded guess that rots the
next time Meta ships a version.

Ask for **Phase 1: the scorer** next — `docs/phase-1-repost-engine.md` §3 is
already specified down to the weights.
