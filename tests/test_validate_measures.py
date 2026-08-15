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


# --------------------------------------------------------------------
# the clean fixtures — both completeness branches (A5)
# --------------------------------------------------------------------


class TestClean(RecordCase):
    def test_complete_entry_of_sixteen_rows_is_silent(self):
        self.assertClean(full())

    def test_incomplete_entry_declaring_its_shortfall_is_silent(self):
        self.assertClean(one())

    def test_entry_carrying_its_own_verify_command_is_silent(self):
        self.assertClean(record_text([entry_text(rows_for(FULL_PLAN), verify=True)], preamble_verify=False))

    def test_two_entries_newest_first_are_silent(self):
        newer = entry_text(rows_for(FULL_PLAN), date="2026-08-09")
        older = entry_text(rows_for(FULL_PLAN), date="2026-08-08")
        self.assertClean(record_text([newer, older]))


# --------------------------------------------------------------------
# C1 (A4) — the entry names the case set it measured, by git revision
# --------------------------------------------------------------------


class TestCoveredCaseSet(RecordCase):
    def test_case_set_named_by_a_full_revision_is_clean(self):
        self.assertClean(full(case_set=SET_REVISION))

    def test_case_set_named_by_an_abbreviated_revision_is_clean(self):
        self.assertClean(full(case_set=SET_REVISION[:7]))

    def test_entry_naming_no_case_set_is_reported(self):
        self.assertViolation(full(case_set=""), "case-set: names no case set", count=1)

    def test_entry_without_the_case_set_block_is_reported(self):
        record = full(sections=("rungs", "incomparability", "scope", "figures"))
        self.assertViolation(record, "case-set: names no case set", count=1)

    def test_a_digest_where_the_revision_belongs_is_reported(self):
        """The retired form is refused, not silently read as a revision."""
        self.assertViolation(
            full(case_set="sha256:" + "b" * 64), "case-set: names no case set", count=1
        )

    def test_a_bare_sixty_four_hex_digest_is_not_a_revision(self):
        self.assertViolation(full(case_set="b" * 64), "case-set: names no case set", count=1)

    def test_a_revision_too_short_to_resolve_is_reported(self):
        self.assertViolation(full(case_set="abc123"), "case-set: names no case set", count=1)


# --------------------------------------------------------------------
# C2 (A5) — sixteen rows, or a declaration naming every absent case
# --------------------------------------------------------------------


class TestCompleteness(RecordCase):
    def test_undeclared_missing_row_is_reported(self):
        rows = rows_for(FULL_PLAN[:-1])
        self.assertViolation(
            record_text([entry_text(rows)]), "has no row for case 'cs-workflow-fresh'"
        )

    def test_row_for_a_case_outside_the_set_is_reported(self):
        rows = rows_for(FULL_PLAN) + [make_row("cs-cli-fresh", "both-pass")]
        rows[-1]["case"] = "cs-invented"
        self.assertViolation(record_text([entry_text(rows)]), "no case directory 'cs-invented'")

    def test_misspelled_case_id_is_reported(self):
        rows = rows_for(FULL_PLAN)
        rows[1]["case"] = "cs-cli-frsh"
        lines = self.assertViolation(record_text([entry_text(rows)]), "no case directory 'cs-cli-frsh'")
        self.assertTrue(any("has no row for case 'cs-cli-fresh'" in line for line in lines))

    def test_duplicate_row_for_one_case_is_reported(self):
        rows = rows_for(FULL_PLAN) + [make_row("cs-cli-fresh", "split")]
        self.assertViolation(
            record_text([entry_text(rows)]), "appears in more than one row", count=1
        )

    def test_declared_count_below_the_rows_carried_is_reported(self):
        rows = rows_for(FULL_PLAN[:2])
        record = record_text([entry_text(rows, incomplete=1)])
        self.assertViolation(record, "declares 1 of 16 rows but carries 2", count=1)

    def test_incomplete_entry_must_name_every_absent_case(self):
        rows = rows_for(ONE_PLAN)
        absent = [case for case, _ in FULL_PLAN if case not in ("cs-cli-fresh", "cs-workflow-fresh")]
        record = record_text([entry_text(rows, incomplete=1, absent=absent)])
        self.assertViolation(record, "does not name the absent case 'cs-workflow-fresh'", count=1)

    def test_case_directory_that_is_not_sixteen_cases_is_reported(self):
        stream = io.StringIO()
        path = WORLD.write_record(full())
        with contextlib.redirect_stdout(stream):
            code = vm.main(
                ["--record", str(path), "--cases-dir", str(WORLD.cases_dir / "cs-cli-fresh")]
            )
        self.assertEqual(code, 1)
        self.assertIn("not the frozen 16", stream.getvalue())


