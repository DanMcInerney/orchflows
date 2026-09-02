"""The two dependency classes `sync` does not build a virtual environment for.

`tools.txt` is declared and checked and never installed; `package.json` plus
its lockfile is installed into the item's own `node_modules/`. Both are read
off the same inventory the Python environments are, so every check here
drives the resolver rather than a directory walk of its own.
"""

from __future__ import annotations

import contextlib
import io
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import (
    orchflows, orchflows_envs, orchflows_home, orchflows_node, orchflows_tools,
    rings, rings_trust, state_root,
)

ROOT = Path(__file__).resolve().parent.parent
# A name no machine running this suite can have on PATH, so "missing" is a
# fact here rather than a property of the developer's laptop.
ABSENT = "orchflows-no-such-tool"


@contextlib.contextmanager
def _world():
    """A home ring and a project ring under one temporary root, the sink moved."""

    with tempfile.TemporaryDirectory(prefix="orchflows-tooling-") as tmp:
        root = Path(tmp).resolve()
        home = root / "home"
        project = root / "project"
        for kind_dir in rings.RING_DIRS.values():
            (home / kind_dir).mkdir(parents=True, exist_ok=True)
            (project / rings.BUNDLE_DIR / kind_dir).mkdir(parents=True, exist_ok=True)
        with patch.dict(os.environ, {state_root.ENV_VAR: str(home / "state")}):
            yield {"root": root, "home": home, "project": project}


def _item(directory: Path, kind: str, name: str, files=None) -> Path:
    """One ring item, plus whatever declaration files the test names."""

    manifest = directory / name / rings.MANIFESTS[kind]
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_bytes(f"---\nname: {name}\n---\n\nbody\n".encode("utf-8"))
    for filename, content in (files or {}).items():
        (manifest.parent / filename).write_bytes(content.encode("utf-8"))
    return manifest.parent


def _inventory(world, *, project=None):
    """The resolver's answer for this world alone: no library, no repository."""

    return rings.inventory(
        project=project, home=world["home"],
        lib=world["root"] / "nolib", start=world["root"],
    )


def _which(*present):
    found = set(present)
    return lambda name: f"/usr/bin/{name}" if name in found else None


def _runner(codes):
    """A probe runner reading `(exit code, output)` out of a table by argv[0]."""

    calls = []

    def run(argv, timeout):
        calls.append((list(argv), timeout))
        return codes.get(argv[0], (127, ""))

    run.calls = calls
    return run


class GrammarTests(unittest.TestCase):
    def test_the_two_forms_parse_with_their_version_spec_and_probe(self):
        with _world() as world:
            item = _item(
                world["home"] / "workflows", "workflow", "render",
                {"tools.txt": (
                    "# the machine's, not ours\n"
                    "ffmpeg\n"
                    "python >= 3.11 :: python --version\n"
                    "node >=20,<21\n"
                    "\n"
                    "env OPENAI_API_KEY\n"
                )},
            )

            parsed, problems = orchflows_tools.declarations(orchflows_tools.tools_of(item))

            self.assertEqual([], problems)
            self.assertEqual(
                [(2, "ffmpeg", [], None),
                 (3, "python", [(">=", "3.11")], "python --version")],
                [(e["line"], e["name"], e["specs"], e["probe"]) for e in parsed[:2]],
            )
            self.assertEqual([(">=", "20"), ("<", "21")], parsed[2]["specs"])
            self.assertEqual((6, "OPENAI_API_KEY"), (parsed[3]["line"], parsed[3]["variable"]))

    def test_every_malformed_line_is_a_problem_carrying_its_line_number(self):
        with _world() as world:
            item = _item(
                world["home"] / "workflows", "workflow", "render",
                {"tools.txt": (
                    "ffmpeg\n"
                    "/usr/bin/ffmpeg\n"
                    "python 3.11\n"
                    "ffmpeg ::\n"
                    "env\n"
                    "env A B\n"
                    "env KEY :: true\n"
                )},
            )

            parsed, problems = orchflows_tools.declarations(orchflows_tools.tools_of(item))

            self.assertEqual(["ffmpeg"], [entry["name"] for entry in parsed])
            self.assertEqual([2, 3, 4, 5, 6, 7], [problem["line"] for problem in problems])
            self.assertIn("is not a tool name", problems[0]["problem"])
            self.assertIn("is not a version spec", problems[1]["problem"])


