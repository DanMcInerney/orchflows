"""Failability proof for tools/validate_measures.py.

Every test runs against synthetic fixtures in a tempdir — a synthetic
case directory, synthetic candidate artifacts, and a record built from
row dicts. None of it reads ``benchmarks/measures/benchmaker.md`` or the
live evidence store: the checker recomputes each artifact identity over
bytes under ``.orch/``, which is gitignored, so a test that read the
live store would pass here and fail in CI the day the store is pruned.
The flagless run over the real record is the acceptance oracle and stays
outside this suite (T17-checker's completion test).

A clean fixture must exit 0 and print nothing. Each other test mutates
exactly one thing and proves the checker reports it — a checker that
never fires is worthless.
"""

from __future__ import annotations

import ast
import contextlib
import copy
import hashlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools import validate_measures as vm  # noqa: E402

# The sixteen frozen case ids, in `ls cases/` order.
CASES = (
    "cs-antigoodhart-2", "cs-cli-fresh", "cs-contradiction-fresh", "cs-cost-fresh",
    "cs-intake-refusal", "cs-judged-fresh", "cs-multidomain-fresh", "cs-nondet-fresh",
    "cs-package-audit", "cs-ranking-fresh", "cs-ratelimit-fresh", "cs-refusal-2",
    "cs-run-conduct", "cs-sparse-fresh", "cs-stateful-fresh", "cs-workflow-fresh",
)
PROTECTED = (
    "cs-antigoodhart-2/workload.json", "cs-nondet-fresh/streams.json",
    "stream-held-1.json", "stream-held-2.json", "stream-held-3.json",
)
# A revision-shaped set reference. The checker reads the shape, never
# the value: which revision an entry names is that entry's own fact.
SET_REVISION = "d8cabcb7dafe95181e279b0f2852cb6364d2a4bf"
MODEL = {"strong": "claude-opus-5", "weak": "claude-sonnet-5"}
EFFORT = {"strong": "xhigh", "weak": "high"}
DECLARED_BOUND = "probe within small tier"
VERDICT_PAIR = {
    "both-pass": ("PASS", "PASS"),
    "split": ("PASS", "FAIL"),
    "both-fail": ("FAIL", "FAIL"),
    "inversion": ("FAIL", "PASS"),
    "undetermined": ("UNVERIFIED", "PASS"),
}
TRIALS = {"PASS": [0], "FAIL": [1], "UNVERIFIED": [124]}
# Four statuses across sixteen rows, plus the fifth an UNVERIFIED forces.
FULL_PLAN = (
    ("cs-antigoodhart-2", "both-fail"), ("cs-cli-fresh", "split"),
    ("cs-contradiction-fresh", "split"), ("cs-cost-fresh", "both-pass"),
    ("cs-intake-refusal", "both-pass"), ("cs-judged-fresh", "both-fail"),
    ("cs-multidomain-fresh", "both-pass"), ("cs-nondet-fresh", "undetermined"),
    ("cs-package-audit", "both-fail"), ("cs-ranking-fresh", "inversion"),
    ("cs-ratelimit-fresh", "both-pass"), ("cs-refusal-2", "split"),
    ("cs-run-conduct", "both-pass"), ("cs-sparse-fresh", "both-fail"),
    ("cs-stateful-fresh", "both-pass"), ("cs-workflow-fresh", "both-pass"),
)
ONE_PLAN = (("cs-cli-fresh", "split"),)

INCOMPARABILITY = (
    "A score is a property of target, model, harness and benchmark together. "
    "These figures bind the benchmark identity above, both rung identities above, "
    "and the host binding above, and they cross none of those boundaries."
)


def tree_identity(root: Path):
    """The checker's evidence-identity recipe, re-implemented not imported.

    Per-file ``<sha256>  <relative posix path>`` lines in path order, one
    newline each, hashed. Independent of the checker's own copy, so a
    drift in either is a test failure.
    """
    names = sorted(p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file())
    payload = "".join(
        "%s  %s\n" % (hashlib.sha256((root / name).read_bytes()).hexdigest(), name)
        for name in names
    ).encode("ascii")
    return "sha256:" + hashlib.sha256(payload).hexdigest(), len(names)


