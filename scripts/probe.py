#!/usr/bin/env python3
"""
Phase 0 capability probe.

Answers, against the live account, the four things the operating plan flags as
unverified -- then writes data/capabilities.json so every later script reads
facts instead of assumptions.

Nothing here publishes, deletes, or modifies anything. The one write-shaped call
(the trial_params check) is deliberately built to fail before a container is
created; see probe_trial_params().

Usage:
    export IG_ACCESS_TOKEN=...
    python scripts/probe.py

Stdlib only -- no pip install, runs anywhere python3 does.
"""

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

# Newest first. The probe walks down until one answers, so we never hardcode a
# guess about which version this account is on.
CANDIDATE_VERSIONS = ["v26.0", "v25.0", "v24.0", "v23.0", "v22.0", "v21.0"]

# Probed one at a time, because "which of these actually return data" IS the
# answer we need -- asking for all of them at once just fails as a batch.
CANDIDATE_MEDIA_METRICS = [
    "reach", "views", "likes", "comments", "shares", "saved",
    "total_interactions", "profile_visits", "follows",
    "ig_reels_avg_watch_time", "ig_reels_video_view_total_time",
    "plays", "impressions", "video_views",
]

CANDIDATE_ACCOUNT_METRICS = [
    "reach", "views", "profile_views", "website_clicks",
    "accounts_engaged", "total_interactions", "follower_count",
]

TIMEOUT = 30


# ---------------------------------------------------------------- http


def call(version, path, params, token, method="GET"):
    """Return (ok, payload). Graph API errors come back as payloads, not raises."""
    params = dict(params or {})
    params["access_token"] = token
    url = f"https://graph.facebook.com/{version}/{path.lstrip('/')}"

    try:
        if method == "GET":
            req = urllib.request.Request(f"{url}?{urllib.parse.urlencode(params)}")
        else:
            body = urllib.parse.urlencode(params).encode()
            req = urllib.request.Request(url, data=body, method=method)
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return True, json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        try:
            return False, json.loads(exc.read().decode())
        except Exception:
            return False, {"error": {"message": f"HTTP {exc.code}", "code": exc.code}}
    except Exception as exc:
        # Never reached Graph at all -- DNS, TLS, proxy, offline. Tagged so
        # callers don't misreport a blocked network as a bad token.
        return False, {"error": {"message": str(exc), "code": None}, "__transport__": True}


def err_text(payload):
    e = payload.get("error", {}) if isinstance(payload, dict) else {}
    parts = [e.get("message", "unknown error")]
    if e.get("error_user_msg"):
        parts.append(e["error_user_msg"])
    return " | ".join(str(p) for p in parts)


# ---------------------------------------------------------------- steps


def detect_version(token):
    """Returns (version, None) or (None, reason). Distinguishes 'network cannot
    reach Graph' from 'Graph answered and rejected the token' -- those need
    completely different fixes and look identical if you only check for success."""
    last_api_error = None
    for version in CANDIDATE_VERSIONS:
        ok, payload = call(version, "me", {"fields": "id"}, token)
        if ok:
            return version, None
        if payload.get("__transport__"):
            return None, ("network: cannot reach graph.facebook.com -- "
                          f"{err_text(payload)}\n  Check proxy/firewall. Corporate and "
                          "sandboxed networks frequently block Meta endpoints outright.")
        last_api_error = err_text(payload)
    return None, f"token: Graph answered but rejected the token on every version -- {last_api_error}"


def resolve_account(version, token):
    """
    Two login flavours produce two token shapes:
      - Instagram API with Instagram Login -> /me IS the IG account
      - Facebook Login for Business        -> /me is a user; walk to the Page
    Try direct first, then the Page hop.
    """
    ok, me = call(
        version, "me",
        {"fields": "id,username,account_type,followers_count,media_count"},
        token,
    )
    if ok and me.get("username"):
        return {"route": "instagram_login", "ig_user_id": me["id"], **me}, None

    ok, pages = call(
        version, "me/accounts",
        {"fields": "id,name,instagram_business_account{id,username,followers_count,media_count}"},
        token,
    )
    if not ok:
        return None, err_text(pages)

    for page in pages.get("data", []):
        iba = page.get("instagram_business_account")
        if iba:
            return {
                "route": "facebook_login",
                "page_id": page["id"],
                "page_name": page.get("name"),
                "ig_user_id": iba["id"],
                "username": iba.get("username"),
                "followers_count": iba.get("followers_count"),
                "media_count": iba.get("media_count"),
            }, None

    return None, "Token is valid but no Instagram Business account is linked to any Page."