# --------------------------------------------------------------------
# C3 (A6) — status recomputed from the verdict pair
# --------------------------------------------------------------------


class TestStatus(RecordCase):
    def test_pass_fail_labelled_both_pass_is_reported(self):
        def change(row):
            row["status"] = "both-pass"

        rows = mutate(FULL_PLAN, "cs-cli-fresh", change)
        self.assertViolation(record_text([entry_text(rows)]), "derives 'split'")

    def test_status_outside_the_enumeration_is_reported(self):
        def change(row):
            row["status"] = "mixed"

        rows = mutate(FULL_PLAN, "cs-cli-fresh", change)
        self.assertViolation(record_text([entry_text(rows)]), "is not one of")

    def test_unverified_verdict_stays_undetermined(self):
        """The fifth status is reachable only from an UNVERIFIED verdict."""

        def change(row):
            row["status"] = "both-pass"
            row["readings"] = ["a", "b"]

        rows = mutate(FULL_PLAN, "cs-nondet-fresh", change)
        self.assertViolation(record_text([entry_text(rows)]), "derives 'undetermined'")

    def test_undetermined_without_an_unverified_verdict_is_reported(self):
        def change(row):
            row["status"] = "undetermined"
            row["discriminating"] = False

        rows = mutate(FULL_PLAN, "cs-cli-fresh", change)
        self.assertViolation(record_text([entry_text(rows)]), "derives 'split'")


# --------------------------------------------------------------------
# C4 (A7) — never PASS or FAIL beside an unclean probe
# --------------------------------------------------------------------


class TestUnverified(RecordCase):
    def test_pass_against_a_crashed_probe_is_reported(self):
        def change(row):
            row["rungs"]["strong"]["trial_exit_codes"] = [124]
            row["rungs"]["strong"]["probe_exit_code"] = 124

        rows = mutate(FULL_PLAN, "cs-cli-fresh", change)
        self.assertViolation(record_text([entry_text(rows)]), "derive UNVERIFIED")

    def test_pass_against_a_canary_hit_is_reported(self):
        def change(row):
            row["rungs"]["strong"]["canary"] = "hit"

        rows = mutate(FULL_PLAN, "cs-cli-fresh", change)
        self.assertViolation(record_text([entry_text(rows)]), "derive UNVERIFIED", count=1)

    def test_fail_against_a_bound_overrun_is_reported(self):
        def change(row):
            row["rungs"]["weak"]["bound"]["status"] = "overrun"

        rows = mutate(FULL_PLAN, "cs-cli-fresh", change)
        self.assertViolation(record_text([entry_text(rows)]), "derive UNVERIFIED", count=1)

    def test_timeout_marker_recorded_as_fail_is_reported(self):
        def change(row):
            row["rungs"]["weak"]["trial_exit_codes"] = ["timeout after 60s"]
            row["rungs"]["weak"]["probe_exit_code"] = "timeout after 60s"

        rows = mutate(FULL_PLAN, "cs-cli-fresh", change)
        self.assertViolation(record_text([entry_text(rows)]), "derive UNVERIFIED")

    def test_wall_clock_past_the_ceiling_must_be_an_overrun(self):
        def change(row):
            row["rungs"]["strong"]["bound"]["probe_wall_clock_s"] = 90

        rows = mutate(FULL_PLAN, "cs-cli-fresh", change)
        self.assertViolation(record_text([entry_text(rows)]), "not 'overrun'", count=1)


# --------------------------------------------------------------------
# C5 (A8) — every verdict traces to an artifact and an exit code
# --------------------------------------------------------------------


