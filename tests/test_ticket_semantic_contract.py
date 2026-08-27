"""Focused regressions for the sole semantic ticket contract."""

from __future__ import annotations

import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from scripts import cutcheck
from scripts import tickets
from scripts import tickets_generations
from scripts.tickets_format import _parse_frontmatter, _sections
from scripts.tickets_issue_render import _render_ticket
from scripts import workspace

ROOT = Path(__file__).resolve().parents[1]


def assignment(ticket_id, executor, dependencies=(), *, root_generation=None):
    fields = {
        "id": ticket_id,
        "run": "cut",
        "status": "pending",
        "admission": "pending",
        "executor": executor,
        "pack": "orch-code-pack",
        "independence": "gate",
        "depends_on": list(dependencies),
        "isolation": "required" if executor == "orch-tdd" else "none",
        "bound": "30m",
        "claimed_by": "",
        "claimed_at": "",
        "root_generation": root_generation,
    }
    sections = [
        ("Goal", f"Deliver the observable result for {ticket_id}."),
        ("Context", "The root assignment and repository are authoritative."),
        ("Result", ""),
        ("Verification", ""),
        ("Feedback", "[]"),
        ("Risks", "[]"),
    ]
    return _render_ticket(fields, sections)


class SemanticTicketContractTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.environment = mock.patch.dict(os.environ, {"ORCHFLOWS_STATE_HOME": self.temporary.name})
        self.environment.start()

    def tearDown(self):
        self.environment.stop()
        self.temporary.cleanup()

    def dispatch(self, *arguments):
        result = tickets._dispatch(list(arguments))
        self.assertNotIn("error", result, result)
        return result

    def seal(self, run, root):
        self.dispatch("stamp-generation", run, root)
        validated = self.dispatch("draft-validate", run, root)
        generation = validated["draft_validation"]["cut_generation"]
        self.dispatch("seal", run, root, "--cut-generation", generation)

    def test_goal_context_only_direct_root_lifecycle(self):
        self.dispatch(
            "new", "direct", "R1", "--executor", "orch-edit",
            "--goal", "Create the observable artifact.",
            "--context", "No exceptional constraints.",
        )
        self.seal("direct", "R1")
        ready = self.dispatch("ready", "--run", "direct")
        self.assertEqual(["R1"], [item["id"] for item in ready["ready"]])
        self.dispatch("claim", "direct", "R1", "--by", "worker")
        packet = self.dispatch("packet", "direct", "R1", "--reply-to", "root")["packet"]
        self.assertIn("Suggested files are non-binding", packet["prompt"])
        text = (Path(self.temporary.name) / "tickets" / "direct" / "R1.md").read_text(encoding="utf-8")
        self.assertEqual({"Goal", "Context", "Result", "Verification", "Feedback", "Risks"}, set(_sections(text)))

    def test_suggested_files_do_not_limit_candidate_paths(self):
        self.dispatch(
            "new", "suggested", "R1", "--executor", "orch-tdd",
            "--goal", "Repair the behavior.", "--context", "The repository is authoritative.",
            "--suggested-file", "src/start.py", "--pack", "orch-code-pack",
            "--isolation", "required",
        )
        self.seal("suggested", "R1")
        ready = self.dispatch("ready", "--run", "suggested")
        self.assertEqual(1, len(ready["ready"]))
        packet_path = Path(self.temporary.name) / "tickets" / "suggested" / "R1.md"
        self.assertNotIn("write_scope", _parse_frontmatter(packet_path.read_text(encoding="utf-8")))
        actual = workspace._actual_mutations("M\0other/path.py\0A\0tests/new_guard.py\0")
        self.assertEqual([("change", "other/path.py"), ("create", "tests/new_guard.py")], actual)

    def test_decomposed_root_uses_same_semantic_shape(self):
        self.dispatch("new", "cut", "R", "--executor", "orch-decompose", "--goal", "Deliver the result.", "--context", "Use the repository facts.")
        self.dispatch("new", "cut", "R.01", "--executor", "orch-edit", "--goal", "Produce one component.", "--context", "It feeds the root result.")
        self.seal("cut", "R")
        for path in sorted((Path(self.temporary.name) / "tickets" / "cut").glob("*.md")):
            sections = _sections(path.read_text(encoding="utf-8"))
            self.assertIn("Goal", sections)
            self.assertIn("Context", sections)

    def test_complete_code_cut_keeps_one_root_generation_before_and_after_seal(self):
        initial = {"R": assignment("R", "orch-decompose")}
        root_draft = tickets_generations.draft_snapshot("R", initial)
        root_receipt = tickets_generations.validate_draft("R", initial, root_draft)
        rooted = tickets_generations.seal_assignments("R", initial, root_draft, root_receipt)
        inherited = root_draft["root_generation"]

        complete = {
            **rooted,
            "R.01": assignment("R.01", "orch-tdd", root_generation=inherited),
            "R.02": assignment("R.02", "orch-tdd", root_generation=inherited),
            "R.gate.critique.code": assignment(
                "R.gate.critique.code", "orch-critique", ("R.01", "R.02"),
                root_generation=inherited,
            ),
            "R.gate.repair": assignment(
                "R.gate.repair", "orch-repair", ("R.gate.critique.code",),
                root_generation=inherited,
            ),
            "R.gate.verify": assignment(
                "R.gate.verify", "orch-verify", ("R.gate.repair",),
                root_generation=inherited,
            ),
        }

        cut_draft = tickets_generations.draft_snapshot("R", complete, ordinal=2)
        self.assertEqual(inherited, cut_draft["root_generation"])
        self.assertNotEqual(root_draft["cut_generation"], cut_draft["cut_generation"])
        receipt = tickets_generations.validate_draft("R", complete, cut_draft)
        sealed = tickets_generations.seal_assignments("R", complete, cut_draft, receipt)
        for ticket_id in sorted(sealed):
            self.assertEqual([], tickets_generations.seal_findings(ticket_id, sealed[ticket_id]))

        self.assertEqual([], cutcheck.graph_findings(complete))
        self.assertEqual([], cutcheck.graph_findings(sealed))

    def test_decompose_builds_the_complete_gate_bearing_draft_before_validation(self):
        skill = (ROOT / "skills" / "kernel" / "orch-decompose" / "SKILL.md").read_text(encoding="utf-8")
        commands = ("tickets.py gate", "cutcheck.py", "tickets.py draft-validate", "tickets.py seal")
        positions = [skill.index(command) for command in commands]
        self.assertEqual(sorted(positions), positions)
        for field in ("`root_generation`", "`executor`", "`assembly`", "`independence: gate`"):
            self.assertIn(field, skill)

    def test_fix_template_instantiates_current_sealed_format(self):
        result = self.dispatch(
            "instantiate", str(ROOT / "compositions" / "fix"), "--run", "fix",
            "--set", "failure=boom", "--set", "workspace=.",
        )
        self.assertEqual("root:00-reproduce", result["instantiate"]["generation"]["root_generation"].split(":1:")[0])
        for path in (Path(self.temporary.name) / "tickets" / "fix").glob("*.md"):
            sections = _sections(path.read_text(encoding="utf-8"))
            self.assertIn("Goal", sections)
            self.assertNotIn("Objective", sections)

    def test_gate_routes_actual_overlap_to_integration(self):
        self.dispatch("new", "gate", "R", "--executor", "orch-decompose", "--goal", "Deliver the result.", "--context", "Two candidates may touch one path.", "--pack", "orch-code-pack", "--independence", "gate")
        for suffix in ("01", "02"):
            self.dispatch("new", "gate", f"R.{suffix}", "--executor", "orch-tdd", "--goal", f"Deliver candidate {suffix}.", "--context", "The candidate feeds the integrated result.", "--pack", "orch-code-pack", "--independence", "gate", "--isolation", "required")
        self.dispatch("stamp-generation", "gate", "R")
        self.dispatch("gate", "gate", "R")
        repair = "\n".join(path.read_text(encoding="utf-8") for path in (Path(self.temporary.name) / "tickets" / "gate").glob("R.gate.*.md"))
        self.assertIn("actual overlapping candidate diffs", repair)
        self.assertIn("ordinary Git conflicts", repair)

    def test_tdd_executor_owns_test_choice(self):
        self.dispatch(
            "new", "tdd", "R", "--executor", "orch-tdd",
            "--goal", "Correct the observable behavior.",
            "--context", "The repository supplies the implementation facts.",
            "--pack", "orch-code-pack", "--isolation", "required",
        )
        self.seal("tdd", "R")
        self.dispatch("ready", "--run", "tdd")
        self.dispatch("claim", "tdd", "R", "--by", "worker")
        prompt = self.dispatch("packet", "tdd", "R", "--reply-to", "root")["packet"]["prompt"]
        self.assertIn("choose the implementation, tests, and verification", prompt.lower())
        self.assertNotIn("oracle_class", prompt)

    def test_content_pack_preserves_whole_artifact_direct_route(self):
        pack = (ROOT / "packs" / "orch-content-pack" / "SKILL.md").read_text(encoding="utf-8")
        slicing = (ROOT / "packs" / "orch-content-pack" / "references" / "slicing.md").read_text(encoding="utf-8")
        text = (pack + "\n" + slicing).lower()
        self.assertIn("whole", text)
        self.assertIn("direct", text)
        self.assertIn("one executor", text)

    def test_live_protocol_surfaces_exclude_removed_schema(self):
        forbidden = ("write_scope", "excluded_actions", "## Objective", "## Fixed inputs", "## Completion test", "## Return fields")
        paths = [ROOT / "contracts" / "work-item.md", *sorted((ROOT / "scripts").glob("tickets*.py")), *sorted((ROOT / "compositions").glob("**/*.md"))]
        findings = []
        for path in paths:
            text = path.read_text(encoding="utf-8")
            findings.extend(f"{path.relative_to(ROOT)}:{token}" for token in forbidden if token in text)
        self.assertEqual([], findings)


if __name__ == "__main__":
    unittest.main()
