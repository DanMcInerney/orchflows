"""The ticket script's view path: `worklog` renders a run, `gate` writes
its gate stubs.

contracts/worklog.md: the worklog is a view `tickets.py` renders from
the ticket directory, never a second hand-written file; work-item.md Root ticket: a root
ticket's subtree ends in `<root>.gate.critique.<lens>`,
`<root>.gate.repair`, `<root>.gate.verify`. `tests/test_tickets.py`
covers the query path and `tests/test_tickets_issue.py` the issue path;
the sink idiom (a temporary `ORCHFLOWS_STATE_HOME`) is the same one,
restated here rather than imported so this module runs alone under
`tools/run_tests.py`'s per-module child.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import scripts.tickets as tickets_mod  # noqa: E402

TICKETS_PY = ROOT / "scripts" / "tickets.py"
FIX_TEMPLATE = ROOT / "compositions" / "fix"
STATE_HOME_ENV_VAR = "ORCHFLOWS_STATE_HOME"

GOOD_CRITERION = (
    "the suite exits 0 | oracle: `python -m unittest` | oracle_class: deterministic"
)

TICKET = """---
id: {tid}
run: testrun
status: {status}
executor: {executor}
depends_on: {deps}
write_scope: []
bound: 30m
claimed_by: {claimed_by}
claimed_at: {claimed_at}
---

## Objective

{objective}

## Fixed inputs

None.

## Completion test

- {criterion}

## Return fields

status; result.

## Result

{result}

## Verification

{verification}

## Feedback

{feedback}

## Risks

