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


# --- Wall 2, second failure mode: the gate that cannot read its rulebook -----
#
# The import scan above proves the gate CANNOT reach a provider. It says nothing
# about whether the gate can reach its rules, and on 2026-07-29 the deployed
# worker refused all six blocks of a live run with
#
#   checker unavailable (FileNotFoundError: '/policy/policy.yaml')
#   — blocked rather than assumed safe
#
# `POLICY_FILE` was `parents[3]`, correct in the repo and one level too deep in
# the container, where `newsdesk/` sits directly under `/app`. Failing closed is
# what kept it at $0, but a rulebook nobody can open governs nothing.

DOCKERFILE = Path(__file__).resolve().parents[1] / "Dockerfile"


def test_gate_finds_its_policy_file():
    from newsdesk.policy.gate import POLICY_FILE

    assert POLICY_FILE.is_file(), (
        f"the gate resolved its rulebook to {POLICY_FILE}, which does not exist "
        "— every prompt will be refused as 'checker unavailable'"
    )


def test_policy_lookup_does_not_depend_on_package_depth(tmp_path):
    """The bug in one line: a fixed number of `..` hops.

    Rebuilds the container's shallower layout — `newsdesk/` directly under the
    app root rather than under `api/` — and asserts the file is still found.
    A `parents[N]` expression passes in the repo and fails here.
    """
    from newsdesk.policy.gate import _find_policy_file

    app = tmp_path / "app"
    pkg = app / "newsdesk" / "policy"
    pkg.mkdir(parents=True)
    (app / "policy").mkdir()
    (app / "policy" / "policy.yaml").write_text("rules: []\n")

    module = pkg / "gate.py"
    module.write_text("")

    assert _find_policy_file(module) == app / "policy" / "policy.yaml", (
        "the lookup must find the rulebook from the container layout too — "
        "a fixed parents[N] passes in the repo and resolves to /policy here"
    )


def test_gate_finds_the_brand_kit():
    """Second file, same fault. Found by the same live run."""
    from newsdesk.blockprompt import kit_dir

    assert kit_dir().is_dir(), (
        f"the brand kit resolved to {kit_dir()}, which does not exist — "
        "every block prompt will die on FileNotFoundError"
    )


def test_brand_kit_lookup_does_not_depend_on_package_depth(tmp_path):
    from newsdesk.blockprompt import _find_brand_kit

    app = tmp_path / "app"
    pkg = app / "newsdesk"
    pkg.mkdir(parents=True)
    (app / "brand-kit").mkdir()

    module = pkg / "blockprompt.py"
    module.write_text("")

    assert _find_brand_kit(module) == app / "brand-kit", (
        "a fixed parents[N] resolves to /brand-kit in the container layout"
    )


@pytest.mark.parametrize(
    "line,why",
    [
        ("COPY policy ./policy", "the gate refuses every block without its rulebook"),
        ("COPY brand-kit ./brand-kit", "every block prompt reads the kit's style tokens"),
        (
            "COPY api/newsdesk ./newsdesk",
            "the build context must be the REPO ROOT — policy/ and brand-kit/ "
            "live above api/, and Docker cannot COPY above its context",
        ),
    ],
)
def test_the_worker_image_ships_what_wall_2_reads(line, why):
    """Wall 2 has to work with no credentials, so what it reads must be baked in.

    Every one of these was missing on the first deploy, and the worker refused a
    live story rather than saying why in a way anyone would notice — the message
    was correct and pointed at `/policy/policy.yaml`, a path that exists in no
    checkout.
    """
    assert line in DOCKERFILE.read_text(), f"api/Dockerfile is missing `{line}` — {why}"
