"""Spec 02 replay guards for the loop's issue-then-claim protocol."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import scripts.tickets as tickets_mod  # noqa: E402
from tests.test_tickets_cases.common import (  # noqa: E402
    run_cmd,
    run_json,
    use_sink,
)


RUN = "loop-spec-02"
FIXTURE_PATH = ROOT / "tests" / "fixtures" / "final_specs" / "02" / "replays.json"
LOOP_SKILL_PATH = ROOT / "skills" / "engines" / "orch-loop" / "SKILL.md"

TICKET = """---
id: {ticket_id}
run: {run}
status: {status}
admission: v1:pending
cohort: v1:ticket:{ticket_id}
executor: orch-tdd
pack: orch-code-pack
independence: gate
depends_on: {depends_on}
write_scope: [scratch/{ticket_id}.txt]
mutations: [change:scratch/{ticket_id}.txt]
excluded_actions: [vcs.integrate, vcs.push, vcs.open-pr]
isolation: required
bound: 30m
claimed_by:
claimed_at:
---

## Objective

Change one observable artifact.

## Fixed inputs

- input: {{"identity":{{"kind":"git-tree","repo":"run-project","revision":"__BASELINE_REVISION__"}},"name":"baseline","type":"identity"}}
- input: {{"name":"question","type":"literal","value":"fixed"}}

## Completion test

- the artifact has the requested value | oracle: `python -m unittest` | oracle_class: deterministic | provenance: pre-existing

## Return fields

status; result; changed_artifacts; verification; feedback; risks

## Result

## Verification

## Feedback

[]

## Risks