class TestTraceability(RecordCase):
    def test_missing_artifact_identity_is_reported(self):
        def change(row):
            del row["rungs"]["strong"]["artifact_identity"]

        rows = mutate(FULL_PLAN, "cs-cli-fresh", change)
        self.assertViolation(record_text([entry_text(rows)]), "lacks 'artifact_identity'", count=1)

    def test_missing_probe_exit_code_is_reported(self):
        def change(row):
            del row["rungs"]["weak"]["probe_exit_code"]

        rows = mutate(FULL_PLAN, "cs-cli-fresh", change)
        lines = self.assertViolation(record_text([entry_text(rows)]), "lacks 'probe_exit_code'")
        self.assertTrue(any("does not govern its trials" in line for line in lines))

    def test_artifact_identity_that_does_not_recompute_is_reported(self):
        def change(row):
            row["rungs"]["strong"]["artifact_identity"] = "sha256:" + "c" * 64

        rows = mutate(FULL_PLAN, "cs-cli-fresh", change)
        self.assertViolation(record_text([entry_text(rows)]), "does not recompute over", count=1)

    def test_artifact_path_that_does_not_resolve_is_reported(self):
        def change(row):
            row["rungs"]["weak"]["artifact_path"] = str(WORLD.root / "no-such-artifact")

        rows = mutate(FULL_PLAN, "cs-cli-fresh", change)
        self.assertViolation(record_text([entry_text(rows)]), "does not resolve to a directory", count=1)

    def test_artifact_file_count_that_disagrees_is_reported(self):
        def change(row):
            row["rungs"]["strong"]["artifact_files"] = 99

        rows = mutate(FULL_PLAN, "cs-cli-fresh", change)
        self.assertViolation(record_text([entry_text(rows)]), "artifact_files 99 but", count=1)

    def test_probe_exit_code_that_does_not_govern_its_trials_is_reported(self):
        def change(row):
            row["rungs"]["weak"]["probe_exit_code"] = 0

        rows = mutate(FULL_PLAN, "cs-cli-fresh", change)
        self.assertViolation(record_text([entry_text(rows)]), "does not govern its trials", count=1)


# --------------------------------------------------------------------
# C6 (A9) — candidate identity per rung, and the incomparability statement
# --------------------------------------------------------------------


class TestRungIdentity(RecordCase):
    def test_rung_row_without_an_effort_cell_is_reported(self):
        table = (
            "| rung | model id | effort | host binding | scaffold |\n"
            "| --- | --- | --- | --- | --- |\n"
            "| strong | `claude-opus-5` |  | Claude Code, this worktree | `benchmaker` |\n"
            "| weak | `claude-sonnet-5` | `high` | same | same |"
        )
        self.assertViolation(full(rung_table=table), "must name model id, effort", count=1)

    def test_absent_rung_row_is_reported(self):
        table = (
            "| rung | model id | effort | host binding | scaffold |\n"
            "| --- | --- | --- | --- | --- |\n"
            "| strong | `claude-opus-5` | `xhigh` | Claude Code | `benchmaker` |"
        )
        self.assertViolation(full(rung_table=table), "has no 'weak' row", count=1)

    def test_row_model_that_contradicts_the_rungs_table_is_reported(self):
        def change(row):
            row["rungs"]["strong"]["model"] = "claude-haiku-5"

        rows = mutate(FULL_PLAN, "cs-cli-fresh", change)
        self.assertViolation(
            record_text([entry_text(rows)]), "but the Rungs table declares", count=1
        )

    def test_row_effort_that_contradicts_the_rungs_table_is_reported(self):
        def change(row):
            row["rungs"]["weak"]["effort_requested"] = "xhigh"

        rows = mutate(FULL_PLAN, "cs-cli-fresh", change)
        self.assertViolation(record_text([entry_text(rows)]), "effort_requested", count=1)

    def test_absent_incomparability_section_is_reported(self):
        record = full(sections=("case set", "rungs", "scope", "figures"))
        self.assertViolation(record, "has no '### Incomparability' section", count=1)

    def test_empty_incomparability_statement_is_reported(self):
        self.assertViolation(full(incomparability="See above."), "states no incomparability", count=1)


# --------------------------------------------------------------------
# C7 (A10) — measured scope
# --------------------------------------------------------------------


class TestScope(RecordCase):
    def test_absent_scope_section_is_reported(self):
        record = full(sections=("case set", "rungs", "incomparability", "figures"))
        self.assertViolation(record, "has no '### Measured scope' section", count=1)

    def test_scope_that_omits_the_protected_workload_is_reported(self):
        scope = (
            "Public subset. Unavailable: `cs-nondet-fresh/streams.json`, `stream-held-1.json`, "
            "`stream-held-2.json`, `stream-held-3.json`. Withheld from candidates: "
            "`expected.md`, `seeds/`, `probe/`."
        )
        self.assertViolation(
            full(scope=scope), "does not name cs-antigoodhart-2/workload.json", count=1
        )

    def test_scope_that_omits_a_withheld_input_is_reported(self):
        scope = (
            "Public subset. Unavailable: " + ", ".join("`%s`" % p for p in PROTECTED)
            + ". Withheld from candidates: `expected.md`, `probe/`."
        )
        self.assertViolation(full(scope=scope), "does not name seeds/ as withheld", count=1)


