#!/usr/bin/env python3
"""
Measure and extend the Instagram long-lived token.

This is the only way to learn a token's expiry on the Instagram Login route:
graph.instagram.com has no debug_token, and /refresh_access_token both reports
`expires_in` AND issues a fresh 60-day token. Reading the number is therefore
inseparable from changing the token, which is why probe.py refuses to do it and
this exists as a separate, explicit command.

Safety, in order:
  1. refuses to run without --yes
  2. backs up .env before touching it (.env.* is gitignored)
  3. VERIFIES the new token with a live call before writing it anywhere
  4. writes only the IG_ACCESS_TOKEN line, preserving comments and other keys
  5. never prints any token

If anything fails, .env is left exactly as it was and the old token stays valid.

Usage:
    python scripts/refresh_token.py            # explains, changes nothing
    python scripts/refresh_token.py --yes      # actually refresh
"""

import argparse
import json
import os
import shutil
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from probe import load_dotenv  # noqa: E402

HOST = "graph.instagram.com"
TIMEOUT = 30


def get_json(url):
    try:
        with urllib.request.urlopen(url, timeout=TIMEOUT) as resp:
            return True, json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        try:
            return False, json.loads(exc.read().decode())
        except Exception:
            return False, {"error": {"message": f"HTTP {exc.code}"}}
    except Exception as exc:
        return False, {"error": {"message": str(exc)}, "__transport__": True}


def find_env():
    here = Path(__file__).resolve().parent
    for candidate in (here.parent / ".env", here / ".env", Path.cwd() / ".env"):
        if candidate.exists():
            return candidate
    return None


def rewrite_env(path, new_token):
    """Replace only the IG_ACCESS_TOKEN value. Comments and other keys survive."""
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    out, replaced = [], False
    for line in lines:
        if line.strip().startswith("IG_ACCESS_TOKEN") and "=" in line and not replaced:
            out.append(f"IG_ACCESS_TOKEN={new_token}")
            replaced = True
        else:
            out.append(line)
    if not replaced:
        out.append(f"IG_ACCESS_TOKEN={new_token}")
    path.write_text("\n".join(out) + "\n", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--yes", action="store_true",
                    help="actually perform the refresh (it changes your token)")
    args = ap.parse_args()

    env_path = find_env()
    load_dotenv()
    token = os.environ.get("IG_ACCESS_TOKEN", "").strip()
    if not token:
        sys.exit("IG_ACCESS_TOKEN is not set (checked .env and the environment).")

    print("\nInstagram token refresh")
    print("=" * 62)
    print(f"  .env: {env_path or 'not found -- will not be able to save the new token'}")

    if not args.yes:
        print("""
  This command CHANGES YOUR TOKEN. It is the only way to read the expiry
  on the Instagram Login route -- the same call that reports `expires_in`
  also issues a new 60-day token.

  What happens with --yes:
    1. back up .env alongside itself (gitignored)
    2. request a refreshed token
    3. verify the new token works with a live call
    4. only then write it to .env
    5. print days remaining -- never the token itself

  Nothing is written unless step 3 passes.

  Run again with --yes when you are ready.
""")
        return

    if env_path is None:
        sys.exit("  Refusing to refresh: no .env found, so the new token would be lost.")

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    backup = env_path.with_name(f"{env_path.name}.backup-{stamp}")
    shutil.copy2(env_path, backup)
    print(f"  backed up to {backup.name}")

    print("\n  requesting refresh...")
    url = f"https://{HOST}/refresh_access_token?" + urllib.parse.urlencode(
        {"grant_type": "ig_refresh_token", "access_token": token})
    ok, payload = get_json(url)
    if not ok:
        err = payload.get("error", {})
        print(f"  FAILED -- {err.get('message', payload)}")
        print("  .env is unchanged and your existing token is untouched.")
        sys.exit(1)

    new_token = payload.get("access_token", "")
    expires_in = payload.get("expires_in")
    if not new_token:
        print(f"  FAILED -- response contained no access_token: {list(payload)}")
        print("  .env is unchanged.")
        sys.exit(1)

    print("  verifying the new token before writing it...")
    vurl = f"https://{HOST}/me?" + urllib.parse.urlencode(
        {"fields": "id,username", "access_token": new_token})
    vok, vpayload = get_json(vurl)
    if not vok:
        print(f"  FAILED verification -- {vpayload.get('error', {}).get('message')}")
        print("  .env is unchanged. Your OLD token is still in place and still valid.")
        sys.exit(1)
    print(f"  verified as @{vpayload.get('username')}")

    rewrite_env(env_path, new_token)

    days = round(expires_in / 86400, 1) if expires_in else None
    expiry = (datetime.now(timezone.utc) + timedelta(seconds=expires_in)) if expires_in else None

    print("\n" + "=" * 62)
    print("  token refreshed and saved")
    print(f"  expires_in     {expires_in} seconds")
    if days:
        print(f"  days remaining {days}")
    if expiry:
        print(f"  expires on     {expiry.date().isoformat()}")
    print(f"\n  old token preserved in {backup.name} -- delete it once you are happy.")
    print("  Re-run this before the expiry date. A dead token silently stops")
    print("  every downstream job, and you would not find out for weeks.\n")


if __name__ == "__main__":
    main()