[]
"""


def use_sink(tmp: Path) -> Path:
    """Point ``ORCHFLOWS_STATE_HOME`` at a sink under this test's tempdir.

    Set for the process rather than restored: ``tests/__init__.py`` holds
    the floor at a temporary directory regardless, so the worst a stale
    value can do is fail a test, never reach the real sink.
    """

    sink = (tmp / "state-sink").resolve()
    os.environ[STATE_HOME_ENV_VAR] = str(sink)
    return sink


def run_cmd(*args):
    """One dispatch in this process, as the payload a reader of stdout gets."""

    payload = tickets_mod._dispatch([str(arg) for arg in args])
    return json.loads(json.dumps(payload, ensure_ascii=False))


def run_full(cwd: Path, *args):
    """A real process: exit code and one JSON document on stdout."""

    return subprocess.run(
        [sys.executable, str(TICKETS_PY), *[str(a) for a in args]],
        capture_output=True, text=True, encoding="utf-8",
        errors="replace", cwd=str(cwd),
    )


def ticket(tid: str, *, status: str = "complete", executor: str = "orch-tdd",
           deps: str = "[]", claimed_at: str = "", claimed_by: str = "agent-a",
           objective: str = "one end state", criterion: str = GOOD_CRITERION,
           result: str = "", verification: str = "", feedback: str = "[]",
           pack: str = "") -> str:
    text = TICKET.format(
        tid=tid, status=status, executor=executor, deps=deps,
        claimed_at=claimed_at, claimed_by=claimed_by, objective=objective,
        criterion=criterion, result=result, verification=verification,
        feedback=feedback,
    )
    if pack:
        text = text.replace(
            f"executor: {executor}\n", f"executor: {executor}\npack: {pack}\n", 1
        )
    return text


def make_run(sink: Path, tickets: dict) -> Path:
    run_dir = sink / "tickets" / "testrun"
    run_dir.mkdir(parents=True, exist_ok=True)
    for tid, text in tickets.items():
        (run_dir / f"{tid}.md").write_text(text, encoding="utf-8")
    return run_dir


def three_ticket_run() -> dict:
    """A root ticket, two units under it, and a gate the second feeds."""

    return {
        "R": ticket(
            "R", status="claimed", executor="orch-decompose",
            objective="the whole delivery lands", claimed_at="2026-08-15T09:00:00Z",
            criterion="every unit ticket is complete | oracle: `tickets.py list` "
            "| oracle_class: deterministic",
        ),
        "R.01": ticket(
            "R.01", status="complete", claimed_at="2026-08-15T09:10:00Z",
            objective="the first unit", verification="PASS: the suite exits 0",
            result="changed scripts/one.py",
        ),
        "R.02": ticket(
            "R.02", status="failed", claimed_at="2026-08-15T09:20:00Z",
            objective="the second unit", verification="FAIL: the suite exits 1",
            result="tried widening the parser", feedback="the parser is the wrong seam",
        ),
        "R.03": ticket(
            "R.03", status="pending", deps="[R.gate.verify]",
            claimed_by="", objective="the successor", verification="",
        ),
    }


class WorklogViewTest(unittest.TestCase):
    """`worklog <run>` renders the run from its tickets: goal, iterations,
    failed approaches, queued scope, terminal."""

    def render(self, *extra) -> str:
        payload = run_cmd("worklog", "testrun", *extra)
        self.assertNotIn("error", payload)
        return payload["worklog"]["markdown"]

    def test_every_section_of_the_view_is_rendered(self):
        with tempfile.TemporaryDirectory() as tmp:
            sink = use_sink(Path(tmp))
            make_run(sink, three_ticket_run())
            markdown = self.render()
            for heading in ("## goal", "## iterations", "## failed approaches",
                            "## queued scope", "## terminal"):
                self.assertIn(heading, markdown)

    def test_the_goal_is_the_root_tickets_objective_and_completion_test(self):
        with tempfile.TemporaryDirectory() as tmp:
            sink = use_sink(Path(tmp))
            make_run(sink, three_ticket_run())
            goal = self.render().split("## iterations")[0]
            self.assertIn("the whole delivery lands", goal)
            self.assertIn("every unit ticket is complete", goal)
            self.assertNotIn("the first unit", goal)

    def template_run(self) -> dict:
        """An instantiated template: three top-level cuts and a chain, the
        shape `compositions/benchmaker` instantiates to."""

        return {
            "00-acquire": ticket(
                "00-acquire", executor="orch-decompose",
                objective="the evidence is acquired"),
            "01-design": ticket("01-design", deps="[00-acquire]",
                                objective="the evaluation is designed"),
            "02-materialize": ticket(
                "02-materialize", executor="orch-decompose", deps="[01-design]",
                objective="the benchmark is built"),
            "03-qualify": ticket(
                "03-qualify", executor="orch-decompose", deps="[02-materialize]",
                objective="the benchmark is qualified"),
            "05-measure": ticket("05-measure", deps="[03-qualify]",
                                 objective="the measurement is recorded"),
        }

    def test_a_template_runs_goal_is_its_terminal_not_its_first_decomposer(self):
        """contracts/work-item.md, Template and stub: the terminal stub's completion test is the
        template's done check. `_root_ticket` took the alphabetically-first
        decomposer, which for a template with several cuts is a stub in the
        middle of the graph — so the rendered goal was never the run's."""

        with tempfile.TemporaryDirectory() as tmp:
            sink = use_sink(Path(tmp))
            make_run(sink, self.template_run())
            payload = run_cmd("worklog", "testrun")["worklog"]
            self.assertEqual("05-measure", payload["root"])
            self.assertEqual("terminal", payload["goal_kind"])
            goal = payload["markdown"].split("## iterations")[0]
            self.assertIn("Terminal ticket `05-measure`", goal)
            self.assertIn("the measurement is recorded", goal)
            self.assertNotIn("the evidence is acquired", goal)

    def test_a_single_cut_run_still_reads_its_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            sink = use_sink(Path(tmp))
            make_run(sink, three_ticket_run())
            payload = run_cmd("worklog", "testrun")["worklog"]
            self.assertEqual("R", payload["root"])
            self.assertEqual("root", payload["goal_kind"])
            self.assertIn("Root ticket `R`", payload["markdown"])

    def test_the_root_is_the_decomposer_however_the_ids_sort(self):
        with tempfile.TemporaryDirectory() as tmp:
            sink = use_sink(Path(tmp))
            make_run(sink, {
                "A": ticket("A", objective="a unit that sorts first"),
                "Z": ticket("Z", executor="orch-decompose", deps="[A]",
                            objective="the root that sorts last"),
            })
            self.assertIn("the root that sorts last", self.render().split("## iterations")[0])

    def test_with_no_decomposer_the_root_is_the_ticket_nothing_depends_on(self):
        with tempfile.TemporaryDirectory() as tmp:
            sink = use_sink(Path(tmp))
            make_run(sink, {
                "A": ticket("A", objective="a unit that sorts first"),
                "Z": ticket("Z", deps="[A]", objective="the terminal ticket"),
            })
            self.assertIn("the terminal ticket", self.render().split("## iterations")[0])

    def test_iterations_carry_executor_status_and_verification_in_claim_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            sink = use_sink(Path(tmp))
            make_run(sink, three_ticket_run())
            iterations = self.render().split("## iterations")[1].split("## failed")[0]
            self.assertLess(iterations.index("R.01"), iterations.index("R.02"))
            self.assertLess(iterations.index("R"), iterations.index("R.01"))
            self.assertIn("orch-tdd", iterations)
            self.assertIn("PASS: the suite exits 0", iterations)
            self.assertIn("FAIL: the suite exits 1", iterations)

    def test_a_failed_ticket_contributes_its_result_and_its_feedback(self):
        with tempfile.TemporaryDirectory() as tmp:
            sink = use_sink(Path(tmp))
            make_run(sink, three_ticket_run())
            failed = self.render().split("## failed approaches")[1].split("## queued")[0]
            self.assertIn("R.02", failed)
            self.assertIn("tried widening the parser", failed)
            self.assertIn("the parser is the wrong seam", failed)
            self.assertNotIn("R.01", failed)

    def test_an_iteration_ticket_is_a_failed_approach_whatever_its_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            sink = use_sink(Path(tmp))
            make_run(sink, {
                "L": ticket("L", executor="orch-loop", objective="the loop"),
                "L.iter.01": ticket("L.iter.01", status="complete",
                                    result="pass one narrowed the parser"),
            })
            failed = self.render().split("## failed approaches")[1].split("## queued")[0]
            self.assertIn("L.iter.01", failed)
            self.assertIn("pass one narrowed the parser", failed)

    def test_queued_scope_is_what_waits_behind_the_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            sink = use_sink(Path(tmp))
            make_run(sink, three_ticket_run())
            queued = self.render().split("## queued scope")[1].split("## terminal")[0]
            self.assertIn("R.03", queued)
            self.assertNotIn("R.01", queued)

    def test_terminal_is_empty_while_the_root_is_still_claimed(self):
        """contracts/worklog.md: `terminal` is empty until the run exits.
        A `claimed` root is a run that has not exited, and rendering that
        lifecycle state here answers "how did this run end" with a state
        no reader may act on."""

        with tempfile.TemporaryDirectory() as tmp:
            sink = use_sink(Path(tmp))
            make_run(sink, three_ticket_run())
            self.assertEqual("", self.render().split("## terminal")[1].strip())

    def test_terminal_is_the_root_tickets_status_once_it_is_terminal(self):
        with tempfile.TemporaryDirectory() as tmp:
            sink = use_sink(Path(tmp))
            run_dir = make_run(sink, three_ticket_run())
            (run_dir / "R.md").write_text(
                ticket("R", status="complete", executor="orch-decompose",
                       objective="the whole delivery lands"),
                encoding="utf-8",
            )
            self.assertIn("complete", self.render().split("## terminal")[1])

    def test_a_loop_run_reads_its_goal_and_its_exit_off_the_loop_ticket(self):
        """A loop run has no `orch-decompose` root: the loop ticket is the
        one nothing depends on, so its `## Objective` and its done-check
        (`## Completion test`) are the goal, and its own `stalled` exit is
        the run's."""

        with tempfile.TemporaryDirectory() as tmp:
            sink = use_sink(Path(tmp))
            make_run(sink, {
                "L": ticket("L", status="stalled", executor="orch-loop",
                            objective="the flake is gone",
                            criterion="the suite is green twice running "
                            "| oracle: the suite | oracle_class: deterministic"),
                "L.iter.01": ticket("L.iter.01", status="complete",
                                    result="pass one narrowed the parser"),
            })
            markdown = self.render()
            goal = markdown.split("## goal")[1].split("## iterations")[0]
            self.assertIn("the flake is gone", goal)
            self.assertIn("the suite is green twice running", goal)
            self.assertIn("stalled", markdown.split("## terminal")[1])

    def test_an_empty_or_unknown_run_is_a_named_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            use_sink(Path(tmp))
            payload = run_cmd("worklog", "testrun")
            self.assertIn("error", payload)
            self.assertIn("testrun", payload["error"])


