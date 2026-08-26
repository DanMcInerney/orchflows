"""Frozen deterministic replay of the catalog-redirect errand."""

from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPLAY = ROOT / ".orch" / "canary" / "errand" / "catalog-redirect.json"


def _metrics(replay: dict) -> dict:
    runs = replay["runs"]
    contexts = [context for run in runs for context in run["agent_contexts"]]
    events = [event for run in runs for event in run["events"]]
    suite_events = [event for event in events if event["kind"] == "required-suite"]
    closure_events = [event for event in events if event["kind"] == "derived-closure"]
    return {
        "runs": len(runs),
        "agent_contexts": len(contexts),
        "full_suite_runs": len(suite_events),
        "wall_minutes": max(run["end_minute"] for run in runs)
        - min(run["start_minute"] for run in runs),
        "derived_closure_in_ticket": bool(closure_events)
        and all(event["owner"] == "ticket" for event in closure_events),
        "suite_is_terminal": bool(suite_events)
        and all(
            event["identity"] == "accepted-terminal"
            and event["minute"] == max(run["end_minute"] for run in runs)
            and event["minute"] >= max(item["minute"] for item in closure_events)
            for event in suite_events
        ),
    }


class ErrandCounterfactualTest(unittest.TestCase):
    def test_catalog_redirect_replay_meets_the_frozen_counterfactual(self):
        counterfactual = json.loads(REPLAY.read_text(encoding="utf-8"))

        self.assertEqual("catalog redirect repair", counterfactual["fixture"])
        self.assertEqual(
            {
                "runs": 7,
                "agent_contexts": 21,
                "full_suite_runs": 5,
                "wall_minutes": 170,
            },
            counterfactual["observed"],
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
            _metrics(counterfactual["errand_replay"]),
        )

        ticket = counterfactual["errand_replay"]["ticket"]
        self.assertEqual(
            [
                "tests/test_errand_counterfactual.py",
                "tests/serial_compat_manifest.json",
            ],
            ticket["derived_closure"],
        )
        self.assertEqual(
            "uv run --no-project python tools/run_serial_compat.py --write-manifest",
            ticket["regeneration_command"],
        )

    def test_replay_check_discriminates_each_target_beside_the_tree(self):
        counterfactual = json.loads(REPLAY.read_text(encoding="utf-8"))
        replay = counterfactual["errand_replay"]
        mutants = {
            "second run": {**replay, "runs": replay["runs"] * 2},
            "third context": {
                **replay,
                "runs": [
                    {
                        **replay["runs"][0],
                        "agent_contexts": replay["runs"][0]["agent_contexts"]
                        + ["extra"],
                    }
                ],
            },
            "second suite": {
                **replay,
                "runs": [
                    {
                        **replay["runs"][0],
                        "events": replay["runs"][0]["events"]
                        + [
                            {
                                "kind": "required-suite",
                                "minute": 23,
                                "identity": "accepted-terminal",
                            }
                        ],
                    }
                ],
            },
            "closure outside ticket": {
                **replay,
                "runs": [
                    {
                        **replay["runs"][0],
                        "events": [
                            {**event, "owner": "run"}
                            if event["kind"] == "derived-closure"
                            else event
                            for event in replay["runs"][0]["events"]
                        ],
                    }
                ],
            },
            "suite before closure": {
                **replay,
                "runs": [
                    {
                        **replay["runs"][0],
                        "events": [
                            {**event, "minute": 10}
                            if event["kind"] == "required-suite"
                            else event
                            for event in replay["runs"][0]["events"]
                        ],
                    }
                ],
            },
            "thirty-one minutes": {
                **replay,
                "runs": [{**replay["runs"][0], "end_minute": 31}],
            },
        }

        for name, mutant in mutants.items():
            with self.subTest(name=name):
                metrics = _metrics(mutant)
                meets_targets = (
                    metrics["runs"] == 1
                    and metrics["agent_contexts"] <= 2
                    and metrics["full_suite_runs"] == 1
                    and metrics["derived_closure_in_ticket"]
                    and metrics["suite_is_terminal"]
                    and metrics["wall_minutes"] <= 30
                )
                self.assertFalse(meets_targets)


if __name__ == "__main__":
    unittest.main()
