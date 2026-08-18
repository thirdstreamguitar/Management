#!/usr/bin/env python3
"""
Phase 1 -- repost candidate scorer.

Ranks old reels by how likely they are to acquire strangers when re-cut and
re-published as a trial reel. Reads data/posts.db (backfill.py + durations.py)
and writes reports/repost-queue.md.

Spec: docs/phase-1-repost-engine.md section 3.
Why the inputs are what they are: reports/phase-0-findings.md.

Three things here look wrong until you read the findings:

  1. Denominator is `views`, not `reach`. `reach` is corrupt for reels posted
     before ~early 2024 -- 36 of 141 report more likes than reach. Because
     norm() is min-max across the cohort, those rows would have taken the top
     of the queue AND crushed every legitimate candidate toward zero.

  2. `ig_reels_avg_watch_time` is in MILLISECONDS. Dividing it by a duration in
     seconds inflates retention 1000x. Converted once, in load_candidates().

  3. The gate is `likes <= reach <= views` even though reach is not otherwise
     used. views fixes the corruption we found; the gate catches what we
     have not.

Usage:
    python scripts/scorer.py               # top 20 to reports/repost-queue.md
    python scripts/scorer.py --top 40
    python scripts/scorer.py --db path/to/posts.db

Publishes nothing. Reads the database; writes one markdown file.
Stdlib only.
"""

import argparse
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

WEIGHTS = {"sends": 0.4375, "retention": 0.3125, "saves": 0.2500}

MIN_AGE_DAYS = 90

# Most mature first. A media can hold several snapshots; the 30d row is the
# most complete measurement, so it wins when present.
BUCKET_RANK = {"30d": 5, "7d": 4, "72h": 3, "24h": 2, "6h": 1}


def norm(values):
    """Min-max to 0..1 across the cohort.

    Degenerate cohort (all identical, or n=1) has no spread to measure, so the
    term carries no ranking information and every row gets 0.0 -- deliberately
    not 0.5, which would silently donate that term's full weight to everyone.
    """
    lo, hi = min(values), max(values)
    if hi == lo:
        return [0.0] * len(values), (lo, hi, True)
    return [(v - lo) / (hi - lo) for v in values], (lo, hi, False)


def load_candidates(db_path):
    """Returns (candidates, rejections, totals). Every drop is counted and
    reasoned, because a queue you cannot audit is a queue you cannot trust."""
    db = sqlite3.connect(db_path)
    db.row_factory = sqlite3.Row

    rows = db.execute(
        """SELECT media_id, permalink, posted_at, duration_s, product_type
           FROM media WHERE product_type = 'REELS' ORDER BY posted_at DESC"""
    ).fetchall()

    snaps = {}
    for s in db.execute("SELECT media_id, age_bucket, metrics FROM snapshots"):
        prev = snaps.get(s["media_id"])
        if prev is None or BUCKET_RANK.get(s["age_bucket"], 0) > BUCKET_RANK.get(prev[0], 0):
            snaps[s["media_id"]] = (s["age_bucket"], json.loads(s["metrics"]))
    db.close()

    now = datetime.now(timezone.utc)
    candidates, rejections = [], []
    counts = {k: 0 for k in
              ("too_young", "no_snapshot", "no_duration", "missing_metrics",
               "zero_views", "failed_gate")}

    for r in rows:
        media_id = r["media_id"]
        posted = datetime.fromisoformat(r["posted_at"].replace("+0000", "+00:00"))
        age_days = (now - posted).total_seconds() / 86400

        def drop(reason, detail=""):
            counts[reason] += 1
            rejections.append({"media_id": media_id, "posted": r["posted_at"][:10],
                               "reason": reason, "detail": detail})

        if age_days < MIN_AGE_DAYS:
            drop("too_young", f"{age_days:.0f}d")
            continue
        if media_id not in snaps:
            drop("no_snapshot")
            continue

        bucket, m = snaps[media_id]
        duration = r["duration_s"]
        if not duration or duration <= 0:
            drop("no_duration", "run scripts/durations.py")
            continue

        # `likes` is the insight metric; `like_count` comes free on the media
        # node and stands in when the metric is absent for that media type.
        likes = m.get("likes", m.get("like_count"))
        views, reach = m.get("views"), m.get("reach")
        shares, saved = m.get("shares"), m.get("saved")
        watch_ms = m.get("ig_reels_avg_watch_time")

        present = {"views": views, "reach": reach, "likes": likes,
                   "shares": shares, "saved": saved,
                   "ig_reels_avg_watch_time": watch_ms}
        missing = [k for k, v in present.items() if v is None]
        if missing:
            drop("missing_metrics", ",".join(missing))
            continue

        if views <= 0:
            drop("zero_views")
            continue

        # Data-quality gate. reach is not used in the score, only here: a row
        # that violates the physical ordering is telling us its numbers cannot
        # be trusted, whichever field is the liar.
        if not (likes <= reach <= views):
            drop("failed_gate", f"likes={likes} reach={reach} views={views}")
            continue

        watch_s = watch_ms / 1000.0          # <- the millisecond conversion
        candidates.append({
            "media_id": media_id,
            "permalink": r["permalink"],
            "posted": r["posted_at"][:10],
            "age_days": age_days,
            "bucket": bucket,
            "views": views, "reach": reach, "likes": likes,
            "shares": shares, "saved": saved,
            "duration_s": duration, "watch_s": watch_s,
            "sends_rate": shares / views,
            "retention": watch_s / duration,
            "saves_rate": saved / views,
        })

    return candidates, rejections, {"reels": len(rows), "counts": counts}


