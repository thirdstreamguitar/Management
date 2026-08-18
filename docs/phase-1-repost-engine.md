# Phase 1 — Repost + Trial Reel Engine

Buildable spec for the first thing that ships. Assumes Phase 0 (Meta app, token, capability probe, insights backfill) is done.

> **Amended 2026-08-18 against live probe results.** Phase 0 ran and three
> assumptions in this document turned out to be wrong. Changes are marked inline
> with the same callout style as this one. Evidence:
> [`reports/phase-0-findings.md`](../reports/phase-0-findings.md).
>
> - **Host:** every call goes to `graph.instagram.com` v26.0 (Instagram Login
>   route), not `graph.facebook.com`.
> - **`trial_params` works** → build the API path, not the §7 fallback.
> - **`profile_visits` does not exist per-post for reels** → the scorer (§3) and
>   the graduation rule (§6) both had to change.

**Goal:** every day, without your involvement, take one proven old video, re-cut its hook, publish it as a Trial Reel to non-followers only, measure it against baseline at 72 hours, and graduate the winners to your feed.

---

## 1. Capability probe (run this first)

Before any pipeline code, one script answers what your account can actually do. It writes `data/capabilities.json` and the plan gets corrected by reality.

```
probe:
  1. GET /me?fields=id,username,account_type          → confirm BUSINESS or CREATOR
  2. GET /{ig-user-id}?fields=followers_count          → confirm ≥ 1000
  3. GET /{ig-user-id}/media?limit=1                   → confirm read scope
  4. GET /{ig-media-id}/insights?metric=reach,shares,saved,
         profile_visits,follows,ig_reels_avg_watch_time
                                                       → record which metrics ERROR
                                                          (this is the real answer to
                                                           "what can we optimize on")
  5. POST /{ig-user-id}/media  (dry run, do NOT publish)
         media_type=REELS, video_url=<test>,
         trial_params={"graduation_strategy":"MANUAL"}
                                                       → does the container accept
                                                          trial_params at all?
```

**Step 5 is the load-bearing one.** Create the container, inspect the response, then abandon it without calling `media_publish` — containers expire on their own in 24h. If it rejects `trial_params`, switch to the assisted-manual fallback in §7 and everything else in this spec stands unchanged.

> **Ran 2026-08-18. Results:**
>
> | Step | Result |
> |---|---|
> | 1 | `MEDIA_CREATOR` on `graph.instagram.com` v26.0 — Instagram Login route |
> | 2 | 1,676 followers — gate passed |
> | 3 | `media_count` reports 552; the `/media` edge paginates to 494. 58 unreconciled — see findings |
> | 4 | supported: `reach`, `views`, `likes`, `comments`, `shares`, `saved`, `total_interactions`, `ig_reels_avg_watch_time`, `ig_reels_video_view_total_time` · **unsupported: `profile_visits`, `follows`** |
> | 5 | **`trial_params` accepted** — container `18619475482009797` created and abandoned. Do not publish it. |
>
> The probe hardcoded `graph.facebook.com`, which cannot parse an `IGAA`
> Instagram-Login token; the error it returns is worded identically to a corrupt
> token. `scripts/probe.py` now selects the host from the token prefix.
>
> Step 4 also had to be run twice per metric — several metrics only answer to
> `metric_type=total_value`, and the error for omitting it is identical to
> "metric not supported". A single-shape probe under-reports capability.

---

## 2. Insights backfill and snapshot schedule

Pull every historical post once, then snapshot on a fixed cadence relative to **post age**, not wall-clock:

| Age | Why |
|---|---|
| 6h | Early velocity — the strongest predictor of eventual reach |
| 24h | Primary comparison point between posts |
| 72h | Trial reel decision point |
| 7d | Catches slow burners |
| 30d | Final. Distinguishes evergreen from spike-and-die |

Store every snapshot as a row, never overwrite. You want the *curve*, not the endpoint — a video still gaining reach on day 14 behaves completely differently from one that flatlined on day 2, and only the curve tells you which is which.

> **Amended 2026-08-18.** The curve is **forward-only**. A snapshot claims only
> the *newest* threshold a post has already passed, so a post already older than
> 30 days gets a `30d` row and can never acquire a `6h` one — the early number
> cannot be reconstructed after the fact. The complete five-point curve exists
> only for posts published from 2026-08-18 onward. The §3 eligibility filter
> leans on `reach_30d`, which every post with insights does have, so the scorer
> is unaffected.
>
> Backfill actuals: 494 media, 303 snapshots (`30d`=288, `7d`=11, `72h`=2,
> `24h`=1, `6h`=1). The 191 media with no snapshot all predate April 2020, when
> the account became Professional; Instagram does not backfill insights across
> that boundary. **All 141 reels have complete insights** — the gap is entirely
> old feed images and videos.

