"""Content-pinned replay of the accepted catalog-redirect repair canary."""

from __future__ import annotations

import base64
import hashlib
import json
import re
import unittest
from pathlib import Path

from scripts.tickets_admission import grade_admission
from scripts.tickets_errand import derived_closure
from scripts.tickets_format import _parse_frontmatter
from scripts.tickets_inputs import section_body


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / ".orch" / "canary" / "errand"
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
    """Replay admission and terminal matching for the frozen completed item."""

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


def _expected_derived_closure(ticket_text: str) -> list[str]:
    return derived_closure(_parse_frontmatter(ticket_text)["mutations"])[
        "write_scope"
    ]


def _counterfactual_metrics(ticket_text: str, model: dict) -> dict:
    """Evaluate the explicit model against live errand closure semantics."""

    runs = model.get("runs") or []
    contexts = [context for run in runs for context in run.get("agent_contexts", [])]
    events = [event for run in runs for event in run.get("events", [])]
    suites = [event for event in events if event.get("kind") == "required-suite"]
    closures = [event for event in events if event.get("kind") == "derived-closure"]
    end_minutes = [run.get("end_minute") for run in runs]
    start_minutes = [run.get("start_minute") for run in runs]
    expected_closure = _expected_derived_closure(ticket_text)
    closure_matches = bool(runs) and all(
        run.get("derived_closure") == expected_closure for run in runs
    )
    closure_owned = bool(closures) and all(
        event.get("owner") == "ticket" for event in closures
    )
    terminal_minute = max(end_minutes) if end_minutes else None
    latest_closure = max((event.get("minute") for event in closures), default=None)
    suite_is_terminal = bool(suites) and latest_closure is not None and all(
        event.get("identity") == "accepted-terminal"
        and event.get("minute") == terminal_minute
        and event.get("minute") >= latest_closure
        for event in suites
    )
    return {
        "runs": len(runs),
        "agent_contexts": len(contexts),
        "full_suite_runs": len(suites),
        "wall_minutes": (
            max(end_minutes) - min(start_minutes)
            if end_minutes and start_minutes else 0
        ),
        "derived_closure_in_ticket": closure_matches and closure_owned,
        "suite_is_terminal": suite_is_terminal,
    }


def _meets_counterfactual(ticket_text: str, model: dict, anchor: dict) -> bool:
    """Return a verdict for incomplete closures instead of raising."""

    metrics = _counterfactual_metrics(ticket_text, model)
    targets = anchor["targets"]
    return (
        metrics["runs"] == targets["runs"]
        and metrics["agent_contexts"] <= targets["agent_contexts_max"]
        and metrics["full_suite_runs"] == targets["full_suite_runs"]
        and metrics["derived_closure_in_ticket"]
        and metrics["suite_is_terminal"]
        and metrics["wall_minutes"] <= targets["wall_minutes_max"]
    )


