"""Per-item environments: declared beside the manifest, built by sync, resolved by env."""

from __future__ import annotations

import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import orchflows, orchflows_envs, rings, rings_trust, state_root


@contextlib.contextmanager
def _world():
    """A home ring and a project ring under one temporary root, the sink moved."""

    with tempfile.TemporaryDirectory(prefix="orchflows-envs-") as tmp:
        root = Path(tmp).resolve()
        home = root / "home"
        project = root / "project"
        for kind_dir in rings.RING_DIRS.values():
            (home / kind_dir).mkdir(parents=True, exist_ok=True)
            (project / rings.BUNDLE_DIR / kind_dir).mkdir(parents=True, exist_ok=True)
        with patch.dict(os.environ, {state_root.ENV_VAR: str(home / "state")}):
            yield {"root": root, "home": home, "project": project}


def _item(directory: Path, kind: str, name: str, requirements=None) -> Path:
    manifest = directory / name / rings.MANIFESTS[kind]
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_bytes(f"---\nname: {name}\n---\n\nbody\n".encode("utf-8"))
    if requirements is not None:
        (manifest.parent / orchflows_envs.REQUIREMENTS_NAME).write_bytes(
            requirements.encode("utf-8")
        )
    return manifest.parent


def _fake_builder(calls):
    """A builder that records its calls and leaves an interpreter behind."""

    def build(env: Path, requirements: Path) -> None:
        calls.append((env, requirements))
        target = orchflows_envs.interpreter(env)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"")

    return build


