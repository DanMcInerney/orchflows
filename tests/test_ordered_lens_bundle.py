"""An ordered lens bundle is one sealed reviewer/repair ticket, then verify.

The production family supplies the packet identities and order.  A compact
execution record models the child return contract so every prohibited split,
pool, repeat, verdict, and identity reuse has a controlled false specimen.
"""

from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

import scripts.tickets as tickets_mod
from scripts import tickets_commands
from tests import test_gate_only_lifecycle as gate_fixture

ROOT_ID = gate_fixture.ROOT_ID
RUN = gate_fixture.RUN
dispatch = gate_fixture.dispatch
fixture = gate_fixture.fixture
frontmatter_text = gate_fixture.frontmatter_text
seal = gate_fixture.seal

EXPECTED_LENSES = ["code", "library"]
EXPECTED_BUNDLE = [
    {"evidence": ["code-baseline"], "identity": "code"},
    {"evidence": ["library-baseline"], "identity": "library"},
]


def _complete(ticket_id: str, result: str) -> None:
    for section, text in (
        ("Result", result),
        ("Context", "- state: ordered-bundle-result is the final identity"),
    ):
        value = dispatch(
            "result", RUN, ticket_id, "--section", section,
            "--text", text, "--append",
        )
        if "error" in value:
            raise AssertionError(value)
    value = dispatch("set-status", RUN, ticket_id, "complete")
    if "error" in value:
        raise AssertionError(value)


def _bundle_literal(ticket_text: str) -> list:
    inputs = tickets_mod._sections(ticket_text)["Fixed inputs"]
    for line in inputs.splitlines():
        if not line.startswith("- input: "):
            continue
        record = json.loads(line[len("- input: "):])
        if record.get("name") == "ordered-lens-bundle":
            return record["value"]
    raise AssertionError("ordered-lens-bundle record is missing")


def _bundle_result(ticket_text: str) -> dict:
    result = tickets_mod._sections(ticket_text)["Result"]
    values = {}
    for line in result.splitlines():
        name, separator, encoded = line.partition(": ")
        if separator and name in {
            "completion-records", "findings", "post-repair-verdicts",
        }:
            values[name.replace("-", "_")] = json.loads(encoded)
    return values


def validate_bundle_execution(record: dict) -> None:
    """The same-child and fresh-verifier contract, independent of prose."""

    if record["lenses"] != EXPECTED_LENSES:
        raise AssertionError("lens identities must be unique and retain input order")
    if len(record["reviewer_children"]) != 1:
        raise AssertionError("all lenses execute in one reviewer child")
    if record["sequence"] != ["orch-critique", "orch-repair"]:
        raise AssertionError("the same ticket contains exactly one repair pass")
    completions = record["completion_records"]
    if [row.get("lens") for row in completions] != EXPECTED_LENSES:
        raise AssertionError("completion evidence must be attributed in lens order")
    evidence = []
    for row in completions:
        if not row.get("artifact_identity") or not row.get("evidence"):
            raise AssertionError("each lens needs its own identity and evidence")
        evidence.extend(row["evidence"])
    if len(evidence) != len(set(evidence)):
        raise AssertionError("pooled evidence cannot stand for two lenses")
    for finding in record["findings"]:
        if finding.get("lens") not in EXPECTED_LENSES:
            raise AssertionError("every finding needs a bundle lens identity")
        if not finding.get("artifact_identity") or not finding.get("evidence"):
            raise AssertionError("every finding needs artifact identity and evidence")
    if record["post_repair_verdicts"]:
        raise AssertionError("the repairing reviewer renders no accepted verdict")
    if record["reviewer_children"][0] == record["verifier_child"]:
        raise AssertionError("gate verification uses a fresh child identity")


