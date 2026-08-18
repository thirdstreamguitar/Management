# Phase 0 findings — capability probe against the live account

**Probed:** 2026-08-18T09:28:49Z · `@fupingryuguitar` · 1,676 followers · `media_count` 552 (the `/media` edge returns 494 — see the discrepancy note at the end)
**Route:** Instagram API with Instagram Login → `graph.instagram.com` **v26.0**
**Evidence:** [`data/capabilities.json`](../data/capabilities.json)

Every claim below cites the probe. Where the probe did not settle a question,
it says so rather than guessing — several of the operating plan's open
questions are **still open** after Phase 0, and pretending otherwise would
defeat the point of running it.

---

## Headline

| | |
|---|---|
| **Phase 1 path** | **API path.** `trial_params` was accepted. Not the assisted-manual fallback. |
| **Scorer** | **Broken as specified**, three ways: `profile_visits` does not exist per-media; `duration_s` is not an API field (solved — see below); and **`reach` is corrupt for 36 of 141 reels**, which would have handed the repost queue to the wrong videos. |
| **Gates** | Both pass — 1,676 followers (≥1,000), account type `MEDIA_CREATOR`. |
| **Token** | **59.9 days — expires 2026-10-17.** Measured, not inferred. |
| **Targets** | §1's performance targets are unachievable at this account's video lengths. 1 reel in 139 has ever hit the 0.75 retention target. |

---

## The four questions from operating-plan.md §14

### Q1 — Does the Content Publishing API accept `trial_params` / `graduation_strategy`?

**ANSWERED: yes, with a caveat worth keeping.**

```json
"trial_params": {
  "supported": true,
  "confidence": "high",
  "note": "Container was created unexpectedly...",
  "container_id": "18619475482009797"
}
```

The probe posted `media_type=REELS` with `trial_params={"graduation_strategy":"MANUAL"}`
and a deliberately unreachable `video_url`. Graph did not reject `trial_params`
by name — it accepted the request and returned a container id. The container
references a video that cannot be fetched, so it will error and expire on its
own within 24h. **Nothing was published. Do not publish container
`18619475482009797`.**

**The caveat:** parameter *acceptance* is not proof the parameter is *honoured*.
Graph sometimes ignores unrecognised parameters rather than rejecting them, and
the container's trial status is not readable back. The evidence is strong —
this is the strongest signal obtainable without publishing — but the definitive
confirmation is the first real trial reel: publish one, then check in the app
that it is marked as a trial and is not on the grid. Treat that check as a
blocking step in Phase 1, not a formality.

The §7 assisted-manual fallback in `phase-1-repost-engine.md` should be kept in
the document, unbuilt, until that confirmation lands.

### Q2 — Publishing rate limit (25 / 50 / 100 per rolling 24h)?

**INCONCLUSIVE. The probe does not test this and nothing in
`capabilities.json` speaks to it.**

No request in the probe exercises a publishing quota, and Graph does not
advertise the limit on any endpoint the probe calls. The three figures in the
operating plan remain uncorroborated secondary-source numbers.

This is harmless at the planned volume of one trial per day, which is what the
plan already says. It becomes load-bearing only before a bulk operation. The
honest way to settle it is to read `X-App-Usage` / `X-Business-Use-Case-Usage`
response headers during real publishing in Phase 1 — the probe does not capture
headers today.

### Q3 — Do media insights expose a follower / non-follower reach breakdown?

**INCONCLUSIVE, leaning no — and the probe's limits here matter.**

No metric in the supported set carries a follower/non-follower split:

```
supported: reach, views, likes, comments, shares, saved,
           total_interactions, ig_reels_avg_watch_time,
           ig_reels_video_view_total_time
```

But the probe tests *metric names only*. It never sends a `breakdown`
parameter, which is the mechanism Meta uses for dimensional splits
(e.g. `breakdown=follow_type`). So the probe establishes that no *standalone
metric* returns the split; it does **not** establish that `reach` cannot be
broken down by follower type. That distinction was not tested and should not
be asserted either way.

Operationally this changes nothing, and the plan already anticipated it:
§6.2's argument stands — 100% of a trial reel's reach is non-follower reach by
definition, so trial reels measure stranger-acquisition cleanly regardless of
how the breakdown question resolves. Worth one probe extension later; not worth
blocking on.

