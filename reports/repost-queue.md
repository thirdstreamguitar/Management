# Repost queue

**Generated:** 2026-08-19 08:34 UTC · **Source:** `/home/user/Management/data/posts.db` · **Cohort:** 84 eligible of 141 reels

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
| — **failed gate** `likes ≤ reach ≤ views` | −36 |
| **Eligible cohort** | **84** |

## Normalisation ranges

Min-max is taken across the eligible cohort, so these bounds define the 0–1 scale. A cohort change moves every score.

| Term | Min | Max | Note |
|---|---:|---:|---|
| `shares / views` | 0.000% | 1.341% |  |
| `avg_watch_s / duration_s` | 0.070 | 0.603 |  |
| `saved / views` | 0.000% | 0.503% |  |

## Top 20

| # | Posted | Reel | views | shares | saved | likes | reach | dur s | watch s | shares/views | nSend | retention | nRet | saved/views | nSave | **score** |
|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 2026-04-11 | [500135](https://www.instagram.com/reel/DW_8CAqonwA/) | 820 | 11 | 0 | 24 | 591 | 24.1 | 7.4 | 1.341% | 1.000 | 0.309 | 0.448 | 0.000% | 0.000 | **0.5774** |
| 2 | 2026-03-06 | [206069](https://www.instagram.com/reel/DVi3KOaiJn6/) | 420 | 3 | 1 | 11 | 286 | 27.1 | 6.3 | 0.714% | 0.532 | 0.233 | 0.306 | 0.238% | 0.473 | **0.4467** |
| 3 | 2026-02-15 | [127147](https://www.instagram.com/reel/DUy0yFZiLbq/) | 839 | 4 | 0 | 16 | 503 | 12.5 | 6.7 | 0.477% | 0.355 | 0.539 | 0.879 | 0.000% | 0.000 | **0.4301** |
| 4 | 2026-01-09 | [835007](https://www.instagram.com/reel/DTSrKSZCFnc/) | 648 | 0 | 2 | 24 | 423 | 11.0 | 5.7 | 0.000% | 0.000 | 0.517 | 0.839 | 0.309% | 0.613 | **0.4155** |
| 5 | 2024-05-28 | [207047](https://www.instagram.com/reel/C7hXo85tW1J/) | 693 | 0 | 3 | 22 | 80 | 17.7 | 7.1 | 0.000% | 0.000 | 0.399 | 0.616 | 0.433% | 0.860 | **0.4076** |
| 6 | 2024-10-01 | [289797](https://www.instagram.com/reel/DAlvgu9Np51/) | 1,293 | 1 | 1 | 60 | 607 | 19.7 | 11.9 | 0.077% | 0.058 | 0.603 | 1.000 | 0.077% | 0.154 | **0.3761** |
| 7 | 2024-09-19 | [200607](https://www.instagram.com/reel/DAHO8EQtGwE/) | 906 | 1 | 2 | 49 | 540 | 17.2 | 7.9 | 0.110% | 0.082 | 0.461 | 0.734 | 0.221% | 0.439 | **0.3750** |
| 8 | 2024-10-02 | [761490](https://www.instagram.com/reel/DAohm0UtaGe/) | 576 | 0 | 1 | 32 | 342 | 12.0 | 6.5 | 0.000% | 0.000 | 0.542 | 0.885 | 0.174% | 0.345 | **0.3628** |
| 9 | 2022-03-26 | [168236](https://www.instagram.com/reel/CblPFr9lDtb/) | 4,542 | 3 | 10 | 84 | 199 | 49.1 | 21.9 | 0.066% | 0.049 | 0.445 | 0.704 | 0.220% | 0.437 | **0.3509** |
| 10 | 2026-01-22 | [797692](https://www.instagram.com/reel/DT0Rh_OiPbh/) | 789 | 1 | 1 | 21 | 508 | 11.2 | 5.4 | 0.127% | 0.094 | 0.483 | 0.775 | 0.127% | 0.252 | **0.3464** |
| 11 | 2025-09-01 | [069919](https://www.instagram.com/reel/DOETyn1iKnS/) | 596 | 0 | 3 | 32 | 409 | 46.6 | 10.4 | 0.000% | 0.000 | 0.223 | 0.286 | 0.503% | 1.000 | **0.3394** |
| 12 | 2025-10-17 | [010250](https://www.instagram.com/reel/DP6y6FLCAq0/) | 876 | 3 | 3 | 35 | 589 | 44.9 | 7.0 | 0.342% | 0.255 | 0.157 | 0.163 | 0.342% | 0.680 | **0.3327** |
| 13 | 2026-03-05 | [435309](https://www.instagram.com/reel/DVg2JgbCC74/) | 715 | 2 | 1 | 29 | 481 | 19.2 | 6.6 | 0.280% | 0.209 | 0.344 | 0.514 | 0.140% | 0.278 | **0.3214** |
| 14 | 2026-04-26 | [470768](https://www.instagram.com/reel/DXl6ixno_6o/) | 540 | 3 | 1 | 29 | 352 | 49.1 | 7.2 | 0.556% | 0.414 | 0.147 | 0.143 | 0.185% | 0.368 | **0.3180** |
| 15 | 2026-02-28 | [038976](https://www.instagram.com/reel/DVTU-2AiICm/) | 506 | 0 | 1 | 24 | 327 | 22.4 | 9.7 | 0.000% | 0.000 | 0.432 | 0.678 | 0.198% | 0.393 | **0.3102** |
| 16 | 2026-03-07 | [552616](https://www.instagram.com/reel/DVmFKVQiNIu/) | 971 | 2 | 1 | 25 | 675 | 18.6 | 7.3 | 0.206% | 0.154 | 0.392 | 0.603 | 0.103% | 0.205 | **0.3068** |
| 17 | 2026-01-13 | [610541](https://www.instagram.com/reel/DTcrSG3CDFn/) | 628 | 0 | 1 | 26 | 420 | 12.8 | 5.7 | 0.000% | 0.000 | 0.444 | 0.701 | 0.159% | 0.316 | **0.2981** |
| 18 | 2026-02-09 | [609163](https://www.instagram.com/reel/DUjcfDnCBfJ/) | 2,154 | 13 | 2 | 83 | 1,320 | 60.5 | 9.4 | 0.604% | 0.450 | 0.155 | 0.160 | 0.093% | 0.184 | **0.2928** |
| 19 | 2025-08-17 | [588721](https://www.instagram.com/reel/DNeJRH8tR3V/) | 1,065 | 1 | 3 | 47 | 736 | 23.0 | 6.1 | 0.094% | 0.070 | 0.267 | 0.370 | 0.282% | 0.560 | **0.2860** |
| 20 | 2025-08-22 | [066137](https://www.instagram.com/reel/DNqUWs2tzlZ/) | 521 | 0 | 1 | 15 | 326 | 18.0 | 6.9 | 0.000% | 0.000 | 0.382 | 0.585 | 0.192% | 0.381 | **0.2782** |

## ⚠ Confirm before publishing

None of the top 20 trip the event-promotion detector.

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

## Dropped by the data-quality gate (36)

These reels report a physically impossible ordering. Phase 0 traced it to `reach` being wrong by ~2 orders of magnitude on older media; the gate drops the row rather than trusting any of its numbers.

| Posted | Reel | Detail |
|---|---|---|
| 2022-04-01 | 374633 | `likes=46 reach=14 views=1629` |
| 2022-04-07 | 037570 | `likes=54 reach=18 views=3796` |
| 2022-04-11 | 331289 | `likes=73 reach=15 views=3507` |
| 2022-04-17 | 004582 | `likes=62 reach=11 views=3564` |
| 2022-04-30 | 564777 | `likes=83 reach=12 views=5416` |
| 2022-05-03 | 755425 | `likes=59 reach=17 views=2137` |
| 2022-05-07 | 781311 | `likes=35 reach=19 views=564` |
| 2022-05-11 | 706605 | `likes=60 reach=10 views=4570` |
| 2022-05-23 | 948396 | `likes=70 reach=9 views=4014` |
| 2022-06-09 | 622564 | `likes=25 reach=9 views=997` |
| 2022-06-15 | 988075 | `likes=35 reach=8 views=889` |
| 2022-06-24 | 217891 | `likes=25 reach=8 views=1288` |
| 2022-07-17 | 053992 | `likes=50 reach=7 views=1899` |
| 2022-07-24 | 710631 | `likes=31 reach=7 views=703` |
| 2022-08-02 | 946219 | `likes=53 reach=6 views=1843` |
| 2022-08-04 | 725685 | `likes=29 reach=9 views=470` |
| 2022-08-13 | 179748 | `likes=29 reach=18 views=1752` |
| 2022-09-21 | 543936 | `likes=48 reach=21 views=607` |
| 2022-09-26 | 273893 | `likes=83 reach=16 views=4383` |
| 2022-10-03 | 490110 | `likes=94 reach=10 views=2751` |
| 2022-12-05 | 468003 | `likes=33 reach=10 views=385` |
| 2022-12-25 | 419309 | `likes=69 reach=12 views=1536` |
| 2023-01-03 | 889949 | `likes=31 reach=10 views=587` |
| 2023-01-24 | 366275 | `likes=33 reach=12 views=642` |
| 2023-03-13 | 688147 | `likes=23 reach=15 views=544` |
| 2023-04-15 | 533656 | `likes=63 reach=15 views=521` |
| 2023-04-23 | 244823 | `likes=51 reach=18 views=644` |
| 2023-05-01 | 379762 | `likes=36 reach=18 views=481` |
| 2023-07-02 | 089422 | `likes=38 reach=13 views=614` |
| 2023-07-23 | 243429 | `likes=33 reach=21 views=563` |
| 2023-08-05 | 555455 | `likes=31 reach=19 views=530` |
| 2023-10-20 | 564746 | `likes=45 reach=19 views=821` |
| 2023-11-14 | 515126 | `likes=43 reach=24 views=688` |
| 2023-12-21 | 141467 | `likes=41 reach=30 views=1070` |
| 2024-03-05 | 404971 | `likes=50 reach=37 views=718` |
| 2024-03-08 | 058854 | `likes=46 reach=34 views=903` |