class TestProtectedEvidence(RecordCase):
    """The scope check's own input: the covered manifest.

    The one live file this suite reads. A shape change to it must fail
    here, because the alternative is what happened on 2026-08-09 — the
    reader answered "no protected files", the scope check required
    nothing, and the run stayed green.
    """

    @contextlib.contextmanager
    def package(self, manifest):
        """A second synthetic package carrying ``manifest``, or none."""
        with tempfile.TemporaryDirectory() as tmp:
            path = World(Path(tmp).resolve()).root / "manifest.json"
            if manifest is None:
                path.unlink()
            else:
                path.write_text(manifest, encoding="utf-8")
            yield path.parent / "cases"

    def test_the_live_manifest_yields_its_five_protected_paths(self):
        live = REPO_ROOT / "benchmarks" / "benchmaker" / "cases"
        self.assertEqual(vm.protected_files(live), PROTECTED)

    def test_scope_that_omits_a_path_only_the_manifest_names_is_reported(self):
        """`stream-held-3.json` is in no module constant: only the
        manifest requires it, so this fails if the manifest goes unread."""
        scope = (
            "Public subset. Unavailable: " + ", ".join("`%s`" % p for p in PROTECTED[:-1])
            + ". Withheld from candidates: `expected.md`, `seeds/`, `probe/`."
        )
        self.assertViolation(full(scope=scope), "does not name stream-held-3.json", count=1)

    def test_a_manifest_that_names_no_protected_files_is_refused(self):
        with self.package('{"anchors": {}}') as cases_dir:
            self.assertViolation(
                full(), "protected-evidence: ", count=1, cases_dir=cases_dir
            )

    def test_a_manifest_whose_protected_files_is_not_a_list_is_refused(self):
        """The 2026-08-09 shape change, inverted: the old map form."""
        with self.package('{"protected_evidence": {"files": {"a.json": "sha256:0"}}}') as cases_dir:
            self.assertViolation(
                full(), "states no 'protected_evidence.files' list", count=1, cases_dir=cases_dir
            )

    def test_an_absent_manifest_is_refused(self):
        with self.package(None) as cases_dir:
            self.assertViolation(
                full(), "protected-evidence: cannot read", count=1, cases_dir=cases_dir
            )

    def test_a_manifest_that_does_not_parse_is_refused(self):
        with self.package("{not json") as cases_dir:
            self.assertViolation(
                full(), "protected-evidence: cannot read", count=1, cases_dir=cases_dir
            )


# --------------------------------------------------------------------
# C8 (A11) — the §5 figures, recomputed from the rows
# --------------------------------------------------------------------


