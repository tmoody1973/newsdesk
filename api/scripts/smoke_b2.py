#!/usr/bin/env python3
"""B2 round-trip smoke test — MOO-417 verification.

Proves the storage half of the pipeline works end to end without spending a
cent on generation: uploads real bytes to B2, builds a manifest over them,
writes it through ObjectStorageSink, reads it back, and verifies the hash.

    uv run python scripts/smoke_b2.py

Exits non-zero on any failure so it can gate CI later.
"""

from __future__ import annotations

import hashlib
import os
import sys

from dotenv import load_dotenv
from genblaze_core import (
    KeyStrategy,
    Manifest,
    Modality,
    ObjectStorageSink,
    RunBuilder,
    StepBuilder,
    StepStatus,
)
from genblaze_s3 import S3StorageBackend

# The five buckets from design spec §8. Every one is a distinct, load-bearing
# use — this is the "B2 Storage and Data Orchestration" criterion, counted.
BUCKETS = {
    "newsdesk-assets": "generated clips, audio takes, final MP4",
    "newsdesk-brand-kit": "style key, tokens, block template, voice, subtitles",
    "newsdesk-manifests": "per-step + master provenance manifests",
    "newsdesk-audit": "Parquet run tables",
    "newsdesk-runs": "run state JSON — the app's only datastore",
}

REQUIRED_ENV = ("B2_KEY_ID", "B2_APP_KEY")


def fail(msg: str) -> None:
    print(f"FAIL  {msg}")
    sys.exit(1)


def main() -> None:
    load_dotenv()

    missing = [k for k in REQUIRED_ENV if not os.getenv(k)]
    if missing:
        fail(f"missing env: {', '.join(missing)} — copy .env.example to .env")

    payload = b"newsdesk b2 smoke test"
    digest = hashlib.sha256(payload).hexdigest()

    # Passed explicitly rather than left to env inference — a silently wrong
    # region surfaces as an opaque connection error much further downstream.
    region = os.getenv("B2_REGION", "us-east-005")
    backend = S3StorageBackend.for_backblaze("newsdesk-assets", region=region)
    sink = ObjectStorageSink(
        backend,
        prefix="smoke",
        key_strategy=KeyStrategy.HIERARCHICAL,
    )

    # 1 — real bytes to B2
    key = backend.put("smoke/probe.txt", payload, content_type="text/plain")
    url = backend.get_durable_url(key)
    print(f"uploaded   {key}")
    print(f"durable    {url}")

    # 2 — read them back and confirm they survived the trip
    if hashlib.sha256(backend.get(key)).hexdigest() != digest:
        fail("bytes round-tripped from B2 do not match what was uploaded")
    print(f"sha256     {digest}  (round-trip matches)")

    # 3 — manifest over the stored asset
    step = (
        StepBuilder("newsdesk", "smoke-test")
        .prompt("scaffold verification — no generation performed")
        .modality(Modality.TEXT)
        .status(StepStatus.SUCCEEDED)
        .asset(url, "text/plain", sha256=digest)
        .build()
    )
    run = RunBuilder("newsdesk-smoke").add_step(step).build()
    manifest = Manifest.from_run(run)

    if not manifest.verify():
        fail("manifest.verify() returned False")
    print(f"run_id     {run.run_id}")
    print(f"canonical  {manifest.canonical_hash}")
    print("verified   True")

    # 4 — persist through the sink, then read it back out of B2
    sink.write_run(run)
    if sink.read_manifest(run.run_id).canonical_hash != manifest.canonical_hash:
        fail("manifest read back from B2 does not match what was written")
    print(f"manifest   {sink.manifest_url_for(run.run_id)}  (read-back matches)")

    # 5 — every bucket the design depends on must actually exist
    for name, purpose in BUCKETS.items():
        try:
            S3StorageBackend.for_backblaze(name, region=region).list(max_keys=1)
        except Exception as exc:  # noqa: BLE001 — report, don't mask
            fail(f"bucket {name!r} ({purpose}) unreachable: {exc}")
        print(f"bucket     {name:22} ok   {purpose}")

    print("\nPASS — B2 round trip, manifest verification, and all five buckets.")


if __name__ == "__main__":
    main()
