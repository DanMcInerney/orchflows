"""Focused regressions for the sole semantic ticket contract."""

from __future__ import annotations

import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from scripts import tickets
from scripts.tickets_format import _parse_frontmatter, _sections
from scripts import workspace

ROOT = Path(__file__).resolve().parents[1]


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
        self.dispatch("new", "gate", "R", "--executor", "orch-edit", "--goal", "Deliver the result.", "--context", "Two candidates may touch one path.")
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