class TestFigures(RecordCase):
    def test_resolution_below_the_stated_spread_is_reported(self):
        figures = figure_table(rows_for(FULL_PLAN)).replace(
            "rerun spread is **unmeasured**; the three-trial cases have not rerun",
            "measured rerun spread is 3 cases across the three-trial cases",
        )
        self.assertViolation(full(figures=figures), "1 case(s) but max(", count=1)

    def test_resolution_matching_a_measured_spread_is_clean(self):
        figures = figure_table(
            rows_for(FULL_PLAN),
            {"resolution": "`max(measured rerun spread, 1 case)` = **3 cases**"},
        ).replace(
            "rerun spread is **unmeasured**; the three-trial cases have not rerun",
            "measured rerun spread is 3 cases across the three-trial cases",
        )
        self.assertClean(full(figures=figures))

    def test_resolution_without_the_formula_is_reported(self):
        self.assertViolation(
            full(figure_overrides={"resolution": "**1 case**"}),
            "must be stated as max(measured rerun spread, 1 case)",
        )

    def test_resolution_without_a_stated_spread_is_reported(self):
        figures = figure_table(rows_for(FULL_PLAN)).replace(
            "rerun spread is **unmeasured**; the three-trial cases have not rerun",
            "the floor stands on its one-case term",
        )
        self.assertViolation(full(figures=figures), "does not state the measured rerun spread", count=1)

    def test_absent_figure_row_is_reported(self):
        figures = "\n".join(
            line
            for line in figure_table(rows_for(FULL_PLAN)).splitlines()
            if not line.startswith("| margin in cases")
        )
        self.assertViolation(full(figures=figures), "has no 'margin in cases' row", count=1)

    def test_status_distribution_that_contradicts_the_rows_is_reported(self):
        self.assertViolation(
            full(figure_overrides={"status distribution": "`split` 9; `both-pass` 7"}),
            "states split 9 but 3 row(s) carry it",
        )

    def test_status_distribution_omitting_a_status_the_rows_carry_is_reported(self):
        self.assertViolation(
            full(figure_overrides={"status distribution": "`split` 3; `both-pass` 7; `both-fail` 4; `inversion` 1"}),
            "omits undetermined",
            count=1,
        )

    def test_discriminating_set_that_contradicts_the_rows_is_reported(self):
        self.assertViolation(
            full(figure_overrides={"discriminating set": "`cs-cli-fresh`"}),
            "the discriminating set figure names",
            count=1,
        )

    def test_inversions_figure_that_hides_an_inversion_is_reported(self):
        self.assertViolation(
            full(figure_overrides={"inversions": "none"}), "the inversions figure names", count=1
        )

    def test_margin_that_contradicts_the_rows_is_reported(self):
        self.assertViolation(
            full(figure_overrides={"margin in cases": "8 (strong 10/16, weak 2/16)"}),
            "the margin figure states 8 but the rows derive 1",
            count=1,
        )

    def test_empty_discriminating_set_must_say_so(self):
        plan = tuple((case, "both-fail") for case, _ in FULL_PLAN)
        rows = rows_for(plan)
        figures = figure_table(rows, {"discriminating set": "the split bucket"})
        self.assertViolation(
            record_text([entry_text(rows, figures=figures)]),
            "the discriminating set figure is empty and must say so",
            count=1,
        )


# --------------------------------------------------------------------
# C9 (A12) — measured cost per case per rung, against the declared bound
# --------------------------------------------------------------------


class TestCost(RecordCase):
    def test_weak_rung_without_a_cost_block_is_reported(self):
        def change(row):
            del row["rungs"]["weak"]["cost_actual"]

        rows = mutate(FULL_PLAN, "cs-cli-fresh", change)
        lines = self.assertViolation(record_text([entry_text(rows)]), "lacks 'cost_actual'")
        self.assertTrue(any("'cost_actual' is not an object" in line for line in lines))

    def test_cost_field_that_is_not_a_number_is_reported(self):
        def change(row):
            row["rungs"]["strong"]["cost_actual"]["subagent_tokens"] = "lots"

        rows = mutate(FULL_PLAN, "cs-cli-fresh", change)
        self.assertViolation(
            record_text([entry_text(rows)]), "cost_actual 'subagent_tokens' must be", count=1
        )

    def test_missing_cost_key_is_reported(self):
        def change(row):
            del row["rungs"]["weak"]["cost_actual"]["wall_ms"]

        rows = mutate(FULL_PLAN, "cs-cli-fresh", change)
        self.assertViolation(record_text([entry_text(rows)]), "cost_actual lacks 'wall_ms'", count=1)

    def test_bound_that_is_not_the_case_declared_bound_is_reported(self):
        def change(row):
            row["rungs"]["strong"]["bound"]["declared"] = "two BC1 shares"

        rows = mutate(FULL_PLAN, "cs-cli-fresh", change)
        self.assertViolation(
            record_text([entry_text(rows)]),
            "does not match the case's declared execution bound",
            count=1,
        )

    def test_predecessor_format_bound_still_matches(self):
        # A row recorded before `bound` became `exec_bound` quotes the
        # conflated string. The record is a fact and is not rewritten;
        # the checker strips the construction clause before comparing.
        def change(row):
            row["rungs"]["strong"]["bound"]["declared"] = (
                "one BC1 share; " + DECLARED_BOUND
            )

        rows = mutate(FULL_PLAN, "cs-cli-fresh", change)
        self.assertClean(record_text([entry_text(rows)]))

    def test_predecessor_format_with_the_wrong_tier_still_fails(self):
        # The normalization drops the construction clause, not the check.
        def change(row):
            row["rungs"]["strong"]["bound"]["declared"] = (
                "one BC1 share; probe within large tier"
            )

        rows = mutate(FULL_PLAN, "cs-cli-fresh", change)
        self.assertViolation(
            record_text([entry_text(rows)]),
            "does not match the case's declared execution bound",
            count=1,
        )


# --------------------------------------------------------------------
# C10 (A15) — the entry idiom
# --------------------------------------------------------------------