class World:
    """A synthetic package: sixteen cases, a manifest, two artifacts."""

    def __init__(self, root: Path):
        self.root = root
        self.cases_dir = root / "cases"
        for index, case in enumerate(CASES):
            directory = self.cases_dir / case
            directory.mkdir(parents=True)
            (directory / "case.toml").write_text(
                'id = "%s"\nangle = "angle-%d"\nsize = "small"\nexec_bound = "%s"\n'
                % (case, index, DECLARED_BOUND),
                encoding="utf-8",
            )
        (root / "manifest.json").write_text(
            json.dumps({"protected_evidence": {"files": list(PROTECTED)}}),
            encoding="utf-8",
        )
        self.artifacts = {}
        for rung, files in (("strong", 3), ("weak", 1)):
            directory = root / "artifacts" / rung
            directory.mkdir(parents=True)
            for number in range(files):
                (directory / ("part-%d.txt" % number)).write_text(
                    "%s payload %d\n" % (rung, number), encoding="utf-8"
                )
            identity, count = tree_identity(directory)
            self.artifacts[rung] = (directory, identity, count)
        self.angles = {case: "angle-%d" % index for index, case in enumerate(CASES)}

    def write_record(self, text: str) -> Path:
        """One file per distinct record text, named for the text.

        Named for the text and not for a call counter: the world is shared
        by the whole module, so a counter makes each test's path depend on
        how many records the tests before it happened to write, and running
        one test alone or in another order names a different file. Same
        text, same path, and the write is idempotent.
        """

        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
        path = self.root / ("record-%s.md" % digest)
        path.write_text(text, encoding="utf-8")
        return path


WORLD = None
_TMP = None


def setUpModule():
    global WORLD, _TMP
    _TMP = tempfile.TemporaryDirectory()
    WORLD = World(Path(_TMP.name).resolve())


def tearDownModule():
    _TMP.cleanup()


# --------------------------------------------------------------------
# fixture builders
# --------------------------------------------------------------------


def make_rung(name: str, verdict: str) -> dict:
    directory, identity, count = WORLD.artifacts[name]
    trials = list(TRIALS[verdict])
    return {
        "model": MODEL[name],
        "effort_requested": EFFORT[name],
        "verdict": verdict,
        "artifact_identity": identity,
        "artifact_path": str(directory),
        "artifact_files": count,
        "probe_exit_code": trials[0],
        "trial_exit_codes": trials,
        "probe_log": "%s/probe-trial1.log" % directory,
        "canary": "clean",
        "bound": {
            "declared": DECLARED_BOUND,
            "probe_tier_ceiling_s": 60,
            "probe_wall_clock_s": 1.5,
            "status": "within",
        },
        "cost_actual": {
            "subagent_tokens": 40000,
            "tool_uses": 30,
            "wall_ms": 200000,
            "attempts": 1,
        },
    }


def make_row(case: str, status: str) -> dict:
    strong, weak = VERDICT_PAIR[status]
    verdicts = {"strong": strong, "weak": weak}
    return {
        "case": case,
        "angle": WORLD.angles[case],
        "size": "small",
        "trials_declared": 1,
        "rungs": {name: make_rung(name, verdicts[name]) for name in ("strong", "weak")},
        "status": status,
        "discriminating": status == "split",
        "readings": (
            ["the case is genuinely hard", "the case is broken"]
            if status in ("both-pass", "both-fail")
            else []
        ),
        "failed_checks": {
            name: (["P0.c: named check"] if verdicts[name] == "FAIL" else [])
            for name in ("strong", "weak")
        },
        "scope": "Public subset; the protected store is unresolvable in this checkout.",
        "observations": ["Recording only; nothing was repaired."],
    }


def rows_for(plan) -> list:
    return [make_row(case, status) for case, status in plan]


def figure_table(rows, overrides=None) -> str:
    counts = {status: 0 for status in vm.STATUSES}
    for row in rows:
        if row.get("status") in counts:
            counts[row["status"]] += 1
    passes = {
        name: sum(1 for row in rows if row["rungs"][name]["verdict"] == "PASS")
        for name in ("strong", "weak")
    }
    def named(status):
        return ", ".join("`%s`" % row["case"] for row in rows if row.get("status") == status) or "none"

    values = {
        "status distribution": "; ".join("`%s` %d" % (s, counts[s]) for s in vm.STATUSES),
        "discriminating set": named("split"),
        "inversions": named("inversion"),
        "margin in cases": "%d (strong %d/%d, weak %d/%d)"
        % (passes["strong"] - passes["weak"], passes["strong"], len(rows), passes["weak"], len(rows)),
        "resolution": "`max(measured rerun spread, 1 case)` = **1 case**",
        "deterministic / judged": "%d deterministic, 0 judged" % len(rows),
    }
    notes = {
        "resolution": "rerun spread is **unmeasured**; the three-trial cases have not rerun",
    }
    values.update(overrides or {})
    lines = ["| figure | value | note |", "| --- | --- | --- |"]
    for label, value in values.items():
        lines.append("| %s | %s | %s |" % (label, value, notes.get(label, "over the measured rows")))
    return "\n".join(lines)