def newest_reel(version, ig_user_id, token):
    ok, payload = call(
        version, f"{ig_user_id}/media",
        {"fields": "id,media_type,media_product_type,timestamp,permalink", "limit": 25},
        token,
    )
    if not ok:
        return None, err_text(payload)
    media = payload.get("data", [])
    if not media:
        return None, "Account has no media yet -- post one reel, then re-run."
    reels = [m for m in media if m.get("media_product_type") == "REELS"]
    return (reels or media)[0], None


def probe_metrics(version, node, candidates, token, extra=None):
    """One request per metric. Slow, but it tells us exactly which ones exist."""
    supported, unsupported = [], {}
    for metric in candidates:
        params = {"metric": metric}
        if extra:
            params.update(extra)
        ok, payload = call(version, f"{node}/insights", params, token)
        if ok and payload.get("data"):
            supported.append(metric)
        else:
            unsupported[metric] = err_text(payload)
    return supported, unsupported


def probe_trial_params(version, ig_user_id, token):
    """
    Does the Content Publishing API accept trial_params on this account?

    We send a deliberately unreachable video_url. Two outcomes, and they are
    distinguishable, which is the whole point:

      - Graph rejects trial_params itself  -> the parameter is not supported
      - Graph accepts the params and fails fetching the video -> it IS supported

    Either way no container is created and nothing is published.
    """
    sentinel = "https://example.invalid/third-stream-probe.mp4"
    ok, payload = call(
        version, f"{ig_user_id}/media",
        {
            "media_type": "REELS",
            "video_url": sentinel,
            "caption": "probe -- not published",
            "trial_params": json.dumps({"graduation_strategy": "MANUAL"}),
        },
        token,
        method="POST",
    )

    if ok:
        # Unexpected: a container came back. Report it so it can be left to expire.
        return {
            "supported": True,
            "confidence": "high",
            "note": "Container was created unexpectedly. Do NOT publish it; "
                    "unpublished containers expire on their own within 24h.",
            "container_id": payload.get("id"),
        }

    msg = err_text(payload).lower()
    rejected_param = any(
        token_ in msg for token_ in ("trial_params", "graduation_strategy", "trial")
    )
    if rejected_param:
        return {"supported": False, "confidence": "high",
                "note": "Graph rejected trial_params by name.", "raw": err_text(payload)}

    fetch_failed = any(
        token_ in msg for token_ in
        ("download", "fetch", "media", "url", "curl", "unsupported format", "timed out")
    )
    if fetch_failed:
        return {"supported": True, "confidence": "high",
                "note": "trial_params passed validation; only the sentinel video URL failed. "
                        "That is the expected signal.", "raw": err_text(payload)}

    return {"supported": None, "confidence": "low",
            "note": "Inconclusive -- read raw and judge manually.", "raw": err_text(payload)}


def token_info(version, token):
    ok, payload = call(version, "debug_token", {"input_token": token}, token)
    if not ok:
        return {"introspection": "unavailable", "note": err_text(payload)}
    data = payload.get("data", {})
    expires = data.get("expires_at")
    out = {
        "type": data.get("type"),
        "app_id": data.get("app_id"),
        "scopes": data.get("scopes", []),
        "expires_at": expires,
    }
    if expires:
        dt = datetime.fromtimestamp(expires, tz=timezone.utc)
        out["expires_at_iso"] = dt.isoformat()
        out["days_remaining"] = round((dt - datetime.now(timezone.utc)).total_seconds() / 86400, 1)
    elif expires == 0:
        out["expires_at_iso"] = "never"
    return out


# ---------------------------------------------------------------- report


def line(label, value, indent=2):
    print(f"{' ' * indent}{label:<34}{value}")


