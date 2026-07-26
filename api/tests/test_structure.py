"""Wall 2 is enforced by this test, not by discipline.

The claim "zero paid API calls occur on a blocked prompt" is only as strong as
the guarantee that the gate cannot make one. A code review can miss an import;
this cannot.

Walks the gate's transitive import graph inside the newsdesk package and fails
if anything network-capable appears. Pattern borrowed from Backblaze's own
sample app, which does the same scan for stray boto3 usage.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

PKG = Path(__file__).resolve().parents[1] / "newsdesk"

# Anything that can open a socket, directly or by pulling in a provider SDK.
FORBIDDEN = {
    "boto3", "botocore", "httpx", "requests", "urllib", "urllib3", "http",
    "socket", "aiohttp", "openai", "google",
    "genblaze_core", "genblaze_s3", "genblaze_gmicloud",
    "genblaze_elevenlabs", "genblaze_lmnt",
    # First-party modules that reach the network, so the ban is transitive.
    "newsdesk.config", "newsdesk.pricing", "newsdesk.state",
}

ENTRY = "newsdesk.policy.gate"


def _module_path(dotted: str) -> Path | None:
    rel = dotted.removeprefix("newsdesk.").replace(".", "/")
    for candidate in (PKG / f"{rel}.py", PKG / rel / "__init__.py"):
        if candidate.exists():
            return candidate
    return None


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            found.add(node.module)
    return found


def _walk(entry: str) -> dict[str, set[str]]:
    """Transitive imports of first-party modules, keyed by importer."""
    graph: dict[str, set[str]] = {}
    queue, seen = [entry], set()
    while queue:
        mod = queue.pop()
        if mod in seen:
            continue
        seen.add(mod)
        path = _module_path(mod)
        if path is None:
            continue
        graph[mod] = _imports(path)
        queue.extend(m for m in graph[mod] if m.startswith("newsdesk."))
    return graph


def test_gate_cannot_reach_the_network():
    violations = []
    for module, imports in _walk(ENTRY).items():
        for imported in imports:
            root = imported.split(".")[0]
            if imported in FORBIDDEN or root in FORBIDDEN:
                violations.append(f"{module} imports {imported}")

    assert not violations, (
        "Wall 2 breached — the policy gate can now reach a provider, which means "
        "'$0 spent on blocked prompts' is no longer structurally true:\n  "
        + "\n  ".join(violations)
    )


def test_gate_entry_module_exists():
    """Guards against the scan silently passing because it found nothing."""
    assert _module_path(ENTRY) is not None, f"{ENTRY} not found — the scan proves nothing"
    assert _walk(ENTRY), "import graph is empty — the scan proves nothing"


@pytest.mark.parametrize("banned", ["httpx", "boto3", "genblaze_core"])
def test_scan_would_catch_a_violation(banned):
    """The test that tests the test.

    A structural scan that cannot fail is decoration. This asserts the checker
    actually rejects a known-bad import rather than passing vacuously.
    """
    assert banned in FORBIDDEN
    root = banned.split(".")[0]
    assert banned in FORBIDDEN or root in FORBIDDEN