### Q4 — Regional monetization eligibility (Subscriptions, Reels bonuses)?

**INCONCLUSIVE. Entirely unprobed.**

Nothing in the probe touches monetization surfaces, and `capabilities.json`
contains no evidence bearing on this. The operating plan's §8 ranking already
treats in-app monetization as tier 4–5 pocket money behind lessons and gigs, so
this does not gate anything. It is answered by looking in the Instagram app
under Professional dashboard → Monetization, not by the API.

---

## The finding the plan did not anticipate

### `profile_visits` and `follows` are unavailable on media insights for reels

```json
"unsupported": {
  "profile_visits": "The Media Insights API does not support the
                     profile_visits metric for this media product type.",
  "follows":        "The Media Insights API does not support the
                     follows metric for this media product type."
}
```

Both names are *recognised* by the API — they appear in the enumerated valid-metric
list Graph returned when rejecting `plays` — but neither is supported **for this
media product type**, and the probe's test media was a reel. Since the whole
repost engine operates on reels, that is the answer that matters.

**Scope limit, stated plainly:** the probe tested one media item, the newest
reel. It did not test a `FEED` image or carousel. If those expose
`profile_visits`, this finding narrows to reels only. That was not tested.

**What this breaks, concretely:**

| Document | What assumed `profile_visits` per-post | Status |
|---|---|---|
| `operating-plan.md` §1 | "Profile conversion = `profile_visits ÷ reach`" | dead per-post |
| `operating-plan.md` §1 | "Follow efficiency = `follows ÷ profile_visits`" | dead per-post |
| `operating-plan.md` §2.1 | nightly pull lists both metrics | wrong, will error |
| `operating-plan.md` §6.3 | `+ 0.20 × normalized(profile_visits ÷ reach)` | uncomputable |
| `phase-1-repost-engine.md` §3 | `+ 0.20 × norm(profile_visits / reach)` | uncomputable |
| `phase-1-repost-engine.md` §6 | graduation gate on `profile_visits/reach` | uncomputable |

**What survives:** `profile_views` *is* available at the **account** level
(daily, `metric_type=total_value`). So profile conversion remains measurable
for the account as a whole, day by day. It is **not** attributable to an
individual post, which is precisely what the scorer and the 72h graduation
rule need. These are not substitutes and the amended documents should not
pretend otherwise.

---

## Amendments made to the plan documents

Per the instruction that probe results are primary evidence and outrank the
secondary sources the plan was written from:

1. **Scorer reweighted** in both documents. Dropping `profile_visits` and
   renormalising the remaining three preserves the author's relative intent
   (sends dominant, retention second, saves third):

   ```
   score =  0.4375 × norm(shares / reach)
          + 0.3125 × norm(avg_watch_s / duration_s)
          + 0.2500 × norm(saved / reach)
   ```

   This is a judgment call, flagged as such in the documents. The alternative —
   substituting `total_interactions / reach` into the vacated 0.20 slot — was
   rejected because it double-counts shares and saves, which are already
   weighted, and would quietly bias the scorer toward likes.

2. **Graduation criteria rewritten** in `phase-1-repost-engine.md` §6. The
   `GRADUATE` vs `HOOK_WON` split as specified cannot be computed per-trial.
   The amended version keeps the reach test, replaces the per-post profile
   test with `saved/reach` as an explicitly-labelled weaker proxy for "the
   body delivered", and records account-level `profile_views` alongside each
   trial as context rather than as a decision input.

3. **Host and route corrected throughout.** The documents assume
   `graph.facebook.com`. This account is on Instagram Login and answers on
   `graph.instagram.com` v26.0. `phase-0-setup.md`'s claim that "the probe
   script handles either" was false and cost a full setup session — an `IGAA`
   token sent to the Facebook host returns `Invalid OAuth access token -
   Cannot parse access token`, which is indistinguishable from a corrupt token.

4. **Dead metrics removed** from the §2.1 nightly pull list: `plays`,
   `impressions`, and `video_views` are not valid on v26.0. `views` replaces
   them.