[]
"""


def ticket(ticket_id: str, *, status: str = "pending", depends_on: str = "[]",
           excluded: str = "[vcs.integrate, vcs.push, vcs.open-pr]", run: str = RUN) -> str:
    return TICKET.format(
        ticket_id=ticket_id,
        run=run,
        status=status,
        depends_on=depends_on,
    ).replace(
        "excluded_actions: [vcs.integrate, vcs.push, vcs.open-pr]",
        f"excluded_actions: {excluded}",
    )


def place_run(tmp: Path, entries: dict[str, str], *, run: str = RUN) -> Path:
    revision = initialize_repo(tmp)
    run_dir = use_sink(tmp) / "tickets" / run
    run_dir.mkdir(parents=True)
    for ticket_id, text in entries.items():
        (run_dir / f"{ticket_id}.md").write_text(
            text.replace("__BASELINE_REVISION__", revision), encoding="utf-8",
        )
    return run_dir


def initialize_repo(tmp: Path) -> str:
    subprocess.run(["git", "init", "-q", str(tmp)], check=True)
    subprocess.run(
        ["git", "-C", str(tmp), "config", "user.email", "loop-test@example.invalid"],
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(tmp), "config", "user.name", "Loop Test"], check=True,
    )
    (tmp / "baseline.txt").write_text("loop fixture baseline\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(tmp), "add", "baseline.txt"], check=True)
    subprocess.run(["git", "-C", str(tmp), "commit", "-qm", "baseline"], check=True)
    return subprocess.check_output(
        ["git", "-C", str(tmp), "rev-parse", "HEAD"], text=True,
    ).strip()


def baseline_input(revision: str) -> str:
    return json.dumps({
        "identity": {"kind": "git-tree", "repo": "run-project", "revision": revision},
        "name": "baseline",
        "type": "identity",
    }, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def dependency_result_input(run: str, ticket_id: str) -> str:
    return json.dumps({
        "identity": {
            "kind": "ticket-section", "run": run,
            "section": "Result", "ticket": ticket_id,
        },
        "name": "dependency-result",
        "type": "identity",
    }, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


class PendingClaimAtomicityTest(unittest.TestCase):
    def test_dependency_complete_pending_ticket_is_claimed_without_ready_bytes(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            run_dir = place_run(tmp, {
                "dependency": ticket("dependency", status="complete"),
                "iteration": ticket("iteration", depends_on="[dependency]"),
            })

            payload = run_cmd(tmp, "claim", RUN, "iteration", "--by", "loop-child")

            self.assertEqual("loop-child", payload["claimed"]["claimed_by"])
            final = (run_dir / "iteration.md").read_text(encoding="utf-8")
            self.assertIn("status: claimed", final)
            self.assertRegex(final, r"admission: v1:git:sha256:[0-9a-f]{64}")
            self.assertNotIn("status: ready", final)

    def test_incomplete_and_dangling_dependencies_leave_pending_bytes_identical(self):
        cases = (
            ("incomplete", {"dependency": ticket("dependency")}, "dependency-incomplete"),
            ("dangling", {}, "dependency-dangling"),
        )
        for name, dependencies, finding_code in cases:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as raw:
                tmp = Path(raw)
                entries = dict(dependencies)
                entries["iteration"] = ticket("iteration", depends_on="[dependency]")
                run_dir = place_run(tmp, entries)
                path = run_dir / "iteration.md"
                before = path.read_bytes()

                payload = run_cmd(tmp, "claim", RUN, "iteration", "--by", "loop-child")

                self.assertEqual("admission refused", payload["error"])
                self.assertIn(finding_code, {item["code"] for item in payload["findings"]})
                self.assertEqual(before, path.read_bytes())

    def test_ready_and_claim_return_the_same_sorted_findings(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            malformed = ticket("iteration", excluded="[vcs.commit]")
            run_dir = place_run(tmp, {"iteration": malformed})

            ready = run_cmd(tmp, "ready", "--run", RUN)
            claim = run_cmd(tmp, "claim", RUN, "iteration", "--by", "loop-child")

            self.assertEqual(ready["skipped"][0]["findings"], claim["findings"])
            self.assertEqual(
                sorted(claim["findings"], key=lambda item: (item["code"], item["field"], item["detail"])),
                claim["findings"],
            )
            final = (run_dir / "iteration.md").read_text(encoding="utf-8")
            self.assertIn("status: pending", final)
            self.assertIn("admission: v1:pending", final)

    def test_two_process_claims_have_one_final_owner(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            run_dir = place_run(tmp, {"iteration": ticket("iteration")})

            with ThreadPoolExecutor(max_workers=2) as pool:
                outcomes = list(pool.map(
                    lambda owner: run_json(
                        tmp, "claim", RUN, "iteration", "--by", owner,
                    ),
                    ("loop-child-a", "loop-child-b"),
                ))

            winners = [item for item in outcomes if "claimed" in item]
            losers = [item for item in outcomes if "error" in item]
            self.assertEqual(1, len(winners), outcomes)
            self.assertEqual(1, len(losers), outcomes)
            winner = winners[0]["claimed"]["claimed_by"]
            final = (run_dir / "iteration.md").read_text(encoding="utf-8")
            self.assertIn(f"claimed_by: {winner}", final)
            self.assertEqual(1, final.count("claimed_by: "))

    def test_failed_final_write_never_exposes_ready_bytes(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            run_dir = place_run(tmp, {"iteration": ticket("iteration")})
            path = run_dir / "iteration.md"
            before = path.read_text(encoding="utf-8")
            observed = []

            def fail_final_write(target, _updated):
                observed.append(Path(target).read_text(encoding="utf-8"))
                raise OSError("injected final-write failure")

            with mock.patch.object(
                tickets_mod, "_write_text_atomically", side_effect=fail_final_write,
            ):
                payload = run_cmd(
                    tmp, "claim", RUN, "iteration", "--by", "loop-child",
                )

            self.assertIn("injected final-write failure", payload["error"])
            self.assertEqual([before], observed)
            self.assertEqual(before, path.read_text(encoding="utf-8"))
            self.assertNotIn("status: ready", path.read_text(encoding="utf-8"))


class FrozenLoopReplayTest(unittest.TestCase):
    def test_both_frozen_iterations_replay_as_issue_then_claim(self):
        fixtures = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        self.assertEqual(2, len(fixtures))

        for fixture in fixtures:
            with self.subTest(run=fixture["run"]), tempfile.TemporaryDirectory() as raw:
                tmp = Path(raw)
                revision = initialize_repo(tmp)
                use_sink(tmp)
                calls = []

                dependency = run_cmd(
                    tmp, "new", fixture["run"], fixture["depends_on"],
                    "--executor", "orch-tdd",
                    "--objective", "Supply the completed loop dependency.",
                    "--criterion", "the dependency is complete | oracle: `python -m unittest` | oracle_class: deterministic | provenance: pre-existing",
                    "--input", baseline_input(revision),
                    "--pack", "orch-code-pack", "--isolation", "required",
                    "--excluded", "vcs.integrate", "--excluded", "vcs.push",
                    "--excluded", "vcs.open-pr",
                )
                self.assertIn("new", dependency)
                completed = run_cmd(
                    tmp, "set-status", fixture["run"], fixture["depends_on"], "complete",
                )
                self.assertEqual("complete", completed["set_status"]["status"])

                calls.append("new")
                issued = run_cmd(
                    tmp, "new", fixture["run"], fixture["id"],
                    "--executor", "orch-tdd",
                    "--objective", fixture["objective"],
                    "--criterion", fixture["completion"],
                    "--depends-on", fixture["depends_on"],
                    "--input", baseline_input(revision),
                    "--input", dependency_result_input(fixture["run"], fixture["depends_on"]),
                    "--pack", "orch-code-pack", "--isolation", "required",
                    "--excluded", "vcs.integrate", "--excluded", "vcs.push",
                    "--excluded", "vcs.open-pr",
                )
                self.assertEqual("pending", issued["new"]["status"])

                calls.append("claim")
                claimed = run_cmd(
                    tmp, "claim", fixture["run"], fixture["id"],
                    "--by", "loop-child",
                )

                self.assertEqual(["new", "claim"], calls)
                self.assertIn("claimed", claimed, claimed)
                self.assertEqual("loop-child", claimed["claimed"]["claimed_by"])
                final = Path(issued["new"]["path"]).read_text(encoding="utf-8")
                sections = tickets_mod._sections(final)
                self.assertEqual(fixture["objective"], sections["Objective"].strip())
                self.assertEqual("- " + fixture["completion"], sections["Completion test"].strip())
                self.assertIn("status: claimed", final)
                self.assertNotIn("status: ready", final)


class LoopProtocolContractTest(unittest.TestCase):
    def test_loop_documents_issue_then_claim_and_points_to_admission_lifecycle(self):
        text = LOOP_SKILL_PATH.read_text(encoding="utf-8")
        issue_at = text.index("issue `<id>.iter.NN`")
        claim_at = text.index("claim it through `tickets.py claim`")

        self.assertLess(issue_at, claim_at)
        self.assertIn(
            "../../../contracts/work-item.md#admission-and-migration",
            text[issue_at:claim_at],
        )
        self.assertNotIn("tickets.py ready", text)


if __name__ == "__main__":
    unittest.main()