**Schema sketch** (`data/posts.db`):

```sql
CREATE TABLE media (
  media_id      TEXT PRIMARY KEY,
  media_type    TEXT,
  permalink     TEXT,
  caption       TEXT,
  posted_at     TIMESTAMP,
  duration_s    REAL,
  library_ref   TEXT,          -- FK into library/ for the source file
  is_trial      BOOLEAN DEFAULT 0,
  parent_media  TEXT,          -- set when this is a repost variant
  variant_note  TEXT           -- "hook B, tighter cut, teaching caption"
);

CREATE TABLE snapshots (
  media_id      TEXT,
  captured_at   TIMESTAMP,
  age_bucket    TEXT,          -- 6h | 24h | 72h | 7d | 30d
  reach         INTEGER,
  views         INTEGER,
  likes         INTEGER,
  comments      INTEGER,
  shares        INTEGER,       -- the signal that matters most
  saved         INTEGER,
  avg_watch_ms  INTEGER,       -- MILLISECONDS as returned; convert at read time
  PRIMARY KEY (media_id, age_bucket)
);
```

> **Amended 2026-08-18.** `profile_visits` and `follows` columns removed — the
> API does not return either for reels, so they would have been permanently
> NULL. As implemented, `backfill.py` stores metrics as a JSON blob keyed by
> metric name rather than as fixed columns, precisely so a capability change on
> Meta's side does not require a migration.

---

## 3. The scorer

Runs weekly. Ranks every eligible library video as a repost candidate.

### Eligibility

```
eligible IF
     age_days           >= 90        -- audience has rotated
 AND days_since_repost  >= 120       -- or never reposted
 AND source_file_exists == true
 AND is_seasonal        == false     -- no "happy new year" in August
 AND reach_30d          >= 0.5 × account_median_reach
                                     -- floor: don't retest genuine duds
```

### Score

All components normalized to 0–1 across the eligible set (min-max over the cohort, so the weights mean something):

```
score =  0.4375 × norm(shares / reach)            -- sends: top-weighted 2026 signal
       + 0.3125 × norm(avg_watch_s / duration_s)  -- retention ratio
       + 0.2500 × norm(saved / reach)
```

Deliberately **not** in the formula: raw reach, and likes. Raw reach is confounded by how much distribution Instagram happened to give it that week. Likes are the weakest 2026 signal and including them would bias toward crowd-pleasing content that doesn't convert.

> **Amended 2026-08-18.** A fourth term, `0.20 × norm(profile_visits / reach)`,
> was removed: the Media Insights API does not support `profile_visits` for
> reels on this account, so it is uncomputable. The three surviving weights are
> the originals divided by 0.80, which preserves their relative ordering exactly.
>
> **This is the one place Phase 0 forced a judgment rather than a fact.** Two
> alternatives were considered:
> - *Substitute `total_interactions / reach`* — rejected. It contains shares and
>   saves, which are already weighted here, so it double-counts them and drags
>   the remainder toward likes.
> - *Substitute account-level `profile_views`* — rejected. It is a daily
>   account figure and cannot be attributed to one post, so it would add the
>   same number to every candidate and change no ranking.
>
> Losing this term costs real information: the scorer can no longer distinguish
> "people watched and shared it" from "people watched, shared it, and then went
> looking at who made it". That second thing is what actually grows the funnel.
> The compensation is that trial reels measure stranger-acquisition directly
> (§6.2), so the signal returns at the *trial* stage even though it is absent at
> the *candidate-selection* stage. Retune the weights from real trial evidence
> after ~40 runs.

> **Blocked, not broken: the retention term needs `ffprobe`.** The backfill found
> `duration_s` NULL on all 494 media, because **no Instagram media field exposes
> video duration**. `avg_watch_s / duration_s` therefore has no denominator, and
> that is 31% of the weight above.
>
> Duration is a property of the file, not of Instagram, so it is recoverable:
> read it locally with `ffprobe` over `library/`, which this section already
> requires to exist for the `source_file_exists` filter. **Build the
> `library/` ↔ `media_id` mapping before the scorer, not after** — retention is
> the second-strongest signal in the model and reweighting around it would leave
> a two-signal proxy doing work the design does not intend.
>
> If that mapping turns out to be impractical, the fallback is `shares` 0.64 /
> `saved` 0.36 — and the repost queue must then state on its face that it is
> ranking on two signals, so nobody reads it as the full model.
>
> **Units:** `ig_reels_avg_watch_time` is returned in **milliseconds**
> (sample: `14536` = 14.5s). Dividing it by a duration in seconds inflates the
> ratio 1000×. Convert once, at ingest.