5. **Request-shape note added.** Several account metrics only answer to
   `metric_type=total_value` (`views`, `profile_views`, `website_clicks`,
   `accounts_engaged`, `total_interactions`). Asking without it returns an
   error identical to "metric unsupported" — a trap that would have made a
   naive probe under-report capability. `capabilities.json` records the working
   shape per metric and `backfill.py` reuses it.

---

## Token lifetime — the one deliverable Phase 0 cannot produce

**Not measurable without changing state.**

`graph.instagram.com` has no `debug_token` endpoint; that is Facebook-host only.
For Instagram Login the only way to read expiry is:

```
GET /refresh_access_token?grant_type=ig_refresh_token&access_token=...
```

which **issues a new token** and is therefore a mutation. `probe.py` promises to
modify nothing, so it does not call it and reports the gap instead.

**MEASURED 2026-08-18 via `scripts/refresh_token.py`:**

```
expires_in     5178316 seconds
days remaining 59.9
expires on     2026-10-17
```

The token was refreshed and verified as `@fupingryuguitar` before being written,
so this is a reading from the API rather than an inference from the issue date.
**Re-run before 2026-10-17.**

To convert that into a fact, run the refresh call deliberately and record the
returned `expires_in`, then write the new token to `.env`. That call is also the
first half of the refresh automation the plan already flags as a single point of
failure (§13, "Token hygiene").

**`scripts/refresh_token.py` does this**, built to be safe about it since it
mutates account credentials:

1. refuses to run without `--yes`
2. backs up `.env` first (`.env.*` is gitignored, so backups cannot be committed)
3. **verifies the new token with a live call before writing it anywhere**
4. rewrites only the `IG_ACCESS_TOKEN` line, preserving comments and other keys
5. never prints a token

If any step fails, `.env` is untouched and the existing token stays valid. All
four paths — no-flag, API failure, verification failure, success — are exercised
and behave correctly.

Running it answers Q4 exactly rather than by inference, and re-running it before
each expiry is the whole of the refresh job until it gets scheduled.

---

## Backfill — ran 2026-08-18

```
494 media, 303 snapshots
by bucket: 6h=1, 24h=1, 72h=2, 7d=11, 30d=288
```

### A prediction I got wrong

Before the run I wrote that "all 552 posts are past 30 days old, so only their
`30d` row can ever exist," and amended both plan documents to say so. **That was
an assumption stated as fact, and it is false** — 15 posts are younger than 30
days, which is why four younger buckets have rows. The account is actively
posting; the most recent media is from 2026-08-17. Those documents have been
corrected. Flagging it here rather than quietly fixing it, because asserting an
unverified number is exactly the failure mode Phase 0 exists to catch, and I
reproduced it.

The *underlying* point survives, restated correctly: `age_bucket()` claims only
the **newest** threshold a post has already passed, so a post that is 200 days
old at first capture gets a `30d` row and can never retroactively acquire a
`6h` one. A complete five-point curve therefore exists only for posts published
from 2026-08-18 onward, as the nightly job catches each threshold in turn.

### Why 303 snapshots and not 494

191 media returned no insights at all, and the boundary is clean:

| | Oldest | Newest |
|---|---|---|
| Media **with** insights | 2020-04-30 | 2026-08-17 |
| Media **without** insights | 2014-03-21 | 2020-03-14 |

A hard cutoff between March and April 2020, almost certainly the date the
account converted to Professional — Instagram does not backfill insights for
media posted before conversion. Those 191 posts (169 feed images, 21 feed
videos, 1 carousel) are permanently metric-less. **No reel is affected.**

### The library, by product type

| Product type | Media type | Count |
|---|---|---|
| FEED | IMAGE | 227 |
| **REELS** | **VIDEO** | **141** |
| FEED | VIDEO | 81 |
| FEED | CAROUSEL_ALBUM | 45 |

**The repost engine's real candidate pool is 141, not 552.** Of those:

- 141/141 have complete insights
- **124** are ≥ 90 days old and therefore pass the §3 age filter
- 124/124 carry all four surviving scorer inputs (`shares`, `saved`, `reach`,
  `ig_reels_avg_watch_time`) with no nulls

124 candidates against a planned one-trial-per-day cadence is roughly four
months of testing before the pool needs the 120-day repost cooloff to recycle.
Comfortable.

---

## A second scorer input is missing: `duration_s`