class ResolutionTests(unittest.TestCase):
    def test_a_missing_tool_is_reported_and_a_present_one_is_silent(self):
        with _world() as world:
            item = _item(
                world["home"] / "workflows", "workflow", "render",
                {"tools.txt": f"ffmpeg\n{ABSENT}\n"},
            )

            reports = orchflows_tools.check(item, which=_which("ffmpeg"))

            self.assertEqual(1, len(reports), reports)
            self.assertEqual(2, reports[0]["line"])
            self.assertEqual(f"'{ABSENT}' is not on PATH", reports[0]["detail"])

    def test_a_probes_exit_code_decides_and_no_path_lookup_is_made(self):
        with _world() as world:
            item = _item(
                world["home"] / "workflows", "workflow", "render",
                {"tools.txt": "chrome :: chrome --headless\nffmpeg :: ffmpeg -version\n"},
            )
            runner = _runner({"chrome": (0, ""), "ffmpeg": (3, "")})

            def refuse(name):
                raise AssertionError(f"resolved {name} on PATH despite a probe")

            reports = orchflows_tools.check(item, which=refuse, runner=runner)

            self.assertEqual(1, len(reports), reports)
            self.assertIn("probe 'ffmpeg -version' exited 3", reports[0]["detail"])
            self.assertEqual(
                [["chrome", "--headless"], ["ffmpeg", "-version"]],
                [argv for argv, _timeout in runner.calls],
            )

    def test_a_probe_that_cannot_run_at_all_is_reported_not_swallowed(self):
        with _world() as world:
            item = _item(
                world["home"] / "workflows", "workflow", "render",
                {"tools.txt": "chrome :: chrome --headless\n"},
            )

            reports = orchflows_tools.check(
                item, which=_which(), runner=lambda argv, timeout: (None, ""),
            )

            self.assertEqual(1, len(reports), reports)
            self.assertIn("could not run", reports[0]["detail"])

    def test_a_version_spec_is_read_off_version_output_only_when_it_parses(self):
        with _world() as world:
            item = _item(
                world["home"] / "workflows", "workflow", "render",
                {"tools.txt": "python >= 3.11\n"},
            )

            met = orchflows_tools.check(
                item, which=_which("python"),
                runner=lambda argv, timeout: (0, "Python 3.13.9\n"),
            )
            unmet = orchflows_tools.check(
                item, which=_which("python"),
                runner=lambda argv, timeout: (0, "Python 3.9.13\n"),
            )
            unshaped = orchflows_tools.check(
                item, which=_which("python"),
                runner=lambda argv, timeout: (0, "a build from source\n"),
            )

            self.assertEqual([], met)
            self.assertEqual([], unshaped)
            self.assertEqual(1, len(unmet), unmet)
            self.assertIn("is 3.9.13, which does not satisfy >= 3.11", unmet[0]["detail"])

    def test_a_version_spec_is_not_read_when_the_line_carries_a_probe(self):
        with _world() as world:
            item = _item(
                world["home"] / "workflows", "workflow", "render",
                {"tools.txt": "python >= 3.11 :: python -c pass\n"},
            )
            runner = _runner({"python": (0, "Python 3.9.13\n")})

            self.assertEqual(
                [], orchflows_tools.check(item, which=_which("python"), runner=runner),
            )
            self.assertEqual([["python", "-c", "pass"]], [argv for argv, _t in runner.calls])

    def test_a_missing_variable_is_reported_by_name_and_never_by_value(self):
        with _world() as world:
            item = _item(
                world["home"] / "workflows", "workflow", "render",
                {"tools.txt": "env SET_KEY\nenv UNSET_KEY\n"},
            )

            reports = orchflows_tools.check(
                item, environ={"SET_KEY": "s3cret-value"}, which=_which(),
            )

            self.assertEqual(1, len(reports), reports)
            self.assertEqual("environment variable UNSET_KEY is not set", reports[0]["detail"])
            self.assertNotIn("s3cret-value", repr(reports))

    def test_an_unparsable_line_is_reported_beside_the_missing_tools(self):
        with _world() as world:
            item = _item(
                world["home"] / "workflows", "workflow", "render",
                {"tools.txt": f"python 3.11\n{ABSENT}\n"},
            )

            reports = orchflows_tools.check(item, which=_which())

            self.assertEqual([1, 2], [report["line"] for report in reports])


