# Repost queue

**Generated:** 2026-08-19 08:39 UTC · **Source:** `/home/user/Management/data/posts.db` · **Cohort:** 120 eligible of 141 reels

Ranked by likelihood of acquiring non-followers when re-cut and republished as a trial reel. Spec: [`docs/phase-1-repost-engine.md`](../docs/phase-1-repost-engine.md) §3.

```
score = 0.4375 x norm(shares / views)            <- sends
      + 0.3125 x norm(avg_watch_s / duration_s)  <- retention
      + 0.2500 x norm(saved / views)             <- saves
```

Every number below is shown so the ranking can be checked by eye: the raw rate, its min-max normalised value, and the weighted total. `score` should equal `0.4375·nSend + 0.3125·nRet + 0.25·nSave`.

## Cohort funnel

| Stage | Count |
|---|---:|
| Reels in library | 141 |
| — **excluded by hand** (never repost) | −5 |
| — younger than 90 days | −16 |
| — no insight snapshot | −0 |
| — no `duration_s` | −0 |
| — missing a scorer input | −0 |
| — zero views | −0 |
| — **failed data-quality gate** | −0 |
| **Eligible cohort** | **120** |

> **`reach` is untrusted on 36 of 120 candidates** and is printed below for reference only — it is not in the formula. Those rows report more likes than reach, which is physically impossible; Phase 0 traced it to Instagram returning a degraded `reach` for pre-2024 media. The gate validates `views`, `likes`, `shares`, `saved` and watch time, all of which are internally consistent across the whole library. Gating on `reach` as originally specified cost 36 candidates and removed the entire 2022–23 catalogue for the sake of one field the scorer never reads.

## Normalisation ranges

Min-max is taken across the eligible cohort, so these bounds define the 0–1 scale. A cohort change moves every score.

| Term | Min | Max | Note |
|---|---:|---:|---|
| `shares / views` | 0.000% | 1.341% |  |
| `avg_watch_s / duration_s` | 0.061 | 0.986 |  |
| `saved / views` | 0.000% | 0.768% |  |

## Top 20

