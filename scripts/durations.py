#!/usr/bin/env python3
"""
Fill in media duration -- the scorer's missing denominator.

The retention term is avg_watch_time / duration, and no Instagram media field
returns a duration. But the API does return `media_url`, a direct link to the
video file, and an MP4 carries its own duration in the `mvhd` box inside `moov`.
So we read the header over HTTP range requests -- typically 32-64 KB per video,
not the whole file -- and write the result into data/posts.db.

This is why the library/ mapping turned out to be unnecessary: the duration is
in the file Instagram is already serving.

Stdlib only. ffprobe is used as a fallback if it happens to be installed and the
header parse fails; it is not required.

Usage:
    python scripts/durations.py              # reels only (the repost pool)
    python scripts/durations.py --all-video  # every VIDEO media, incl. FEED
    python scripts/durations.py --limit 20   # try a handful first
"""

import argparse
import json
import os
import shutil
import sqlite3
import struct
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from probe import call, err_text, load_dotenv  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "posts.db"
CAPS = ROOT / "data" / "capabilities.json"

HEAD_BYTES = 96 * 1024      # usually enough: faststart files put moov up front
TAIL_BYTES = 512 * 1024     # fallback when moov sits at the end
TIMEOUT = 30


# ---------------------------------------------------------------- mp4