Output: `reports/repost-queue.md`, top 20 ranked with their numbers, so the ranking is auditable rather than a black box.

---

## 4. Variant generation

Reposting the identical file is the mistake to avoid — it gets weaker distribution and wastes the slot. Each repost is a **variant test with a written hypothesis.**

For each queued video, Studio produces:

| Variant axis | What changes | Hypothesis it tests |
|---|---|---|
| **Hook** | First 3s replaced with a different candidate from `hooks.json` | Which musical moment stops the scroll |
| **Cover** | Different frame | Does the still matter, or is it all in the first second of motion |
| **Caption angle** | Teaching vs story vs invitation | Which register drives sends |
| **Length** | Trimmed tighter | Does retention ratio beat total watch time |

**Change one axis at a time.** Two changes and you learn nothing about either. The queue interleaves so you're not testing hooks for three straight weeks.

Each variant is written as a row in `trials.db` **with its hypothesis recorded before publishing** — this is what turns posting into experimenting.

```sql
CREATE TABLE trials (
  trial_id      TEXT PRIMARY KEY,
  parent_media  TEXT,
  variant_axis  TEXT,          -- hook | cover | caption | length
  hypothesis    TEXT,          -- "opening on the descending run will beat the
                               --  static chord because motion in frame 1"
  published_at  TIMESTAMP,
  baseline_at_publish INTEGER, -- median trial reach at the time, frozen
  reach_72h     INTEGER,
  shares_72h    INTEGER,
  saved_72h     INTEGER,       -- decides GRADUATE vs HOOK_WON (see §6)
  acct_profile_views_on_day INTEGER,
                               -- account-level context ONLY, never a decision
                               -- input: it is a whole-account daily figure
  verdict       TEXT,          -- graduate | hook_won | archive
  verdict_note  TEXT
);
```

> **Amended 2026-08-18.** `profile_visits_72h` removed — unavailable per-post
> for reels, so it would have been permanently NULL. `saved_72h` takes its place
> in the verdict logic. `acct_profile_views_on_day` is recorded deliberately as
> *context you can look at later*, kept structurally separate from the columns
> the verdict reads, so nobody is tempted to treat an account-wide daily number
> as evidence about one trial.

Freezing `baseline_at_publish` matters: as the account grows the baseline moves, and you need to compare each trial against the baseline *at its own moment*, not today's.

---

## 5. Publishing a trial reel

All calls below go to **`https://graph.instagram.com/v26.0/`** — confirmed by the Phase 0 probe. Not `graph.facebook.com`.

```
1. Upload render to VPS temp path → signed public URL (expires 2h)

2. POST /{ig-user-id}/media
     media_type   = REELS
     video_url    = <signed url>
     cover_url    = <chosen cover>
     caption      = <variant caption>
     trial_params = {"graduation_strategy": "MANUAL"}
     share_to_feed = false

3. Poll GET /{container-id}?fields=status_code,status
     until FINISHED  (typically 30s–2min; time out at 10 min and alert)
     on ERROR → log the status string, do not retry blindly

4. POST /{ig-user-id}/media_publish
     creation_id = <container-id>

5. Write trials.db row, schedule the 72h review, revoke the signed URL
```

**`MANUAL` graduation, deliberately.** `SS_PERFORMANCE` lets Instagram auto-graduate on its own performance notion, which optimises for watch time and little else. A reel can rack up views from people who will never care about guitar lessons. Keep the decision.

> **Amended 2026-08-18.** The original wording justified `MANUAL` on the grounds
> that Instagram "can't see profile visits or follows, the two metrics that
> actually matter to your funnel". Neither is available to *you* per-post either,
> so that argument no longer holds as stated. `MANUAL` is still right — it keeps
> the graduation criteria yours and lets them improve as trial evidence
> accumulates — but the honest reason is control, not an information advantage
> you do not have.

**Cadence:** one per day, published into the timing window the model derived from your own `online_followers` data. Rate limits are irrelevant at this volume.

---

## 6. The 72-hour review

Runs daily, evaluates every trial that has just crossed 72 hours.

