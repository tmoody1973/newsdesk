#!/usr/bin/env python3
"""Create the five B2 buckets from design spec §8.

Run once after B2_KEY_ID / B2_APP_KEY are in api/.env:

    uv run python scripts/setup_buckets.py

Idempotent — buckets that already exist are reported and skipped. Requires a
key with access to ALL buckets; a bucket-scoped key cannot create new ones.
"""

from __future__ import annotations

import os
import sys

import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

BUCKETS = {
    "newsdesk-assets": "generated clips, audio takes, final MP4",
    "newsdesk-brand-kit": "style key, tokens, block template, voice, subtitles",
    "newsdesk-manifests": "per-step + master provenance manifests",
    "newsdesk-audit": "Parquet run tables",
    "newsdesk-runs": "run state JSON — the app's only datastore",
}


def main() -> None:
    load_dotenv()

    key_id = os.getenv("B2_KEY_ID")
    app_key = os.getenv("B2_APP_KEY")
    region = os.getenv("B2_REGION", "us-west-004")

    if not key_id or not app_key:
        print("FAIL  set B2_KEY_ID and B2_APP_KEY in api/.env first")
        sys.exit(1)

    s3 = boto3.client(
        "s3",
        endpoint_url=f"https://s3.{region}.backblazeb2.com",
        aws_access_key_id=key_id,
        aws_secret_access_key=app_key,
        region_name=region,
    )

    # Fail loudly on bad credentials or a wrong region rather than reporting
    # five confusing per-bucket errors.
    try:
        existing = {b["Name"] for b in s3.list_buckets()["Buckets"]}
    except ClientError as exc:
        print(f"FAIL  could not reach B2 at region {region!r}: {exc}")
        print("      Check B2_REGION matches the endpoint shown on your Buckets page.")
        sys.exit(1)

    failed = False
    for name, purpose in BUCKETS.items():
        if name in existing:
            print(f"exists   {name:22} {purpose}")
            continue
        try:
            s3.create_bucket(Bucket=name)
            print(f"created  {name:22} {purpose}")
        except ClientError as exc:
            code = exc.response["Error"]["Code"]
            if code in ("BucketAlreadyOwnedByYou", "BucketAlreadyExists"):
                print(f"exists   {name:22} {purpose}")
            else:
                # B2 bucket names are globally unique across all accounts.
                print(f"FAILED   {name:22} {code}: {exc}")
                failed = True

    if failed:
        print("\nSome buckets could not be created. If the name is taken globally,")
        print("pick a suffix (e.g. newsdesk-assets-mke) and update BUCKETS here,")
        print("scripts/smoke_b2.py, and design spec §8 to match.")
        sys.exit(1)

    print("\nPASS — all five buckets present.")


if __name__ == "__main__":
    main()