def score(candidates):
    if not candidates:
        return [], {}
    n_sends, r_sends = norm([c["sends_rate"] for c in candidates])
    n_ret, r_ret = norm([c["retention"] for c in candidates])
    n_saves, r_saves = norm([c["saves_rate"] for c in candidates])

    for c, a, b, d in zip(candidates, n_sends, n_ret, n_saves):
        c["n_sends"], c["n_retention"], c["n_saves"] = a, b, d
        c["score"] = (WEIGHTS["sends"] * a
                      + WEIGHTS["retention"] * b
                      + WEIGHTS["saves"] * d)

    candidates.sort(key=lambda c: c["score"], reverse=True)
    return candidates, {"sends": r_sends, "retention": r_ret, "saves": r_saves}


def write_report(ranked, ranges, rejections, totals, top_n, out_path, db_path):
    n = len(ranked)
    counts = totals["counts"]
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    L = []
    L.append("# Repost queue\n")
    L.append(f"**Generated:** {generated} · **Source:** `{db_path}` · "
             f"**Cohort:** {n} eligible of {totals['reels']} reels\n")
    L.append("Ranked by likelihood of acquiring non-followers when re-cut and "
             "republished as a trial reel. Spec: "
             "[`docs/phase-1-repost-engine.md`](../docs/phase-1-repost-engine.md) §3.\n")
    L.append("```")
    L.append("score = 0.4375 x norm(shares / views)            <- sends")
    L.append("      + 0.3125 x norm(avg_watch_s / duration_s)  <- retention")
    L.append("      + 0.2500 x norm(saved / views)             <- saves")
    L.append("```")
    L.append("\nEvery number below is shown so the ranking can be checked by eye: "
             "the raw rate, its min-max normalised value, and the weighted total. "
             "`score` should equal `0.4375·nSend + 0.3125·nRet + 0.25·nSave`.\n")

    L.append("## Cohort funnel\n")
    L.append("| Stage | Count |")
    L.append("|---|---:|")
    L.append(f"| Reels in library | {totals['reels']} |")
    L.append(f"| — younger than {MIN_AGE_DAYS} days | −{counts['too_young']} |")
    L.append(f"| — no insight snapshot | −{counts['no_snapshot']} |")
    L.append(f"| — no `duration_s` | −{counts['no_duration']} |")
    L.append(f"| — missing a scorer input | −{counts['missing_metrics']} |")
    L.append(f"| — zero views | −{counts['zero_views']} |")
    L.append(f"| — **failed gate** `likes ≤ reach ≤ views` | −{counts['failed_gate']} |")
    L.append(f"| **Eligible cohort** | **{n}** |\n")

    if ranges:
        L.append("## Normalisation ranges\n")
        L.append("Min-max is taken across the eligible cohort, so these bounds "
                 "define the 0–1 scale. A cohort change moves every score.\n")
        L.append("| Term | Min | Max | Note |")
        L.append("|---|---:|---:|---|")
        for key, label, pct in (("sends", "shares / views", True),
                                ("retention", "avg_watch_s / duration_s", False),
                                ("saves", "saved / views", True)):
            lo, hi, degenerate = ranges[key]
            fmt = (lambda v: f"{v * 100:.3f}%") if pct else (lambda v: f"{v:.3f}")
            note = "**degenerate — term contributes 0 to every row**" if degenerate else ""
            L.append(f"| `{label}` | {fmt(lo)} | {fmt(hi)} | {note} |")
        L.append("")

    L.append(f"## Top {min(top_n, n)}\n")
    if not ranked:
        L.append("_No eligible candidates._\n")
    else:
        L.append("| # | Posted | Reel | views | shares | saved | likes | reach | "
                 "dur s | watch s | shares/views | nSend | retention | nRet | "
                 "saved/views | nSave | **score** |")
        L.append("|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
        for i, c in enumerate(ranked[:top_n], 1):
            link = f"[{c['media_id'][-6:]}]({c['permalink']})" if c["permalink"] else c["media_id"][-6:]
            L.append(
                f"| {i} | {c['posted']} | {link} | {c['views']:,} | {c['shares']:,} | "
                f"{c['saved']:,} | {c['likes']:,} | {c['reach']:,} | {c['duration_s']:.1f} | "
                f"{c['watch_s']:.1f} | {c['sends_rate']*100:.3f}% | {c['n_sends']:.3f} | "
                f"{c['retention']:.3f} | {c['n_retention']:.3f} | "
                f"{c['saves_rate']*100:.3f}% | {c['n_saves']:.3f} | **{c['score']:.4f}** |")
        L.append("")

    L.append("## Filters specified but not applied\n")
    L.append("§3 lists four more eligibility filters. Each is deliberately "
             "absent, not overlooked:\n")
    L.append("| Filter | Why not applied |")
    L.append("|---|---|")
    L.append("| `days_since_repost >= 120` | No reposts exist yet — `trials.db` "
             "is unbuilt, so the filter is vacuously true. Wire it in when the "
             "publisher lands. |")
    L.append("| `source_file_exists` | Needs the `library/` ↔ `media_id` mapping, "
             "which does not exist yet. Every candidate here still has to be "
             "matched to a source file before it can be re-cut. |")
    L.append("| `is_seasonal` | Needs content tagging from Studio. Check the top "
             "of this queue by eye for dated material until then. |")
    L.append("| `reach_30d >= 0.5 × median` | **Would actively harm the ranking.** "
             "It filters on `reach`, the field Phase 0 found corrupt for pre-2024 "
             "reels. Leave it out until reach is trustworthy. |")
    L.append("")

    if rejections:
        gated = [r for r in rejections if r["reason"] == "failed_gate"]
        if gated:
            L.append(f"## Dropped by the data-quality gate ({len(gated)})\n")
            L.append("These reels report a physically impossible ordering. Phase 0 "
                     "traced it to `reach` being wrong by ~2 orders of magnitude on "
                     "older media; the gate drops the row rather than trusting any "
                     "of its numbers.\n")
            L.append("| Posted | Reel | Detail |")
            L.append("|---|---|---|")
            for r in sorted(gated, key=lambda x: x["posted"])[:40]:
                L.append(f"| {r['posted']} | {r['media_id'][-6:]} | `{r['detail']}` |")
            if len(gated) > 40:
                L.append(f"| … | | _{len(gated) - 40} more_ |")
            L.append("")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(L))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=str(ROOT / "data" / "posts.db"))
    ap.add_argument("--out", default=str(ROOT / "reports" / "repost-queue.md"))
    ap.add_argument("--top", type=int, default=20)
    args = ap.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        sys.exit(f"{db_path} not found.\n"
                 "Run scripts/backfill.py then scripts/durations.py first -- and run\n"
                 "them on the machine holding the database (it is gitignored, so it\n"
                 "does not travel with the repo).")

    candidates, rejections, totals = load_candidates(db_path)
    ranked, ranges = score(candidates)
    out = Path(args.out)
    write_report(ranked, ranges, rejections, totals, args.top, out, db_path)

    c = totals["counts"]
    print(f"\n  {totals['reels']} reels -> {len(ranked)} eligible")
    print(f"  dropped: {c['too_young']} too young, {c['failed_gate']} failed gate, "
          f"{c['no_duration']} no duration, {c['missing_metrics']} missing metrics, "
          f"{c['no_snapshot']} no snapshot, {c['zero_views']} zero views")

    if ranked:
        print(f"\n  {'#':<3}{'posted':<12}{'reel':<9}{'views':>8}{'sh':>5}{'sv':>5}"
              f"{'dur':>7}{'watch':>7}{'sh/v':>9}{'ret':>7}{'sv/v':>8}{'score':>8}")
        print("  " + "-" * 86)
        for i, r in enumerate(ranked[:5], 1):
            print(f"  {i:<3}{r['posted']:<12}{r['media_id'][-6:]:<9}{r['views']:>8,}"
                  f"{r['shares']:>5}{r['saved']:>5}{r['duration_s']:>7.1f}"
                  f"{r['watch_s']:>7.1f}{r['sends_rate']*100:>8.3f}%"
                  f"{r['retention']:>7.3f}{r['saves_rate']*100:>7.3f}%{r['score']:>8.4f}")
    print(f"\n  -> {out}\n")


if __name__ == "__main__":
    main()
