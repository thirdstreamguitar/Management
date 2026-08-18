# Phase 1 — Repost + Trial Reel Engine

Buildable spec for the first thing that ships. Assumes Phase 0 (Meta app, token, capability probe, insights backfill) is done.

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
  profile_visits INTEGER,
  follows       INTEGER,
  avg_watch_s   REAL,
  PRIMARY KEY (media_id, age_bucket)
);
```

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
score =  0.35 × norm(shares / reach)            -- sends: top-weighted 2026 signal
       + 0.25 × norm(avg_watch_s / duration_s)  -- retention ratio
       + 0.20 × norm(saved / reach)
       + 0.20 × norm(profile_visits / reach)    -- did it make them curious about YOU
```

Deliberately **not** in the formula: raw reach, and likes. Raw reach is confounded by how much distribution Instagram happened to give it that week. Likes are the weakest 2026 signal and including them would bias toward crowd-pleasing content that doesn't convert.

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
  profile_visits_72h INTEGER,
  verdict       TEXT,          -- graduate | hook_won | archive
  verdict_note  TEXT
);
```

Freezing `baseline_at_publish` matters: as the account grows the baseline moves, and you need to compare each trial against the baseline *at its own moment*, not today's.

---

## 5. Publishing a trial reel

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

**`MANUAL` graduation, deliberately.** `SS_PERFORMANCE` lets Instagram auto-graduate on its own performance notion — which can't see profile visits or follows, the two metrics that actually matter to your funnel. A reel can rack up views from people who will never care about guitar lessons. Keep the decision.

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
        AND profile_visits/reach ≥ account median
              → GRADUATE. Publish to followers and the grid.
                Log what won and why.

           reach_72h ≥ 1.5 × baseline
        AND profile_visits/reach < account median
              → HOOK_WON, CONTENT DIDN'T.
                The opening stopped people; the body didn't convert.
                Reuse this hook on different material. Retire the clip.

           0.8 × baseline ≤ reach_72h < 1.5 × baseline
              → INCONCLUSIVE. Archive, no strong signal either way.

           reach_72h < 0.8 × baseline
              → ARCHIVE. Log the failed hypothesis — negative results are
                half the dataset.
```

The `HOOK_WON` branch is the one that pays off over time. Separating "did the opening work" from "did the content work" is the distinction that most creators never make, because without trial reels you can't isolate it cleanly.

Results append to the weekly brief. After ~40 trials the Analyst has enough to state which hook types, lengths, and caption registers reliably beat baseline **for your audience specifically** — and the scorer's weights get retuned from your own evidence rather than from general advice.

---

## 7. Fallback if `trial_params` isn't available

If the probe in §1 shows the API rejects `trial_params` on your account, nothing about this design changes except the last mile:

- The engine still scores, still generates variants, still writes hypotheses, still tracks results
- Instead of publishing, it drops the finished render + cover + caption into a synced folder and pings you
- You upload in the app and toggle "Trial" yourself — **about 60 seconds a day**
- The engine picks the trial back up by matching the new media_id on the next insights pull, and the 72h review runs unchanged

Worth noting: Buffer, Hootsuite, Sprout Social and similar can't schedule Trial Reels at all. So even the fallback puts you ahead of anyone using off-the-shelf tooling.

---

## 8. Definition of done for Phase 1

- [ ] `capabilities.json` written and the four §1 unknowns answered from the live account
- [ ] All historical posts backfilled with insights
- [ ] Snapshot cron running on the five age buckets
- [ ] Scorer produces a ranked, auditable `repost-queue.md`
- [ ] At least 3 hook variants generated for the top queued video
- [ ] One trial reel published end-to-end via API (or via the §7 fallback)
- [ ] 72h reviewer runs and writes a verdict with its reasoning
- [ ] Token refresh job running with failure alerting
- [ ] `library/` backed up off the PC

**Success criterion at 30 days:** 25–30 trials run, a baseline established from real data, and at least 3 graduated reposts on the grid — with a written record of *why* each one won.
