"""Ring host adapters: inert bodies, two scopes, and the committed proof."""

from __future__ import annotations

import contextlib
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import orchflows_adapters, rings


ROOT = Path(__file__).resolve().parents[1]
SUPER_RESEARCH = ROOT / ".claude" / "skills" / "super-research" / "SKILL.md"
AGENTS_SUPER_RESEARCH = ROOT / ".agents" / "skills" / "super-research" / "SKILL.md"
# No preprocessing construct may reach a generated adapter body: `@` includes
# and `` !`cmd` `` both run before the model sees anything (FM-6).
FORBIDDEN = ("@", "!`", "```")


@contextlib.contextmanager
def _world():
    with tempfile.TemporaryDirectory(prefix="orchflows-adapters-") as tmp:
        root = Path(tmp).resolve()
        home = root / "home"
        project = root / "project"
        (home / "skills").mkdir(parents=True)
        (home / "workflows").mkdir(parents=True)
        (project / ".git").mkdir(parents=True)
        (project / ".orchflows" / "skills").mkdir(parents=True)
        with patch.dict(os.environ, {
            "ORCHFLOWS_STATE_HOME": str(home / "state"),
            "CLAUDE_CONFIG_DIR": str(root / "claude-home"),
        }):
            yield {"root": root, "home": home, "project": project}


def _skill(directory: Path, name: str, extra: str = "") -> Path:
    path = directory / name / "SKILL.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(
        f"---\nname: {name}\ndescription: does {name}.\nrole: worker\n{extra}---\n\nbody\n".encode("utf-8")
    )
    return path


class BodyTests(unittest.TestCase):
    def test_a_generated_body_carries_no_preprocessing_construct(self):
        with _world() as world:
            item = _skill(world["home"] / "skills", "digest")
            records = orchflows_adapters.host_records()

            text = orchflows_adapters.render("skill", "digest", item, records["claude"])

            body = text.split("---\n", 2)[-1]
            for token in FORBIDDEN:
                self.assertNotIn(token, body, token)
            self.assertIn(str(item), body)

    def test_an_orchflows_only_field_never_reaches_a_host(self):
        with _world() as world:
            item = _skill(world["home"] / "skills", "digest")
            records = orchflows_adapters.host_records()

            text = orchflows_adapters.render("skill", "digest", item, records["grok"])

            self.assertNotIn("role:", text)
            self.assertIn("name: digest", text)

    def test_the_manual_invocation_flag_survives_into_a_claude_adapter(self):
        with _world() as world:
            item = _skill(
                world["home"] / "skills", "digest", extra="disable-model-invocation: true\n",
            )
            records = orchflows_adapters.host_records()

            text = orchflows_adapters.render("skill", "digest", item, records["claude"])

            self.assertIn("disable-model-invocation: true", text)

    def test_a_workflow_adapter_carries_the_instantiate_route(self):
        with _world() as world:
            item = world["home"] / "workflows" / "team-flow" / "template.md"
            item.parent.mkdir(parents=True)
            item.write_bytes(b"---\nname: team-flow\nentry: team-flow\n---\n\nbody\n")
            records = orchflows_adapters.host_records()

            text = orchflows_adapters.render("workflow", "team-flow", item, records["claude"])

            self.assertIn("tickets.py instantiate team-flow --run <run>", text)