| # | Posted | Reel | views | shares | saved | likes | reach | dur s | watch s | shares/views | nSend | retention | nRet | saved/views | nSave | **score** |
|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 2026-04-11 | [500135](https://www.instagram.com/reel/DW_8CAqonwA/) | 820 | 11 | 0 | 24 | 591 | 24.1 | 7.4 | 1.341% | 1.000 | 0.309 | 0.268 | 0.000% | 0.000 | **0.5211** |
| 2 | 2022-08-04 | [725685](https://www.instagram.com/reel/Cg2HXk8FEtv/) | 470 | 0 | 2 | 29 | 9† | 6.0 | 5.9 | 0.000% | 0.000 | 0.986 | 1.000 | 0.426% | 0.554 | **0.4511** |
| 3 | 2026-03-06 | [206069](https://www.instagram.com/reel/DVi3KOaiJn6/) | 420 | 3 | 1 | 11 | 286 | 27.1 | 6.3 | 0.714% | 0.532 | 0.233 | 0.186 | 0.238% | 0.310 | **0.3685** |
| 4 | 2026-02-15 | [127147](https://www.instagram.com/reel/DUy0yFZiLbq/) | 839 | 4 | 0 | 16 | 503 | 12.5 | 6.7 | 0.477% | 0.355 | 0.539 | 0.516 | 0.000% | 0.000 | **0.3168** |
| 5 | 2023-12-21 | [141467](https://www.instagram.com/reel/C1HX0q-N3ZI/) | 1,070 | 0 | 2 | 41 | 30† | 9.4 | 6.7 | 0.000% | 0.000 | 0.717 | 0.709 | 0.187% | 0.243 | **0.2826** |
| 6 | 2023-04-15 | [533656](https://www.instagram.com/reel/CrDttjdANAG/) | 521 | 0 | 4 | 63 | 15† | 153.4 | 21.3 | 0.000% | 0.000 | 0.139 | 0.084 | 0.768% | 1.000 | **0.2762** |
| 7 | 2026-04-26 | [470768](https://www.instagram.com/reel/DXl6ixno_6o/) | 540 | 3 | 1 | 29 | 352 | 49.1 | 7.2 | 0.556% | 0.414 | 0.147 | 0.092 | 0.185% | 0.241 | **0.2703** |
| 8 | 2026-02-09 | [609163](https://www.instagram.com/reel/DUjcfDnCBfJ/) ⚠ | 2,154 | 13 | 2 | 83 | 1,320 | 60.5 | 9.4 | 0.604% | 0.450 | 0.155 | 0.102 | 0.093% | 0.121 | **0.2588** |
| 9 | 2025-10-17 | [010250](https://www.instagram.com/reel/DP6y6FLCAq0/) | 876 | 3 | 3 | 35 | 589 | 44.9 | 7.0 | 0.342% | 0.255 | 0.157 | 0.104 | 0.342% | 0.446 | **0.2556** |
| 10 | 2024-05-28 | [207047](https://www.instagram.com/reel/C7hXo85tW1J/) | 693 | 0 | 3 | 22 | 80 | 17.7 | 7.1 | 0.000% | 0.000 | 0.399 | 0.365 | 0.433% | 0.564 | **0.2550** |
| 11 | 2026-01-09 | [835007](https://www.instagram.com/reel/DTSrKSZCFnc/) | 648 | 0 | 2 | 24 | 423 | 11.0 | 5.7 | 0.000% | 0.000 | 0.517 | 0.493 | 0.309% | 0.402 | **0.2547** |
| 12 | 2022-10-03 | [490110](https://www.instagram.com/reel/CjQsGorDANO/) | 2,751 | 0 | 12 | 94 | 10† | 17.8 | 6.7 | 0.000% | 0.000 | 0.376 | 0.340 | 0.436% | 0.568 | **0.2484** |
| 13 | 2024-09-19 | [200607](https://www.instagram.com/reel/DAHO8EQtGwE/) | 906 | 1 | 2 | 49 | 540 | 17.2 | 7.9 | 0.110% | 0.082 | 0.461 | 0.433 | 0.221% | 0.288 | **0.2431** |
| 14 | 2022-12-05 | [468003](https://www.instagram.com/reel/ClzD0LqMykW/) | 385 | 0 | 2 | 33 | 10† | 31.2 | 8.2 | 0.000% | 0.000 | 0.262 | 0.217 | 0.519% | 0.677 | **0.2369** |
| 15 | 2024-10-01 | [289797](https://www.instagram.com/reel/DAlvgu9Np51/) | 1,293 | 1 | 1 | 60 | 607 | 19.7 | 11.9 | 0.077% | 0.058 | 0.603 | 0.586 | 0.077% | 0.101 | **0.2336** |
| 16 | 2026-03-05 | [435309](https://www.instagram.com/reel/DVg2JgbCC74/) | 715 | 2 | 1 | 29 | 481 | 19.2 | 6.6 | 0.280% | 0.209 | 0.344 | 0.306 | 0.140% | 0.182 | **0.2324** |
| 17 | 2026-01-22 | [797692](https://www.instagram.com/reel/DT0Rh_OiPbh/) | 789 | 1 | 1 | 21 | 508 | 11.2 | 5.4 | 0.127% | 0.094 | 0.483 | 0.456 | 0.127% | 0.165 | **0.2252** |
| 18 | 2022-09-26 | [273893](https://www.instagram.com/reel/Ci-wQcfvdEa/) | 4,383 | 0 | 14 | 83 | 16† | 46.6 | 19.5 | 0.000% | 0.000 | 0.417 | 0.385 | 0.319% | 0.416 | **0.2244** |
| 19 | 2022-03-26 | [168236](https://www.instagram.com/reel/CblPFr9lDtb/) | 4,542 | 3 | 10 | 84 | 199 | 49.1 | 21.9 | 0.066% | 0.049 | 0.445 | 0.416 | 0.220% | 0.287 | **0.2231** |
| 20 | 2024-10-02 | [761490](https://www.instagram.com/reel/DAohm0UtaGe/) | 576 | 0 | 1 | 32 | 342 | 12.0 | 6.5 | 0.000% | 0.000 | 0.542 | 0.520 | 0.174% | 0.226 | **0.2190** |

## ⚠ Confirm before publishing

1 of the top 20 use forward-looking language. A reposted event promo tells people a gig is happening that already happened — check these before they go anywhere, and add any real promo to `data/repost-exclusions.json` so it never surfaces again.

| # | Posted | Reel | Signals | Caption |
|---:|---|---|---|---|
| 8 | 2026-02-09 | 609163 | dated claim | Dear friends and music lovers, I will be recording an album with these amazing musicians, and I need your help |

> The detector reads **forward-looking language only** — *tomorrow*, *see you there*, a date paired with a time. Venue @mentions are deliberately ignored: 36 of 141 reels carry one and most are past-tense recaps, which are exactly the good repost material. It flags for review and **never excludes on its own** — a false positive would quietly drop a good candidate with nothing to show for it.

## Excluded (5)

From [`data/repost-exclusions.json`](../data/repost-exclusions.json), versioned in git rather than in the gitignored database so it survives every backfill rebuild.

### Permanent — the footage is the advert (4)

| Posted | Reel | By | Why |
|---|---|---|---|
| 2026-08-12 | [014103](https://www.instagram.com/reel/Db86Zbio1Rs/) | claude-proposed | "Latin Jazz Night 22.8 Sat 21:30 at Frau Mayer Rudolfsplatz 12, 1010 Wien". Full street address and a 14-second runtime - this is a flyer, not a performance. |
| 2026-05-16 | [565363](https://www.instagram.com/reel/DYanO02oUAR/) | human | Frau Mayer Latin Dance Party, 23 May 20:15. Date and venue are the content. |
| 2026-04-05 | [100294](https://www.instagram.com/reel/DWwni80CBrN/) | human | "Playing tomorrow at @miles.smiles.vienna, see you there". Made to fill a room on a specific night. |
| 2026-01-17 | [198452](https://www.instagram.com/reel/DTnKsN3iBjn/) | claude-proposed | "Next week in @fraumayerwien ... Poster by @jwsst__" - the caption credits a poster designer, so the footage is the poster. Also the one reel durations.py could not read, so it was already outside the cohort. |

### ⏳ Caption was dated, footage may be fine (1)

**These are candidates on hold, not rejects.** A repost gets a new caption anyway, so if the footage carries no on-screen date, venue card or poster frame, the reel is repostable — delete its entry from the exclusions file and it re-enters the queue on the next run. Held out until then because reposting a real promotion misinforms people about a live date, and that is worse than a delayed candidate.

| Posted | Reel | dur | Why it is held | What to check |
|---|---|---:|---|---|
| 2026-01-14 | [133078](https://www.instagram.com/reel/DTgm74VCGph/) | 68.7s | Concert invitation for Porgy & Bess on 26 January - but the caption itself says "You are listening in the video to one of my latest composition: Island Songs", with the full 15-musician ensemble credited. The footage is the composition, not the advert. This one reached rank 13 of the queue. | Strongest reuse candidate of the four. Island Songs is evergreen material; only the concert pitch was dated. |

### Reviewed and kept (4)

Flagged by the detector, checked, and left in the queue — recorded so the same reel is not re-litigated every week.

| Posted | Reel | Flagged as | Verdict |
|---|---|---|---|
| 2023-07-23 | [243429](https://www.instagram.com/reel/CvDGcE1AAbs/) | future verb ("upcoming") | "Practicing for the upcoming gigs!" names no date, no venue, no specific event. Reposting it cannot mislead anyone about a live show. This is the detector's one false positive across 141 reels. |
| 2026-08-07 | [462250](https://www.instagram.com/reel/DbvlDuNoE1V/) | Caption is just "Tomorrow @fraumayerwien with @daviddolliner @avraimov.music", b | Human watched the video: no on-screen date, venue card or poster frame. The dated content was caption-only. |
| 2025-02-10 | [598825](https://www.instagram.com/reel/DF5i8SbN9Vq/) | Caption is a three-gig week schedule (@cafekorb, @atlas.wien, @fraumayerwien). 8 | Human watched the video: no on-screen date, venue card or poster frame. The dated content was caption-only. |
| 2023-08-05 | [555455](https://www.instagram.com/reel/CvkGYUtvTiz/) | "Preparing for the gig tomorrow at @jazzcafezwe, here is a beautiful tune by @lu | Human watched the video: no on-screen date, venue card or poster frame. The dated content was caption-only. |

## Filters specified but not applied

§3 lists four more eligibility filters. Each is deliberately absent, not overlooked:

| Filter | Why not applied |
|---|---|
| `days_since_repost >= 120` | No reposts exist yet — `trials.db` is unbuilt, so the filter is vacuously true. Wire it in when the publisher lands. |
| `source_file_exists` | Needs the `library/` ↔ `media_id` mapping, which does not exist yet. Every candidate here still has to be matched to a source file before it can be re-cut. |
| `is_seasonal` | **Partly handled.** Event promotion — the case that actually matters, since reposting one misinforms people about a live date — is caught by the hand-maintained exclusion list plus the ⚠ detector above. Genuine seasonal content (holidays, anniversaries) still needs Studio tagging. |
| `reach_30d >= 0.5 × median` | **Would actively harm the ranking.** It filters on `reach`, the field Phase 0 found corrupt for pre-2024 reels. Leave it out until reach is trustworthy. |