class OrderedLensBundleTest(unittest.TestCase):
    def test_public_gate_help_names_the_opt_in_and_gate_only_shape(self):
        gate_help = dispatch("--help")["help"]["subcommands"]["gate"]
        self.assertIn("--ordered-lens-bundle", gate_help["usage"])
        self.assertIn("gate-only", gate_help["summary"])
        self.assertIn("--ordered-lens-bundle", tickets_commands.VALUE_FLAGS)

    def test_packet_and_frontier_preserve_one_ordered_same_child_sequence(self):
        with fixture(gate_fixture.GateOnlyLifecycleTest.COVERAGE) as (_base, run_dir):
            seal()
            self.assertNotIn(
                "error", dispatch("claim", RUN, ROOT_ID, "--by", "planner")
            )
            dispatch(
                "packet", RUN, ROOT_ID, "--reply-to", "outer", "--by", "planner"
            )
            payload = dispatch(
                "gate", RUN, ROOT_ID, "--ordered-lens-bundle", "code,library",
                "--write-scope", "scripts/a.py",
            )
            self.assertNotIn("error", payload, payload)
            self.assertEqual(EXPECTED_LENSES, payload["gate"]["lenses"])
            self.assertEqual(EXPECTED_BUNDLE, payload["gate"]["ordered_lens_bundle"])
            self.assertEqual(
                [f"{ROOT_ID}.gate.critique.bundle", f"{ROOT_ID}.gate.verify"],
                payload["gate"]["ids"],
            )
            seal()
            _complete(ROOT_ID, "the root emitted the ordered composite gate")

            closer = f"{ROOT_ID}.gate.critique.bundle"
            verifier = f"{ROOT_ID}.gate.verify"
            self.assertEqual(
                [closer],
                [item["id"] for item in dispatch("ready", "--run", RUN)["ready"]],
            )
            self.assertNotIn(
                "error", dispatch("claim", RUN, closer, "--by", "one-reviewer")
            )
            reviewer_packet = dispatch(
                "packet", RUN, closer, "--reply-to", "outer", "--by", "one-reviewer"
            )["packet"]
            closer_text = (run_dir / f"{closer}.md").read_text(encoding="utf-8")
            self.assertEqual(EXPECTED_BUNDLE, _bundle_literal(closer_text))
            root_text = (run_dir / f"{ROOT_ID}.md").read_text(encoding="utf-8")
            root_line = next(
                line for line in tickets_mod._sections(root_text)["Fixed inputs"].splitlines()
                if '"name":"ordered-lens-bundle"' in line
            )
            self.assertIn(root_line, tickets_mod._sections(closer_text)["Fixed inputs"])
            self.assertIn(
                "sequence: [orch-critique, orch-repair]", frontmatter_text(
                    run_dir / f"{closer}.md"
                )
            )
            self.assertEqual("orch-critique", reviewer_packet["executor"])

            completion_records = [
                {
                    "lens": "code", "artifact_identity": "git:code-result",
                    "evidence": ["code-baseline"],
                },
                {
                    "lens": "library", "artifact_identity": "git:library-result",
                    "evidence": ["library-baseline"],
                },
            ]
            findings = [
                {
                    "lens": "library", "artifact_identity": "git:library-result",
                    "evidence": "library-baseline", "blocking": True,
                }
            ]
            actual_result = "\n".join((
                "completion-records: " + json.dumps(completion_records),
                "findings: " + json.dumps(findings),
                "post-repair-verdicts: []",
            ))
            _complete(closer, actual_result)
            closer_text = (run_dir / f"{closer}.md").read_text(encoding="utf-8")
            self.assertIn(
                "completion records", tickets_mod._sections(closer_text)["Return fields"]
            )
            self.assertEqual(
                [verifier],
                [item["id"] for item in dispatch("ready", "--run", RUN)["ready"]],
            )
            self.assertNotIn(
                "error", dispatch("claim", RUN, verifier, "--by", "separate-verifier")
            )
            verifier_packet = dispatch(
                "packet", RUN, verifier, "--reply-to", "outer",
                "--by", "separate-verifier",
            )["packet"]

            recorded = _bundle_result(closer_text)
            execution = {
                "lenses": [row["identity"] for row in _bundle_literal(closer_text)],
                "reviewer_children": [reviewer_packet["assigned_name"]],
                "sequence": ["orch-critique", "orch-repair"],
                **recorded,
                "verifier_child": verifier_packet["assigned_name"],
            }
            validate_bundle_execution(execution)

            frontier_skill = (
                Path(gate_fixture.ROOT, "skills", "engines", "orch-frontier", "SKILL.md")
                .read_text(encoding="utf-8")
            )
            critique_skill = (
                Path(gate_fixture.ROOT, "skills", "kernel", "orch-critique", "SKILL.md")
                .read_text(encoding="utf-8")
            )
            self.assertIn("without evaluator redispatch", frontier_skill)
            self.assertIn("another fresh child", frontier_skill)
            self.assertIn("identify every finding", critique_skill)
            self.assertRegex(critique_skill, r"return no post-repair\s+verdict")

    def test_each_controlled_wrong_bundle_is_rejected(self):
        valid = {
            "lenses": list(EXPECTED_LENSES),
            "reviewer_children": ["one-reviewer"],
            "sequence": ["orch-critique", "orch-repair"],
            "completion_records": [
                {
                    "lens": "code", "artifact_identity": "git:code",
                    "evidence": ["code-only"],
                },
                {
                    "lens": "library", "artifact_identity": "git:library",
                    "evidence": ["library-only"],
                },
            ],
            "findings": [
                {
                    "lens": "code", "artifact_identity": "git:code",
                    "evidence": "code-only",
                }
            ],
            "post_repair_verdicts": [],
            "verifier_child": "fresh-verifier",
        }
        mutants = []

        duplicate = copy.deepcopy(valid)
        duplicate["lenses"] = ["code", "code"]
        mutants.append(("duplicate lens", duplicate))
        reordered = copy.deepcopy(valid)
        reordered["lenses"] = ["library", "code"]
        mutants.append(("reordered lens", reordered))
        split = copy.deepcopy(valid)
        split["reviewer_children"] = ["code-reviewer", "library-reviewer"]
        mutants.append(("split reviewer", split))
        second_repair = copy.deepcopy(valid)
        second_repair["sequence"].append("orch-repair")
        mutants.append(("second repair", second_repair))
        pooled = copy.deepcopy(valid)
        pooled["completion_records"][1].pop("lens")
        pooled["completion_records"][1]["evidence"] = ["code-only"]
        mutants.append(("pooled evidence", pooled))
        verdict = copy.deepcopy(valid)
        verdict["post_repair_verdicts"] = ["PASS"]
        mutants.append(("repairing reviewer verdict", verdict))
        reused = copy.deepcopy(valid)
        reused["verifier_child"] = "one-reviewer"
        mutants.append(("reused verifier", reused))

        for name, mutant in mutants:
            with self.subTest(name=name), self.assertRaises(AssertionError):
                validate_bundle_execution(mutant)


if __name__ == "__main__":
    unittest.main()
