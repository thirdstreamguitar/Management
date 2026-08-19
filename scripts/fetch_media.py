#!/usr/bin/env python3
"""
Pull source video files out of Instagram into the local library.

The library is the actual capital in this project (operating-plan.md section 13):
metrics can be re-pulled, a deleted original cannot. It is also what unblocks the
`source_file_exists` eligibility filter and every variant cut the Studio step needs.

Writes:
    library/{media_id}/original.mp4      the file itself, never modified
    library/{media_id}/metadata.json     caption, permalink, metrics at fetch time
and sets media.library_ref in posts.db so the scorer can see what exists on disk.

Usage:
    python scripts/fetch_media.py CvkGYUtvTiz          # permalink slug
    python scripts/fetch_media.py 17964979568555455    # media id
    python scripts/fetch_media.py --top 10             # top N of the repost queue
    python scripts/fetch_media.py --all-reels          # the whole reel catalogue
    python scripts/fetch_media.py CvkGYUtvTiz --force  # re-download

Must run where graph.instagram.com and scontent*.cdninstagram.com are reachable.
Both are blocked by egress policy in most hosted sandboxes, so this belongs on
your PC or the VPS. The script says which of the two failed rather than making
you guess.

Stdlib only.
"""

import argparse
import json
import os
import sqlite3
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from probe import call, err_text, load_dotenv          # noqa: E402
from durations import duration_from_url, _find_mvhd, _mvhd_seconds  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "posts.db"
LIBRARY = ROOT / "library"
CHUNK = 1 << 16
TIMEOUT = 120


def resolve(db, target):
    """Accept a media id, a permalink slug, or a full permalink. No API needed --
    the database already knows every reel we have ever seen."""
    row = db.execute("SELECT media_id, permalink, posted_at, duration_s, caption, "
                     "media_type, product_type FROM media WHERE media_id = ?",
                     (target,)).fetchone()
    if row:
        return row
    slug = target.rstrip("/").split("/")[-1] if "/" in target else target
    rows = db.execute("SELECT media_id, permalink, posted_at, duration_s, caption, "
                      "media_type, product_type FROM media WHERE permalink LIKE ?",
                      (f"%/{slug}/%",)).fetchall()
    if len(rows) == 1:
        return rows[0]
    if not rows:
        return None
    raise SystemExit(f"'{target}' matches {len(rows)} media. Use the media_id.")


def fresh_media_url(host, version, media_id, token):
    """Always re-fetch. Instagram's media_url is a signed CDN link that expires
    within hours, so caching it in the database would be a trap: the stale URL
    404s later and reads like an API failure rather than an expiry."""
    ok, payload = call(host, version, media_id, {"fields": "media_url"}, token)
    if not ok:
        return None, f"graph: {err_text(payload)}"
    url = payload.get("media_url")
    if not url:
        return None, "graph returned no media_url (pre-conversion media has none)"
    return url, None


def download(url, dest):
    """Stream to a .part file, then rename. A half-written original.mp4 that
    looks complete is worse than no file at all."""
    part = dest.with_suffix(dest.suffix + ".part")
    part.parent.mkdir(parents=True, exist_ok=True)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "third-stream-library/1.0"})
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp, open(part, "wb") as fh:
            total = int(resp.headers.get("Content-Length") or 0)
            got = 0
            while True:
                chunk = resp.read(CHUNK)
                if not chunk:
                    break
                fh.write(chunk)
                got += len(chunk)
                if total:
                    pct = got / total * 100
                    print(f"\r      {got/1e6:5.1f} / {total/1e6:.1f} MB  {pct:3.0f}%",
                          end="", flush=True)
        print("\r" + " " * 46 + "\r", end="")
        if total and got != total:
            part.unlink(missing_ok=True)
            return None, f"truncated: {got} of {total} bytes"
        part.replace(dest)
        return got, None
    except urllib.error.HTTPError as exc:
        part.unlink(missing_ok=True)
        return None, f"cdn: HTTP {exc.code}"
    except Exception as exc:
        part.unlink(missing_ok=True)
        return None, f"cdn: {exc}"


def local_duration(path):
    """Parse the downloaded file's own mvhd box. Verifies the bytes we got are a
    playable MP4 and match what the API reported -- catches a silent truncation
    that Content-Length alone would miss."""
    try:
        with open(path, "rb") as fh:
            head = fh.read(1 << 20)
            found = _find_mvhd(head)
            if found:
                return _mvhd_seconds(head, *found)
            fh.seek(max(0, path.stat().st_size - (1 << 20)))
            tail = fh.read()
            found = _find_mvhd(tail)
            if found:
                return _mvhd_seconds(tail, *found)
    except Exception:
        pass
    return None