```
baseline = median(reach_72h) over the last 20 trials
           -- if fewer than 5 trials exist yet, fall back to median 72h reach
              of non-trial posts × 0.7 (trials reach less; they have no
              follower seed) and mark the verdict low-confidence

           reach_72h ≥ 1.5 × baseline
        AND saved/reach ≥ account median
              → GRADUATE. Publish to followers and the grid.
                Log what won and why.

           reach_72h ≥ 1.5 × baseline
        AND saved/reach < account median
              → HOOK_WON, CONTENT DIDN'T.
                The opening stopped people; the body didn't hold them.
                Reuse this hook on different material. Retire the clip.

           0.8 × baseline ≤ reach_72h < 1.5 × baseline
              → INCONCLUSIVE. Archive, no strong signal either way.

           reach_72h < 0.8 × baseline
              → ARCHIVE. Log the failed hypothesis — negative results are
                half the dataset.
```

> **Amended 2026-08-18.** Both `GRADUATE` and `HOOK_WON` originally keyed on
> `profile_visits/reach`, which does not exist per-post for reels. `saved/reach`
> replaces it, and the substitution is **weaker in a way worth naming**:
>
> - *What was intended:* "did this make a stranger curious enough to go look at
>   who I am" — a funnel signal, one step from a follow or an enquiry.
> - *What is now measured:* "did a stranger think this was worth keeping" — an
>   engagement signal that correlates with quality but says nothing about
>   whether attention transferred from the clip to **you**.
>
> Record account-level `profile_views` for the trial day alongside each verdict
> as context. Do **not** feed it into the decision: it is a whole-account daily
> number, it moves for reasons unrelated to the trial, and treating it as
> per-trial evidence would be the exact false precision this document exists to
> avoid. After ~40 trials, check whether `saved/reach` on graduated trials
> actually tracks follower growth — if it does not, this rule needs replacing
> with something better, not defending.

The `HOOK_WON` branch is still the one that pays off over time. Separating "did the opening work" from "did the content work" is the distinction that most creators never make, because without trial reels you can't isolate it cleanly — and that separation survives the metric change intact, since it rests on reach versus a body-quality proxy, not on which proxy you use.

Results append to the weekly brief. After ~40 trials the Analyst has enough to state which hook types, lengths, and caption registers reliably beat baseline **for your audience specifically** — and the scorer's weights get retuned from your own evidence rather than from general advice.

---

## 7. Fallback if `trial_params` isn't available

> **Not needed — but do not delete yet.** The Phase 0 probe confirmed Graph
> accepts `trial_params`, so Phase 1 builds the API path in §5. This section
> stays because acceptance is not proof the parameter is *honoured*: the first
> real trial reel must be verified in-app as flagged "Trial" and absent from the
> grid. If that check fails, everything below becomes live again.

If the probe in §1 shows the API rejects `trial_params` on your account, nothing about this design changes except the last mile:

- The engine still scores, still generates variants, still writes hypotheses, still tracks results
- Instead of publishing, it drops the finished render + cover + caption into a synced folder and pings you
- You upload in the app and toggle "Trial" yourself — **about 60 seconds a day**
- The engine picks the trial back up by matching the new media_id on the next insights pull, and the 72h review runs unchanged

Worth noting: Buffer, Hootsuite, Sprout Social and similar can't schedule Trial Reels at all. So even the fallback puts you ahead of anyone using off-the-shelf tooling.

---

## 8. Definition of done for Phase 1

- [x] `capabilities.json` written and the §1 unknowns answered from the live account *(2026-08-18 — two of the four operating-plan §14 questions remain open; see `reports/phase-0-findings.md`)*
- [x] All historical posts backfilled with insights *(494 media, 303 snapshots; 191 pre-April-2020 posts have no insights and never will — no reel affected)*
- [ ] **`library/` ↔ `media_id` mapping + `ffprobe` durations** — blocks the retention term, 31% of the scorer
- [ ] **First trial reel verified in-app as an actual trial** — the check §7 depends on
- [ ] Snapshot cron running on the five age buckets
- [ ] Scorer produces a ranked, auditable `repost-queue.md`
- [ ] At least 3 hook variants generated for the top queued video
- [ ] One trial reel published end-to-end via API (or via the §7 fallback)
- [ ] 72h reviewer runs and writes a verdict with its reasoning
- [ ] Token refresh job running with failure alerting
- [ ] `library/` backed up off the PC

**Success criterion at 30 days:** 25–30 trials run, a baseline established from real data, and at least 3 graduated reposts on the grid — with a written record of *why* each one won.
