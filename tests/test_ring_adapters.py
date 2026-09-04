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


class CommittedProofTests(unittest.TestCase):
    """This repository's own research-acquire shim is now generated."""

    def _expected(self, host: str) -> str:
        item = ROOT / ".orchflows" / "skills" / "research-acquire" / "SKILL.md"
        records = orchflows_adapters.host_records(ROOT)
        return orchflows_adapters.render(
            "skill", "research-acquire", item, records[host],
            orchflows_adapters.pointer_for(item, ROOT),
        )

    def test_the_committed_claude_shim_is_what_the_machinery_renders(self):
        self.assertEqual(
            self._expected("claude"), RESEARCH_ACQUIRE.read_text(encoding="utf-8"),
        )

    def test_the_committed_agents_shim_is_what_the_machinery_renders(self):
        self.assertEqual(
            self._expected("claude"), AGENTS_RESEARCH_ACQUIRE.read_text(encoding="utf-8"),
        )

    def test_the_committed_shim_keeps_its_manual_invocation_flag(self):
        text = RESEARCH_ACQUIRE.read_text(encoding="utf-8")
        self.assertIn("name: research-acquire", text)
        self.assertIn("disable-model-invocation: true", text)
        self.assertIn(orchflows_adapters.MARKER, text)

    def test_the_committed_shim_holds_no_machine_specific_path(self):
        for path in (RESEARCH_ACQUIRE, AGENTS_RESEARCH_ACQUIRE):
            text = path.read_text(encoding="utf-8")
            self.assertNotIn(str(ROOT), text)
            self.assertIn("Read .orchflows/skills/research-acquire/SKILL.md", text)


class PortabilityTests(unittest.TestCase):
    """Goal clause 5's own wording: 'from a checkout that is not this one.'
    A resolution or a rendering read against ROOT proves nothing about
    portability -- this repository is always its own project ring. Copying
    the two manifests into a scratch home ring and resolving/rendering them
    from there is the only reading that can fail if the pair stopped being
    portable."""

    def test_the_acquisition_pair_copies_out_under_two_distinct_names(self):
        """U7d renamed the skill, so the pair no longer shares one name.
        The `-workflow` slug keeps their *paths* apart either way; what the
        rename fixes is the name each adapter declares to its host, which
        was `super-research` on both of them before it."""

        with _world() as world:
            skill_copy = world["home"] / "skills" / "research-acquire" / "SKILL.md"
            skill_copy.parent.mkdir(parents=True)
            skill_copy.write_bytes(
                (ROOT / ".orchflows" / "skills" / "research-acquire" / "SKILL.md").read_bytes()
            )
            workflow_copy = world["home"] / "workflows" / "super-research" / "SKILL.md"
            workflow_copy.parent.mkdir(parents=True)
            workflow_copy.write_bytes(
                (ROOT / "example-workflows" / "super-research" / "SKILL.md").read_bytes()
            )

            skill_record = rings.resolve(
                "skill", "research-acquire", trust=False, start=world["root"],
            )
            workflow_record = rings.resolve(
                "workflow", "super-research", start=world["root"],
            )
            self.assertEqual("home", skill_record["ring"])
            self.assertEqual("home", workflow_record["ring"])

            with patch.object(orchflows_adapters, "detected", return_value=["claude"]):
                entries = orchflows_adapters.plan("home", start=world["root"])

            rendered = {
                path.parent.name: text
                for path, text in entries
                if path.parent.name in ("research-acquire", "super-research-workflow")
            }
            self.assertEqual(
                {"research-acquire", "super-research-workflow"}, set(rendered),
            )
            declared = sorted(
                line for text in rendered.values()
                for line in text.splitlines() if line.startswith("name: ")
            )
            self.assertEqual(["name: research-acquire", "name: super-research"], declared)
            self.assertIn("is a workflow skill", rendered["super-research-workflow"])
            self.assertNotIn("is a workflow skill", rendered["research-acquire"])
            self.assertIn(
                "disable-model-invocation: true", rendered["super-research-workflow"],
            )


if __name__ == "__main__":
    unittest.main()