def main():
    token = os.environ.get("IG_ACCESS_TOKEN", "").strip()
    if not token:
        sys.exit("IG_ACCESS_TOKEN is not set. See docs/phase-0-setup.md step 5.")

    print("\n\033[1mThird Stream -- Phase 0 capability probe\033[0m")
    print("=" * 62)

    version, reason = detect_version(token)
    if not version:
        sys.exit(f"\n[1/6] FAILED -- {reason}\n\n"
                 "If the reason starts with 'token', re-run step 5 of docs/phase-0-setup.md.\n"
                 "If it starts with 'network', run this from your PC or the VPS instead.")
    print(f"\n[1/6] Graph API version    {version}")

    account, error = resolve_account(version, token)
    if error:
        sys.exit(f"\n[2/6] Account resolution FAILED\n  {error}")
    ig_user_id = account["ig_user_id"]
    followers = account.get("followers_count")
    print(f"[2/6] Account resolved     @{account.get('username')}  ({account['route']})")
    line("instagram user id", ig_user_id)
    line("account_type", account.get("account_type", "-- (via Page)"))
    line("followers_count", followers if followers is not None else "not returned")
    line("media_count", account.get("media_count", "not returned"))

    gate_ok = followers is None or followers >= 1000
    if not gate_ok:
        print(f"\n  \033[33mGATE: {followers} followers. Trial Reels and the Insights API "
              f"both require 1,000.\n  The rest of this probe will mostly fail -- that is expected, "
              f"not a bug.\033[0m")

    print("\n[3/6] Token")
    tinfo = token_info(version, token)
    for k, v in tinfo.items():
        line(k, v if not isinstance(v, list) else ", ".join(v) or "(none)")

    print("\n[4/6] Media insights -- probing one metric at a time")
    reel, error = newest_reel(version, ig_user_id, token)
    media_supported, media_unsupported = [], {}
    if error:
        print(f"  could not fetch media: {error}")
    else:
        print(f"  test media: {reel['id']}  ({reel.get('media_product_type', reel.get('media_type'))}, "
              f"{reel.get('timestamp', '')[:10]})")
        media_supported, media_unsupported = probe_metrics(
            version, reel["id"], CANDIDATE_MEDIA_METRICS, token
        )
        print(f"\n  \033[32msupported ({len(media_supported)}):\033[0m {', '.join(media_supported) or 'none'}")
        print(f"  \033[2munsupported ({len(media_unsupported)}):\033[0m {', '.join(media_unsupported) or 'none'}")

    print("\n[5/6] Account insights")
    acct_supported, acct_unsupported = probe_metrics(
        version, ig_user_id, CANDIDATE_ACCOUNT_METRICS, token, extra={"period": "day"}
    )
    print(f"  \033[32msupported ({len(acct_supported)}):\033[0m {', '.join(acct_supported) or 'none'}")

    print("\n[6/6] trial_params support  (no container is published)")
    trial = probe_trial_params(version, ig_user_id, token)
    verdict = {True: "\033[32mSUPPORTED\033[0m",
               False: "\033[31mNOT SUPPORTED\033[0m",
               None: "\033[33mINCONCLUSIVE\033[0m"}[trial["supported"]]
    line("verdict", verdict)
    line("confidence", trial["confidence"])
    print(f"  note: {trial['note']}")
    if trial.get("raw"):
        print(f"  raw:  {trial['raw']}")

    # ---- the four questions from operating-plan.md section 14
    scorer_inputs = {"shares", "saved", "profile_visits", "ig_reels_avg_watch_time", "reach"}
    have = scorer_inputs & set(media_supported)
    missing = scorer_inputs - set(media_supported)

    caps = {
        "probed_at": datetime.now(timezone.utc).isoformat(),
        "graph_version": version,
        "account": account,
        "token": tinfo,
        "gates": {
            "followers_1000": gate_ok,
            "scorer_inputs_available": sorted(have),
            "scorer_inputs_missing": sorted(missing),
        },
        "media_metrics": {"supported": media_supported, "unsupported": media_unsupported},
        "account_metrics": {"supported": acct_supported, "unsupported": acct_unsupported},
        "trial_params": trial,
    }

    out = Path(__file__).resolve().parent.parent / "data" / "capabilities.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(caps, indent=2))

    print("\n" + "=" * 62)
    print("\033[1mVERDICT\033[0m\n")
    line("Q1  trial_params usable",
         {True: "yes -- build the API path",
          False: "no  -- build the assisted-manual fallback",
          None: "unclear -- inspect raw above"}[trial["supported"]], indent=2)
    line("Q2  followers gate", "passed" if gate_ok else f"BLOCKED at {followers}")
    line("Q3  scorer inputs",
         "all present" if not missing else f"MISSING {', '.join(sorted(missing))}")
    line("Q4  token lifetime",
         f"{tinfo.get('days_remaining', '?')} days" if tinfo.get("days_remaining")
         else tinfo.get("expires_at_iso", "unknown"))
    print(f"\nWritten to {out}")
    print("Next: python scripts/backfill.py\n")


if __name__ == "__main__":
    main()