**`duration_s` is NULL for all 494 media.** Nothing populates it, because the
Instagram media node does not expose a video duration field — `backfill.py`
cannot request what the API does not offer.

This breaks the retention term:

```
0.3125 × norm(avg_watch_s / duration_s)      <- denominator does not exist
```

That is **31% of the scorer weight**, on top of the 20% already lost with
`profile_visits`. Between them, half the originally-specified formula cannot be
computed from API data alone.

**SOLVED — and my first recommendation here was wrong.**

I originally wrote that this was blocked on building a `library/` ↔ `media_id`
mapping and reading durations off the local source files with `ffprobe`. That
was unnecessary. The API already returns **`media_url`** — a direct link to the
video file Instagram is serving — and `backfill.py` was requesting that field
and discarding it. An MP4 states its own duration in the `mvhd` box, so the
duration can be read straight from the file over HTTP range requests, typically
32–96 KB per video rather than a download.

`scripts/durations.py` does this: pulls `media_url` per media, reads the MP4
header, writes `duration_s` into `posts.db`. No local library, no filename
matching, no `ffprobe` dependency (pure stdlib parse, with `ffprobe` used only
as a fallback if it happens to be installed).

**The retention term is therefore recoverable now, and the scorer keeps all
three of its surviving inputs.** No second reweighting is needed.

The `library/` mapping is still required eventually — §3's
`source_file_exists` eligibility filter needs it, and the Studio department
needs it to cut variants — but it is no longer on the critical path for
scoring.

### Unit trap in the schema

`ig_reels_avg_watch_time` comes back in **milliseconds** (sample value `14536`
= 14.5s). The `phase-1-repost-engine.md` schema names the column `avg_watch_s`
and the scorer divides it by a duration in seconds. Left alone this produces a
retention ratio inflated by 1000×. The column is now documented as milliseconds.

Related, and worth not assuming: `ig_reels_video_view_total_time` does **not**
divide cleanly by either `views` or `reach` to reproduce
`ig_reels_avg_watch_time` (4317226 / 480 ≈ 8994ms, / 238 ≈ 18139ms, against a
reported 14536ms). The two are computed over different denominators. Do not
derive one from the other.

---

## CRITICAL: `reach` is corrupt for reels older than ~early 2024

Running the durations job made the scorer computable for the first time, and
computing it surfaced a data problem that would have shipped silently.

**36 of the 141 reels report more likes than reach**, which is physically
impossible — reach counts unique accounts, likes are a subset of them. Median
`reach` by year:

| Year | n | median reach | median views | median likes | likes > reach |
|---|---|---|---|---|---|
| 2022 | 23 | **11** | 1,843 | 53 | 22/23 |
| 2023 | 12 | **18** | 600 | 37 | 12/12 |
| 2024 | 16 | 192 | 706 | 35 | 2/16 |
| 2025 | 27 | 463 | 750 | 33 | 0/27 |
| 2026 | 63 | 466 | 696 | 29 | 0/63 |

A 2022 reel reporting `reach=14`, `views=1629`, `likes=46` is not a reel that
reached 14 people. The `reach` field is returning something else for older
media — a recent-window figure, or a degraded value — and it is wrong by roughly
two orders of magnitude.

### Why this would have wrecked the repost queue

Two of the scorer's three terms divide by reach. On the corrupt rows the
denominator is ~100× too small, so the ratios explode:

| | n | mean `saved/reach` | max |
|---|---|---|---|
| Corrupt rows (likes > reach) | 36 | **24.50%** | 130.00% |
| Sane rows | 88 | 0.34% | 5.03% |

**71× the mean, and a maximum of 130% — a reel "saved by more people than saw
it".** The scorer min-max normalises across the eligible cohort, so the maximum
sets the scale. These 36 rows would have taken the top of the repost queue *and*
compressed all 88 legitimate candidates toward zero on that term. The queue would
have looked plausible and been almost entirely wrong.

Worth being clear: nothing about the probe would have caught this. The metric
is *supported*, it returns a number, and the number is garbage.

### The fix: use `views` as the denominator

`views` is sane across the entire library — **zero** of 141 reels report more
likes than views. Recomputing the same reels with views as the denominator:

| | mean `saved/views` | max |
|---|---|---|
| Rows that were corrupt-by-reach | 0.19% | 0.77% |
| Sane rows | 0.12% | 0.50% |