class TestEntryIdiom(RecordCase):
    def test_entry_without_a_dated_header_is_reported(self):
        record = full().replace("## 2026-08-08 — two-rung", "## two-rung")
        self.assertViolation(record, "heading is not", count=1)

    def test_entries_out_of_newest_first_order_are_reported(self):
        older = entry_text(rows_for(FULL_PLAN), date="2026-08-01")
        newer = entry_text(rows_for(FULL_PLAN), date="2026-08-09")
        self.assertViolation(record_text([older, newer]), "not newest-first", count=1)

    def test_record_without_an_inline_verify_command_is_reported(self):
        record = record_text([entry_text(rows_for(FULL_PLAN))], preamble_verify=False)
        self.assertViolation(record, "names no inline command that verifies it", count=1)

    def test_record_with_no_entry_is_reported(self):
        self.assertViolation(record_text([]), "carries no entry", count=1)

    def test_entry_with_no_row_is_reported(self):
        record = record_text([entry_text([], incomplete=0)])
        self.assertViolation(record, "carries no case row")

    def test_unparsable_row_is_reported(self):
        record = full().replace('"case": "cs-cli-fresh"', '"case": cs-cli-fresh')
        self.assertViolation(record, "does not parse")


# --------------------------------------------------------------------
# the row schema T01-tracer-cs-cli-fresh froze
# --------------------------------------------------------------------


class TestRowSchema(RecordCase):
    def rows_with(self, case, change):
        return record_text([entry_text(mutate(FULL_PLAN, case, change))])

    def test_ambiguous_status_without_both_readings_is_reported(self):
        """§5: a both-fail row is genuinely hard or broken, and says both."""

        def change(row):
            row["readings"] = []

        self.assertViolation(
            self.rows_with("cs-judged-fresh", change), "admits two readings", count=1
        )

    def test_unambiguous_status_carrying_readings_is_reported(self):
        def change(row):
            row["readings"] = ["one reading too many"]

        self.assertViolation(self.rows_with("cs-cli-fresh", change), "must be empty", count=1)

    def test_discriminating_flag_that_is_not_the_split_flag_is_reported(self):
        def change(row):
            row["discriminating"] = True

        self.assertViolation(
            self.rows_with("cs-cost-fresh", change), "'discriminating' must be true", count=1
        )

    def test_passing_rung_that_lists_a_failed_check_is_reported(self):
        def change(row):
            row["failed_checks"]["strong"] = ["P0.a: something"]

        self.assertViolation(
            self.rows_with("cs-cost-fresh", change), "is PASS but lists failed checks", count=1
        )

    def test_failing_rung_that_names_no_failed_check_is_reported(self):
        def change(row):
            row["failed_checks"]["weak"] = []

        self.assertViolation(
            self.rows_with("cs-judged-fresh", change), "is FAIL but names no failed check", count=1
        )

    def test_failed_checks_missing_a_rung_is_reported(self):
        def change(row):
            del row["failed_checks"]["weak"]

        self.assertViolation(self.rows_with("cs-cli-fresh", change), "'failed_checks' must be")

    def test_trial_count_that_is_not_the_declared_count_is_reported(self):
        def change(row):
            row["rungs"]["weak"]["trial_exit_codes"] = [1, 1]

        self.assertViolation(
            self.rows_with("cs-judged-fresh", change), "against 1 declared trial(s)"
        )

    def test_trials_declared_that_is_not_positive_is_reported(self):
        def change(row):
            row["trials_declared"] = 0

        self.assertViolation(
            self.rows_with("cs-cli-fresh", change), "'trials_declared' must be a positive integer"
        )

    def test_angle_that_contradicts_case_toml_is_reported(self):
        def change(row):
            row["angle"] = "invented-angle"

        self.assertViolation(self.rows_with("cs-cli-fresh", change), "but case.toml declares", count=1)

    def test_size_that_contradicts_case_toml_is_reported(self):
        def change(row):
            row["size"] = "large"

        self.assertViolation(self.rows_with("cs-cli-fresh", change), "'size' is 'large'", count=1)

    def test_canary_outside_its_two_values_is_reported(self):
        def change(row):
            row["rungs"]["strong"]["canary"] = "probably fine"

        self.assertViolation(self.rows_with("cs-cli-fresh", change), "is not 'clean' or 'hit'", count=1)

    def test_artifact_identity_that_is_not_a_sha256_is_reported(self):
        def change(row):
            row["rungs"]["weak"]["artifact_identity"] = "the weak one"

        self.assertViolation(
            self.rows_with("cs-cli-fresh", change), "is not a sha256:<64 hex> identity"
        )

    def test_missing_top_level_key_is_reported(self):
        def change(row):
            del row["observations"]

        self.assertViolation(self.rows_with("cs-cli-fresh", change), "row lacks 'observations'")

    def test_empty_observations_list_is_reported(self):
        def change(row):
            row["observations"] = []

        self.assertViolation(
            self.rows_with("cs-cli-fresh", change), "'observations' must be a non-empty list", count=1
        )

    def test_empty_scope_statement_is_reported(self):
        def change(row):
            row["scope"] = "   "

        self.assertViolation(self.rows_with("cs-cli-fresh", change), "'scope' must be a non-empty", count=1)

    def test_verdict_outside_the_enumeration_is_reported(self):
        def change(row):
            row["rungs"]["strong"]["verdict"] = "GREEN"

        self.assertViolation(self.rows_with("cs-cli-fresh", change), "verdict 'GREEN' is not one of")

    def test_row_key_outside_the_schema_is_tolerated(self):
        """T01 froze the required keys, not a closed set: a lane may add."""
        record = record_text([entry_text(rows_for(ONE_PLAN), incomplete=1)]).replace(
            '"case": "cs-cli-fresh"', '"case": "cs-cli-fresh", "extra": 1', 1
        )
        self.assertClean(record)


