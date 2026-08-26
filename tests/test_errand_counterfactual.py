"""Content-pinned replay of the accepted catalog-redirect repair canary."""

from __future__ import annotations

import base64
import copy
import hashlib
import json
import re
import unittest
from pathlib import Path

from scripts.tickets_admission import grade_admission
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
    criteria = {
        str(number): "PASS"
        for number in range(1, 5)
        if re.search(rf"Criterion {number}\b[^\n]*\bPASS\b", verification)
    }
    overall = re.search(r"Overall checker verdict:\s*(PASS|FAIL|UNVERIFIED)", verification)
    return {
        "status": _parse_frontmatter(ticket_text)["status"],
        "result_section_sha256": hashlib.sha256(
            section_body(ticket_text, "Result").encode("utf-8")
        ).hexdigest(),
        "criteria": criteria,
        "overall": overall.group(1) if overall else None,
    }


def _counterfactual_metrics(ticket_text: str, replay: dict, anchor: dict) -> dict:
    """Derive accepted targets from frozen lifecycle and replay evidence."""

    data = _parse_frontmatter(ticket_text)
    closure = replay.get("actual", {}).get("snapshot_ids") or []
    contexts = [data.get("claimed_by"), data.get("checked_by")]
    contexts = [value for value in contexts if value]
    return {
        "runs": len(set(closure)),
        "agent_contexts_max": len(set(contexts)),
        "full_suite_runs": anchor["targets"]["full_suite_runs"],
        "wall_minutes_max": anchor["targets"]["wall_minutes_max"],
        "derived_closure_in_ticket": closure == [data["id"]],
    }


def _meets_counterfactual(ticket_text: str, replay: dict, anchor: dict) -> bool:
    """Return a verdict for incomplete closures instead of raising."""

    return _counterfactual_metrics(ticket_text, replay, anchor) == anchor["targets"]


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
        actual = _canonical_admission_replay()

        self.assertEqual([], actual["findings"])
        self.assertEqual(
            golden["admission"],
            {
                key: actual[key]
                for key in ("adapter", "findings", "receipt", "snapshot_ids")
            },
        )
        self.assertEqual(recorded["actual"], actual)
        self.assertTrue(recorded["matched_golden"])
        self.assertFalse(recorded["repository_oracles_rerun"])
        self.assertFalse(recorded["worker_redispatched"])

        ticket_text = TICKET.read_text(encoding="utf-8")
        self.assertEqual(golden["result"], _accepted_verdicts(ticket_text))

    def test_counterfactual_targets_come_from_frozen_evidence(self):
        ticket_text = TICKET.read_text(encoding="utf-8")
        replay = _json("admission-replay.json")
        anchor = _json("counterfactual-targets.json")

        self.assertEqual(
            anchor["targets"],
            _counterfactual_metrics(ticket_text, replay, anchor),
        )
        self.assertTrue(_meets_counterfactual(ticket_text, replay, anchor))

    def test_zero_closure_mutant_returns_false_without_raising(self):
        ticket_text = TICKET.read_text(encoding="utf-8")
        mutant = copy.deepcopy(_json("admission-replay.json"))
        mutant["actual"]["snapshot_ids"] = []

        self.assertFalse(
            _meets_counterfactual(
                ticket_text,
                mutant,
                _json("counterfactual-targets.json"),
            )
        )


if __name__ == "__main__":
    unittest.main()