class ScopeTests(unittest.TestCase):
    def test_project_adapters_point_repository_relative(self):
        with _world() as world:
            _skill(world["project"] / ".orchflows" / "skills", "team-skill")

            entries = orchflows_adapters.plan(
                "project", project=world["project"], start=world["project"],
            )

            self.assertEqual(2, len(entries))
            for destination, text in entries:
                self.assertIn(".orchflows/skills/team-skill/SKILL.md", text)
                self.assertNotIn(str(world["project"]), text)
            self.assertEqual(
                {
                    world["project"] / ".claude" / "skills" / "team-skill" / "SKILL.md",
                    world["project"] / ".agents" / "skills" / "team-skill" / "SKILL.md",
                },
                {destination for destination, _ in entries},
            )

    def test_a_pack_gets_no_adapter(self):
        with _world() as world:
            pack = world["home"] / "packs" / "widget-pack" / "SKILL.md"
            pack.parent.mkdir(parents=True)
            pack.write_bytes(b"---\nname: widget-pack\n---\n")

            entries = orchflows_adapters.plan("home", project=world["project"])

            self.assertEqual([], [path for path, _ in entries if "widget-pack" in str(path)])

    def test_sync_removes_the_adapter_of_a_deleted_ring_item(self):
        with _world() as world:
            item = _skill(world["project"] / ".orchflows" / "skills", "team-skill")

            orchflows_adapters.write("project", project=world["project"], start=world["project"])
            adapter = world["project"] / ".claude" / "skills" / "team-skill" / "SKILL.md"
            self.assertTrue(adapter.is_file())

            for path in sorted(item.parent.rglob("*"), reverse=True):
                path.unlink()
            item.parent.rmdir()
            result = orchflows_adapters.write(
                "project", project=world["project"], start=world["project"],
            )

            self.assertFalse(adapter.exists())
            self.assertIn(str(adapter), result["removed"])

    def test_a_hand_written_neighbour_is_never_removed(self):
        with _world() as world:
            _skill(world["project"] / ".orchflows" / "skills", "team-skill")
            mine = world["project"] / ".claude" / "skills" / "mine" / "SKILL.md"
            mine.parent.mkdir(parents=True)
            mine.write_bytes(b"---\nname: mine\n---\n\nhand written\n")

            orchflows_adapters.write("project", project=world["project"], start=world["project"])

            self.assertTrue(mine.is_file())

    def test_a_reserved_ring_item_gets_no_adapter(self):
        with _world() as world:
            _skill(world["project"] / ".orchflows" / "skills", "orch-widget")

            entries = orchflows_adapters.plan(
                "project", project=world["project"], start=world["project"],
            )

            self.assertEqual([], entries)


class CommittedProofTests(unittest.TestCase):
    """This repository's own super-research shim is now generated."""

    def _expected(self, host: str) -> str:
        item = ROOT / ".orchflows" / "skills" / "super-research" / "SKILL.md"
        records = orchflows_adapters.host_records(ROOT)
        return orchflows_adapters.render(
            "skill", "super-research", item, records[host],
            orchflows_adapters.pointer_for(item, ROOT),
        )

    def test_the_committed_claude_shim_is_what_the_machinery_renders(self):
        self.assertEqual(
            self._expected("claude"), SUPER_RESEARCH.read_text(encoding="utf-8"),
        )

    def test_the_committed_agents_shim_is_what_the_machinery_renders(self):
        self.assertEqual(
            self._expected("claude"), AGENTS_SUPER_RESEARCH.read_text(encoding="utf-8"),
        )

    def test_the_committed_shim_keeps_its_manual_invocation_flag(self):
        text = SUPER_RESEARCH.read_text(encoding="utf-8")
        self.assertIn("name: super-research", text)
        self.assertIn("disable-model-invocation: true", text)
        self.assertIn(orchflows_adapters.MARKER, text)

    def test_the_committed_shim_holds_no_machine_specific_path(self):
        for path in (SUPER_RESEARCH, AGENTS_SUPER_RESEARCH):
            text = path.read_text(encoding="utf-8")
            self.assertNotIn(str(ROOT), text)
            self.assertIn("Read .orchflows/skills/super-research/SKILL.md", text)


class InstantiateResolutionTests(unittest.TestCase):
    def test_a_workflow_name_resolves_and_a_bare_path_still_works(self):
        from scripts import tickets_instantiate

        with _world() as world:
            template = world["home"] / "workflows" / "team-flow" / "template.md"
            template.parent.mkdir(parents=True)
            template.write_bytes(b"---\nname: team-flow\nentry: team-flow\n---\n")

            with patch.object(rings.Path, "cwd", return_value=world["root"]):
                resolved, failure = tickets_instantiate._template_directory("team-flow")
                self.assertIsNone(failure)
                self.assertEqual(template.parent, resolved)
                direct, failure = tickets_instantiate._template_directory(str(template.parent))
                self.assertIsNone(failure)
                self.assertEqual(template.parent, direct)
                missing, failure = tickets_instantiate._template_directory("no-such-flow")
                self.assertIsNone(missing)
                self.assertIn("does not resolve", failure["error"])


if __name__ == "__main__":
    unittest.main()
