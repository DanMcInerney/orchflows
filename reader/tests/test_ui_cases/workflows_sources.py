"""Contained opaque source inspection for canonical Workflows definitions."""

from __future__ import annotations

import hashlib
import os
import re
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from reader.scripts import ui_workflows_identity as identity
from reader.scripts import ui_workflows_sources as sources


ROOT = Path(__file__).resolve().parents[3]
NOT_FOUND = {"error": {"code": "not_found", "message": "resource not found"}}
UNREADABLE = {
    "error": {
        "code": "unreadable_source",
        "message": "workflow source is unavailable",
    }
}


class WorkflowSourceTests(unittest.TestCase):
    def test_installed_bin_root_symlink_cannot_redirect_source_inventory(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as outside:
            package = Path(directory)
            root = package / "lib"
            self._skill(
                root,
                "workflows",
                "demo",
                "Require: input.\n\nRun `runner.py execute`.\n\nReturn: output.\n",
            )
            external_bin = Path(outside) / "bin"
            external_bin.mkdir()
            (external_bin / "runner.py").write_text(
                "OUTSIDE_SECRET\n", encoding="utf-8"
            )
            try:
                os.symlink(external_bin, package / "bin", target_is_directory=True)
            except OSError as error:
                self.skipTest(f"symlink unavailable: {error}")
            source_id = identity.source_id("bin/runner.py")

            inventory = sources.source_inventory(root, "demo")
            status, payload = sources.project_source(root, "demo", source_id)

        self.assertNotIn(source_id, inventory)
        self.assertEqual((404, NOT_FOUND), (status, payload))
        self.assertNotIn("OUTSIDE_SECRET", repr(payload))

    def test_redacts_posix_drive_and_unc_paths_with_spaces_before_hashing(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            body = (
                'POSIX "/etc/orchflows/Private Folder/secret.txt"\n'
                'Drive "C:\\Users\\Jane Doe\\secret.txt"\n'
                'UNC "\\\\server\\Private Share\\secret.txt"\n'
            )
            self._skill(root, "workflows", "demo", body)
            source_id = identity.source_id("lib/skills/workflows/demo/SKILL.md")

            status, payload = sources.project_source(root, "demo", source_id)

        newline = os.linesep
        expected = newline.join((
            "---",
            "name: demo",
            "description: Test demo.",
            "role: none",
            "---",
            "",
            f'POSIX "{sources.REDACTED_HOST_PATH}"',
            f'Drive "{sources.REDACTED_HOST_PATH}"',
            f'UNC "{sources.REDACTED_HOST_PATH}"',
            "",
        ))
        self.assertEqual(200, status)
        self.assertEqual(expected, payload["text"])
        self.assertTrue(payload["redacted"])
        self.assertEqual(
            hashlib.sha256(expected.encode("utf-8")).hexdigest(), payload["sha256"]
        )
        for leaked in ("/etc/orchflows", "Jane Doe", "Private Share"):
            self.assertNotIn(leaked, payload["text"])

    def test_installed_layout_source_route_reads_sibling_bin(self):
        with tempfile.TemporaryDirectory() as directory:
            package = Path(directory)
            root = package / "lib"
            self._skill(
                root,
                "workflows",
                "demo",
                "Require: input.\n\nRun `runner.py execute`.\n\nReturn: output.\n",
            )
            script = package / "bin" / "runner.py"
            script.parent.mkdir(parents=True)
            script.write_text("print('installed')\n", encoding="utf-8")
            source_id = identity.source_id("bin/runner.py")

            status, payload = sources.project_source(root, "demo", source_id)

        self.assertEqual(200, status)
        self.assertEqual(f"print('installed'){os.linesep}", payload["text"])
        self.assertEqual("python", payload["language"])

    def test_inventory_to_open_symlink_swap_never_delivers_external_bytes(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as outside:
            root = Path(directory)
            self._skill(root, "workflows", "demo", "Require: input.\n\nReturn: output.\n")
            # Resolved, because that is the only spelling the subject ever
            # hands out: workflow_roots canonicalizes the root, so on a host
            # whose temporary directory is not already canonical -- macOS
            # /var -> /private/var, a Windows 8.3 short name -- the raw path
            # matches nothing and the arming comparison below sees no read.
            target = root.resolve() / "skills" / "workflows" / "demo" / "SKILL.md"
            external = Path(outside) / "secret.md"
            external.write_text("OUTSIDE_SECRET\n", encoding="utf-8")
            source_id = identity.source_id("lib/skills/workflows/demo/SKILL.md")
            original_inventory = sources._inventory
            original_read_bytes = Path.read_bytes
            original_os_open = os.open
            armed = False
            swapped = False

            def inventory_then_arm(*args, **kwargs):
                nonlocal armed
                projected = original_inventory(*args, **kwargs)
                armed = True
                return projected

            def swap() -> None:
                nonlocal swapped
                if swapped:
                    return
                target.unlink()
                os.symlink(external, target)
                swapped = True

            def racing_read(path):
                if armed and Path(path) == target:
                    swap()
                return original_read_bytes(path)

            def racing_open(path, flags, mode=0o777, *, dir_fd=None):
                if armed and Path(path) == target:
                    swap()
                if dir_fd is None:
                    return original_os_open(path, flags, mode)
                return original_os_open(path, flags, mode, dir_fd=dir_fd)

            try:
                with mock.patch.object(sources, "_inventory", inventory_then_arm), mock.patch.object(Path, "read_bytes", racing_read), mock.patch.object(os, "open", racing_open):
                    status, payload = sources.project_source(root, "demo", source_id)
            except OSError as error:
                self.skipTest(f"symlink unavailable: {error}")

        self.assertNotEqual(200, status)
        self.assertNotIn("OUTSIDE_SECRET", repr(payload))

    def test_inventory_is_exact_and_exposes_only_opaque_ids(self):
        evolve = sources.source_inventory(ROOT, "evolve")
        expected_evolve_paths = {
            "lib/example-workflows/evolve/SKILL.md",
            "lib/packs/orch-code-pack/SKILL.md",
            "bin/search_plan.py",
            "bin/tickets.py",
        }
        self.assertEqual(
            {identity.source_id(path) for path in expected_evolve_paths},
            set(evolve),
        )

        self.assertTrue(all(re.fullmatch(r"src_[A-Za-z0-9_-]{43}", item) for item in evolve))
        self.assertTrue(all("/" not in item and "\\" not in item for item in evolve))

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
            # Resolved, because that is the only spelling the subject ever
            # hands out: workflow_roots canonicalizes the root, so on a host
            # whose temporary directory is not already canonical -- macOS
            # /var -> /private/var, a Windows 8.3 short name -- the raw path
            # matches nothing and the arming comparison below sees no read.
            target = root.resolve() / "skills" / "workflows" / "demo" / "SKILL.md"
            original_inventory = sources._inventory
            original = identity.read_contained_bytes
            reads = []
            armed = False

            def inventory_then_arm(*args, **kwargs):
                nonlocal armed
                projected = original_inventory(*args, **kwargs)
                armed = True
                return projected

            def counted(boundary, path):
                if armed and path == target:
                    reads.append(path)
                return original(boundary, path)

            with mock.patch.object(sources, "_inventory", inventory_then_arm), mock.patch.object(identity, "read_contained_bytes", counted):
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
                status, payload = sources.project_source(ROOT, "orch-outline", source_id)
                self.assertEqual((404, NOT_FOUND), (status, payload))
                self.assertNotIn(str(ROOT), repr(payload))
                self.assertNotIn("state", repr(payload).lower())

        self.assertEqual((), sources.source_inventory(ROOT, "../../orch-outline"))
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