class InventoryTests(unittest.TestCase):
    def test_every_declaring_item_is_checked_and_nothing_is_installed(self):
        with _world() as world:
            _item(
                world["home"] / "workflows", "workflow", "render",
                {"tools.txt": f"{ABSENT}\n"},
            )
            _item(world["home"] / "skills", "skill", "quiet")

            reports = orchflows_tools.check_inventory(_inventory(world), which=_which())

            self.assertEqual(
                [("workflow", "render", 1)],
                [(r["kind"], r["name"], r["line"]) for r in reports],
            )
            self.assertFalse((world["home"] / orchflows_envs.ENVS_DIR).exists())

    def test_an_untrusted_project_items_probes_are_never_run(self):
        with _world() as world:
            bundle = world["project"] / rings.BUNDLE_DIR
            _item(
                bundle / "workflows", "workflow", "render",
                {"tools.txt": "ffmpeg :: ffmpeg -version\n"},
            )

            def refuse(argv, timeout):
                raise AssertionError(f"ran {argv} from an untrusted item")

            reports = orchflows_tools.check_inventory(
                _inventory(world, project=bundle), which=_which(), runner=refuse,
            )

            self.assertEqual(1, len(reports), reports)
            self.assertIsNone(reports[0]["line"])
            self.assertIn(f"orchflows trust {bundle}", reports[0]["detail"])

            rings_trust.grant(bundle)
            reports = orchflows_tools.check_inventory(
                _inventory(world, project=bundle), which=_which(),
                runner=lambda argv, timeout: (0, ""),
            )
            self.assertEqual([], reports)