def fetch_one(db, host, version, token, row, force=False):
    media_id = row["media_id"]
    folder = LIBRARY / media_id
    dest = folder / "original.mp4"
    label = f"{row['posted_at'][:10]}  {(row['permalink'] or '').rstrip('/').split('/')[-1] or media_id}"

    if dest.exists() and not force:
        print(f"  = {label}  already in library ({dest.stat().st_size/1e6:.1f} MB)")
        return "skipped"

    print(f"  > {label}")
    url, err = fresh_media_url(host, version, media_id, token)
    if err:
        print(f"      FAILED  {err}")
        return "failed"

    size, err = download(url, dest)
    if err:
        print(f"      FAILED  {err}")
        return "failed"

    secs = local_duration(dest)
    expected = row["duration_s"]
    note = ""
    if secs and expected and abs(secs - expected) > 1.0:
        note = f"  ⚠ duration {secs:.1f}s vs {expected:.1f}s recorded"
    elif secs:
        note = f"  {secs:.1f}s verified"

    snap = db.execute("SELECT metrics FROM snapshots WHERE media_id=? "
                      "ORDER BY captured_at DESC LIMIT 1", (media_id,)).fetchone()
    (folder / "metadata.json").write_text(json.dumps({
        "media_id": media_id,
        "permalink": row["permalink"],
        "posted_at": row["posted_at"],
        "media_type": row["media_type"],
        "product_type": row["product_type"],
        "duration_s_recorded": expected,
        "duration_s_verified": secs,
        "original_caption": row["caption"],
        "_caption_note": "Historical record. Never republish this text — a repost "
                         "gets a new caption (phase-1-repost-engine.md section 4).",
        "metrics_at_fetch": json.loads(snap["metrics"]) if snap else None,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "bytes": size,
    }, indent=2, ensure_ascii=False) + "\n")

    db.execute("UPDATE media SET library_ref=? WHERE media_id=?",
               (str(dest.relative_to(ROOT)), media_id))
    db.commit()
    print(f"      saved {size/1e6:.1f} MB -> {dest.relative_to(ROOT)}{note}")
    return "fetched"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("targets", nargs="*", help="media ids, permalink slugs, or URLs")
    ap.add_argument("--top", type=int, help="fetch the top N of the current repost queue")
    ap.add_argument("--all-reels", action="store_true", help="fetch every reel")
    ap.add_argument("--force", action="store_true", help="re-download even if present")
    args = ap.parse_args()

    if not (args.targets or args.top or args.all_reels):
        ap.error("give a target, --top N, or --all-reels")

    env_path = load_dotenv()
    token = os.environ.get("IG_ACCESS_TOKEN", "").strip()
    if not token:
        sys.exit("IG_ACCESS_TOKEN is not set. See docs/phase-0-setup.md.")
    if not DB.exists():
        sys.exit(f"{DB} not found. Run scripts/backfill.py first.")

    caps = json.loads((ROOT / "data" / "capabilities.json").read_text())
    # key name matches durations.py, so all scripts read the same field
    host = caps.get("host", "graph.instagram.com")
    version = caps["graph_version"]

    db = sqlite3.connect(DB)
    db.row_factory = sqlite3.Row

    rows = []
    if args.top:
        from scorer import load_candidates, score
        cands, _, _ = load_candidates(DB)
        ranked, _ = score(cands)
        for c in ranked[:args.top]:
            r = resolve(db, c["media_id"])
            if r:
                rows.append(r)
    if args.all_reels:
        rows += db.execute("SELECT media_id, permalink, posted_at, duration_s, caption, "
                           "media_type, product_type FROM media WHERE product_type='REELS' "
                           "ORDER BY posted_at DESC").fetchall()
    for t in args.targets:
        r = resolve(db, t)
        if not r:
            print(f"  ? '{t}' not found in posts.db — check the slug, or re-run backfill")
            continue
        rows.append(r)

    seen, unique = set(), []
    for r in rows:
        if r["media_id"] not in seen:
            seen.add(r["media_id"])
            unique.append(r)

    print(f"\nlibrary: {LIBRARY.relative_to(ROOT)}   source: {host} {version}"
          + (f"   env: {env_path}" if env_path else ""))
    print(f"{len(unique)} item{'s' if len(unique) != 1 else ''} to consider\n")

    tally = {"fetched": 0, "skipped": 0, "failed": 0}
    for i, r in enumerate(unique):
        tally[fetch_one(db, host, version, token, r, args.force)] += 1
        if i < len(unique) - 1:
            time.sleep(0.3)

    print(f"\n  fetched {tally['fetched']}   already had {tally['skipped']}   "
          f"failed {tally['failed']}")
    if tally["failed"]:
        print("\n  A 'graph:' failure is the API — check the token with scripts/probe.py.")
        print("  A 'cdn:' failure is the download — the signed URL expired or the")
        print("  network blocks scontent*.cdninstagram.com. Re-running gets a fresh URL.")
    total = sum(f.stat().st_size for f in LIBRARY.rglob("original.mp4")) if LIBRARY.exists() else 0
    n = len(list(LIBRARY.glob("*"))) if LIBRARY.exists() else 0
    print(f"  library now holds {n} item{'s' if n != 1 else ''}, {total/1e6:.0f} MB\n")
    db.close()


if __name__ == "__main__":
    main()
