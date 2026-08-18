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
import re
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


EXCLUSIONS = ROOT / "data" / "repost-exclusions.json"

# Forward-looking language. A reposted event promo does not merely underperform
# -- it announces a gig that already happened, and someone can turn up at a
# venue on the wrong night. So this is a correctness guard, not a ranking tweak.
#
# Venue @mentions are deliberately NOT a signal. 36 of 141 reels mention one,
# because the player gigs constantly, and most are past-tense recaps ("the other
# night at @fraumayerwien") which are exactly the good repost material. Future
# tense is what separates a promo from a performance clip.
_MONTHS = r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)"
PROMO_SIGNALS = {
    "imminent": re.compile(
        r"\b(tomorrow|tonight|this (?:evening|friday|saturday|sunday|weekend)"
        r"|next (?:week|month|friday|saturday|sunday))\b", re.I),
    "invitation": re.compile(
        r"\b(see you there|see you tomorrow|invite you|join us|join me|save the date"
        r"|don'?t miss|come by|entry free|free donation|tickets?|doors? open|rsvp)\b", re.I),
    "date+time": re.compile(
        rf"(\b\d{{1,2}}\s*[./]\s*\d{{1,2}}\b|\b\d{{1,2}}(?:st|nd|rd|th)?\s+(?:of\s+)?{_MONTHS}"
        rf"|{_MONTHS}\w*\s+\d{{1,2}}\b).{{0,40}}?\b\d{{1,2}}[:.]\d{{2}}", re.I | re.S),
    "future verb": re.compile(
        r"\b(i'?ll be|we'?ll be|playing (?:tomorrow|this|next)|performing (?:tomorrow|this|next)"
        r"|will be playing|upcoming)\b", re.I),
}
# Past-tense markers pull the score back down: "the other night at X" is a
# performance recap, not an invitation.
PROMO_PAST = re.compile(
    r"\b(the other (?:day|night)|yesterday'?s?|last (?:night|week)|was recorded"
    r"|from (?:the|my|our|yesterday)|a while ago|throwback)\b", re.I)


def promo_flag(caption):
    """(score, signals). >= 1 means review before publishing. Never auto-excludes:
    a false positive would silently drop a good candidate with nothing to show
    for it, and the human approval gate already catches what this misses."""
    caption = caption or ""
    hits = [name for name, rx in PROMO_SIGNALS.items() if rx.search(caption)]
    return len(hits) - (1 if PROMO_PAST.search(caption) else 0), hits