class WorklogWriteTest(unittest.TestCase):
    """`--write` puts the view where contracts/worklog.md's readers look,
    and never over a file it did not render."""

    def worklog_path(self, sink: Path) -> Path:
        return sink / "runs" / "testrun" / "worklog.md"

    def test_write_lands_under_runs_and_carries_the_marker(self):
        with tempfile.TemporaryDirectory() as tmp:
            sink = use_sink(Path(tmp))
            make_run(sink, three_ticket_run())
            payload = run_cmd("worklog", "testrun", "--write")
            self.assertNotIn("error", payload)
            path = self.worklog_path(sink)
            self.assertEqual(str(path), payload["worklog"]["path"])
            text = path.read_text(encoding="utf-8")
            self.assertTrue(text.startswith(tickets_mod.WORKLOG_RENDER_MARKER))
            self.assertIn("## iterations", text)

    def test_a_note_and_the_rendered_view_are_two_files_in_one_run(self):
        """F1's split: `run-state --note` has its own file, so the view
        `--write` lands is never a file some other writer owns."""

        with tempfile.TemporaryDirectory() as tmp:
            sink = use_sink(Path(tmp))
            make_run(sink, three_ticket_run())
            noted = run_cmd("run-state", "testrun", "--note", "slice one landed")
            notes = sink / "runs" / "testrun" / tickets_mod.RUN_NOTES_NAME
            self.assertEqual(str(notes), noted["run_state"]["path"])
            payload = run_cmd("worklog", "testrun", "--write")
            self.assertNotIn("error", payload)
            self.assertEqual(str(self.worklog_path(sink)), payload["worklog"]["path"])
            self.assertEqual("slice one landed\n", notes.read_text(encoding="utf-8"))
            self.assertTrue(
                self.worklog_path(sink)
                .read_text(encoding="utf-8")
                .startswith(tickets_mod.WORKLOG_RENDER_MARKER)
            )

    def test_a_second_render_replaces_the_first(self):
        with tempfile.TemporaryDirectory() as tmp:
            sink = use_sink(Path(tmp))
            run_dir = make_run(sink, three_ticket_run())
            run_cmd("worklog", "testrun", "--write")
            (run_dir / "R.02.md").write_text(
                ticket("R.02", status="complete", claimed_at="2026-08-15T09:20:00Z",
                       objective="the second unit", verification="PASS: repaired"),
                encoding="utf-8",
            )
            run_cmd("worklog", "testrun", "--write")
            text = self.worklog_path(sink).read_text(encoding="utf-8")
            self.assertIn("PASS: repaired", text)
            self.assertNotIn("tried widening the parser", text)
            self.assertEqual(1, text.count(tickets_mod.WORKLOG_RENDER_MARKER))

    def test_a_hand_written_worklog_is_refused_and_survives(self):
        with tempfile.TemporaryDirectory() as tmp:
            sink = use_sink(Path(tmp))
            make_run(sink, three_ticket_run())
            path = self.worklog_path(sink)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("a note someone appended\n", encoding="utf-8")
            payload = run_cmd("worklog", "testrun", "--write")
            self.assertIn("error", payload)
            self.assertIn(str(path), payload["error"])
            self.assertEqual("a note someone appended\n", path.read_text(encoding="utf-8"))

    def test_without_write_nothing_lands(self):
        with tempfile.TemporaryDirectory() as tmp:
            sink = use_sink(Path(tmp))
            make_run(sink, three_ticket_run())
            run_cmd("worklog", "testrun")
            self.assertFalse(self.worklog_path(sink).exists())


