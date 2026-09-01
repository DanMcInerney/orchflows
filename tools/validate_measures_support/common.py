"""Shared schema constants and value helpers for measure validation."""

from __future__ import annotations

import hashlib
import re
from collections import namedtuple

# tools/validate_measures.py, this module's only importer, already binds
# the repository root onto sys.path (as the ``tools`` namespace package)
# before reaching this import, so the fact is read from the leaf rather
# than re-walked here.
from scripts._bootstrap import ROOT as REPO_ROOT
DEFAULT_RECORD = REPO_ROOT / "benchmarks" / "measures" / "benchmaker.md"
DEFAULT_CASES_DIR = REPO_ROOT / "benchmarks" / "benchmaker" / "cases"

CASE_COUNT = 16

SHA256 = re.compile(r"^sha256:[0-9a-f]{64}$")
ENTRY_HEADING = re.compile(r"^## (\d{4}-\d{2}-\d{2}) [—-] (.+)$")
INCOMPLETE = re.compile(r"INCOMPLETE: (\d+) of (\d+) rows")
FENCED_JSON = re.compile(r"^```json\n(.*?)^```", re.M | re.S)
# A benchmark's version is its git revision, so an entry names the case
# set it measured by revision. The 7-to-40 bound admits an abbreviated
# sha and excludes a 64-hex content digest, the form this replaced.
CASE_SET_LINE = re.compile(r"case set\s+([0-9a-f]{7,40})\b")
CASE_SET_RULE = "case-set"
VERIFY_COMMAND = re.compile(r"^ {4,}.*tools/validate_measures\.py", re.M)
CASE_KEYS = ("angle", "size", "exec_bound")
TOML_SCALAR = re.compile(r'^(%s)\s*=\s*"(.*)"\s*$' % "|".join(CASE_KEYS))
CASE_SCHEMA_RULE = "case-schema"
# A row recorded before `bound` became `exec_bound` quotes the old
# construction clause. Strip only that historical half before comparing.
CONSTRUCTION_CLAUSE = re.compile(r"^\s*one BC\d+ share;\s*")
STATUS_COUNT = re.compile(r"(both-pass|both-fail|inversion|undetermined|split)\D{0,3}(\d+)")
RESOLUTION_VALUE = re.compile(r"=\s*(\d+(?:\.\d+)?)\s*cases?\b")
SPREAD = re.compile(r"spread[^.\n]{0,80}?\b(unmeasured|(\d+(?:\.\d+)?)\s*cases?)\b")
EMPTY_FIGURE = re.compile(r"\bnone\b|\bempty\b|\bno case", re.I)
FIRST_NUMBER = re.compile(r"-?\d+")

RUNGS = ("strong", "weak")
VERDICTS = ("PASS", "FAIL", "UNVERIFIED")
STATUSES = ("both-pass", "split", "both-fail", "inversion", "undetermined")
AMBIGUOUS = ("both-pass", "both-fail")
BOUND_STATUSES = ("within", "overrun", "unmeasured")

ROW_KEYS = (
    "case", "angle", "size", "trials_declared", "rungs", "status",
    "discriminating", "readings", "failed_checks", "scope", "observations",
)
RUNG_KEYS = (
    "model", "effort_requested", "verdict", "artifact_identity",
    "artifact_path", "artifact_files",
    "probe_exit_code", "trial_exit_codes", "probe_log", "canary", "bound",
    "cost_actual",
)
BOUND_KEYS = ("declared", "probe_tier_ceiling_s", "probe_wall_clock_s", "status")
COST_KEYS = ("subagent_tokens", "tool_uses", "wall_ms", "attempts")
ENTRY_SECTIONS = ("Rungs", "Incomparability", "Measured scope", "Figures")
FIGURE_LABELS = (
    "status distribution", "discriminating set", "inversions",
    "margin in cases", "resolution", "deterministic",
)
RESOLUTION_FORMULA = "max(measured rerun spread, 1 case)"
SCOPE_TOKENS = ("cs-antigoodhart-2/workload.json", "cs-nondet-fresh")
WITHHELD_TOKENS = ("expected.md", "seeds/", "probe/")
PROTECTED_EVIDENCE_RULE = "protected-evidence"
SKIP_DIR_PREFIXES = (".", "_", "__")

Env = namedtuple("Env", "cases_dir cases resolve_root preamble_verify")


def _text(value):
    return isinstance(value, str) and value.strip() != ""


def _int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def tree_digest(root):
    """One subtree's evidence identity: sorted per-file lock, hashed."""
    files = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        if any(part.startswith(SKIP_DIR_PREFIXES) for part in relative.parts[:-1]):
            continue
        if relative.parts[-1].endswith(".pyc"):
            continue
        files.append(relative.as_posix())
    files.sort()
    lines = ["%s  %s" % (hashlib.sha256((root / f).read_bytes()).hexdigest(), f) for f in files]
    payload = ("".join(line + "\n" for line in lines)).encode("ascii")
    return "sha256:" + hashlib.sha256(payload).hexdigest(), len(lines)
