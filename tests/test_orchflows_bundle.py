"""The bundle manifest: what `add` follows, what it refuses, what `sync` restores.

Every bundle here is a real local git repository tagged `v1`, because the
closure `add` walks is made of clones and remote reads: a fake would prove
the walk and not the thing the walk is made of.
"""

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

from scripts import orchflows, orchflows_bundle, orchflows_home, rings, state_root
from tools.validate_support import bundle as bundle_check
from tools.validate_support.packages import Diagnostics

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
    with tempfile.TemporaryDirectory(prefix="orchflows-bundle-") as tmp:
        home = Path(tmp).resolve()
        with patch.dict(os.environ, {state_root.ENV_VAR: str(home / "state")}):
            yield home


def _run(*argv):
    stream = io.StringIO()
    with contextlib.redirect_stdout(stream):
        code = orchflows.main(list(argv))
    return code, stream.getvalue()


def _write(root: Path, name: str, requires=None) -> Path:
    """One bundle's working tree: a skill, and a manifest unless `requires`
    is ``None``, which is a bundle published before manifests existed."""

    source = root / name
    skill = source / rings.BUNDLE_DIR / "skills" / f"{name}-skill"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text(
        f"---\nname: {name}-skill\n---\n\nbody\n", encoding="utf-8",
    )
    if requires is None:
        return source
    lines = ["---", f"name: {name}", "version: 2026-09-02"]
    if requires:
        lines.append("requires:")
        lines.extend(f"  - {entry}" for entry in requires)
    else:
        lines.append("requires: []")
    lines.extend(["---", "", f"# {name}", ""])
    (source / rings.BUNDLE_DIR / rings.BUNDLE_MANIFEST).write_text(
        "\n".join(lines), encoding="utf-8",
    )
    return source


def _publish(source: Path) -> str:
    """Commit and tag one bundle tree at `v1`; its URL is its path."""

    for args in (
        ("init", "--quiet", "-b", "main"), ("add", "-A"),
        ("commit", "--quiet", "-m", source.name), ("tag", "v1"),
    ):
        done = _git(*args, cwd=source)
        if done.returncode != 0:
            raise unittest.SkipTest(f"git {args[0]}: {done.stderr.strip()}")
    return source.as_posix()


def _bundle(root: Path, name: str, requires=()) -> str:
    return _publish(_write(root, name, requires))


def _clone_manifest(home: Path, name: str) -> Path:
    """The manifest `add` actually read: the clone's, not the source tree's."""

    return (home / rings.IMPORTS_DIR / name / rings.BUNDLE_DIR
            / rings.BUNDLE_MANIFEST)


def _lock(home: Path):
    return json.loads((home / rings.IMPORTS_LOCK).read_text(encoding="utf-8"))["imports"]


