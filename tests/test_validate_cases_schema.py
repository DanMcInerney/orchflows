"""Public discovery seam for benchmaker case-schema regression tests.

``bound`` used to carry two quantities in one string — the construction
run's builder-context allocation and the candidate-facing probe tier. The
first told a candidate how the case was authored; only the second was
measurable. ``exec_bound`` carries the second alone, and these tests prove
the validator refuses the conflation rather than accepting it silently.

The behavioral checks live in ``test_validate_cases_schema_cases``. Their
classes are imported here explicitly so the established module seam keeps
discovering the complete collection.
"""

from __future__ import annotations

import json
import re
import sys
import unittest
from pathlib import Path

if __name__ == "test_validate_cases_schema":
    sys.modules["tests.test_validate_cases_schema"] = sys.modules[__name__]

REPO_ROOT = Path(__file__).resolve().parent.parent
TOOL_DIR = REPO_ROOT / "benchmarks" / "benchmaker" / "tools"
if str(TOOL_DIR) not in sys.path:
    sys.path.insert(0, str(TOOL_DIR))

import deseal_cases as dc  # noqa: E402
import validate_cases as vc  # noqa: E402

CASES = REPO_ROOT / "benchmarks" / "benchmaker" / "cases"

CLEAN = {
    "id": "cs-cli-fresh",
    "angle": "deterministic-cli",
    "outcome": "an outcome",
    "target": "target",
    "probe": "python probe/check.py {impl}",
    "port": "cli-dedupe",
    "tests": "one line",
    "provenance": "synthesis@41ee9ea2 claims 1",
    "evidence": ["evidence/spec.md"],
    "expected_qualification": ["schema-valid"],
    "exec_bound": "probe within small tier",
    "negative": False,
    "size": "small",
    "parallel_safe": True,
}


def errors(**overrides):
    data = dict(CLEAN)
    data.update(overrides)
    found = []
    vc.check_schema(data, data["id"], found.append)
    return found


# A benchmark's version is its git revision. Nothing in the case set asks
# a candidate to mint a whole-package identity or to record a digest beside
# a component's locator. Evidence identity is a different discipline with a
# different owner and is deliberately not caught here.
RETIRED_TOKENS = ("benchmark_identity", "covered_set_digest")
COMPONENT_DIGEST_KEYS = ("sha256", "identity")
DIGEST_RE = re.compile(r"(?:sha256:[0-9a-f]{8,}|\b[0-9a-f]{64}\b)")
COMPONENTS = (
    "evaluation_design",
    "runnable_cases",
    "runner",
    "scoring",
    "provenance",
    "qualification",
)
RETIRED_RECIPE_PHRASES = (
    "canonical payload",
    "canonical json",
    "ensure_ascii",
    "keys sorted",
    "sorted keys",
    "mints a successor",
    "successor identity",
    "successor benchmark",
)


# Three tests walk the same immutable case set and two parse the same JSON;
# the walk and parse happen once.
_SCAN = {}


def case_files():
    if "files" not in _SCAN:
        _SCAN["files"] = tuple(
            path
            for path in sorted(CASES.rglob("*"))
            if path.is_file() and "__pycache__" not in path.parts
        )
    return _SCAN["files"]


def case_json():
    if "json" not in _SCAN:
        _SCAN["json"] = tuple(
            path
            for path in sorted(CASES.rglob("*.json"))
            if "__pycache__" not in path.parts
        )
    return _SCAN["json"]


def case_documents():
    """Return ``(path, parsed)`` for every case JSON file."""
    if "documents" not in _SCAN:
        _SCAN["documents"] = tuple(
            (path, json.loads(path.read_text(encoding="utf-8"))) for path in case_json()
        )
    return _SCAN["documents"]


def walk_objects(node):
    if isinstance(node, dict):
        yield node
        for value in node.values():
            yield from walk_objects(value)
    elif isinstance(node, list):
        for value in node:
            yield from walk_objects(value)


from tests.test_validate_cases_schema_cases.coverage import (  # noqa: E402,F401
    CoverageCensusTest,
    CoverageDeclarationTest,
    CoverageTeethTest,
)
from tests.test_validate_cases_schema_cases.deseal import DesealToolTest  # noqa: E402,F401
from tests.test_validate_cases_schema_cases.retired_seal import (  # noqa: E402,F401
    RetiredSealTest,
)
from tests.test_validate_cases_schema_cases.schema import (  # noqa: E402,F401
    CaseSetTest,
    ExecBoundTest,
)


if __name__ == "__main__":
    unittest.main()