class NodeTests(unittest.TestCase):
    def test_the_lockfile_install_runs_in_the_item_directory_and_reuses_after(self):
        with _world() as world:
            item = _item(
                world["home"] / "skills", "skill", "capture",
                {"package.json": '{"name": "capture"}\n',
                 "package-lock.json": '{"lockfileVersion": 3}\n'},
            )
            calls = []

            def record(directory, command):
                calls.append((directory, command))

            first = orchflows_node.ensure(
                "skill", "capture", item, which=_which("node", "npm"), installer=record,
            )
            second = orchflows_node.ensure(
                "skill", "capture", item, which=_which("node", "npm"), installer=record,
            )
            (item / "package-lock.json").write_bytes(b'{"lockfileVersion": 4}\n')
            third = orchflows_node.ensure(
                "skill", "capture", item, which=_which("node", "npm"), installer=record,
            )

            self.assertEqual(
                ["install", "reuse", "install"],
                [first["action"], second["action"], third["action"]],
            )
            self.assertEqual([(item, ("npm", "ci")), (item, ("npm", "ci"))], calls)
            self.assertEqual(str(item / orchflows_node.MODULES_DIR), first["modules"])
            self.assertEqual(
                orchflows_node.digest(item / "package-lock.json"),
                orchflows_node.read_stamp(item)["lock_sha256"],
            )

    def test_a_pnpm_lockfile_takes_pnpms_frozen_install(self):
        with _world() as world:
            item = _item(
                world["home"] / "skills", "skill", "capture",
                {"package.json": '{"name": "capture"}\n',
                 "pnpm-lock.yaml": "lockfileVersion: '9.0'\n"},
            )
            calls = []

            orchflows_node.ensure(
                "skill", "capture", item, which=_which("node", "pnpm"),
                installer=lambda directory, command: calls.append(command),
            )

            self.assertEqual([("pnpm", "install", "--frozen-lockfile")], calls)

    def test_no_node_no_lockfile_and_no_manager_are_skipped_with_their_remedy(self):
        with _world() as world:
            pinned = _item(
                world["home"] / "skills", "skill", "capture",
                {"package.json": "{}\n", "package-lock.json": "{}\n"},
            )
            unpinned = _item(
                world["home"] / "skills", "skill", "loose", {"package.json": "{}\n"},
            )

            def refuse(directory, command):
                raise AssertionError(f"installed {command} in {directory}")

            nodeless = orchflows_node.ensure(
                "skill", "capture", pinned, which=_which(), installer=refuse,
            )
            lockless = orchflows_node.ensure(
                "skill", "loose", unpinned, which=_which("node", "npm"), installer=refuse,
            )
            managerless = orchflows_node.ensure(
                "skill", "capture", pinned, which=_which("node"), installer=refuse,
            )

            self.assertEqual(
                ["skipped", "skipped", "skipped"],
                [nodeless["action"], lockless["action"], managerless["action"]],
            )
            self.assertIn("'node' is not on PATH", nodeless["detail"])
            self.assertIn("no lockfile beside it", lockless["detail"])
            self.assertIn("'npm' is not on PATH", managerless["detail"])
            self.assertFalse(orchflows_node.modules_dir(pinned).exists())

    def test_an_untrusted_project_item_is_named_with_its_remedy_and_never_installed(self):
        with _world() as world:
            bundle = world["project"] / rings.BUNDLE_DIR
            _item(
                bundle / "skills", "skill", "capture",
                {"package.json": "{}\n", "package-lock.json": "{}\n"},
            )

            def refuse(directory, command):
                raise AssertionError(f"installed {command} in {directory}")

            outcomes = orchflows_node.sync(
                _inventory(world, project=bundle),
                which=_which("node", "npm"), installer=refuse,
            )

            self.assertEqual(1, len(outcomes), outcomes)
            self.assertEqual("skipped", outcomes[0]["action"])
            self.assertIn(f"orchflows trust {bundle}", outcomes[0]["detail"])

    def test_a_failed_install_leaves_no_stamp_to_reuse(self):
        with _world() as world:
            item = _item(
                world["home"] / "skills", "skill", "capture",
                {"package.json": "{}\n", "package-lock.json": "{}\n"},
            )

            def failing(directory, command):
                raise RuntimeError("npm exit 1")

            with self.assertRaises(RuntimeError):
                orchflows_node.ensure(
                    "skill", "capture", item, which=_which("node", "npm"), installer=failing,
                )

            self.assertIsNone(orchflows_node.read_stamp(item))
            self.assertEqual("install", orchflows_node.action(item, item / "package-lock.json"))


class PruneTests(unittest.TestCase):
    def test_prune_removes_exactly_the_environment_no_item_claims(self):
        with _world() as world:
            _item(
                world["home"] / "skills", "skill", "fetcher",
                {"requirements.txt": "requests==2.32.3\n"},
            )
            kept = orchflows_envs.env_home("skill", "fetcher", world["home"])
            orphan = orchflows_envs.env_home("pack", "retired", world["home"])
            stranger = world["home"] / orchflows_envs.ENVS_DIR / "not-a-kind" / "thing"
            for directory in (kept, orphan, stranger):
                directory.mkdir(parents=True)

            removed = orchflows_envs.prune(_inventory(world), home=world["home"])

            self.assertEqual(
                [("pack", "retired", "pruned", str(orphan))],
                [(r["kind"], r["name"], r["action"], r["env"]) for r in removed],
            )
            self.assertFalse(orphan.exists())
            self.assertTrue(kept.is_dir())
            self.assertTrue(stranger.is_dir())

    def test_prune_says_nothing_when_there_is_no_environments_tree_at_all(self):
        with _world() as world:
            self.assertEqual([], orchflows_envs.prune(_inventory(world), home=world["home"]))


