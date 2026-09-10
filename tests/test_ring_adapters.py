"""Ring host adapters: inert bodies, two scopes, and the committed proof."""

from __future__ import annotations

import contextlib
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import orchflows_adapters, rings, state_root


from tests._repo_root import ROOT
RESEARCH_ACQUIRE = ROOT / ".claude" / "skills" / "research-acquire" / "SKILL.md"
AGENTS_RESEARCH_ACQUIRE = ROOT / ".agents" / "skills" / "research-acquire" / "SKILL.md"
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
            state_root.ENV_VAR: str(home / "state"),
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

    def test_a_workflow_adapter_points_at_its_body_and_is_manual_only(self):
        """The flag is forced, never inherited: a ring workflow is authored
        outside this library, its prose runs as orchestrator reasoning, and a
        host firing it on its own reading of a description would open that
        surface with nobody asking."""

        with _world() as world:
            item = world["home"] / "workflows" / "team-flow" / "SKILL.md"
            item.parent.mkdir(parents=True)
            item.write_bytes(b"---\nname: team-flow\ndescription: does it.\n---\n\nbody\n")
            records = orchflows_adapters.host_records()

            text = orchflows_adapters.render("workflow", "team-flow", item, records["claude"])

            self.assertIn("is a workflow skill", text)
            self.assertIn(str(item), text)
            self.assertIn("disable-model-invocation: true", text)
            self.assertNotIn("instantiate", text)


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

    def test_a_standard_gets_no_adapter(self):
        with _world() as world:
            standard = world["home"] / "standards" / "widget-standard" / "STANDARD.md"
            standard.parent.mkdir(parents=True)
            standard.write_bytes(b"---\nname: widget-standard\n---\n")

            entries = orchflows_adapters.plan("home", project=world["project"])

            self.assertEqual([], [path for path, _ in entries if "widget-standard" in str(path)])

    def test_a_standard_gets_no_adapter(self):
        """A standard is stamped on a ticket and never invoked, so it is the
        standard's case exactly: a name in a host's skill list that cannot be
        called crowds out the names that can. `ADAPTED_KINDS` is the one
        place that is decided, and `standard` is not in it."""

        with _world() as world:
            standard = world["home"] / "standards" / "market-brief" / "STANDARD.md"
            standard.parent.mkdir(parents=True)
            standard.write_bytes(b"---\nname: market-brief\n---\n")

            entries = orchflows_adapters.plan("home", project=world["project"])

            self.assertNotIn("standard", orchflows_adapters.ADAPTED_KINDS)
            self.assertEqual(
                [], [path for path, _ in entries if "market-brief" in str(path)],
            )

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

    def test_a_home_ring_skill_and_workflow_of_one_name_render_to_two_destinations(self):
        """The blocking defect R.03 measured: `_destination()` ignored kind,
        so a skill and a workflow sharing a name rendered to the same host
        path and the second write silently clobbered the first. Goal clause
        5 asks for exactly this shape -- a skill and a workflow of one name
        in one home ring -- so this is the collision case, not an
        incidental sweep."""

        with _world() as world:
            _skill(world["home"] / "skills", "collide-flow")
            workflow = world["home"] / "workflows" / "collide-flow" / "SKILL.md"
            workflow.parent.mkdir(parents=True)
            workflow.write_bytes(
                b"---\nname: collide-flow\ndescription: collides.\n---\n\nbody\n"
            )

            with patch.object(orchflows_adapters, "detected", return_value=["claude"]):
                entries = orchflows_adapters.plan("home", start=world["root"])

                destinations = [destination for destination, _ in entries]
                self.assertEqual(2, len(entries))
                self.assertEqual(2, len(set(destinations)), destinations)
                claude_home = world["root"] / "claude-home"
                skill_dest = claude_home / "skills" / "collide-flow" / "SKILL.md"
                workflow_dest = claude_home / "skills" / "collide-flow-workflow" / "SKILL.md"
                self.assertEqual({skill_dest, workflow_dest}, set(destinations))
                bodies = dict(entries)
                self.assertIn("is a workflow skill", bodies[workflow_dest])
                self.assertNotIn("is a workflow skill", bodies[skill_dest])

                orchflows_adapters.write("home", start=world["root"])

            self.assertEqual(bodies[skill_dest], skill_dest.read_text(encoding="utf-8"))
            self.assertEqual(bodies[workflow_dest], workflow_dest.read_text(encoding="utf-8"))


class RecentSearchAdapterTests(unittest.TestCase):
    def test_only_the_public_workflow_gets_a_host_adapter(self):
        with _world() as world:
            import shutil
            package = world["home"] / "workflows" / "recent-search"
            shutil.copytree(ROOT / "example-workflows" / "recent-search", package,
                            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
            with patch.object(orchflows_adapters, "detected", return_value=["claude"]):
                entries = orchflows_adapters.plan("home", start=world["root"])
            selected = {path.parent.name: body for path, body in entries
                        if "recent-search" in path.parent.name or "research-acquire" in path.parent.name}
            self.assertEqual({"recent-search-workflow"}, set(selected))
            self.assertIn("name: recent-search", selected["recent-search-workflow"])
            self.assertIn("disable-model-invocation: true", selected["recent-search-workflow"])

    def test_retired_project_adapters_are_absent(self):
        self.assertFalse(RESEARCH_ACQUIRE.exists())
        self.assertFalse(AGENTS_RESEARCH_ACQUIRE.exists())


if __name__ == "__main__":
    unittest.main()