class ErrandCounterfactualTest(unittest.TestCase):
    def test_fixture_freezes_every_named_input_and_oracle_by_content(self):
        manifest = _json("manifest.json")

        ticket = manifest["ticket"]
        self.assertEqual(ticket["sha256"], _sha256(FIXTURE / ticket["path"]))
        self.assertEqual(
            ticket["result_section_sha256"],
            _section_sha256(FIXTURE / ticket["path"], "Result"),
        )

        spec = manifest["spec"]
        self.assertEqual(spec["sha256"], _sha256(FIXTURE / spec["path"]))
        ticket_text = TICKET.read_text(encoding="utf-8")
        spec_text = (FIXTURE / spec["path"]).read_text(encoding="utf-8")
        for section in ("Objective", "Fixed inputs", "Completion test", "Return fields"):
            with self.subTest(spec_section=section):
                self.assertEqual(
                    section_body(ticket_text, section),
                    section_body(spec_text, section),
                )

        for record in manifest["replay_artifacts"]:
            with self.subTest(replay_artifact=record["path"]):
                self.assertEqual(record["sha256"], _sha256(FIXTURE / record["path"]))

        for fixed_input in manifest["fixed_inputs"]:
            if "path" not in fixed_input:
                continue
            with self.subTest(fixed_input=fixed_input["path"]):
                input_path = FIXTURE / fixed_input["path"]
                self.assertEqual(fixed_input["sha256"], _sha256(input_path))
                if "result_section_sha256" in fixed_input:
                    self.assertEqual(
                        fixed_input["result_section_sha256"],
                        _section_sha256(input_path, "Result"),
                    )

        for artifact in manifest["oracle_artifacts"]:
            with self.subTest(artifact=artifact["source_path"]):
                self.assertEqual(
                    artifact["decoded_sha256"],
                    _decoded_sha256(FIXTURE / artifact["archive_path"]),
                )

    def test_actual_frontier_admission_replay_matches_the_golden(self):
        golden = _json("golden.json")
        recorded = _json("admission-replay.json")
        ticket_text = TICKET.read_text(encoding="utf-8")
        replayed = _frontier_replay(ticket_text)

        self.assertEqual([], replayed["admission"]["findings"])
        self.assertEqual(
            golden["admission"],
            {
                key: replayed["admission"][key]
                for key in ("adapter", "findings", "receipt", "snapshot_ids")
            },
        )
        self.assertEqual(recorded["actual"], replayed["admission"])
        self.assertEqual(recorded["terminal_actual"], replayed["terminal"])
        self.assertTrue(recorded["matched_golden"])
        self.assertFalse(recorded["repository_oracles_rerun"])
        self.assertFalse(recorded["worker_redispatched"])

        self.assertEqual(golden["result"], _accepted_verdicts(ticket_text))

    def test_counterfactual_model_is_evidence_bound_and_meets_targets(self):
        ticket_text = TICKET.read_text(encoding="utf-8")
        model = _json("counterfactual-replay.json")
        anchor = _json("counterfactual-targets.json")

        self.assertTrue(model["modeled"])
        self.assertEqual(
            _expected_derived_closure(ticket_text),
            model["runs"][0]["derived_closure"],
        )
        self.assertEqual(
            {
                "runs": 1,
                "agent_contexts": 2,
                "full_suite_runs": 1,
                "wall_minutes": 24,
                "derived_closure_in_ticket": True,
                "suite_is_terminal": True,
            },
            _counterfactual_metrics(ticket_text, model),
        )
        self.assertTrue(_meets_counterfactual(ticket_text, model, anchor))

    def test_counterfactual_mutants_fail_every_target_without_raising(self):
        ticket_text = TICKET.read_text(encoding="utf-8")
        model = _json("counterfactual-replay.json")
        run = model["runs"][0]
        mutants = {
            "second run": {**model, "runs": model["runs"] * 2},
            "third context": {
                **model,
                "runs": [{
                    **run,
                    "agent_contexts": run["agent_contexts"] + ["extra"],
                }],
            },
            "second suite": {
                **model,
                "runs": [{
                    **run,
                    "events": run["events"] + [{
                        "kind": "required-suite",
                        "minute": 23,
                        "identity": "accepted-terminal",
                    }],
                }],
            },
            "zero closure": {
                **model,
                "runs": [{**run, "derived_closure": []}],
            },
            "suite before closure": {
                **model,
                "runs": [{
                    **run,
                    "events": [
                        {**event, "minute": 10}
                        if event["kind"] == "required-suite" else event
                        for event in run["events"]
                    ],
                }],
            },
            "thirty-one minutes": {
                **model,
                "runs": [{**run, "end_minute": 31}],
            },
        }

        for name, mutant in mutants.items():
            with self.subTest(name=name):
                self.assertFalse(
                    _meets_counterfactual(
                        ticket_text,
                        mutant,
                        _json("counterfactual-targets.json"),
                    )
                )


if __name__ == "__main__":
    unittest.main()
