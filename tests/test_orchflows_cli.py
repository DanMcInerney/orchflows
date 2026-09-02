"""The ring commands: home layout, pinned imports, scaffolds, inventory, trust."""

from __future__ import annotations

import contextlib
import io
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import orchflows, orchflows_home, orchflows_scaffold, rings, rings_trust, state_root


from tests._repo_root import ROOT


def _git(*args, cwd):
    return subprocess.run(
        ["git", "-c", "commit.gpgsign=false", "-c", "gc.auto=0",
         "-c", "gc.autoDetach=false", *args],
        cwd=str(cwd), capture_output=True, text=True, encoding="utf-8",
        errors="replace",
        env=dict(
            os.environ,
            GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.invalid",
            GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.invalid",
        ),
    )


@contextlib.contextmanager
def _home():
    with tempfile.TemporaryDirectory(prefix="orchflows-cli-") as tmp:
        home = Path(tmp).resolve()
        with patch.dict(os.environ, {state_root.ENV_VAR: str(home / "state")}):
            yield home


def _row(output: str, name: str):
    """One `list` row, split on whitespace: the table pads to fit."""

    for line in output.splitlines():
        cells = line.split()
        if len(cells) >= 5 and cells[1] == name:
            return cells
    raise AssertionError(f"{name} is not listed in:\n{output}")


def _run(*argv):
    stream = io.StringIO()
    with contextlib.redirect_stdout(stream):
        code = orchflows.main(list(argv))
    return code, stream.getvalue()


class SyncTests(unittest.TestCase):
    def test_sync_makes_a_fresh_home_ring_whole(self):
        with _home() as home:
            code, output = _run("sync")

            self.assertEqual(0, code, output)
            for name in ("skills", "packs", "workflows", "imports"):
                self.assertTrue((home / name).is_dir(), name)
            self.assertTrue((home / "lib.version").is_file())
            self.assertTrue((home / ".gitignore").is_file())

    def test_the_gitignore_covers_the_regenerable_half_and_keeps_the_history(self):
        with _home() as home:
            _run("sync")

            body = (home / ".gitignore").read_text(encoding="utf-8")
            for entry in orchflows_home.MANAGED_IGNORES:
                self.assertIn(f"\n{entry}\n", body, entry)
            self.assertNotIn("state/friction/", body)
            self.assertNotIn("state/runs/", body)
            self.assertIn("trust.json", body)

    def test_sync_keeps_a_ring_owners_own_ignores(self):
        with _home() as home:
            (home / ".gitignore").write_text("*.swp\n", encoding="utf-8")
            _run("sync")
            _run("sync")

            body = (home / ".gitignore").read_text(encoding="utf-8")
            self.assertIn("*.swp", body)
            self.assertEqual(1, body.count(orchflows_home.GITIGNORE_START))

    def test_sync_never_touches_committed_ring_content(self):
        with _home() as home:
            item = home / "skills" / "mine" / "SKILL.md"
            item.parent.mkdir(parents=True)
            item.write_text("mine\n", encoding="utf-8")

            _run("sync")

            self.assertEqual("mine\n", item.read_text(encoding="utf-8"))

    def test_lib_version_records_the_installed_identity_or_nulls(self):
        with _home() as home:
            (home / "receipt.json").write_text(
                json.dumps({"version": 4, "source_commit": "a" * 40}), encoding="utf-8",
            )
            _run("sync")

            self.assertEqual(
                {"receipt_version": 4, "source_commit": "a" * 40},
                json.loads((home / "lib.version").read_text(encoding="utf-8")),
            )

    def test_lib_version_guesses_nothing_when_no_receipt_is_readable(self):
        with _home() as home:
            _run("sync")

            self.assertEqual(
                {"receipt_version": None, "source_commit": None},
                json.loads((home / "lib.version").read_text(encoding="utf-8")),
            )


