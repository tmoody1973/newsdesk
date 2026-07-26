#!/usr/bin/env python3
"""Create the five B2 buckets from design spec §8, with correct visibility.

    b2 account authorize <keyID> <applicationKey>   # a key scoped to ALL buckets
    uv run python scripts/setup_buckets.py

Uses the b2 CLI rather than S3 CreateBucket for two reasons: the S3 API cannot
set B2's bucket type, and it rejects creation outright for keys scoped to a
single bucket. Idempotent — existing buckets are reported and left alone.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys

from newsdesk.config import BUCKETS, PUBLIC_BUCKETS

PURPOSE = {
    "assets": "clips, audio takes, final MP4",
    "brand_kit": "style key, tokens, block template, voice",
    "manifests": "per-step + master provenance manifests",
    "audit": "Parquet run tables",
    "runs": "run state JSON — the app's only datastore",
}


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["b2", *args], capture_output=True, text=True)


def main() -> None:
    if not shutil.which("b2"):
        sys.exit("FAIL  b2 CLI not found — brew install b2-tools")

    account = run("account", "get")
    if account.returncode != 0:
        sys.exit("FAIL  b2 CLI not authorized — run: b2 account authorize <keyID> <appKey>")

    allowed = json.loads(account.stdout)["allowed"]
    scoped = allowed.get("buckets")
    if scoped:
        names = ", ".join(b["name"] for b in scoped)
        sys.exit(
            f"FAIL  this key is restricted to bucket(s): {names}\n"
            "      Bucket creation needs a key with access to ALL buckets.\n"
            "      Create one at https://secure.backblaze.com/app_keys.htm"
        )
    if "writeBuckets" not in allowed["capabilities"]:
        sys.exit("FAIL  key lacks the writeBuckets capability")

    existing = set(run("bucket", "list").stdout.split())
    failed = False

    for role, name in BUCKETS.items():
        visibility = "allPublic" if name in PUBLIC_BUCKETS else "allPrivate"
        label = "PUBLIC " if visibility == "allPublic" else "private"

        if name in existing:
            print(f"exists   {name:22} {label}  {PURPOSE[role]}")
            continue

        result = run("bucket", "create", name, visibility)
        if result.returncode == 0:
            print(f"created  {name:22} {label}  {PURPOSE[role]}")
        else:
            detail = (result.stderr or result.stdout).strip().splitlines()[-1]
            print(f"FAILED   {name:22} {detail}")
            failed = True

    if failed:
        print(
            "\nB2 bucket names are globally unique across all Backblaze accounts.\n"
            "If a name is taken, set an override in api/.env (e.g.\n"
            "B2_BUCKET_ASSETS=newsdesk-assets-mke) and re-run — no code change needed."
        )
        sys.exit(1)

    print("\nPASS — all five buckets present with correct visibility.")


if __name__ == "__main__":
    main()