def _run(*argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = orchflows.main(list(argv))
    return code, out.getvalue(), err.getvalue()


class DeclarationTests(unittest.TestCase):
    def test_the_declaration_is_one_requirements_file_beside_the_manifest(self):
        with _world() as world:
            declaring = _item(world["home"] / "skills", "skill", "fetcher", "requests==2.32.3\n")
            silent = _item(world["home"] / "skills", "skill", "quiet")

            self.assertEqual(
                declaring / orchflows_envs.REQUIREMENTS_NAME,
                orchflows_envs.requirements_of(declaring),
            )
            self.assertIsNone(orchflows_envs.requirements_of(silent))

    def test_requirement_lines_drop_comments_and_blanks(self):
        with _world() as world:
            item = _item(
                world["home"] / "skills", "skill", "fetcher",
                "# pinned on 2026-09-02\n\nrequests==2.32.3  # http\n   \nlxml==5.3.0\n",
            )

            self.assertEqual(
                ["requests==2.32.3", "lxml==5.3.0"],
                orchflows_envs.requirement_lines(orchflows_envs.requirements_of(item)),
            )

    def test_the_environment_lives_under_the_home_ring_by_kind_and_name(self):
        with _world() as world:
            env = orchflows_envs.env_home("skill", "fetcher", world["home"])

            self.assertEqual(world["home"] / "envs" / "skill" / "fetcher", env)
            self.assertIn("envs", orchflows_envs.interpreter(env).parts)


class EnsureTests(unittest.TestCase):
    def test_create_then_reuse_then_refresh_follow_the_files_digest(self):
        with _world() as world:
            item = _item(world["home"] / "skills", "skill", "fetcher", "requests==2.32.3\n")
            calls = []
            builder = _fake_builder(calls)

            first = orchflows_envs.ensure("skill", "fetcher", item, home=world["home"], builder=builder)
            second = orchflows_envs.ensure("skill", "fetcher", item, home=world["home"], builder=builder)
            (item / orchflows_envs.REQUIREMENTS_NAME).write_bytes(b"requests==2.32.4\n")
            third = orchflows_envs.ensure("skill", "fetcher", item, home=world["home"], builder=builder)

            self.assertEqual(["create", "reuse", "refresh"], [first["action"], second["action"], third["action"]])
            self.assertEqual(2, len(calls))
            stamp = json.loads((Path(third["env"]) / orchflows_envs.STAMP_NAME).read_text(encoding="utf-8"))
            self.assertEqual(orchflows_envs.digest(item / orchflows_envs.REQUIREMENTS_NAME), stamp["requirements_sha256"])
            self.assertEqual(str(orchflows_envs.interpreter(Path(third["env"]))), third["interpreter"])

    def test_a_stamp_without_an_interpreter_is_not_a_built_environment(self):
        with _world() as world:
            item = _item(world["home"] / "skills", "skill", "fetcher", "requests==2.32.3\n")
            env = orchflows_envs.env_home("skill", "fetcher", world["home"])
            env.mkdir(parents=True)
            (env / orchflows_envs.STAMP_NAME).write_text(
                json.dumps({"schema": orchflows_envs.STAMP_SCHEMA, "requirements_sha256": orchflows_envs.digest(item / "requirements.txt")}),
                encoding="utf-8",
            )

            self.assertEqual("create", orchflows_envs.action(env, item / "requirements.txt"))

    def test_a_failed_build_leaves_no_stamp_and_no_directory(self):
        with _world() as world:
            item = _item(world["home"] / "skills", "skill", "fetcher", "requests==2.32.3\n")

            def failing(env: Path, requirements: Path) -> None:
                orchflows_envs.interpreter(env).parent.mkdir(parents=True, exist_ok=True)
                raise RuntimeError("pip exit 1")

            with self.assertRaises(RuntimeError):
                orchflows_envs.ensure("skill", "fetcher", item, home=world["home"], builder=failing)

            env = orchflows_envs.env_home("skill", "fetcher", world["home"])
            self.assertFalse(env.exists())
            self.assertEqual("create", orchflows_envs.action(env, item / "requirements.txt"))

    def test_an_item_that_declares_nothing_has_no_environment_to_ensure(self):
        with _world() as world:
            item = _item(world["home"] / "skills", "skill", "quiet")

            with self.assertRaises(ValueError):
                orchflows_envs.ensure("skill", "quiet", item, home=world["home"], builder=_fake_builder([]))

    def test_a_comment_only_declaration_builds_a_bare_venv_without_pip(self):
        # The one real build: no requirement lines means no pip bootstrap and
        # no network, so it is cheap enough to run here and it proves the
        # builder makes an interpreter the stamp can stand behind.
        with _world() as world:
            item = _item(world["home"] / "skills", "skill", "bare", "# nothing yet\n")

            record = orchflows_envs.ensure("skill", "bare", item, home=world["home"])

            self.assertEqual("create", record["action"])
            self.assertTrue(Path(record["interpreter"]).is_file(), record)
            self.assertIsNotNone(orchflows_envs.read_stamp(Path(record["env"])))


class SyncTests(unittest.TestCase):
    def test_sync_builds_declaring_items_and_passes_the_silent_ones(self):
        with _world() as world:
            _item(world["home"] / "skills", "skill", "fetcher", "requests==2.32.3\n")
            _item(world["home"] / "skills", "skill", "quiet")
            _item(world["home"] / "packs", "pack", "tabular", "pandas==2.2.3\n")
            calls = []

            outcomes = orchflows_envs.sync(
                rings.inventory(home=world["home"], lib=world["root"] / "nolib", start=world["root"]),
                home=world["home"], builder=_fake_builder(calls),
            )

            self.assertEqual(
                [("pack", "tabular", "create"), ("skill", "fetcher", "create")],
                sorted((o["kind"], o["name"], o["action"]) for o in outcomes),
            )
            self.assertEqual(2, len(calls))

    def test_an_untrusted_project_item_is_named_with_its_remedy_and_never_built(self):
        with _world() as world:
            bundle = world["project"] / rings.BUNDLE_DIR
            _item(bundle / "skills", "skill", "fetcher", "requests==2.32.3\n")
            calls = []

            outcomes = orchflows_envs.sync(
                rings.inventory(project=bundle, home=world["home"], lib=world["root"] / "nolib", start=world["root"]),
                home=world["home"], builder=_fake_builder(calls),
            )

            self.assertEqual([], calls)
            self.assertEqual(1, len(outcomes), outcomes)
            self.assertEqual("skipped", outcomes[0]["action"])
            self.assertIn(f"orchflows trust {bundle}", outcomes[0]["detail"])

            rings_trust.grant(bundle)
            outcomes = orchflows_envs.sync(
                rings.inventory(project=bundle, home=world["home"], lib=world["root"] / "nolib", start=world["root"]),
                home=world["home"], builder=_fake_builder(calls),
            )
            self.assertEqual("create", outcomes[0]["action"])
            self.assertEqual(1, len(calls))

    def test_the_home_gitignore_covers_the_environments(self):
        from scripts import orchflows_home

        self.assertIn(f"{orchflows_envs.ENVS_DIR}/", orchflows_home.MANAGED_IGNORES)


class EnvCommandTests(unittest.TestCase):
    def test_env_prints_this_interpreter_for_an_item_that_declares_nothing(self):
        with _world() as world:
            _item(world["home"] / "skills", "skill", "quiet")

            code, out, err = _run("env", "skill", "quiet")

            self.assertEqual(0, code, err)
            self.assertEqual(sys.executable, out.strip())

    def test_env_refuses_a_declared_but_unbuilt_environment_with_the_sync_remedy(self):
        with _world() as world:
            _item(world["home"] / "skills", "skill", "fetcher", "requests==2.32.3\n")

            code, out, err = _run("env", "skill", "fetcher")

            self.assertEqual(1, code, out)
            self.assertIn("orchflows sync", err)

    def test_env_prints_the_items_own_interpreter_once_sync_built_it(self):
        with _world() as world:
            item = _item(world["home"] / "skills", "skill", "fetcher", "requests==2.32.3\n")
            with patch.object(orchflows_envs, "build", _fake_builder([])):
                code, out, err = _run("sync")
            self.assertEqual(0, code, err)
            self.assertIn("env skill 'fetcher': create", out)

            code, out, err = _run("env", "skill", "fetcher")

            self.assertEqual(0, code, err)
            expected = orchflows_envs.interpreter(orchflows_envs.env_home("skill", "fetcher", world["home"]))
            self.assertEqual(str(expected), out.strip())
            self.assertEqual(
                str(item / orchflows_envs.REQUIREMENTS_NAME),
                orchflows_envs.read_stamp(expected.parent.parent)["requirements"],
            )


if __name__ == "__main__":
    unittest.main()