class IgnoreTests(unittest.TestCase):
    def test_the_home_ring_block_carries_the_node_modules_line(self):
        with _world() as world:
            orchflows_home.ensure(world["home"])

            text = (world["home"] / orchflows_home.GITIGNORE_NAME).read_text(encoding="utf-8")

            self.assertIn(f"{orchflows_node.MODULES_DIR}/", orchflows_home.MANAGED_IGNORES)
            self.assertIn(f"\n{orchflows_node.MODULES_DIR}/\n", text)

    def test_the_project_block_carries_it_and_keeps_the_repositorys_own_lines(self):
        with _world() as world:
            gitignore = world["project"] / orchflows_home.GITIGNORE_NAME
            gitignore.write_bytes(b"dist/\n")

            written = orchflows_home.ensure_project_ignores(world["project"])
            orchflows_home.ensure_project_ignores(world["project"])

            text = written.read_text(encoding="utf-8")
            self.assertEqual(gitignore, written)
            self.assertIn("dist/", text)
            self.assertIn(f"\n{orchflows_node.MODULES_DIR}/\n", text)
            self.assertEqual(1, text.count(orchflows_home.GITIGNORE_START))


class ValidatorTests(unittest.TestCase):
    def test_the_library_validator_names_the_line_a_reader_cannot_parse(self):
        """`orchflows check` runs these item checks over a ring; the library
        validator runs them over the library. A line the parser cannot read
        is a declaration `sync` would skip in silence, so it is an error at
        both doors, named by its line number."""

        from tools.validate_support import packages as validate_packages
        from tools.validate_support import tooling as validate_tooling

        with _world() as world:
            graded = world["root"] / "graded"
            item = graded / "example-workflows" / "render"
            item.mkdir(parents=True)
            shutil.copytree(ROOT / "packs", graded / "packs")
            (item / "SKILL.md").write_bytes(b"---\nname: render\n---\n\nbody\n")
            (item / orchflows_tools.TOOLS_NAME).write_bytes(b"ffmpeg\npython 3.11\n")
            diag = validate_packages.Diagnostics()
            for module in (validate_packages, validate_tooling):
                module.ROOT = graded
            try:
                validate_tooling.validate_tools_declarations(diag)
            finally:
                for module in (validate_packages, validate_tooling):
                    module.ROOT = ROOT

            lines = diag.lines()
            self.assertEqual(1, len(lines), lines)
            self.assertIn("line 2", lines[0])
            self.assertTrue(diag.has_errors)


class SyncReportTests(unittest.TestCase):
    def test_sync_reports_each_missing_tool_with_its_line_and_prunes_the_orphan(self):
        with _world() as world:
            _item(
                world["home"] / "workflows", "workflow", "render",
                {"tools.txt": f"{ABSENT}\n"},
            )
            orphan = orchflows_envs.env_home("skill", "gone", world["home"])
            orphan.mkdir(parents=True)
            nowhere = world["root"] / "nowhere"
            nowhere.mkdir()

            out = io.StringIO()
            with patch.object(rings.Path, "cwd", return_value=nowhere), \
                    contextlib.redirect_stdout(out):
                orchflows._report_dependencies()

            printed = out.getvalue()
            self.assertIn(
                f"tools workflow 'render': '{ABSENT}' is not on PATH "
                f"({orchflows_tools.TOOLS_NAME} line 1)",
                printed,
            )
            self.assertIn(f"env skill 'gone': pruned {orphan}", printed)
            self.assertFalse(orphan.exists())


if __name__ == "__main__":
    unittest.main()
