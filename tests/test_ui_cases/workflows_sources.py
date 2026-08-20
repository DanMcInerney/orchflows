"""Contained opaque source inspection for canonical Workflows definitions."""

from __future__ import annotations

import hashlib
import os
import re
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts import ui_workflows_identity as identity
from scripts import ui_workflows_sources as sources


ROOT = Path(__file__).resolve().parents[2]
NOT_FOUND = {"error": {"code": "not_found", "message": "resource not found"}}
UNREADABLE = {
    "error": {
        "code": "unreadable_source",
        "message": "workflow source is unavailable",
    }
}


class WorkflowSourceTests(unittest.TestCase):
    def test_inventory_is_exact_and_exposes_only_opaque_ids(self):
        evolve = sources.source_inventory(ROOT, "evolve")
        expected_evolve_paths = {
            "lib/compositions/evolve/template.md",
            "lib/compositions/evolve/00-eval.md",
            "lib/compositions/evolve/01-eligibility.md",
            "lib/compositions/evolve/02-campaign.md",
            "lib/compositions/evolve/03-result.md",
            "lib/skills/workflows/orch-eval-design/SKILL.md",
            "lib/skills/engines/orch-loop/SKILL.md",
            "lib/skills/kernel/orch-verify/SKILL.md",
        }
        self.assertEqual(
            {identity.source_id(path) for path in expected_evolve_paths},
            set(evolve),
        )

        orch_build = sources.source_inventory(ROOT, "orch-build")
        expected_build_paths = {
            "lib/skills/workflows/orch-build/SKILL.md",
            "lib/skills/kernel/orch-critique/SKILL.md",
            "bin/tickets.py",
        }
        self.assertEqual(
            {identity.source_id(path) for path in expected_build_paths},
            set(orch_build),
        )
        self.assertTrue(all(re.fullmatch(r"src_[A-Za-z0-9_-]{43}", item) for item in evolve))
        self.assertTrue(all("/" not in item and "\\" not in item for item in (*evolve, *orch_build)))
        self.assertNotIn(identity.source_id("tools/validate.py"), orch_build)

    def test_success_reads_once_and_hashes_the_redacted_delivered_text(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            host_path = str(root / "private" / "secret.txt")
            self._skill(
                root,
                "workflows",
                "demo",
                f"Require: input.\n\nRead {host_path}. Run `runner.py execute`.\n\nReturn: output.\n",
            )
            self._script(root, "runner.py", "print('ok')\n")
            source_id = identity.source_id("lib/skills/workflows/demo/SKILL.md")
            target = root / "skills" / "workflows" / "demo" / "SKILL.md"
            original = Path.read_bytes
            reads = []

            def counted(path):
                if path == target:
                    reads.append(path)
                return original(path)

            with mock.patch.object(Path, "read_bytes", counted):
                status, payload = sources.project_source(root, "demo", source_id)

        self.assertEqual(200, status)
        self.assertEqual(
            {"schema", "id", "text", "sha256", "language", "redacted"},
            set(payload),
        )
        self.assertEqual("orchflows.workflow-source.v1", payload["schema"])
        self.assertEqual(source_id, payload["id"])
        self.assertEqual("markdown", payload["language"])
        self.assertTrue(payload["redacted"])
        self.assertIn("[redacted-host-path]", payload["text"])
        self.assertNotIn(host_path, payload["text"])
        self.assertEqual(
            hashlib.sha256(payload["text"].encode("utf-8")).hexdigest(),
            payload["sha256"],
        )
        self.assertEqual([target], reads)

    def test_unknown_traversal_state_and_arbitrary_ids_share_generic_not_found(self):
        state_id = identity.source_id("lib/rules/visibility.md")
        arbitrary_id = identity.source_id("bin/ui.py")
        requests = ("../../rules/visibility.md", "src_bad/slash", state_id, arbitrary_id)

        for source_id in requests:
            with self.subTest(source_id=source_id):
                status, payload = sources.project_source(ROOT, "orch-spec", source_id)
                self.assertEqual((404, NOT_FOUND), (status, payload))
                self.assertNotIn(str(ROOT), repr(payload))
                self.assertNotIn("state", repr(payload).lower())

        self.assertEqual((), sources.source_inventory(ROOT, "../../orch-spec"))
        self.assertEqual((), sources.source_inventory(ROOT, "missing-workflow"))

    def test_escaped_symlink_is_not_opened_and_is_indistinguishable_from_missing(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as outside:
            root = Path(directory)
            self._skill(
                root,
                "workflows",
                "demo",
                "Require: input.\n\nCall `orch-target`.\n\nReturn: output.\n",
            )
            outside_path = Path(outside) / "SKILL.md"
            outside_path.write_text(
                "---\nname: orch-target\ndescription: Outside.\nrole: none\n---\n\nReturn: secret.\n",
                encoding="utf-8",
            )
            link = root / "skills" / "kernel" / "orch-target" / "SKILL.md"
            link.parent.mkdir(parents=True)
            try:
                os.symlink(outside_path, link)
            except OSError as error:
                self.skipTest(f"symlink unavailable: {error}")
            source_id = identity.source_id("lib/skills/kernel/orch-target/SKILL.md")
            original = Path.read_text
            escaped_reads = []

            def counted(path, *args, **kwargs):
                if path == link:
                    escaped_reads.append(path)
                return original(path, *args, **kwargs)

            with mock.patch.object(Path, "read_text", counted):
                status, payload = sources.project_source(root, "demo", source_id)

        self.assertEqual((404, NOT_FOUND), (status, payload))
        self.assertEqual([], escaped_reads)
        self.assertNotIn(str(outside_path), repr(payload))

    def test_cataloged_invalid_utf8_is_a_closed_typed_unreadable_result(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._skill(
                root,
                "workflows",
                "demo",
                "Require: input.\n\nRun `broken.py`.\n\nReturn: output.\n",
            )
            broken = root / "scripts" / "broken.py"
            broken.parent.mkdir(parents=True)
            broken.write_bytes(b"\xff\xfe")
            source_id = identity.source_id("bin/broken.py")

            status, payload = sources.project_source(root, "demo", source_id)

        self.assertEqual((422, UNREADABLE), (status, payload))
        self.assertNotIn(str(broken), repr(payload))

    @staticmethod
    def _skill(root: Path, tier: str, name: str, body: str) -> None:
        path = root / "skills" / tier / name / "SKILL.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            f"---\nname: {name}\ndescription: Test {name}.\nrole: none\n---\n\n{body}",
            encoding="utf-8",
        )

    @staticmethod
    def _script(root: Path, name: str, text: str) -> None:
        path = root / "scripts" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
