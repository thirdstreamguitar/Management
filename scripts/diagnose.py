#!/usr/bin/env python3
"""
Token diagnostic -- run this when probe.py reports "Cannot parse access token".

Checks the token in .env AND the one in the environment, reports what is
structurally wrong with either, and shows Graph's raw error. It never prints
the token: only its length, its first four characters (which identify the
token TYPE), and which forbidden characters it contains.

Usage:
    python scripts/diagnose.py
"""

import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent


def find_env():
    """Repo root is correct, but accept scripts/ and cwd too -- a .env in the
    wrong directory is a silent failure that looks exactly like a bad token."""
    for candidate in (ROOT / ".env", HERE / ".env", Path.cwd() / ".env"):
        if candidate.exists():
            return candidate
    return None

# A Meta access token is base64url: letters, digits, underscore, hyphen.
# Anything else in the string is the bug.
TOKEN_CHARS = re.compile(r"[A-Za-z0-9_\-]")

SUSPECTS = [
    ('"', "double quote"),
    ("'", "single quote"),
    (" ", "space"),
    ("\t", "tab"),
    ("\n", "newline"),
    ("\r", "carriage return"),
    ("﻿", "BOM (byte-order mark -- Notepad wrote this)"),
    ("“", "smart quote"),
    ("”", "smart quote"),
    ("…", "ellipsis -- the token was copied truncated"),
    ("...", "literal '...' -- the token was copied truncated"),
    ("=", "equals sign -- you may have copied 'IG_ACCESS_TOKEN=' too"),
]


def describe(label, value):
    print(f"\n  [{label}]")
    if not value:
        print("    not set")
        return None

    problems = []
    print(f"    length              {len(value)}")
    print(f"    first 4 chars       {value[:4]!r}")
    print(f"    last 2 chars        {value[-2:]!r}")

    if value != value.strip():
        problems.append("surrounding whitespace or a trailing newline")

    for ch, name in SUSPECTS:
        if ch in value:
            problems.append(f"contains {name}")

    clean = value.strip()
    bad = sorted({c for c in clean if not TOKEN_CHARS.match(c)})
    if bad:
        problems.append(f"illegal characters: {[repr(c) for c in bad]}")

    if clean.startswith("IGAA"):
        print("    token type          Instagram Login long-lived  <-- expected here")
    elif clean.startswith("EAA"):
        print("    token type          Facebook Login (also workable)")
    else:
        problems.append(
            "does not start with IGAA or EAA -- this is not an IG/FB access "
            "token. You have probably copied the App Secret, the App ID, or a "
            "token id from the wrong field."
        )

    if problems:
        for p in problems:
            print(f"    !! {p}")
    else:
        print("    structure           looks like a well-formed token")
    return clean


def read_env_file():
    env = find_env()
    if env is None:
        print(f"\n  .env not found. Looked in:")
        for c in (ROOT / ".env", HERE / ".env", Path.cwd() / ".env"):
            print(f"    {c}")
        return None
    print(f"\n  .env found: {env}  ({env.stat().st_size} bytes)")
    if env.parent != ROOT:
        print(f"    note: it belongs at {ROOT / '.env'} -- reading it here anyway")
    raw = env.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        print("    !! file begins with a UTF-8 BOM (Notepad). Save as UTF-8 "
              "without BOM, or use VS Code / Notepad++.")
    for line in raw.decode("utf-8-sig", errors="replace").splitlines():
        line = line.strip()
        if line.startswith("IG_ACCESS_TOKEN") and "=" in line:
            return line.partition("=")[2].strip().strip('"').strip("'")
    print("    !! no IG_ACCESS_TOKEN= line found in .env")
    return None


def live_check(token):
    """One real call. Shows Graph's verbatim error, including subcode."""
    url = "https://graph.facebook.com/v21.0/me?" + urllib.parse.urlencode(
        {"fields": "id,username", "access_token": token}
    )
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            data = json.loads(resp.read().decode())
            print(f"    ACCEPTED -- Graph resolved this token to id {data.get('id')}")
            return True
    except urllib.error.HTTPError as exc:
        try:
            err = json.loads(exc.read().decode()).get("error", {})
        except Exception:
            err = {}
        print(f"    REJECTED -- HTTP {exc.code}")
        for key in ("message", "type", "code", "error_subcode", "error_user_msg"):
            if err.get(key) is not None:
                print(f"      {key:<16}{err[key]}")
        sub = err.get("error_subcode")
        if err.get("code") == 190 and not sub:
            print("\n      code 190 with no subcode = the string is not parseable as a\n"
                  "      token at all. It is malformed or it is not a token.")
        elif sub == 463:
            print("\n      subcode 463 = the token EXPIRED. Generate a new one.")
        elif sub == 467:
            print("\n      subcode 467 = the token was INVALIDATED (password change,\n"
                  "      or you regenerated it). Generate a new one.")
        return False
    except Exception as exc:
        print(f"    NETWORK FAILURE -- could not reach graph.facebook.com: {exc}")
        print("    This machine cannot talk to Meta. Nothing else will work here.")
        return None


def main():
    print("\nThird Stream -- token diagnostic")
    print("=" * 62)

    file_token = read_env_file()
    env_token = os.environ.get("IG_ACCESS_TOKEN")

    f = describe(".env file", file_token)
    e = describe("environment variable", env_token)

    if f and e and f != e:
        print("\n  !! .env and the environment variable DISAGREE.")
        print("     probe.py uses the environment variable when one is set, so the")
        print("     .env edit you made is being ignored. Open a fresh terminal, or")
        print("     clear it with:  Remove-Item Env:IG_ACCESS_TOKEN")

    chosen = e or f
    if not chosen:
        sys.exit("\n  No token found in either place. Nothing to test.\n")

    source = "environment variable" if e else ".env file"
    print(f"\n  [live check -- using the {source}]")
    live_check(chosen)
    print()


if __name__ == "__main__":
    main()