class AddTests(unittest.TestCase):
    def _bundle(self, root: Path) -> tuple:
        source = root / "team-bundle"
        (source / ".orchflows" / "skills" / "team-skill").mkdir(parents=True)
        (source / ".orchflows" / "skills" / "team-skill" / "SKILL.md").write_text(
            "---\nname: team-skill\n---\n\nbody\n", encoding="utf-8",
        )
        for args in (
            ("init", "--quiet", "-b", "main"), ("add", "-A"),
            ("commit", "--quiet", "-m", "bundle"), ("tag", "v1"),
        ):
            done = _git(*args, cwd=source)
            if done.returncode != 0:
                raise unittest.SkipTest(f"git {args[0]}: {done.stderr.strip()}")
        head = _git("rev-parse", "HEAD", cwd=source).stdout.strip()
        return source, head

    def test_a_tag_is_a_pin_and_the_import_resolves_through_the_ring(self):
        with _home() as home, tempfile.TemporaryDirectory() as raw:
            source, _head = self._bundle(Path(raw).resolve())

            code, output = _run("add", f"{source.as_posix()}@v1")

            self.assertEqual(0, code, output)
            lock = json.loads((home / "imports.lock").read_text(encoding="utf-8"))
            self.assertEqual(
                [{"name": "team-bundle", "pin": "v1", "url": source.as_posix()}],
                lock["imports"],
            )
            record = rings.resolve("skill", "team-skill")
            self.assertEqual("imports", record["ring"])

    def test_a_branch_name_is_refused_with_the_pin_remedy(self):
        with _home(), tempfile.TemporaryDirectory() as raw:
            source, _head = self._bundle(Path(raw).resolve())

            with self.assertRaises(rings.RingError) as raised:
                orchflows_home.add(f"{source.as_posix()}@main")

            self.assertEqual("mutable-ref", raised.exception.code)
            self.assertIn("<tag-or-sha>", raised.exception.detail)

    def test_a_full_commit_sha_is_a_pin_without_asking_the_remote(self):
        with _home(), tempfile.TemporaryDirectory() as raw:
            source, head = self._bundle(Path(raw).resolve())

            self.assertEqual(head, orchflows_home.resolve_pin(source.as_posix(), head))

    def test_sync_restores_a_deleted_import_from_the_lock(self):
        with _home() as home, tempfile.TemporaryDirectory() as raw:
            source, _head = self._bundle(Path(raw).resolve())
            _run("add", f"{source.as_posix()}@v1")
            target = home / "imports" / "team-bundle"
            self.assertTrue(target.is_dir())
            for path in sorted(target.rglob("*"), reverse=True):
                path.chmod(0o700)
            subprocess.run(["git", "init"], cwd=str(target), capture_output=True)

            restored = orchflows_home.restore()

            self.assertEqual(["present"], [item["action"] for item in restored])

    def test_a_reference_without_a_pin_is_refused(self):
        with _home():
            with self.assertRaises(rings.RingError) as raised:
                orchflows_home.split_reference("https://example.invalid/x.git")
            self.assertEqual("reference-invalid", raised.exception.code)


class NewTests(unittest.TestCase):
    def test_a_new_pack_is_a_valid_pack_the_day_it_is_written(self):
        with _home() as home:
            with patch.object(rings.Path, "cwd", return_value=home / "nowhere"):
                (home / "nowhere").mkdir()
                code, output = _run("new", "pack", "widget-pack")

            self.assertEqual(0, code, output)
            skill = home / "packs" / "widget-pack" / "SKILL.md"
            craft = home / "packs" / "widget-pack" / "references" / "craft.md"
            self.assertTrue(skill.is_file())
            body = craft.read_text(encoding="utf-8")
            for heading in orchflows_scaffold.sections():
                self.assertIn(f"## {heading}", body)
            # The Lens is keyed by artifact kind, so a skeleton carrying the
            # heading and none of the entries is a craft no verb can read.
            for kind in orchflows_scaffold.lens_entries():
                self.assertIn(f"### {kind}", body)
            for retired in ("## Outline", "## Slicing", "## Evidence", "## Shape"):
                self.assertNotIn(retired, body)

    def test_a_new_item_lands_in_the_project_ring_when_you_stand_in_one(self):
        with _home(), tempfile.TemporaryDirectory() as raw:
            project = Path(raw).resolve()
            (project / ".git").mkdir()

            with patch.object(rings.Path, "cwd", return_value=project), \
                    patch.object(orchflows.Path, "cwd", return_value=project):
                code, output = _run("new", "workflow", "team-flow")

            self.assertEqual(0, code, output)
            self.assertTrue((project / ".orchflows" / "workflows" / "team-flow" / "SKILL.md").is_file())
            self.assertIn("orchflows trust", output)

    def test_a_reserved_name_is_refused_before_anything_is_written(self):
        with _home() as home:
            with patch.object(rings.Path, "cwd", return_value=home / "nowhere"):
                (home / "nowhere").mkdir()
                code = orchflows.main(["new", "skill", "orch-widget"])

            self.assertEqual(1, code)
            self.assertFalse((home / "skills" / "orch-widget").exists())


