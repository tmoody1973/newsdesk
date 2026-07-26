"""Environment and B2 configuration.

Single place that reads credentials and hands back storage backends, so no
caller has to remember which env var holds what — or which of the two forms
Backblaze shows for a region.
"""

from __future__ import annotations

import os
import re

from dotenv import load_dotenv
from genblaze_s3 import S3StorageBackend

load_dotenv()

# The five data classes from design spec §8. Values are the bucket names;
# swap them here if the deployment consolidates onto fewer buckets.
BUCKETS = {
    "assets": "newsdesk-assets",
    "brand_kit": "newsdesk-brand-kit",
    "manifests": "newsdesk-manifests",
    "audit": "newsdesk-audit",
    "runs": "newsdesk-runs",
}

_REGION_RE = re.compile(r"([a-z]{2}-[a-z]+-\d{3})")


class ConfigError(RuntimeError):
    """Raised when required configuration is missing or unusable."""


def region() -> str:
    """B2 region, accepting either form Backblaze displays.

    The Buckets page shows a full endpoint (`s3.us-east-005.backblazeb2.com`)
    while the SDK wants just the region (`us-east-005`). Both get pasted into
    .env in practice, so accept either rather than failing on a plausible one.
    """
    raw = (os.getenv("B2_REGION") or "").strip()
    if not raw:
        raise ConfigError("B2_REGION is not set — see api/.env.example")
    match = _REGION_RE.search(raw)
    if not match:
        raise ConfigError(
            f"B2_REGION={raw!r} is neither a region (us-east-005) "
            "nor an endpoint (s3.us-east-005.backblazeb2.com)"
        )
    return match.group(1)


def require(*names: str) -> None:
    """Fail fast with every missing name at once, not one per run."""
    missing = [n for n in names if not (os.getenv(n) or "").strip()]
    if missing:
        raise ConfigError(
            f"missing env: {', '.join(missing)} — copy api/.env.example to api/.env"
        )


def backend(bucket: str) -> S3StorageBackend:
    """Storage backend for one bucket, region passed explicitly.

    Explicit beats inferred here: a wrong region otherwise surfaces as an
    opaque connection error deep inside a generation run.
    """
    require("B2_KEY_ID", "B2_APP_KEY")
    return S3StorageBackend.for_backblaze(bucket, region=region())
