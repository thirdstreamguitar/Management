#!/usr/bin/env python3
"""
Phase 0 insights backfill + ongoing snapshot job.

Reads data/capabilities.json (written by probe.py) so it only ever requests
metrics this account actually supports -- no hardcoded metric list to rot.

Pulls every post into data/posts.db and records an insight snapshot bucketed by
POST AGE, not wall-clock. Snapshots are never overwritten: we want the curve.
A reel still gaining reach on day 14 is evergreen and a repost candidate; one
that spiked and died on day 2 is not. Only the curve separates them.

Usage:
    export IG_ACCESS_TOKEN=...
    python scripts/backfill.py            # incremental, safe to run hourly
    python scripts/backfill.py --full     # re-walk all history

Stdlib only.
"""

import argparse
import json
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from probe import call, err_text, load_dotenv  # noqa: E402  (same-dir helper reuse)

import os  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "posts.db"
CAPS = ROOT / "data" / "capabilities.json"

# Age buckets, in hours. A snapshot is claimed by the newest bucket the post has
# passed. Each (media, bucket) pair is written exactly once.
BUCKETS = [("6h", 6), ("24h", 24), ("72h", 72), ("7d", 168), ("30d", 720)]

MEDIA_FIELDS = (
    "id,media_type,media_product_type,caption,permalink,timestamp,"
    "thumbnail_url,media_url,like_count,comments_count"
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS media (
  media_id      TEXT PRIMARY KEY,
  media_type    TEXT,
  product_type  TEXT,
  permalink     TEXT,
  caption       TEXT,
  posted_at     TEXT,
  duration_s    REAL,
  library_ref   TEXT,
  is_trial      INTEGER DEFAULT 0,
  parent_media  TEXT,
  variant_axis  TEXT,
  variant_note  TEXT,
  first_seen    TEXT
);

CREATE TABLE IF NOT EXISTS snapshots (
  media_id    TEXT NOT NULL,
  age_bucket  TEXT NOT NULL,
  captured_at TEXT NOT NULL,
  metrics     TEXT NOT NULL,          -- json blob: whatever this account supports
  PRIMARY KEY (media_id, age_bucket)
);

CREATE TABLE IF NOT EXISTS account_snapshots (
  captured_at TEXT PRIMARY KEY,
  metrics     TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_media_posted  ON media(posted_at);
CREATE INDEX IF NOT EXISTS idx_snap_bucket   ON snapshots(age_bucket);
"""


def load_caps():
    if not CAPS.exists():
        sys.exit(f"{CAPS} not found. Run scripts/probe.py first.")
    caps = json.loads(CAPS.read_text())
    metrics = caps["media_metrics"]["supported"]
    if not metrics:
        sys.exit("probe.py found no supported media metrics. Fix that before backfilling.")
    return caps, metrics


def age_bucket(posted_at):
    """Newest bucket this post has aged past, or None if younger than 6h."""
    posted = datetime.fromisoformat(posted_at.replace("+0000", "+00:00"))
    hours = (datetime.now(timezone.utc) - posted).total_seconds() / 3600
    claimed = None
    for name, threshold in BUCKETS:
        if hours >= threshold:
            claimed = name
    return claimed


def walk_media(host, version, ig_user_id, token, stop_at=None):
    """Page through /media newest-first. Stops early on incremental runs."""
    path, params = f"{ig_user_id}/media", {"fields": MEDIA_FIELDS, "limit": 50}
    seen = 0
    while True:
        ok, payload = call(host, version, path, params, token)
        if not ok:
            print(f"  ! media page failed: {err_text(payload)}")
            return
        batch = payload.get("data", [])
        for item in batch:
            if stop_at and item["id"] == stop_at:
                print(f"  reached last-known post after {seen} items -- stopping")
                return
            seen += 1
            yield item
        after = payload.get("paging", {}).get("cursors", {}).get("after")
        if not after or not batch:
            return
        params = {"fields": MEDIA_FIELDS, "limit": 50, "after": after}
        time.sleep(0.25)  # be a good citizen; we are nowhere near the rate limit


def _values(payload):
    out = {}
    for e in payload.get("data", []):
        vals = e.get("values") or []
        if vals:
            out[e["name"]] = vals[0].get("value")
        elif e.get("total_value") is not None:
            out[e["name"]] = e["total_value"].get("value")
    return out


def fetch_insights(host, version, media_id, metrics, shapes, token):
    """
    Ask for everything at once; on rejection, fall back to one-by-one so a
    single unsupported metric on one media type cannot blank the whole row.

    `shapes` comes from capabilities.json and records which request form each
    metric answered to during the probe -- plain, or metric_type=total_value.
    Metrics of different shapes cannot be batched, so they are grouped.
    """
    plain = [m for m in metrics if shapes.get(m, "plain") == "plain"]
    totals = [m for m in metrics if shapes.get(m) == "total_value"]

    out = {}
    for group, extra in ((plain, {}), (totals, {"metric_type": "total_value"})):
        if not group:
            continue
        ok, payload = call(host, version, f"{media_id}/insights",
                           {"metric": ",".join(group), **extra}, token)
        if ok:
            out.update(_values(payload))
            continue
        for metric in group:
            ok, payload = call(host, version, f"{media_id}/insights",
                               {"metric": metric, **extra}, token)
            if ok:
                out.update(_values(payload))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--full", action="store_true",
                    help="re-walk all history instead of stopping at the newest known post")
    args = ap.parse_args()

    load_dotenv()
    token = os.environ.get("IG_ACCESS_TOKEN", "").strip()
    if not token:
        sys.exit("IG_ACCESS_TOKEN is not set (checked .env and the environment).")

    caps, metrics = load_caps()
    version = caps["graph_version"]
    host = caps.get("host", "graph.facebook.com")
    shapes = caps["media_metrics"].get("request_shape", {})
    ig_user_id = caps["account"]["ig_user_id"]
    acct_metrics = caps["account_metrics"]["supported"]
    acct_shapes = caps["account_metrics"].get("request_shape", {})

    DB.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DB)
    db.executescript(SCHEMA)

    print(f"\nBackfill -- @{caps['account'].get('username')} on {host} {version}")
    print(f"metrics: {', '.join(metrics)}\n")

    stop_at = None
    if not args.full:
        row = db.execute("SELECT media_id FROM media ORDER BY posted_at DESC LIMIT 1").fetchone()
        stop_at = row[0] if row else None

    now = datetime.now(timezone.utc).isoformat()
    new_media = snaps_written = skipped = 0

    for item in walk_media(host, version, ig_user_id, token, stop_at=stop_at):
        db.execute(
            """INSERT INTO media (media_id, media_type, product_type, permalink,
                                  caption, posted_at, first_seen)
               VALUES (?,?,?,?,?,?,?)
               ON CONFLICT(media_id) DO UPDATE SET
                 caption=excluded.caption, permalink=excluded.permalink""",
            (item["id"], item.get("media_type"), item.get("media_product_type"),
             item.get("permalink"), item.get("caption"), item.get("timestamp"), now),
        )
        if db.total_changes:
            new_media += 1

        bucket = age_bucket(item["timestamp"])
        if not bucket:
            skipped += 1
            continue

        exists = db.execute(
            "SELECT 1 FROM snapshots WHERE media_id=? AND age_bucket=?",
            (item["id"], bucket),
        ).fetchone()
        if exists:
            continue

        values = fetch_insights(host, version, item["id"], metrics, shapes, token)
        if not values:
            continue
        # like_count / comments_count come free on the media node
        for k in ("like_count", "comments_count"):
            if item.get(k) is not None:
                values.setdefault(k, item[k])

        db.execute(
            "INSERT INTO snapshots (media_id, age_bucket, captured_at, metrics) VALUES (?,?,?,?)",
            (item["id"], bucket, now, json.dumps(values)),
        )
        snaps_written += 1
        if snaps_written % 10 == 0:
            db.commit()
            print(f"  {snaps_written} snapshots...")
        time.sleep(0.2)

    if acct_metrics:
        values = {}
        for metric in acct_metrics:
            params = {"metric": metric, "period": "day"}
            if acct_shapes.get(metric) == "total_value":
                params["metric_type"] = "total_value"
            ok, payload = call(host, version, f"{ig_user_id}/insights", params, token)
            if ok:
                values.update(_values(payload))
        if values:
            db.execute("INSERT OR REPLACE INTO account_snapshots VALUES (?,?)",
                       (now, json.dumps(values)))

    db.commit()

    total_media = db.execute("SELECT COUNT(*) FROM media").fetchone()[0]
    total_snaps = db.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0]
    by_bucket = dict(db.execute(
        "SELECT age_bucket, COUNT(*) FROM snapshots GROUP BY age_bucket").fetchall())

    print(f"\n  new media       {new_media}")
    print(f"  new snapshots   {snaps_written}")
    print(f"  too young (<6h) {skipped}")
    print(f"\n  db totals: {total_media} media, {total_snaps} snapshots")
    print(f"  by bucket: {', '.join(f'{k}={v}' for k, v in sorted(by_bucket.items())) or 'none'}")
    print(f"\n  -> {DB}\n")
    db.close()


if __name__ == "__main__":
    main()