# --------------------------------------------------------------------
# the row check's other input: the case's own declaration
# --------------------------------------------------------------------


class TestCaseSchema(RecordCase):
    """One injected lie, every state of `case.toml`.

    A row's angle is checked against what the case declares, so a
    `case.toml` the reader cannot use turns the comparison off rather
    than red — the shape T07 closed in `protected_files`. The same lie
    must be caught whether the declaration is readable or not.
    """

    LIE = "time-semantics"

    @contextlib.contextmanager
    def case_toml(self, text):
        """A second synthetic package whose cs-cli-fresh declaration is ``text``."""
        with tempfile.TemporaryDirectory() as tmp:
            cases = World(Path(tmp).resolve()).cases_dir
            path = cases / "cs-cli-fresh" / "case.toml"
            if text is None:
                path.unlink()
            else:
                path.write_text(text, encoding="utf-8")
            yield cases

    def lying_record(self):
        def change(row):
            row["angle"] = self.LIE

        return record_text([entry_text(mutate(FULL_PLAN, "cs-cli-fresh", change))])

    def assertLieCaught(self, declaration, needle):
        with self.case_toml(declaration) as cases_dir:
            lines = self.assertViolation(self.lying_record(), needle, cases_dir=cases_dir)
            self.assertEqual(
                1, len(lines), "the lie must be caught exactly once:\n" + "\n".join(lines)
            )

    def test_the_lie_is_caught_against_a_readable_declaration(self):
        """The control: the comparison itself works."""
        self.assertViolation(
            self.lying_record(), "but case.toml declares 'angle-1'", count=1
        )

    def test_the_lie_is_caught_when_the_declaration_carries_a_trailing_comment(self):
        """`validate_cases.py` blesses this line; this reader cannot use it."""
        self.assertLieCaught(
            'id = "cs-cli-fresh"\nangle = "angle-1"  # the CLI row\n'
            'size = "small"\nexec_bound = "%s"\n' % DECLARED_BOUND,
            "case-schema",
        )

    def test_the_lie_is_caught_when_the_declaration_uses_a_literal_string(self):
        self.assertLieCaught(
            "id = 'cs-cli-fresh'\nangle = 'angle-1'\n"
            "size = 'small'\nexec_bound = '%s'\n" % DECLARED_BOUND,
            "case-schema",
        )

    def test_the_lie_is_caught_when_the_declaration_is_absent(self):
        with tempfile.TemporaryDirectory() as tmp:
            cases = World(Path(tmp).resolve()).cases_dir
            (cases / "cs-cli-fresh" / "case.toml").unlink()
            lines = self.assertViolation(
                self.lying_record(), "case-schema: cannot read", cases_dir=cases
            )
            self.assertEqual(1, len(lines), "\n".join(lines))

    def test_a_declaration_outside_the_subset_is_refused_with_no_lie_present(self):
        """The refusal is the missing reading, not the contradiction."""
        with self.case_toml(
            'id = "cs-cli-fresh"\nangle = "angle-1"\nsize = "small"\n'
        ) as cases_dir:
            self.assertViolation(
                full(), "states no 'exec_bound'", count=1, cases_dir=cases_dir
            )

    def test_case_keys_reads_every_live_case(self):
        """The narrow subset is a claim about the frozen set; here it is checked."""
        live = REPO_ROOT / "benchmarks" / "benchmaker" / "cases"
        for case in sorted(entry.name for entry in live.iterdir() if entry.is_dir()):
            self.assertEqual(set(vm.CASE_KEYS), set(vm.case_keys(live, case)), case)