def _fetch_range(url, start, length):
    req = urllib.request.Request(url, headers={"Range": f"bytes={start}-{start + length - 1}"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return resp.read()


def _fetch_tail(url, length):
    """Servers ignore negative ranges inconsistently; ask for suffix explicitly."""
    req = urllib.request.Request(url, headers={"Range": f"bytes=-{length}"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return resp.read()


def _iter_boxes(buf, offset=0, end=None):
    """Yield (type, payload_start, payload_end) for top-level boxes in buf."""
    end = len(buf) if end is None else end
    while offset + 8 <= end:
        size = struct.unpack(">I", buf[offset:offset + 4])[0]
        btype = buf[offset + 4:offset + 8]
        header = 8
        if size == 1:                                    # 64-bit largesize
            if offset + 16 > end:
                return
            size = struct.unpack(">Q", buf[offset + 8:offset + 16])[0]
            header = 16
        elif size == 0:                                  # extends to EOF
            size = end - offset
        if size < header:
            return
        yield btype, offset + header, offset + size
        offset += size


def _mvhd_seconds(buf, start, end):
    """mvhd: version/flags, then times, timescale, duration. v1 uses 64-bit."""
    if start + 4 > end:
        return None
    version = buf[start]
    p = start + 4
    if version == 1:
        p += 16                                          # created + modified (8+8)
        if p + 12 > end:
            return None
        timescale = struct.unpack(">I", buf[p:p + 4])[0]
        duration = struct.unpack(">Q", buf[p + 4:p + 12])[0]
    else:
        p += 8                                           # created + modified (4+4)
        if p + 8 > end:
            return None
        timescale = struct.unpack(">I", buf[p:p + 4])[0]
        duration = struct.unpack(">I", buf[p + 4:p + 8])[0]
    if not timescale or duration in (0, 0xFFFFFFFF, 0xFFFFFFFFFFFFFFFF):
        return None
    return round(duration / timescale, 3)


def _find_mvhd(buf):
    for btype, s, e in _iter_boxes(buf):
        if btype == b"moov":
            for sub, ss, se in _iter_boxes(buf, s, e):
                if sub == b"mvhd":
                    return _mvhd_seconds(buf, ss, se)
            return None
    return None


def duration_from_url(url):
    """(seconds, method) or (None, reason). Reads header bytes, not the file."""
    try:
        head = _fetch_range(url, 0, HEAD_BYTES)
    except Exception as exc:
        return None, f"range request failed: {exc}"

    secs = _find_mvhd(head)
    if secs:
        return secs, "moov@head"

    # moov may be at the end (non-faststart). Scan the tail for it.
    try:
        tail = _fetch_tail(url, TAIL_BYTES)
    except Exception as exc:
        return None, f"tail request failed: {exc}"
    idx = tail.rfind(b"moov")
    if idx >= 4:
        secs = _find_mvhd(tail[idx - 4:])
        if secs:
            return secs, "moov@tail"

    if shutil.which("ffprobe"):
        try:
            out = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                 "-of", "default=nw=1:nk=1", url],
                capture_output=True, text=True, timeout=60)
            if out.returncode == 0 and out.stdout.strip():
                return round(float(out.stdout.strip()), 3), "ffprobe"
        except Exception:
            pass

    return None, "no mvhd found (and ffprobe unavailable or failed)"


# ---------------------------------------------------------------- main


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--all-video", action="store_true",
                    help="include FEED videos, not just reels")
    ap.add_argument("--limit", type=int, help="only process the first N")
    ap.add_argument("--refresh", action="store_true",
                    help="re-read durations that are already stored")
    args = ap.parse_args()

    load_dotenv()
    token = os.environ.get("IG_ACCESS_TOKEN", "").strip()
    if not token:
        sys.exit("IG_ACCESS_TOKEN is not set (checked .env and the environment).")
    if not CAPS.exists():
        sys.exit(f"{CAPS} not found. Run scripts/probe.py first.")
    if not DB.exists():
        sys.exit(f"{DB} not found. Run scripts/backfill.py --full first.")

    caps = json.loads(CAPS.read_text())
    host, version = caps.get("host", "graph.instagram.com"), caps["graph_version"]

    db = sqlite3.connect(DB)
    where = "product_type='REELS'" if not args.all_video else "media_type='VIDEO'"
    if not args.refresh:
        where += " AND duration_s IS NULL"
    sql = f"SELECT media_id FROM media WHERE {where} ORDER BY posted_at DESC"
    if args.limit:
        sql += f" LIMIT {args.limit}"
    targets = [r[0] for r in db.execute(sql).fetchall()]

    scope = "all video" if args.all_video else "reels"
    print(f"\nDurations -- {len(targets)} {scope} to resolve on {host} {version}\n")
    if not targets:
        print("  nothing to do\n")
        return

    ok = failed = 0
    reasons = {}
    for i, media_id in enumerate(targets, 1):
        got, payload = call(host, version, media_id, {"fields": "media_url"}, token)
        if not got or not payload.get("media_url"):
            failed += 1
            reasons[media_id] = f"no media_url: {err_text(payload) if not got else 'field empty'}"
            continue

        secs, how = duration_from_url(payload["media_url"])
        if secs:
            db.execute("UPDATE media SET duration_s=? WHERE media_id=?", (secs, media_id))
            ok += 1
        else:
            failed += 1
            reasons[media_id] = how

        if i % 10 == 0:
            db.commit()
            print(f"  {i}/{len(targets)}  ok={ok} failed={failed}")
        time.sleep(0.2)

    db.commit()

    scope_sql = "media_type='VIDEO'" if args.all_video else "product_type='REELS'"
    total = db.execute(f"SELECT COUNT(*) FROM media WHERE {scope_sql}").fetchone()[0]
    have = db.execute(
        f"SELECT COUNT(*) FROM media WHERE {scope_sql} AND duration_s IS NOT NULL"
    ).fetchone()[0]

    print(f"\n  resolved   {ok}")
    print(f"  failed     {failed}")
    print(f"\n  coverage: {have}/{total} {scope} now have duration_s")

    if reasons:
        print("\n  first few failures:")
        for mid, why in list(reasons.items())[:5]:
            print(f"    {mid}  {why}")

    # A retention ratio needs both halves; report the pair, not just duration.
    pair = db.execute("""
        SELECT COUNT(*) FROM media m JOIN snapshots s ON s.media_id=m.media_id
        WHERE m.duration_s IS NOT NULL
          AND json_extract(s.metrics,'$.ig_reels_avg_watch_time') IS NOT NULL
    """).fetchone()[0]
    print(f"\n  retention ratio computable for {pair} media")
    print("  (ig_reels_avg_watch_time is MILLISECONDS -- divide by 1000 before "
          "dividing by duration_s)\n")
    db.close()


if __name__ == "__main__":
    main()