def entry_text(
    rows,
    date="2026-08-08",
    title="two-rung measurement pass",
    incomplete=None,
    absent=None,
    case_set=None,
    rung_table=None,
    incomparability=INCOMPARABILITY,
    scope=None,
    figures=None,
    figure_overrides=None,
    verify=False,
    sections=("case set", "rungs", "incomparability", "scope", "figures"),
) -> str:
    """One entry. ``sections`` drops a whole section; ``case_set=""`` drops
    the case-set line alone; ``incomplete=N`` adds the declaration."""
    heading = "## %s — %s" % (date, title)
    if incomplete is not None:
        heading += " (INCOMPLETE: %d of 16 rows)" % incomplete
    parts = [heading, ""]
    if "case set" in sections:
        if case_set != "":
            parts.append("    case set           %s" % (case_set or SET_REVISION))
        parts.append("")
    if verify:
        parts += ["Verify this entry with:", "", "    python tools/validate_measures.py", ""]
    if absent is None and incomplete is not None:
        absent = [case for case, _ in FULL_PLAN if case not in {row["case"] for row in rows}]
    if absent:
        parts += ["Absent, not measured: %s." % ", ".join("`%s`" % case for case in absent), ""]
    if "rungs" in sections:
        parts += [
            "### Rungs",
            "",
            rung_table
            if rung_table is not None
            else (
                "| rung | model id | effort | host binding | scaffold |\n"
                "| --- | --- | --- | --- | --- |\n"
                "| strong | `claude-opus-5` | `xhigh`, requested | Claude Code, this worktree | "
                "`benchmaker` composition |\n"
                "| weak | `claude-sonnet-5` | `high`, requested | same | same |"
            ),
            "",
        ]
    if "incomparability" in sections:
        parts += ["### Incomparability", "", incomparability, ""]
    if "scope" in sections:
        parts += [
            "### Measured scope",
            "",
            scope
            if scope is not None
            else (
                "Public subset. Unavailable to every probe in this pass: "
                + ", ".join("`%s`" % path for path in PROTECTED)
                + ". Withheld from every candidate context: `expected.md`, `seeds/`, "
                "`probe/`, `case.toml`, and every case directory but the one measured."
            ),
            "",
        ]
    if "figures" in sections:
        parts += [
            "### Figures (redesign-spec §5)",
            "",
            figures if figures is not None else figure_table(rows, figure_overrides),
            "",
        ]
    for row in rows:
        parts += [
            "### Row — %s" % row.get("case", "unnamed"),
            "",
            "```json",
            json.dumps(row, indent=2, ensure_ascii=False),
            "```",
            "",
        ]
    return "\n".join(parts)


def record_text(entries, preamble_verify=True) -> str:
    head = ["# BenchMaker measurements", "", "One entry per measurement event, newest first.", ""]
    if preamble_verify:
        head += ["Verify with, from the repository root:", "", "    python tools/validate_measures.py", ""]
    return "\n".join(head + list(entries)) + "\n"


def run(record: str, cases_dir=None):
    """(exit code, output lines) for a flagless run over one record."""
    path = WORLD.write_record(record)
    stream = io.StringIO()
    with contextlib.redirect_stdout(stream):
        code = vm.main(["--record", str(path), "--cases-dir", str(cases_dir or WORLD.cases_dir)])
    output = stream.getvalue()
    return code, [line for line in output.splitlines() if line]


def full(**kwargs):
    return record_text([entry_text(rows_for(FULL_PLAN), **kwargs)])


def one(**kwargs):
    kwargs.setdefault("incomplete", 1)
    return record_text([entry_text(rows_for(ONE_PLAN), **kwargs)])


def mutate(plan, case, change):
    """The plan's rows with one row rewritten by ``change``."""
    rows = rows_for(plan)
    for row in rows:
        if row["case"] == case:
            change(row)
    return rows


class RecordCase(unittest.TestCase):
    def assertClean(self, record):
        code, lines = run(record)
        self.assertEqual((code, lines), (0, []))

    def assertViolation(self, record, needle, count=None, cases_dir=None):
        code, lines = run(record, cases_dir)
        self.assertEqual(code, 1, "expected a violation, got a clean run")
        self.assertTrue(
            any(needle in line for line in lines),
            "no violation mentioned %r; got:\n%s" % (needle, "\n".join(lines)),
        )
        if count is not None:
            self.assertEqual(len(lines), count, "\n".join(lines))
        return lines



# Compatibility seam: these classes retain their defining modules so unittest
# applies each partition's module fixture while this module remains the sole
# discovery entry point.
from tests.test_validate_measures_cases.record import (  # noqa: E402,F401
    TestClean, TestCompleteness, TestCoveredCaseSet, TestEntryIdiom,
    TestStatus, TestUnverified,
)
from tests.test_validate_measures_cases.evidence import (  # noqa: E402,F401
    TestCost, TestProtectedEvidence, TestRungIdentity, TestScope, TestTraceability,
)
from tests.test_validate_measures_cases.figure import TestFigures  # noqa: E402,F401
from tests.test_validate_measures_cases.row import (  # noqa: E402,F401
    TestCaseSchema, TestCheckerShape, TestRowMode, TestRowSchema,
)


if __name__ == "__main__":
    unittest.main()
