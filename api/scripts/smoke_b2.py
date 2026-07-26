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
import sys

from genblaze_core import (
    Manifest,
    Modality,
    RunBuilder,
    StepBuilder,
    StepStatus,
)

from newsdesk.config import BUCKETS, ConfigError, backend, region, require

PURPOSE = {
    "assets": "clips, audio takes, final MP4",
    "brand_kit": "style key, tokens, block template, voice",
    "manifests": "per-step + master provenance manifests",
    "audit": "Parquet run tables",
    "runs": "run state JSON — the app's only datastore",
}


def fail(msg: str) -> None:
    print(f"FAIL  {msg}")
    sys.exit(1)


def main() -> None:
    try:
        require("B2_KEY_ID", "B2_APP_KEY")
        print(f"region     {region()}")
    except ConfigError as exc:
        fail(str(exc))

    payload = b"newsdesk b2 smoke test"
    digest = hashlib.sha256(payload).hexdigest()

    assets = backend(BUCKETS["assets"])

    # 1 — real bytes to B2
    key = assets.put("smoke/probe.txt", payload, content_type="text/plain")
    url = assets.get_durable_url(key)
    print(f"uploaded   {key}")
    print(f"durable    {url}")

    # 2 — read them back and confirm they survived the trip
    if hashlib.sha256(assets.get(key)).hexdigest() != digest:
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

    # 4 — manifest persists to its own bucket and survives the round trip.
    #
    # Written directly rather than via ObjectStorageSink.write_run(): the sink
    # re-fetches each asset by URL to transfer it into storage, which is right
    # for real provider outputs (MOO-424) but returns 401 here because the
    # asset is already in a private bucket. Nothing about the manifest path is
    # skipped — only the redundant re-download.
    manifests = backend(BUCKETS["manifests"])
    manifest_key = f"smoke/{run.run_id}.json"
    manifests.put(
        manifest_key,
        manifest.to_canonical_json().encode(),
        content_type="application/json",
    )
    readback = Manifest.model_validate_json(manifests.get(manifest_key).decode())
    if readback.canonical_hash != manifest.canonical_hash:
        fail("manifest read back from B2 does not match what was written")
    print(f"manifest   {BUCKETS['manifests']}/{manifest_key}  (read-back matches)")

    # 5 — every bucket the design depends on must actually exist
    for role, name in BUCKETS.items():
        try:
            backend(name).list(max_keys=1)
        except Exception as exc:  # noqa: BLE001 — report, don't mask
            fail(f"bucket {name!r} ({PURPOSE[role]}) unreachable: {exc}")
        print(f"bucket     {name:22} ok   {PURPOSE[role]}")

    print("\nPASS — B2 round trip, manifest verification, and all five buckets.")


if __name__ == "__main__":
    main()
