"""Content-pinned replay of the catalog repair as ordinary single work."""

from __future__ import annotations

import base64
import hashlib
import json
import re
import unittest
from pathlib import Path

from scripts.tickets_admission import grade_admission
from scripts.tickets_format import _parse_frontmatter
from scripts.tickets_inputs import section_body
from scripts import ui_workflows_summary


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / ".orch" / "canary" / "single"
TICKET = FIXTURE / "tickets" / "canary" / "repair.md"


def _json(name: str) -> dict:
    return json.loads((FIXTURE / name).read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _section_sha256(path: Path, section: str) -> str:
    body = section_body(path.read_text(encoding="utf-8"), section)
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def _decoded_sha256(path: Path) -> str:
    encoded = "".join(path.read_text(encoding="ascii").split())
    return hashlib.sha256(base64.b64decode(encoded)).hexdigest()


def _canonical_admission_replay() -> dict:
    text = TICKET.read_text(encoding="utf-8")
    return grade_admission(
        "repair",
        text,
        {"repair": text},
        {
            "run": "orch-install-catalog-repair-20260825",
            "ticket_id": "repair",
            "tickets_root": str((FIXTURE / "inputs" / "tickets").resolve()),
            "runs_root": str((FIXTURE / "runs").resolve()),
            "project_root": str(ROOT),
        },
    )


def _accepted_verdicts(ticket_text: str) -> dict:
    verification = section_body(ticket_text, "Verification")
    criteria = {}
    for number in range(1, 5):
        verdicts = re.findall(
            rf"Criterion {number}\b[^\n]*\b(PASS|FAIL|UNVERIFIED)\b",
            verification,
        )
        if verdicts:
            criteria[str(number)] = verdicts[-1]
    overall = re.search(r"Overall checker verdict:\s*(PASS|FAIL|UNVERIFIED)", verification)
    return {
        "status": _parse_frontmatter(ticket_text)["status"],
        "result_section_sha256": hashlib.sha256(
            section_body(ticket_text, "Result").encode("utf-8")
        ).hexdigest(),
        "criteria": criteria,
        "overall": overall.group(1) if overall else None,
    }


def _frontier_replay(ticket_text: str) -> dict:
    admission = _canonical_admission_replay()
    return {
        "admission": {
            key: admission[key]
            for key in (
                "adapter", "findings", "input_fingerprint", "receipt",
                "scope_fingerprint", "snapshot_ids",
            )
        },
        "terminal": {
            "checked_by": _parse_frontmatter(ticket_text)["checked_by"],
            **_accepted_verdicts(ticket_text),
        },
    }


def _counterfactual_metrics(model: dict) -> dict:
    runs = model.get("runs") or []
    contexts = [context for run in runs for context in run.get("agent_contexts", [])]
    events = [event for run in runs for event in run.get("events", [])]
    suites = [event for event in events if event.get("kind") == "required-suite"]
    end_minutes = [run.get("end_minute") for run in runs]
    start_minutes = [run.get("start_minute") for run in runs]
    terminal_minute = max(end_minutes) if end_minutes else None
    return {
        "runs": len(runs),
        "agent_contexts": len(contexts),
        "full_suite_runs": len(suites),
        "wall_minutes": (
            max(end_minutes) - min(start_minutes)
            if end_minutes and start_minutes else 0
        ),
        "suite_is_terminal": bool(suites) and all(
            event.get("identity") == "accepted-terminal"
            and event.get("minute") == terminal_minute
            for event in suites
        ),
    }


def _meets_counterfactual(model: dict, anchor: dict) -> bool:
    metrics = _counterfactual_metrics(model)
    targets = anchor["targets"]
    return (
        metrics["runs"] == targets["runs"]
        and metrics["agent_contexts"] <= targets["agent_contexts_max"]
        and metrics["full_suite_runs"] == targets["full_suite_runs"]
        and metrics["suite_is_terminal"]
        and metrics["wall_minutes"] <= targets["wall_minutes_max"]
    )


class RoutingCounterfactualTest(unittest.TestCase):
    def test_public_composition_and_ui_identity_are_absent(self):
        self.assertFalse((ROOT / "compositions" / "errand").exists())
        manifest = json.loads(
            (ROOT / "docs" / "ui" / "workflow-summary-manifest.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertNotIn("errand", manifest["workflows"])
        self.assertNotIn("errand", ui_workflows_summary.CANONICAL_WORKFLOW_IDS)

    def test_fixture_freezes_every_named_input_and_oracle_by_content(self):
        manifest = _json("manifest.json")
        for record in (manifest["ticket"], manifest["spec"]):
            self.assertEqual(record["sha256"], _sha256(FIXTURE / record["path"]))
        self.assertEqual(
            manifest["ticket"]["result_section_sha256"],
            _section_sha256(FIXTURE / manifest["ticket"]["path"], "Result"),
        )

        ticket_text = TICKET.read_text(encoding="utf-8")
        spec_text = (FIXTURE / manifest["spec"]["path"]).read_text(encoding="utf-8")
        for section in ("Objective", "Fixed inputs", "Completion test", "Return fields"):
            with self.subTest(spec_section=section):
                self.assertEqual(section_body(ticket_text, section), section_body(spec_text, section))

        for record in manifest["replay_artifacts"]:
            self.assertEqual(record["sha256"], _sha256(FIXTURE / record["path"]))
        for record in manifest["fixed_inputs"]:
            if "path" not in record:
                continue
            path = FIXTURE / record["path"]
            self.assertEqual(record["sha256"], _sha256(path))
            if "result_section_sha256" in record:
                self.assertEqual(record["result_section_sha256"], _section_sha256(path, "Result"))
        for record in manifest["oracle_artifacts"]:
            self.assertEqual(
                record["decoded_sha256"],
                _decoded_sha256(FIXTURE / record["archive_path"]),
            )

    def test_actual_frontier_admission_replay_matches_the_golden(self):
        golden = _json("golden.json")
        recorded = _json("admission-replay.json")
        ticket_text = TICKET.read_text(encoding="utf-8")
        replayed = _frontier_replay(ticket_text)

        self.assertEqual([], replayed["admission"]["findings"])
        self.assertEqual(
            golden["admission"],
            {key: replayed["admission"][key] for key in (
                "adapter", "findings", "receipt", "snapshot_ids",
            )},
        )
        self.assertEqual(recorded["actual"], replayed["admission"])
        self.assertEqual(recorded["terminal_actual"], replayed["terminal"])
        self.assertTrue(recorded["matched_golden"])
        self.assertFalse(recorded["repository_oracles_rerun"])
        self.assertFalse(recorded["worker_redispatched"])
        self.assertEqual(golden["result"], _accepted_verdicts(ticket_text))

    def test_single_model_meets_the_frozen_cost_targets(self):
        model = _json("counterfactual-replay.json")
        anchor = _json("counterfactual-targets.json")
        self.assertTrue(model["modeled"])
        self.assertEqual(
            {
                "runs": 1,
                "agent_contexts": 2,
                "full_suite_runs": 1,
                "wall_minutes": 24,
                "suite_is_terminal": True,
            },
            _counterfactual_metrics(model),
        )
        self.assertTrue(_meets_counterfactual(model, anchor))

    def test_cost_target_mutants_all_fail_without_raising(self):
        model = _json("counterfactual-replay.json")
        run = model["runs"][0]
        mutants = {
            "second run": {**model, "runs": model["runs"] * 2},
            "third context": {**model, "runs": [{
                **run, "agent_contexts": run["agent_contexts"] + ["extra"],
            }]},
            "second suite": {**model, "runs": [{
                **run,
                "events": run["events"] + [{
                    "kind": "required-suite", "minute": 24,
                    "identity": "accepted-terminal",
                }],
            }]},
            "suite before terminal": {**model, "runs": [{
                **run,
                "events": [{**event, "minute": 10} for event in run["events"]],
            }]},
            "thirty-one minutes": {**model, "runs": [{**run, "end_minute": 31}]},
        }
        anchor = _json("counterfactual-targets.json")
        for name, mutant in mutants.items():
            with self.subTest(name=name):
                self.assertFalse(_meets_counterfactual(mutant, anchor))

    def test_rehomed_fixture_has_no_obsolete_route_identity(self):
        for path in FIXTURE.rglob("*"):
            if path.is_file() and path.suffix in {".md", ".json"}:
                with self.subTest(path=path.relative_to(FIXTURE)):
                    self.assertNotIn("errand", path.read_text(encoding="utf-8").lower())


if __name__ == "__main__":
    unittest.main()
