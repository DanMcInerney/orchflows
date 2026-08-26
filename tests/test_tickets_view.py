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

if __name__ == "test_tickets_view": sys.modules["tests.test_tickets_view"] = sys.modules[__name__]
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

    def test_a_research_goal_projects_its_four_dispatch_inputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            sink = use_sink(Path(tmp))
            inputs = (
                '- input: {"name":"evidence-store-root","type":"literal",'
                '"value":"sink:evidence/testrun/R/"}\n'
                '- input: {"name":"question","type":"literal",'
                '"value":"Which source answers this?"}\n'
                '- input: {"name":"source-policy","type":"literal",'
                '"value":"primary evidence only"}\n'
                '- input: {"name":"rigor-bar","type":"literal",'
                '"value":"support each claim or record a gap"}'
            )
            research = ticket(
                "R", executor="orch-investigate", pack="orch-research-pack",
                objective="answer one bounded question",
            ).replace("## Fixed inputs\n\nNone.",
                      "## Fixed inputs\n\n" + inputs)
            make_run(sink, {"R": research})
            goal = self.render().split("## iterations")[0]
            for field in (
                "evidence-store-root", "question", "source-policy", "rigor-bar"
            ):
                self.assertIn(field, goal)
            self.assertIn("Which source answers this?", goal)
            self.assertIn("primary evidence only", goal)

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

    def test_terminal_timing_is_durable_across_shapes_and_retries(self):
        shapes = (
            (
                "single",
                {"R": ticket("R", status="claimed", executor="orch-loop")},
                "R",
                "complete",
            ),
            (
                "terminal",
                {
                    "A": ticket("A", status="complete"),
                    "B": ticket("B", status="claimed", deps="[A]"),
                },
                "B",
                "failed",
            ),
        )
        for label, tickets, terminal_id, terminal_status in shapes:
            with self.subTest(label=label), tempfile.TemporaryDirectory() as tmp:
                tmp = Path(tmp)
                sink = use_sink(tmp)
                (tmp / ".git").mkdir()
                make_run(sink, tickets)
                run_cmd("run-state", "testrun", "--note", "opened")
                closed = run_cmd(
                    "set-status", "testrun", terminal_id, terminal_status
                )
                self.assertNotIn("error", closed)
                identity_path = sink / "runs" / "testrun" / "run.json"
                identity = json.loads(identity_path.read_text(encoding="utf-8"))
                self.assertEqual(terminal_id, identity["terminal_ticket_id"])
                self.assertEqual(terminal_status, identity["terminal_status"])
                self.assertGreaterEqual(identity["elapsed_ms"], 0)
                first = identity_path.read_bytes()
                run_cmd("set-status", "testrun", terminal_id, terminal_status)
                self.assertEqual(first, identity_path.read_bytes())

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


from tests.test_tickets_view_cases.gate_stubs import GateStubsTest  # noqa: E402,F401

if __name__ == "__main__":
    unittest.main()
