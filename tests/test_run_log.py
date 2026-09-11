"""Behavior checks use disposable homes outside the checkout and real user home."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
import run_log


class RunLogTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="orchflows-run-test-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.home = self.root / "home"
        self.home.mkdir()
        self.summary = self.root / "actual-summary.md"
        self.summary.write_bytes(b"Checked two sources. One gap remains.\n")

    def start(self):
        return run_log.start_run(self.home, "social-search:social-search", "demo")

    def finish(self, run, status="complete"):
        return run_log.finish_run(self.home, Path(run["run_dir"]), status, self.summary)

    def assert_bytes_unchanged(self, files):
        for path, content in files.items():
            self.assertEqual(path.read_bytes(), content)

    def test_concurrent_process_starts_have_unique_portable_records(self):
        program = (
            "import json,sys; from pathlib import Path; sys.path.insert(0,sys.argv[1]); "
            "from run_log import start_run; "
            "print(json.dumps(start_run(Path(sys.argv[2]),'personal:check','demo')))"
        )

        def launch(_):
            result = subprocess.run([sys.executable, "-B", "-c", program, str(SCRIPTS), str(self.home)],
                                    cwd=self.root, capture_output=True, text=True, check=True)
            return json.loads(result.stdout)

        with ThreadPoolExecutor(max_workers=8) as executor:
            runs = list(executor.map(launch, range(16)))
        self.assertEqual(len({run["run_dir"] for run in runs}), 16)
        for run in runs:
            path = Path(run["run_json"])
            metadata = json.loads(path.read_bytes())
            self.assertEqual(metadata["status"], "running")
            self.assertNotIn("provenance", metadata)
            self.assertNotIn(str(self.home), path.read_text())
            self.assertEqual(path.parent.parent.name, metadata["started_at"][:7])
            self.assertEqual(run["run_id"], path.parent.name)

    def test_collision_retries_without_modifying_existing_run(self):
        instant = datetime(2026, 9, 11, 8, 0, tzinfo=timezone.utc)
        fixed = run_log.uuid.UUID(int=1)
        next_id = run_log.uuid.UUID(int=2)
        with patch.object(run_log, "datetime") as clock:
            clock.now.return_value = instant
            with patch.object(run_log.uuid, "uuid4", return_value=fixed):
                first = self.start()
            before = Path(first["run_json"]).read_bytes()
            with patch.object(run_log.uuid, "uuid4", side_effect=[fixed, next_id]):
                second = self.start()
            self.assertNotEqual(first["run_dir"], second["run_dir"])
            with patch.object(run_log.uuid, "uuid4", return_value=fixed):
                with self.assertRaisesRegex(OSError, "unique run"):
                    self.start()
        self.assertEqual(Path(first["run_json"]).read_bytes(), before)

    def test_provenance_contains_observed_package_and_skill_identity_only(self):
        package = self.home / "libraries/social-search"
        skill = package / "skills/social-search/SKILL.md"
        skill.parent.mkdir(parents=True)
        skill.write_bytes(b"actual skill contents")
        manifest_bytes = json.dumps({"name": "social-search", "version": "0.1.0", "source": str(self.root)}).encode()
        (package / "plugin.json").write_bytes(manifest_bytes)
        core = self.home / ".local/packages/orchflows-light/.codex-plugin"
        core.mkdir(parents=True)
        (core / "plugin.json").write_text('{"name":"orchflows-light","version":"0.3.0"}')
        run = self.start()
        metadata = json.loads(Path(run["run_json"]).read_bytes())
        identity = metadata["provenance"]["workflow"]
        self.assertEqual(identity["version"], "0.1.0")
        self.assertEqual(identity["home_path"], "libraries/social-search")
        self.assertEqual(identity["manifest_sha256"], hashlib.sha256(manifest_bytes).hexdigest())
        self.assertEqual(identity["skill"]["sha256"], hashlib.sha256(skill.read_bytes()).hexdigest())
        self.assertEqual(metadata["provenance"]["core"]["version"], "0.3.0")
        self.assertNotIn(str(self.root), json.dumps(metadata))
        skill.write_bytes(b"changed after this run started")
        self.assertEqual(self.finish(run)["provenance"], metadata["provenance"])

    def test_missing_or_malformed_manifest_does_not_invent_provenance(self):
        package = self.home / "libraries/social-search"
        package.mkdir(parents=True)
        (package / "plugin.json").write_text("{bad-json")
        self.assertNotIn("provenance", self.start())
        (package / "plugin.json").write_text('{"name":"another-library","version":"4"}')
        self.assertNotIn("provenance", self.start())

    def test_finalization_preserves_raw_artifacts_and_is_deliberately_idempotent(self):
        run = self.start()
        directory = Path(run["run_dir"])
        files = {}
        for relative in ("raw/source.json", "artifacts/report.html", "notes.txt"):
            path = directory / relative
            path.parent.mkdir(exist_ok=True)
            files[path] = b"existing actual evidence"
            path.write_bytes(files[path])
        result = self.finish(run, "partial")
        files[Path(result["run_json"])] = Path(result["run_json"]).read_bytes()
        files[Path(result["summary_file"])] = self.summary.read_bytes()
        repeated = self.finish(result, "partial")
        self.assertEqual(result, repeated)
        self.assert_bytes_unchanged(files)
        with self.assertRaisesRegex(ValueError, "already finalized"):
            self.finish(result, "complete")
        self.summary.write_text("A different account of the result.\n")
        with self.assertRaisesRegex(ValueError, "already finalized"):
            self.finish(result, "partial")
        self.assert_bytes_unchanged(files)

    def test_concurrent_finalization_rejects_second_writer(self):
        run = self.start()
        entered = threading.Event()
        release = threading.Event()
        original = run_log._atomic_write

        def paused_write(path, content):
            if path.name == "summary.md":
                entered.set()
                if not release.wait(timeout=10):
                    raise AssertionError("writer was not released")
            return original(path, content)

        with patch.object(run_log, "_atomic_write", side_effect=paused_write):
            with ThreadPoolExecutor(max_workers=1) as executor:
                first = executor.submit(self.finish, run)
                try:
                    self.assertTrue(entered.wait(timeout=10))
                    with self.assertRaisesRegex(OSError, "locked"):
                        self.finish(run, "blocked")
                finally:
                    release.set()
                result = first.result(timeout=10)
        self.assertEqual(result["status"], "complete")
        self.assertFalse((Path(run["run_dir"]) / ".finish.lock").exists())

    def test_interrupted_metadata_publish_keeps_valid_metadata_and_can_resume(self):
        run = self.start()
        metadata = Path(run["run_json"])
        before = metadata.read_bytes()
        replace = run_log.os.replace

        def fail_metadata(source, destination):
            if Path(destination).name == "run.json":
                raise OSError("simulated disk failure")
            return replace(source, destination)

        with patch.object(run_log.os, "replace", side_effect=fail_metadata):
            with self.assertRaisesRegex(OSError, "simulated disk failure"):
                self.finish(run)
        self.assertEqual(metadata.read_bytes(), before)
        self.assertEqual((metadata.parent / "summary.md").read_bytes(), self.summary.read_bytes())
        self.assertEqual(sorted(p.name for p in metadata.parent.iterdir()), ["run.json", "summary.md"])
        self.assertEqual(self.finish(run)["status"], "complete")

    def test_existing_summary_or_damaged_metadata_is_preserved(self):
        run = self.start()
        path = Path(run["run_json"])
        destination = path.parent / "summary.md"
        destination.write_bytes(b"User's earlier notes")
        before = {path: path.read_bytes(), destination: destination.read_bytes()}
        with self.assertRaisesRegex(ValueError, "different data"):
            self.finish(run)
        self.assert_bytes_unchanged(before)
        path.write_text("{not valid JSON")
        before[path] = path.read_bytes()
        with self.assertRaisesRegex(ValueError, "valid UTF-8 JSON"):
            self.finish(run)
        self.assert_bytes_unchanged(before)

    def test_finalized_run_with_missing_or_changed_summary_is_not_repaired(self):
        run = self.finish(self.start())
        metadata = Path(run["run_json"])
        before = metadata.read_bytes()
        Path(run["summary_file"]).unlink()
        with self.assertRaisesRegex(ValueError, "already finalized"):
            self.finish(run)
        self.assertEqual(metadata.read_bytes(), before)
        self.assertFalse(Path(run["summary_file"]).exists())

    def test_invalid_metadata_fields_fail_clearly_without_changes(self):
        run = self.start()
        path = Path(run["run_json"])
        original = json.loads(path.read_bytes())
        for field, value in (("status", []), ("schema_version", True), ("workflow", {}),
                             ("started_at", "yesterday"), ("started_at", "2026-01-01"),
                             ("started_at", "2026-01-01T01:00:00+01:00")):
            with self.subTest(field=field, value=value):
                path.write_text(json.dumps({**original, field: value}))
                before = path.read_bytes()
                with self.assertRaises(ValueError):
                    self.finish(run)
                self.assertEqual(path.read_bytes(), before)
                self.assertFalse((path.parent / "summary.md").exists())

    def test_invalid_inputs_do_not_create_or_finalize_data(self):
        for workflow in ("../escape:check", "personal:../check", "check", "personal:check:extra"):
            with self.subTest(workflow=workflow), self.assertRaises(ValueError):
                run_log.start_run(self.home, workflow)
        with self.assertRaises(ValueError):
            run_log.start_run(self.home, "personal:check", str(self.root))
        self.assertEqual(list(self.home.iterdir()), [])
        run = self.start()
        before = Path(run["run_json"]).read_bytes()
        with self.assertRaises(ValueError):
            self.finish(run, "successful")
        for content in (b" \n", b"\xff\xfe"):
            self.summary.write_bytes(content)
            with self.assertRaises(ValueError):
                self.finish(run)
        self.assertEqual(Path(run["run_json"]).read_bytes(), before)

    def test_outside_or_another_home_run_cannot_be_finalized(self):
        run = self.start()
        other_home = self.root / "other-home"
        other_home.mkdir()
        (other_home / "logs").mkdir()
        before = Path(run["run_json"]).read_bytes()
        with self.assertRaises(ValueError):
            run_log.finish_run(other_home, Path(run["run_dir"]), "complete", self.summary)
        with self.assertRaises(ValueError):
            run_log.finish_run(self.home, self.root, "complete", self.summary)
        self.assertEqual(Path(run["run_json"]).read_bytes(), before)

    def symlink(self, link, target, directory=False):
        try:
            link.symlink_to(target, target_is_directory=directory)
        except OSError as error:
            self.skipTest(f"symlinks unavailable: {error}")

    def test_symlinked_logs_cannot_redirect_run_creation(self):
        outside = self.root / "outside"
        outside.mkdir()
        self.symlink(self.home / "logs", outside, directory=True)
        with self.assertRaises(ValueError):
            self.start()
        self.assertEqual(list(outside.iterdir()), [])

    def test_symlinked_summary_or_metadata_cannot_redirect_finalization(self):
        run = self.start()
        directory = Path(run["run_dir"])
        outside = self.root / "untouched.md"
        outside.write_bytes(b"private content")
        self.symlink(directory / "summary.md", outside)
        with self.assertRaises(ValueError):
            self.finish(run)
        self.assertEqual(outside.read_bytes(), b"private content")
        (directory / "summary.md").unlink()
        Path(run["run_json"]).unlink()
        self.symlink(Path(run["run_json"]), outside)
        with self.assertRaises(ValueError):
            self.finish(run)
        self.assertEqual(outside.read_bytes(), b"private content")


if __name__ == "__main__":
    unittest.main()
