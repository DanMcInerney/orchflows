"""The ring commands: home layout, pinned imports, scaffolds, inventory, trust."""

from __future__ import annotations

import contextlib
import io
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import orchflows, orchflows_home, orchflows_scaffold, rings, rings_trust, state_root
from tools.validate_support.common import BODY_BUDGET


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

    def test_a_new_sheet_is_a_valid_sheet_the_day_it_is_written(self):
        """The scaffold's whole promise, on the kind that has no host
        surface to notice a defect later: what `orchflows new sheet` writes
        passes the library validator's sheet checks unedited.

        It is graded by the real checks against a tree holding the real
        `packs/`, not by a re-listing of the anchors here -- a skeleton that
        named a pack no install carries, or keyed its `## Lens` by a kind
        that pack's adapter never emits, would satisfy an anchor list and
        still be a sheet no ticket could stamp.
        """

        from tools.validate_support import packages as validate_packages
        from tools.validate_support import sheets as validate_sheets

        with _home() as home:
            with patch.object(rings.Path, "cwd", return_value=home / "nowhere"):
                (home / "nowhere").mkdir()
                code, output = _run("new", "sheet", "market-brief")

            self.assertEqual(0, code, output)
            manifest = home / "sheets" / "market-brief" / "SHEET.md"
            self.assertTrue(manifest.is_file())

            graded = home / "graded"
            (graded / "sheets").mkdir(parents=True)
            shutil.copytree(ROOT / "packs", graded / "packs")
            shutil.copytree(manifest.parent, graded / "sheets" / "market-brief")
            diag = validate_packages.Diagnostics()
            for module in (validate_packages, validate_sheets):
                module.ROOT = graded
            try:
                validate_sheets.validate_sheets(diag)
            finally:
                for module in (validate_packages, validate_sheets):
                    module.ROOT = ROOT
            self.assertEqual([], diag.lines())

    def test_a_reserved_name_is_refused_before_anything_is_written(self):
        with _home() as home:
            with patch.object(rings.Path, "cwd", return_value=home / "nowhere"):
                (home / "nowhere").mkdir()
                code = orchflows.main(["new", "skill", "orch-widget"])

            self.assertEqual(1, code)
            self.assertFalse((home / "skills" / "orch-widget").exists())