# --------------------------------------------------------------------
# C11 (A13) — the checker's own shape
# --------------------------------------------------------------------


STDLIB = frozenset(
    """__future__ argparse ast collections contextlib copy hashlib io json os pathlib
    re shlex subprocess sys tempfile unittest""".split()
)


class TestCheckerShape(unittest.TestCase):
    def test_checker_imports_only_the_standard_library(self):
        tree = ast.parse((REPO_ROOT / "tools" / "validate_measures.py").read_text(encoding="utf-8"))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                imported.add(node.module.split(".")[0])
        self.assertEqual(imported - STDLIB, set())

    def test_clean_record_prints_nothing_at_all(self):
        path = WORLD.write_record(full())
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            code = vm.main(["--record", str(path), "--cases-dir", str(WORLD.cases_dir)])
        self.assertEqual((code, stream.getvalue()), (0, ""))

    def test_every_violation_line_carries_one_scope_and_one_message(self):
        rows = rows_for(FULL_PLAN)
        rows[1]["status"] = "both-pass"
        del rows[3]["rungs"]["weak"]["cost_actual"]
        rows[5]["rungs"]["strong"]["canary"] = "hit"
        code, lines = run(record_text([entry_text(rows)]))
        self.assertEqual(code, 1)
        self.assertTrue(lines)
        for line in lines:
            scope, separator, message = line.partition(": ")
            self.assertTrue(scope.startswith("ERROR "), line)
            self.assertEqual(separator, ": ", line)
            self.assertTrue(message.strip(), line)

    def test_no_violation_is_reported_twice(self):
        rows = rows_for(FULL_PLAN)
        rows[1]["rungs"]["strong"]["canary"] = "hit"
        _, lines = run(record_text([entry_text(rows)]))
        self.assertEqual(len(set(lines)), len(lines), "\n".join(lines))


# --------------------------------------------------------------------
# --row: the single-row convenience the case lanes use
# --------------------------------------------------------------------


class TestRowMode(unittest.TestCase):
    def row_file(self, text):
        """One file per distinct row text, named for the text.

        Every test in this class wrote the same ``row.md``, so each one
        depended on the previous one's content being overwritten before it
        read: a test that failed after writing left the next one a file it
        did not author. Named for the text, no two tests share a path.
        """

        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
        path = WORLD.root / ("row-%s.md" % digest)
        path.write_text(text, encoding="utf-8")
        return path

    def run_row(self, path):
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            code = vm.main(["--row", str(path), "--cases-dir", str(WORLD.cases_dir)])
        return code, [line for line in stream.getvalue().splitlines() if line]

    def block(self, row):
        return "# Row\n\n```json\n%s\n```\n" % json.dumps(row, indent=2, ensure_ascii=False)

    def test_valid_row_file_is_clean(self):
        path = self.row_file(self.block(make_row("cs-cli-fresh", "split")))
        self.assertEqual(self.run_row(path), (0, []))

    def test_row_file_violation_is_reported(self):
        row = copy.deepcopy(make_row("cs-cli-fresh", "split"))
        row["status"] = "both-pass"
        path = self.row_file(self.block(row))
        code, lines = self.run_row(path)
        self.assertEqual(code, 1)
        self.assertTrue(any("derives 'split'" in line for line in lines))

    def test_row_file_with_two_blocks_is_reported(self):
        row = make_row("cs-cli-fresh", "split")
        path = self.row_file(self.block(row) + self.block(row))
        code, lines = self.run_row(path)
        self.assertEqual(code, 1)
        self.assertTrue(any("expected exactly 1" in line for line in lines))

    def test_absent_row_file_is_reported(self):
        code, lines = self.run_row(WORLD.root / "no-such-row.md")
        self.assertEqual(code, 1)
        self.assertTrue(any("no such file" in line for line in lines))


if __name__ == "__main__":
    unittest.main()