The anomaly disappears completely. It was the field, not the reels.

**Recommended amendment (a decision, flagged as such):** switch the scorer's
denominators from `reach` to `views`, and add a data-quality gate that drops any
row failing `likes ≤ reach ≤ views`. Both, not either — views fixes the known
corruption, the gate catches whatever else Meta's historical data is hiding.

The semantic cost is real and should be stated: *sends per view* is not *sends
per person reached*, because views counts replays. For **ranking** — which is all
the scorer does — the distinction barely matters, and it arguably suits reels
better since replays are themselves a positive signal. For the §1 headline
ratios, which are meant to be read as human-legible rates, it does matter, and
they should be labelled per-view rather than quietly redefined.

Pool impact: requiring trustworthy reach would cut the eligible set from 124 to
**87**. Using views keeps **139**.

---

## The plan's performance targets are not achievable at this account's video lengths

With durations available, the four §1 targets can be checked against reality for
the first time. n = 139 reels:

| Metric | p25 | median | p75 | p90 | Plan target | Reels clearing it |
|---|---|---|---|---|---|---|
| Sends per reach | 0.00% | 0.00% | 0.17% | 0.43% | > 1.0% | **5/139** |
| Saves per reach | 0.00% | 0.22% | 0.81% | 17.33%¹ | > 0.8% | 36/139 |
| Retention ratio | 0.13 | 0.17 | 0.31 | 0.44 | > 0.75 | **1/139** |

¹ inflated by the corrupt-reach rows above.

**The 0.75 retention target is unreachable — one reel in 139 has ever hit it.**
That target was taken from general advice about short-form video; it does not
describe this library.

### Why, and it is actionable

Median reel duration is **48.4s**. Median watch time is **7.7s**. And watch time
is remarkably flat regardless of length:

| Duration bucket | n | median retention | median watch | median reach |
|---|---|---|---|---|
| 0–15s | 13 | **0.48** | 5.7s | 423 |
| 15–30s | 19 | 0.34 | 7.0s | 431 |
| 30–60s | 58 | 0.19 | 7.8s | 391 |
| 60–120s | 45 | 0.11 | 8.6s | 338 |
| 120s+ | 4 | 0.08 | 11.9s | 162 |

Viewers give roughly **6–12 seconds no matter how long the reel is.** A 120-second
reel does not earn proportionally more attention; it just divides the same ~8
seconds by a larger number. `duration` vs `retention ratio` correlates at
**−0.66** — the retention term is substantially a proxy for *shortness*.

That has a direct consequence for the scorer: giving retention 0.3125 weight
gives "is this reel short" 0.3125 weight. Defensible — shorter probably *is*
better here — but it should be a deliberate choice, not an accident, and the
§4 **Length** variant axis is the cheapest experiment in the whole plan. The
`0–15s` bucket shows the highest median retention *and* the highest median
reach.

### A caution against overreading this

Correlations with historical reach are weak across the board (retention→reach
`+0.15`, sends-per-reach→reach `+0.07`, absolute watch time→reach `−0.09`). It
would be easy to conclude the scorer's inputs do not predict anything. **Do not
conclude that yet**, for three reasons:

1. Historical reach is mostly *follower*-driven and confounded by however much
   distribution Instagram gave a post that week — the plan says exactly this in
   §3, which is why raw reach was excluded from the formula in the first place.
2. The scorer is not trying to predict historical reach. It predicts which old
   video will acquire *strangers* as a trial reel. Trials are the clean
   measurement (§6.2); this data is not.
3. A quarter of the reach values are corrupt, which poisons every correlation
   that touches reach.

The honest position: these numbers are not evidence the scorer is wrong, and not
evidence it is right. They are the **baseline to validate against after ~40
trials**, which the plan already schedules. Recorded here so that comparison is
possible.

---

## Remaining discrepancy, unresolved

The probe reported `media_count: 552`; the `/media` edge paginated to **494**.
58 media are unaccounted for. Not investigated. Candidates include story media,
media excluded from the edge by type, or a `media_count` that counts something
the edge does not return. It does not affect the reel pool — 141 reels were
walked and all have insights — but the number should not be quietly reconciled
by assuming one of the two is authoritative.