class CheckTests(unittest.TestCase):
    """`orchflows check`: the compiler's item checks over a ring.

    The valid case is built by the product's own scaffolds rather than by
    hand, so the pass is the claim `scripts/orchflows_scaffold.py` makes --
    what `orchflows new` writes is valid the day it is written -- read back
    through the checker that would refuse it. Each refusal case then mutates
    that same ring in exactly one place, so a green reading here is the
    can-fail one: the ring goes red for the mutation and nothing else.
    """

    def _ring(self, home: Path) -> Path:
        """A home ring holding one scaffolded item of every kind."""

        (home / "nowhere").mkdir(exist_ok=True)
        with patch.object(rings.Path, "cwd", return_value=home / "nowhere"):
            for kind, name in (
                ("skill", "helper"), ("pack", "widget-pack"),
                ("workflow", "team-flow"), ("sheet", "market-brief"),
            ):
                code, output = _run("new", kind, name)
                self.assertEqual(0, code, output)
        return home

    def _check(self, home: Path, *argv):
        elsewhere = home / "nowhere"
        with patch.object(rings.Path, "cwd", return_value=elsewhere), \
                patch.object(orchflows.Path, "cwd", return_value=elsewhere):
            return _run("check", *argv)

    def test_a_scaffolded_home_ring_passes_every_item_check(self):
        with _home() as home:
            self._ring(home)

            code, output = self._check(home, str(home))

            self.assertEqual(0, code, output)
            self.assertNotIn("ERROR", output)
            self.assertIn(f"ring: {home}", output)
            self.assertIn("skill 1, pack 1, workflow 1, sheet 1", output)

    def test_a_sheet_carrying_a_pack_only_section_is_refused(self):
        with _home() as home:
            self._ring(home)
            manifest = home / "sheets" / "market-brief" / "SHEET.md"
            manifest.write_text(
                manifest.read_text(encoding="utf-8") + "\n## Workspace\n\nMine.\n",
                encoding="utf-8",
            )

            code, output = self._check(home, str(home))

            self.assertEqual(1, code, output)
            self.assertIn("sheets/market-brief/SHEET.md", output)
            self.assertIn("'## Workspace' is the pack's", output)

    def test_a_workflow_body_over_the_tier_budget_is_refused(self):
        with _home() as home:
            self._ring(home)
            manifest = home / "workflows" / "team-flow" / "SKILL.md"
            padding = " ".join(["padding"] * (BODY_BUDGET["workflows"] + 1))
            manifest.write_text(
                manifest.read_text(encoding="utf-8") + "\n" + padding + "\n",
                encoding="utf-8",
            )

            code, output = self._check(home, str(home))

            self.assertEqual(1, code, output)
            self.assertIn("workflows/team-flow/SKILL.md", output)
            self.assertIn(
                f"exceeds the workflow-tier budget of {BODY_BUDGET['workflows']}",
                output,
            )

    def test_a_call_edge_that_resolves_to_nothing_is_refused(self):
        """A ring item's edges point out of the ring, so the checker grades
        them against every name that resolves from here. The library verb
        both bodies name has to pass on the same reading that refuses the
        typo beside it, or the check would be measuring the ring alone."""

        with _home() as home:
            self._ring(home)
            manifest = home / "workflows" / "team-flow" / "SKILL.md"
            manifest.write_text(
                manifest.read_text(encoding="utf-8")
                + "\nCalls `orch-do` and `orch-nonesuch`.\n",
                encoding="utf-8",
            )

            code, output = self._check(home, str(home))

            self.assertEqual(1, code, output)
            self.assertIn(
                "backtick reference `orch-nonesuch` does not resolve", output,
            )
            self.assertNotIn("`orch-do` does not resolve", output)

    def test_the_ring_defaults_to_this_project_then_the_home_ring(self):
        with _home() as home, tempfile.TemporaryDirectory() as raw:
            self._ring(home)
            project = Path(raw).resolve()
            (project / ".git").mkdir(parents=True)
            (project / ".orchflows" / "skills").mkdir(parents=True)

            code, at_home = self._check(home)
            self.assertEqual(0, code, at_home)
            self.assertIn(f"ring: {home}", at_home)

            with patch.object(rings.Path, "cwd", return_value=project), \
                    patch.object(orchflows.Path, "cwd", return_value=project):
                code, in_project = _run("check")

            self.assertEqual(0, code, in_project)
            self.assertIn(f"ring: {project / '.orchflows'}", in_project)

    def test_a_directory_holding_a_ring_is_read_as_that_ring(self):
        with _home() as home, tempfile.TemporaryDirectory() as raw:
            project = Path(raw).resolve()
            (project / ".orchflows" / "workflows").mkdir(parents=True)

            code, output = self._check(home, str(project))

            self.assertEqual(0, code, output)
            self.assertIn(f"ring: {project / '.orchflows'}", output)

    def test_a_ring_that_is_not_there_is_named_rather_than_passed(self):
        with _home() as home:
            missing = home / "no-such-ring"

            with patch.object(rings.Path, "cwd", return_value=home / "nowhere"):
                (home / "nowhere").mkdir(exist_ok=True)
                code = orchflows.main(["check", str(missing)])

            self.assertEqual(1, code)


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

    def test_a_library_workflow_is_listed_once_and_only_as_a_workflow(self):
        """One directory, one kind. `skills/workflows` ships inside the
        skills tier for the installer's and the validator's sake, so its
        bodies used to resolve under kind `skill` as well and reach the
        inventory twice -- two rows for one file, each claiming a different
        door. Derived from the home rather than named, so a workflow added
        there is covered the day it lands."""

        home = ROOT / "skills" / "workflows"
        names = sorted(
            path.name for path in home.iterdir()
            if (path / "SKILL.md").is_file()
        )
        self.assertTrue(names, f"{home} ships no workflow for this to read")

        with _home() as ring:
            (ring / "nowhere").mkdir()
            with patch.object(rings.Path, "cwd", return_value=ring / "nowhere"):
                code, output = _run("list")

        self.assertEqual(0, code, output)
        for name in names:
            with self.subTest(workflow=name):
                rows = [
                    cells for cells in (line.split() for line in output.splitlines())
                    if len(cells) >= 5 and cells[1] == name
                ]
                self.assertEqual(
                    1, len(rows),
                    f"{name} is listed {len(rows)} times, not once: {output}",
                )
                self.assertEqual("workflow", rows[0][0])

    def test_a_sheet_is_listed_like_every_other_ring_item(self):
        """A sheet has no host surface, so `list` is the only place a user
        sees one at all: absent from the inventory it is an item that
        resolves and cannot be found."""

        with _home() as home:
            (home / "sheets" / "market-brief").mkdir(parents=True)
            (home / "sheets" / "market-brief" / "SHEET.md").write_text(
                "---\nname: market-brief\n---\n", encoding="utf-8",
            )

            with patch.object(rings.Path, "cwd", return_value=home / "nowhere"):
                (home / "nowhere").mkdir()
                code, output = _run("list", "--kind", "sheet")

            self.assertEqual(0, code, output)
            self.assertEqual(
                ["sheet", "market-brief", "home"], _row(output, "market-brief")[:3],
            )

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