def load_exclusions():
    """Human judgment, versioned in git rather than in the gitignored database
    so it survives every backfill rebuild."""
    if not EXCLUSIONS.exists():
        return {}
    data = json.loads(EXCLUSIONS.read_text())
    return {e["media_id"]: e for e in data.get("excluded", [])}


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
        """SELECT media_id, permalink, posted_at, duration_s, product_type, caption
           FROM media WHERE product_type = 'REELS' ORDER BY posted_at DESC"""
    ).fetchall()

    snaps = {}
    for s in db.execute("SELECT media_id, age_bucket, metrics FROM snapshots"):
        prev = snaps.get(s["media_id"])
        if prev is None or BUCKET_RANK.get(s["age_bucket"], 0) > BUCKET_RANK.get(prev[0], 0):
            snaps[s["media_id"]] = (s["age_bucket"], json.loads(s["metrics"]))
    db.close()

    excluded = load_exclusions()
    now = datetime.now(timezone.utc)
    candidates, rejections = [], []
    counts = {k: 0 for k in
              ("excluded_by_human", "too_young", "no_snapshot", "no_duration",
               "missing_metrics", "zero_views", "failed_gate")}

    for r in rows:
        media_id = r["media_id"]
        posted = datetime.fromisoformat(r["posted_at"].replace("+0000", "+00:00"))
        age_days = (now - posted).total_seconds() / 86400

        def drop(reason, detail=""):
            counts[reason] += 1
            rejections.append({"media_id": media_id, "posted": r["posted_at"][:10],
                               "reason": reason, "detail": detail})

        # Human exclusions come first: never spend API calls or reasoning on a
        # reel that must not be republished whatever its numbers say.
        if media_id in excluded:
            e = excluded[media_id]
            counts["excluded_by_human"] += 1
            rejections.append({"media_id": media_id, "posted": r["posted_at"][:10],
                               "reason": "excluded_by_human", "record": e,
                               "detail": f"{e.get('reason','')}: {e.get('note','')}"})
            continue

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
        p_score, p_hits = promo_flag(r["caption"])
        candidates.append({
            "media_id": media_id,
            "caption": (r["caption"] or "").strip(),
            "promo_score": p_score, "promo_hits": p_hits,
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
    L.append(f"| — **excluded by hand** (never repost) | −{counts['excluded_by_human']} |")
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
            if c["promo_score"] >= 1:
                link += " ⚠"
            L.append(
                f"| {i} | {c['posted']} | {link} | {c['views']:,} | {c['shares']:,} | "
                f"{c['saved']:,} | {c['likes']:,} | {c['reach']:,} | {c['duration_s']:.1f} | "
                f"{c['watch_s']:.1f} | {c['sends_rate']*100:.3f}% | {c['n_sends']:.3f} | "
                f"{c['retention']:.3f} | {c['n_retention']:.3f} | "
                f"{c['saves_rate']*100:.3f}% | {c['n_saves']:.3f} | **{c['score']:.4f}** |")
        L.append("")

    flagged = [c for c in ranked[:top_n] if c["promo_score"] >= 1]
    L.append("## ⚠ Confirm before publishing\n")
    if not flagged:
        L.append(f"None of the top {min(top_n, n)} trip the event-promotion detector.\n")
    else:
        L.append(f"{len(flagged)} of the top {min(top_n, n)} use forward-looking language. "
                 "A reposted event promo tells people a gig is happening that already "
                 "happened — check these before they go anywhere, and add any real promo "
                 "to `data/repost-exclusions.json` so it never surfaces again.\n")
        L.append("| # | Posted | Reel | Signals | Caption |")
        L.append("|---:|---|---|---|---|")
        for c in flagged:
            rank = ranked.index(c) + 1
            cap = " ".join(c["caption"].split())[:110]
            L.append(f"| {rank} | {c['posted']} | {c['media_id'][-6:]} | "
                     f"{', '.join(c['promo_hits'])} | {cap} |")
        L.append("")
    L.append("> The detector reads **forward-looking language only** — *tomorrow*, "
             "*see you there*, a date paired with a time. Venue @mentions are "
             "deliberately ignored: 36 of 141 reels carry one and most are past-tense "
             "recaps, which are exactly the good repost material. It flags for review "
             "and **never excludes on its own** — a false positive would quietly drop a "
             "good candidate with nothing to show for it.\n")

    manual = [r for r in rejections if r["reason"] == "excluded_by_human"]
    if manual:
        recs = [(r_, r_.get("record", {})) for r_ in
                sorted(manual, key=lambda x: x["posted"], reverse=True)]
        pending = [(r_, e) for r_, e in recs if e.get("video_may_be_reusable")]
        permanent = [(r_, e) for r_, e in recs if not e.get("video_may_be_reusable")]

        L.append(f"## Excluded ({len(manual)})\n")
        L.append("From [`data/repost-exclusions.json`](../data/repost-exclusions.json), "
                 "versioned in git rather than in the gitignored database so it survives "
                 "every backfill rebuild.\n")

        if permanent:
            L.append(f"### Permanent — the footage is the advert ({len(permanent)})\n")
            L.append("| Posted | Reel | By | Why |")
            L.append("|---|---|---|---|")
            for r_, e in permanent:
                L.append(f"| {r_['posted']} | [{r_['media_id'][-6:]}]({e.get('permalink','')}) "
                         f"| {e.get('added_by','')} | {e.get('note','')} |")
            L.append("")

        if pending:
            L.append(f"### ⏳ Caption was dated, footage may be fine ({len(pending)})\n")
            L.append("**These are candidates on hold, not rejects.** A repost gets a new "
                     "caption anyway, so if the footage carries no on-screen date, venue "
                     "card or poster frame, the reel is repostable — delete its entry from "
                     "the exclusions file and it re-enters the queue on the next run. "
                     "Held out until then because reposting a real promotion misinforms "
                     "people about a live date, and that is worse than a delayed "
                     "candidate.\n")
            L.append("| Posted | Reel | dur | Why it is held | What to check |")
            L.append("|---|---|---:|---|---|")
            for r_, e in pending:
                dur = e.get("duration_s")
                L.append(f"| {r_['posted']} | [{r_['media_id'][-6:]}]({e.get('permalink','')}) "
                         f"| {dur if dur else '—'}s | {e.get('note','')} "
                         f"| {e.get('action_needed','')} |")
            L.append("")

    reviewed = []
    if EXCLUSIONS.exists():
        reviewed = json.loads(EXCLUSIONS.read_text()).get("reviewed_not_excluded", [])
    if reviewed:
        L.append(f"### Reviewed and kept ({len(reviewed)})\n")
        L.append("Flagged by the detector, checked, and left in the queue — recorded so "
                 "the same reel is not re-litigated every week.\n")
        L.append("| Posted | Reel | Flagged as | Verdict |")
        L.append("|---|---|---|---|")
        for x in reviewed:
            L.append(f"| {x.get('posted','')} | [{x['media_id'][-6:]}]({x.get('permalink','')}) "
                     f"| {x.get('flagged_as','')} | {x.get('note','')} |")
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
    L.append("| `is_seasonal` | **Partly handled.** Event promotion — the case that "
             "actually matters, since reposting one misinforms people about a live "
             "date — is caught by the hand-maintained exclusion list plus the ⚠ "
             "detector above. Genuine seasonal content (holidays, anniversaries) "
             "still needs Studio tagging. |")
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
    print(f"  dropped: {c['excluded_by_human']} excluded by hand, "
          f"{c['too_young']} too young, {c['failed_gate']} failed gate, "
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
        flagged = [x for x in ranked[:args.top] if x["promo_score"] >= 1]
        if flagged:
            print(f"\n  {len(flagged)} of the top {min(args.top, len(ranked))} flagged for "
                  f"review (possible event promotion) -- see the report")
    print(f"\n  -> {out}\n")


if __name__ == "__main__":
    main()