class ClosureTests(unittest.TestCase):
    def test_add_pins_every_bundle_the_named_one_requires(self):
        with _home() as home, tempfile.TemporaryDirectory() as raw:
            root = Path(raw).resolve()
            beta = _bundle(root, "beta-bundle")
            alpha = _bundle(root, "alpha-bundle", [f"{beta}@v1"])

            code, output = _run("add", f"{alpha}@v1")

            self.assertEqual(0, code, output)
            self.assertEqual(
                [("alpha-bundle", "v1"), ("beta-bundle", "v1")],
                [(entry["name"], entry["pin"]) for entry in _lock(home)],
            )
            self.assertIn("required beta-bundle @ v1", output)
            self.assertEqual(
                "imports", rings.resolve("skill", "beta-bundle-skill")["ring"],
            )

    def test_a_bundle_reached_twice_is_cloned_once_and_is_not_a_cycle(self):
        with _home() as home, tempfile.TemporaryDirectory() as raw:
            root = Path(raw).resolve()
            delta = _bundle(root, "delta-bundle")
            left = _bundle(root, "left-bundle", [f"{delta}@v1"])
            right = _bundle(root, "right-bundle", [f"{delta}@v1"])
            top = _bundle(root, "top-bundle", [f"{left}@v1", f"{right}@v1"])

            code, output = _run("add", f"{top}@v1")

            self.assertEqual(0, code, output)
            self.assertEqual(
                ["delta-bundle", "left-bundle", "right-bundle", "top-bundle"],
                [entry["name"] for entry in _lock(home)],
            )

    def test_a_cycle_is_refused_naming_the_manifest_that_closes_it(self):
        with _home() as home, tempfile.TemporaryDirectory() as raw:
            root = Path(raw).resolve()
            first = (root / "first-bundle").as_posix()
            second = (root / "second-bundle").as_posix()
            _publish(_write(root, "first-bundle", [f"{second}@v1"]))
            _publish(_write(root, "second-bundle", [f"{first}@v1"]))

            with self.assertRaises(rings.RingError) as raised:
                orchflows_home.add(f"{first}@v1")

            self.assertEqual("requires-cycle", raised.exception.code)
            self.assertIn(
                str(_clone_manifest(home, "second-bundle")),
                raised.exception.detail,
            )
            self.assertIn(
                "first-bundle -> second-bundle -> first-bundle",
                raised.exception.detail,
            )
            self.assertFalse((home / rings.IMPORTS_LOCK).exists())
            self.assertFalse((home / rings.IMPORTS_DIR / "first-bundle").exists())

    def test_an_unpinned_requirement_is_refused_naming_the_manifest(self):
        for label, entry in (("no pin at all", "{url}"), ("a branch", "{url}@main")):
            with self.subTest(label), _home() as home, \
                    tempfile.TemporaryDirectory() as raw:
                root = Path(raw).resolve()
                loose = _bundle(root, "loose-bundle")
                asking = _bundle(root, "asking-bundle", [entry.format(url=loose)])

                with self.assertRaises(rings.RingError) as raised:
                    orchflows_home.add(f"{asking}@v1")

                self.assertEqual("requires-unpinned", raised.exception.code)
                self.assertIn(
                    str(_clone_manifest(home, "asking-bundle")),
                    raised.exception.detail,
                )
                self.assertIn(entry.format(url=loose), raised.exception.detail)
                self.assertFalse((home / rings.IMPORTS_LOCK).exists())
                self.assertFalse(
                    (home / rings.IMPORTS_DIR / "asking-bundle").exists(),
                )

    def test_a_bundle_with_no_manifest_imports_as_it_always_did(self):
        with _home() as home, tempfile.TemporaryDirectory() as raw:
            root = Path(raw).resolve()
            plain = _publish(_write(Path(raw).resolve(), "plain-bundle", None))
            self.assertFalse(
                (root / "plain-bundle" / rings.BUNDLE_DIR
                 / rings.BUNDLE_MANIFEST).exists(),
            )

            code, output = _run("add", f"{plain}@v1")

            self.assertEqual(0, code, output)
            self.assertEqual(["plain-bundle"], [e["name"] for e in _lock(home)])
            self.assertNotIn("required ", output)

    def test_sync_restores_a_closure_the_lock_names_only_the_root_of(self):
        with _home() as home, tempfile.TemporaryDirectory() as raw:
            root = Path(raw).resolve()
            needed = _bundle(root, "needed-bundle")
            asking = _bundle(root, "asking-bundle", [f"{needed}@v1"])
            orchflows_home.write_lock(
                [{"name": "asking-bundle", "url": asking, "pin": "v1"}], home,
            )

            restored = orchflows_home.restore(home)

            self.assertEqual(
                [("asking-bundle", "cloned"), ("needed-bundle", "cloned")],
                [(item["name"], item["action"]) for item in restored],
            )
            self.assertEqual(
                ["asking-bundle", "needed-bundle"],
                [entry["name"] for entry in _lock(home)],
            )

    def test_restore_reports_a_requirement_it_cannot_pin_and_syncs_on(self):
        with _home() as home, tempfile.TemporaryDirectory() as raw:
            root = Path(raw).resolve()
            loose = (root / "loose-bundle").as_posix()
            asking = _bundle(root, "asking-bundle", [loose])
            orchflows_home.write_lock(
                [{"name": "asking-bundle", "url": asking, "pin": "v1"}], home,
            )

            restored = orchflows_home.restore(home)

            self.assertEqual(["asking-bundle"], [item["name"] for item in restored])
            self.assertEqual("cloned", restored[0]["action"])
            self.assertIn("is not a pinned bundle", restored[0]["detail"])
            self.assertEqual(["asking-bundle"], [e["name"] for e in _lock(home)])


class ScaffoldTests(unittest.TestCase):
    def test_a_scaffolded_manifest_reads_back_through_the_reader(self):
        with _home() as home:
            (home / "nowhere").mkdir(parents=True)
            with patch.object(rings.Path, "cwd", return_value=home / "nowhere"):
                code, output = _run("new", "bundle", "my-bundle")

            self.assertEqual(0, code, output)
            manifest = orchflows_bundle.read_manifest(home)
            self.assertEqual("my-bundle", manifest["name"])
            self.assertEqual([], manifest["requires"])
            self.assertRegex(manifest["version"], r"^\d{4}-\d{2}-\d{2}$")

    def test_a_manifest_takes_its_rings_own_name_when_nobody_names_it(self):
        with _home() as home:
            project = home / "widget-app"
            (project / rings.BUNDLE_DIR).mkdir(parents=True)
            with patch.object(rings.Path, "cwd", return_value=project):
                code, output = _run("new", "bundle")

            self.assertEqual(0, code, output)
            manifest = orchflows_bundle.read_manifest(project / rings.BUNDLE_DIR)
            self.assertEqual("widget-app", manifest["name"])

    def test_this_repositorys_own_bundle_is_named_and_requires_nothing(self):
        manifest = orchflows_bundle.read_manifest(ROOT / rings.BUNDLE_DIR)

        self.assertIsNotNone(manifest)
        self.assertEqual("orchflows-contrib", manifest["name"])
        self.assertEqual([], manifest["requires"])
        self.assertRegex(manifest["version"], r"^\d{4}-\d{2}-\d{2}$")

    def test_the_compiler_grades_this_repositorys_own_manifest(self):
        """The shape above is a fact about the file; this is the check that
        holds it there. `tools/validate.py` runs the same function
        `orchflows check` runs over a ring, so a `requires` entry that lost
        its pin fails here rather than in a consumer's `orchflows add`."""

        diag = Diagnostics()

        bundle_check.validate_bundle_manifest(diag)

        self.assertEqual([], diag.lines())


if __name__ == "__main__":
    unittest.main()