class ListTests(unittest.TestCase):
    def test_list_reports_ring_trust_and_shadow_through_the_one_resolver(self):
        with _home() as home, tempfile.TemporaryDirectory() as raw:
            project = Path(raw).resolve()
            (project / ".git").mkdir()
            for directory in ("skills", "packs", "workflows"):
                (home / directory).mkdir(parents=True, exist_ok=True)
            (home / "workflows" / "team-flow").mkdir(parents=True)
            (home / "workflows" / "team-flow" / "SKILL.md").write_text(
                "---\nname: team-flow\n---\n", encoding="utf-8",
            )
            (project / ".orchflows" / "workflows" / "team-flow").mkdir(parents=True)
            (project / ".orchflows" / "workflows" / "team-flow" / "SKILL.md").write_text(
                "---\nname: team-flow\n---\n", encoding="utf-8",
            )

            with patch.object(rings.Path, "cwd", return_value=project):
                code, output = _run("list", "--kind", "workflow")

            self.assertEqual(0, code, output)
            row = _row(output, "team-flow")
            self.assertEqual(["workflow", "team-flow", "project", "untrusted"], row[:4])
            self.assertIn("shadow:", output)
            with patch.object(rings.Path, "cwd", return_value=project):
                rings_trust.grant(project / ".orchflows")
                _code, after = _run("list", "--kind", "workflow")
            self.assertEqual("trusted", _row(after, "team-flow")[3])

    def test_list_names_a_reserved_ring_item_rather_than_hiding_it(self):
        with _home() as home:
            (home / "packs" / "orch-widget-pack").mkdir(parents=True)
            (home / "packs" / "orch-widget-pack" / "SKILL.md").write_text(
                "---\nname: orch-widget-pack\n---\n", encoding="utf-8",
            )

            with patch.object(rings.Path, "cwd", return_value=home / "nowhere"):
                (home / "nowhere").mkdir()
                code, output = _run("list", "--kind", "pack")

            self.assertEqual(0, code, output)
            self.assertIn("refused", output)
            self.assertIn("reserved 'orch-' prefix", output)


class TrustCommandTests(unittest.TestCase):
    def test_trust_and_untrust_move_the_ledger_and_nothing_else(self):
        with _home() as home, tempfile.TemporaryDirectory() as raw:
            bundle = Path(raw).resolve() / ".orchflows"
            (bundle / "packs").mkdir(parents=True)

            code, granted = _run("trust", str(bundle))
            self.assertEqual(0, code, granted)
            self.assertTrue(rings_trust.state(bundle)["trusted"])
            self.assertIn(str(home / "trust.json"), granted)

            code, revoked = _run("untrust", str(bundle))
            self.assertEqual(0, code, revoked)
            self.assertFalse(rings_trust.state(bundle)["trusted"])

    def test_trust_once_is_spent_and_says_so(self):
        with _home(), tempfile.TemporaryDirectory() as raw:
            bundle = Path(raw).resolve() / ".orchflows"
            (bundle / "packs").mkdir(parents=True)

            code, output = _run("trust", "--once", str(bundle))

            self.assertEqual(0, code, output)
            self.assertIn("for this one use", output)
            self.assertTrue(rings_trust.consume(bundle)["trusted"])
            self.assertFalse(rings_trust.state(bundle)["trusted"])


if __name__ == "__main__":
    unittest.main()