class WorklogRendersTheLiveTemplateTest(unittest.TestCase):
    """The view against a real instantiated template rather than a fixture
    built to suit it: `compositions/fix`, four stubs, one chain."""

    def test_the_fix_template_renders_every_section(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            use_sink(tmp)
            payload = run_cmd(
                "instantiate", str(FIX_TEMPLATE), "--run", "testrun",
                "--set", "failure=the parser drops a trailing comma",
                "--set", "workspace=scripts/",
            )
            self.assertNotIn("error", payload)
            rendered = run_cmd("worklog", "testrun")
            self.assertNotIn("error", rendered)
            markdown = rendered["worklog"]["markdown"]
            for heading in ("## goal", "## iterations", "## failed approaches",
                            "## queued scope", "## terminal"):
                self.assertIn(heading, markdown)
            # 03-verify is the terminal stub, so it is the run's root
            self.assertIn("03-verify", markdown)
            self.assertIn("the parser drops a trailing comma", markdown)

    def test_the_process_prints_one_json_document_carrying_the_view(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            use_sink(tmp)
            run_cmd(
                "instantiate", str(FIX_TEMPLATE), "--run", "testrun",
                "--set", "failure=the parser drops a trailing comma",
                "--set", "workspace=scripts/",
            )
            result = run_full(tmp, "worklog", "testrun")
            self.assertEqual(0, result.returncode, result.stdout)
            self.assertIn("## goal", json.loads(result.stdout)["worklog"]["markdown"])


class GateStubsTest(unittest.TestCase):
    """`gate <run> <root>` writes work-item.md Root ticket's three stubs:
    critique per lens (read-only, parallel, over every unit ticket), one
    repair behind them all, one verify carrying the root's acceptance."""

    def make(self, sink: Path, units=("R.01", "R.02"), pack: str = "") -> Path:
        tickets = {
            "R": ticket(
                "R", status="claimed", executor="orch-decompose",
                objective="the whole delivery lands",
                criterion="the suite exits 0 | oracle: `python tools/run_tests.py` "
                "| oracle_class: deterministic | provenance: pre-existing",
                pack=pack,
            )
        }
        for unit in units:
            tickets[unit] = ticket(unit, deps="[R]", objective=f"unit {unit}")
        return make_run(sink, tickets)

    def gate(self, *extra):
        return run_cmd(
            "gate", "testrun", "R", "--lens", "cut-lens",
            "--write-scope", "scripts/one.py", *extra
        )

    def stub(self, run_dir: Path, tid: str) -> str:
        return (run_dir / f"{tid}.md").read_text(encoding="utf-8")

    def test_exactly_the_three_stubs_are_written(self):
        with tempfile.TemporaryDirectory() as tmp:
            sink = use_sink(Path(tmp))
            run_dir = self.make(sink)
            payload = self.gate()
            self.assertNotIn("error", payload)
            self.assertEqual(
                ["R.gate.critique.cut-lens", "R.gate.repair", "R.gate.verify"],
                payload["gate"]["ids"],
            )
            self.assertEqual(
                {"R", "R.01", "R.02", "R.gate.critique.cut-lens", "R.gate.repair",
                 "R.gate.verify"},
                {path.stem for path in run_dir.glob("*.md")},
            )

    def test_the_edges_run_units_to_critiques_to_repair_to_verify(self):
        with tempfile.TemporaryDirectory() as tmp:
            sink = use_sink(Path(tmp))
            run_dir = self.make(sink)
            self.gate()
            edges = {
                item["id"]: item["depends_on"]
                for item in run_cmd("list", "--run", "testrun")["tickets"]
            }
            self.assertEqual(["R.01", "R.02"], edges["R.gate.critique.cut-lens"])
            self.assertEqual(["R.gate.critique.cut-lens"], edges["R.gate.repair"])
            self.assertEqual(["R.gate.repair"], edges["R.gate.verify"])
            self.assertIn("status: pending", self.stub(run_dir, "R.gate.verify"))

    def test_the_critique_is_read_only_and_names_its_lens_and_the_acceptance(self):
        with tempfile.TemporaryDirectory() as tmp:
            sink = use_sink(Path(tmp))
            run_dir = self.make(sink)
            self.gate()
            text = self.stub(run_dir, "R.gate.critique.cut-lens")
            self.assertIn("executor: orch-critique", text)
            self.assertIn("write_scope: []", text)
            inputs = tickets_mod._sections(text)["Fixed inputs"]
            self.assertIn("cut-lens", inputs)
            self.assertIn("the suite exits 0", inputs)

    def test_the_repair_carries_the_given_write_scope(self):
        with tempfile.TemporaryDirectory() as tmp:
            sink = use_sink(Path(tmp))
            run_dir = self.make(sink)
            self.gate()
            text = self.stub(run_dir, "R.gate.repair")
            self.assertIn("executor: orch-repair", text)
            self.assertIn("write_scope: [scripts/one.py]", text)

    def test_the_repairs_body_states_its_scope_as_the_paths_it_grants(self):
        """A Python list repr is not a path anyone can grep for.

        The body rendered `['scripts\\\\one.py']` on Windows -- repr doubles
        every separator -- so the executor read one spelling in the frontmatter
        and another in the two sections that tell it what it may write.
        """

        with tempfile.TemporaryDirectory() as tmp:
            sink = use_sink(Path(tmp))
            run_dir = self.make(sink)
            payload = run_cmd(
                "gate", "testrun", "R", "--lens", "cut-lens",
                "--write-scope", "scripts\\one.py,docs/two.md",
            )
            self.assertNotIn("error", payload)
            sections = tickets_mod._sections(self.stub(run_dir, "R.gate.repair"))
            body = sections["Objective"] + sections["Fixed inputs"]
            for entry in (r"scripts\one.py", "docs/two.md"):
                self.assertIn(entry, body)
            self.assertNotIn("\\\\", body)
            self.assertNotIn("['", body)

    def test_the_critique_states_the_units_it_reads_as_a_list_of_ids(self):
        with tempfile.TemporaryDirectory() as tmp:
            sink = use_sink(Path(tmp))
            run_dir = self.make(sink)
            self.gate()
            inputs = tickets_mod._sections(
                self.stub(run_dir, "R.gate.critique.cut-lens")
            )["Fixed inputs"]
            self.assertIn("`R.01`", inputs)
            self.assertIn("`R.02`", inputs)
            self.assertNotIn("['", inputs)

    def test_the_verify_carries_the_roots_completion_test_verbatim(self):
        with tempfile.TemporaryDirectory() as tmp:
            sink = use_sink(Path(tmp))
            run_dir = self.make(sink)
            self.gate()
            text = self.stub(run_dir, "R.gate.verify")
            self.assertIn("executor: orch-verify", text)
            self.assertEqual(
                tickets_mod._sections(self.stub(run_dir, "R"))["Completion test"],
                tickets_mod._sections(text)["Completion test"],
            )

    def test_acceptance_can_be_taken_from_another_ticket(self):
        with tempfile.TemporaryDirectory() as tmp:
            sink = use_sink(Path(tmp))
            run_dir = self.make(sink)
            self.gate("--acceptance-from", "R.01")
            self.assertEqual(
                tickets_mod._sections(self.stub(run_dir, "R.01"))["Completion test"],
                tickets_mod._sections(self.stub(run_dir, "R.gate.verify"))["Completion test"],
            )

    def test_two_lenses_are_two_critiques_and_one_repair_behind_both(self):
        with tempfile.TemporaryDirectory() as tmp:
            sink = use_sink(Path(tmp))
            run_dir = self.make(sink)
            payload = run_cmd(
                "gate", "testrun", "R", "--lens", "cut-lens,craft",
                "--write-scope", "scripts/one.py",
            )
            self.assertNotIn("error", payload)
            self.assertEqual(
                ["R.gate.critique.craft", "R.gate.critique.cut-lens",
                 "R.gate.repair", "R.gate.verify"],
                sorted(payload["gate"]["ids"]),
            )
            edges = tickets_mod._parse_frontmatter(
                self.stub(run_dir, "R.gate.repair")
            )["depends_on"]
            self.assertEqual(
                ["R.gate.critique.craft", "R.gate.critique.cut-lens"], sorted(edges)
            )

    def test_one_root_owns_gate_files_and_distinct_lenses(self):
        with tempfile.TemporaryDirectory() as tmp:
            sink = use_sink(Path(tmp))
            run_dir = self.make(sink)
            duplicate = run_cmd(
                "gate", "testrun", "R", "--lens", "code,code",
                "--write-scope", "scripts/one.py",
            )
            self.assertIn("distinct", duplicate["error"])
            self.assertEqual([], list(run_dir.glob("R.gate.*.md")))

            created = run_cmd(
                "gate", "testrun", "R", "--lens", "code,security",
                "--write-scope", "scripts/one.py",
            )
            self.assertNotIn("error", created)
            self.assertEqual(["code", "security"], created["gate"]["lenses"])
            before = {
                path.name: path.read_bytes() for path in run_dir.glob("R.gate.*.md")
            }

            (run_dir / "Q.md").write_text(
                ticket(
                    "Q", status="claimed", executor="orch-decompose",
                    objective="a legacy second kind",
                ),
                encoding="utf-8",
            )
            (run_dir / "Q.01.md").write_text(
                ticket("Q.01", deps="[Q]", objective="legacy unit"),
                encoding="utf-8",
            )
            second = run_cmd(
                "gate", "testrun", "Q", "--lens", "content",
                "--write-scope", "docs/one.md",
            )
            self.assertIn("one gate", second["error"])
            self.assertIn("R", second["error"])
            self.assertEqual(before, {
                path.name: path.read_bytes() for path in run_dir.glob("R.gate.*.md")
            })
            self.assertEqual([], list(run_dir.glob("Q.gate.*.md")))

    def test_a_second_gate_is_refused_and_the_first_stubs_stand(self):
        with tempfile.TemporaryDirectory() as tmp:
            sink = use_sink(Path(tmp))
            run_dir = self.make(sink)
            self.gate()
            before = self.stub(run_dir, "R.gate.repair")
            payload = self.gate()
            self.assertIn("error", payload)
            self.assertIn("R.gate.critique.cut-lens", payload["error"])
            self.assertEqual(before, self.stub(run_dir, "R.gate.repair"))

    def test_a_root_with_no_unit_tickets_is_refused_and_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            sink = use_sink(Path(tmp))
            run_dir = self.make(sink, units=())
            payload = self.gate()
            self.assertIn("error", payload)
            self.assertIn("R.` subtree", payload["error"])
            self.assertEqual({"R"}, {path.stem for path in run_dir.glob("*.md")})

    def test_the_critique_depends_on_an_assembly_item_outside_the_nn_shape(self):
        """orch-decompose emits a terminal assembly item depending on every
        unit; no id shape is fixed for it. A critique that does not depend
        on it can complete -- taking the root with it -- while assembly is
        still running."""

        with tempfile.TemporaryDirectory() as tmp:
            sink = use_sink(Path(tmp))
            run_dir = self.make(sink)
            (run_dir / "R.assembly.md").write_text(
                ticket("R.assembly", status="pending", deps="[R.01,R.02]",
                       objective="the units become one deliverable"),
                encoding="utf-8",
            )
            self.gate()
            edges = {
                item["id"]: item["depends_on"]
                for item in run_cmd("list", "--run", "testrun")["tickets"]
            }
            self.assertEqual(
                ["R.01", "R.02", "R.assembly"],
                edges["R.gate.critique.cut-lens"],
            )

    def test_the_gate_stubs_are_not_their_own_dependencies(self):
        """The subtree the critique closes over excludes the gate itself:
        a critique depending on the repair that depends on it is a cycle."""

        with tempfile.TemporaryDirectory() as tmp:
            sink = use_sink(Path(tmp))
            self.make(sink)
            self.gate()
            edges = {
                item["id"]: item["depends_on"]
                for item in run_cmd("list", "--run", "testrun")["tickets"]
            }
            self.assertEqual(["R.01", "R.02"], edges["R.gate.critique.cut-lens"])

    def test_the_write_scope_defaults_to_the_root_tickets_own(self):
        """contracts/work-item.md: the root's `write_scope` is the run's
        scope and the repair holds it, so the caller states it once."""

        with tempfile.TemporaryDirectory() as tmp:
            sink = use_sink(Path(tmp))
            run_dir = self.make(sink)
            root = run_dir / "R.md"
            root.write_text(
                root.read_text(encoding="utf-8").replace(
                    "write_scope: []", "write_scope: [scripts/one.py]"
                ),
                encoding="utf-8",
            )
            payload = run_cmd("gate", "testrun", "R", "--lens", "cut-lens")
            self.assertNotIn("error", payload)
            self.assertIn(
                "write_scope: [scripts/one.py]", self.stub(run_dir, "R.gate.repair")
            )

    def test_an_unknown_root_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            sink = use_sink(Path(tmp))
            self.make(sink)
            payload = run_cmd(
                "gate", "testrun", "Q", "--lens", "cut-lens",
                "--write-scope", "scripts/one.py",
            )
            self.assertIn("error", payload)
            self.assertIn("Q", payload["error"])

    def test_the_lens_is_required_and_so_is_a_scope_to_default_to(self):
        """`--lens` has no source but the caller. `--write-scope` has one
        -- the root ticket -- so it is refused only when the root declares
        none either."""

        with tempfile.TemporaryDirectory() as tmp:
            sink = use_sink(Path(tmp))
            self.make(sink)
            for argv in (
                ("gate", "testrun", "R", "--write-scope", "scripts/one.py"),
                ("gate", "testrun", "R", "--lens", "cut-lens"),
            ):
                with self.subTest(argv=argv):
                    self.assertIn("error", run_cmd(*argv))

    def test_every_stub_is_a_ticket_the_dispatcher_accepts(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            sink = use_sink(tmp)
            run_dir = self.make(sink)
            self.gate()
            for tid in ("R.gate.critique.cut-lens", "R.gate.repair", "R.gate.verify"):
                with self.subTest(tid):
                    self.assertEqual([], tickets_mod.ticket_defects(self.stub(run_dir, tid)))
                    run_cmd("set-status", "testrun", tid, "ready")
                    payload = run_cmd("packet", "testrun", tid, "--reply-to", "main")
                    self.assertNotIn("error", payload)

    def test_every_stub_declares_its_independence_as_the_gate(self):
        """`rules/verification.md` §10: acceptance resting only on checks
        the executing context authored is UNVERIFIED, and the frontier's
        checker path keys on `independence: checker`. A gate lane authored
        none of these criteria and re-verification is the gate's own
        `<root>.gate.verify`, so the field says `gate` rather than reading
        `checker` by absence.
        """

        with tempfile.TemporaryDirectory() as tmp:
            sink = use_sink(Path(tmp))
            run_dir = self.make(sink)
            self.gate()
            for tid in ("R.gate.critique.cut-lens", "R.gate.repair",
                        "R.gate.verify"):
                with self.subTest(tid):
                    self.assertIn("independence: gate", self.stub(run_dir, tid))

    def test_every_criterion_the_gate_writes_is_pre_existing(self):
        """The script authored these criteria before the lane existed, so
        their provenance is the lane's, not the criterion's: `pre-existing`
        per contracts/work-item.md. The verify stub carries the root's own
        `## Completion test` verbatim and is not re-stamped here.
        """

        with tempfile.TemporaryDirectory() as tmp:
            sink = use_sink(Path(tmp))
            run_dir = self.make(sink)
            self.gate()
            for tid in ("R.gate.critique.cut-lens", "R.gate.repair"):
                with self.subTest(tid):
                    body = self.stub(run_dir, tid).split("## Completion test")[1]
                    body = body.split("## Return fields")[0]
                    self.assertNotIn("provenance: authored-here", body)
                    self.assertIn("provenance: pre-existing", body)

    def test_the_lens_defaults_to_the_stamped_packs_domain(self):
        """`--lens` names a label, and the pack's lens cell names none.

        The stamped pack's domain is that label -- the pack name without
        `orch-` and `-pack` -- so the decomposer that stamped the root has
        already said it and never has to improvise a second name.
        """

        with tempfile.TemporaryDirectory() as tmp:
            sink = use_sink(Path(tmp))
            run_dir = self.make(sink, pack="orch-code-pack")
            payload = run_cmd(
                "gate", "testrun", "R", "--write-scope", "scripts/one.py"
            )
            self.assertNotIn("error", payload)
            self.assertEqual(["code"], payload["gate"]["lenses"])
            self.assertIn("R.gate.critique.code", payload["gate"]["ids"])
            self.assertIn("`code`", self.stub(run_dir, "R.gate.critique.code"))

    def test_a_root_with_no_pack_still_requires_the_lens(self):
        """The default is the stamp's; a root carrying no stamp has none to
        read, and the refusal that names `--lens` stands."""

        with tempfile.TemporaryDirectory() as tmp:
            sink = use_sink(Path(tmp))
            self.make(sink)
            payload = run_cmd(
                "gate", "testrun", "R", "--write-scope", "scripts/one.py"
            )
            self.assertIn("error", payload)
            self.assertIn("--lens", payload["error"])

    def test_the_gate_is_the_queued_scopes_edge_in_the_view(self):
        """The two subcommands meet: what `gate` writes is what `worklog`
        reads as scope queued behind the root subtree."""

        with tempfile.TemporaryDirectory() as tmp:
            sink = use_sink(Path(tmp))
            run_dir = self.make(sink)
            self.gate()
            (run_dir / "R.04.md").write_text(
                ticket("R.04", status="pending", deps="[R.gate.verify]",
                       objective="the successor"),
                encoding="utf-8",
            )
            markdown = run_cmd("worklog", "testrun")["worklog"]["markdown"]
            queued = markdown.split("## queued scope")[1].split("## terminal")[0]
            self.assertIn("R.04", queued)


if __name__ == "__main__":
    unittest.main()
