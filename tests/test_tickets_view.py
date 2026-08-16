"""The ticket script's view path: `worklog` renders a run, `gate` writes
its gate stubs.

SPEC-ticket-set.md §1: the worklog is a view `tickets.py` renders from
the ticket directory, never a second hand-written file; §2: a root
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
           result: str = "", verification: str = "", feedback: str = "[]") -> str:
    return TICKET.format(
        tid=tid, status=status, executor=executor, deps=deps,
        claimed_at=claimed_at, claimed_by=claimed_by, objective=objective,
        criterion=criterion, result=result, verification=verification,
        feedback=feedback,
    )


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

    def test_terminal_is_the_root_tickets_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            sink = use_sink(Path(tmp))
            make_run(sink, three_ticket_run())
            self.assertIn("claimed", self.render().split("## terminal")[1])

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


if __name__ == "__main__":
    unittest.main()
