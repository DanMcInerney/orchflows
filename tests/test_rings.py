"""The one ring resolver: fixed order, a reserved floor, and never-portable trust."""

from __future__ import annotations

import contextlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import rings, rings_trust, state_root


from tests._repo_root import ROOT


@contextlib.contextmanager
def _world():
    """A home ring, a project ring and a library, all under one temporary root."""

    with tempfile.TemporaryDirectory(prefix="orchflows-rings-") as tmp:
        root = Path(tmp).resolve()
        home = root / "home"
        project = root / "project"
        lib = root / "lib"
        for kind_dir in rings.RING_DIRS.values():
            (home / kind_dir).mkdir(parents=True, exist_ok=True)
            (project / ".orchflows" / kind_dir).mkdir(parents=True, exist_ok=True)
        for lib_dirs in rings.LIB_DIRS.values():
            for kind_dir in lib_dirs:
                (lib / kind_dir).mkdir(parents=True, exist_ok=True)
        with patch.dict(os.environ, {state_root.ENV_VAR: str(home / "state")}):
            yield {"root": root, "home": home, "project": project, "lib": lib}


def _item(directory: Path, kind: str, name: str, body: str = "body\n") -> Path:
    path = directory / name / rings.MANIFESTS[kind]
    path.parent.mkdir(parents=True, exist_ok=True)
    # Bytes, not text: a Windows text write would already carry CRLF, and the
    # line-ending case below would then be testing a mangling rather than a
    # checkout difference.
    path.write_bytes(f"---\nname: {name}\n---\n\n{body}".encode("utf-8"))
    return path


class RingOrderTests(unittest.TestCase):
    def test_the_search_order_is_project_home_imports_then_lib(self):
        with _world() as world:
            (world["home"] / rings.IMPORTS_LOCK).write_text(
                json.dumps({"imports": [{"name": "team", "url": "u", "pin": "p"}]}),
                encoding="utf-8",
            )
            order = rings.item_roots(
                "standard", project=world["project"], lib=world["lib"],
            )

            self.assertEqual(
                ["project", "home", "imports", "lib"], [ring for ring, _ in order]
            )
            self.assertEqual(
                [
                    world["project"] / ".orchflows" / "standards",
                    world["home"] / "standards",
                    world["home"] / "imports" / "team" / ".orchflows" / "standards",
                    world["lib"] / "standards",
                ],
                [path for _, path in order],
            )

    def test_a_workflow_reads_workflows_in_a_ring_and_example_workflows_in_lib(self):
        with _world() as world:
            order = dict(
                (ring, path)
                for ring, path in rings.item_roots(
                    "workflow", project=world["project"], lib=world["lib"],
                )
            )

            self.assertEqual(world["project"] / ".orchflows" / "workflows", order["project"])
            self.assertEqual(world["lib"] / "example-workflows", order["lib"])

    def test_lib_workflows_search_the_skills_tier_before_the_gallery(self):
        """A reusable workflow ships in `skills/workflows`, a domain-bearing
        one in `example-workflows`, and both are the library's."""

        with _world() as world:
            libs = [
                path
                for ring, path in rings.item_roots(
                    "workflow", project=world["project"], lib=world["lib"],
                )
                if ring == "lib"
            ]

            self.assertEqual(
                [
                    world["lib"] / "skills" / "workflows",
                    world["lib"] / "example-workflows",
                ],
                libs,
            )

    def test_a_reusable_workflow_shadows_a_gallery_name(self):
        """The nearer library home wins, and the notice names what it hid --
        the collision `tools/validate.py` refuses before it can happen."""

        with _world() as world:
            _item(world["lib"] / "skills" / "workflows", "workflow", "both-homes")
            _item(world["lib"] / "example-workflows", "workflow", "both-homes")

            record = rings.resolve(
                "workflow", "both-homes", project=world["project"], lib=world["lib"],
            )

            self.assertEqual(
                str(world["lib"] / "skills" / "workflows" / "both-homes" / "SKILL.md"),
                record["path"],
            )
            self.assertIn("example-workflows", rings.shadow_notice(record))

    def test_lib_skills_expand_every_sublayer_but_the_workflow_home(self):
        """`skills/workflows` ships inside the skills tier and is still a
        workflow home, not a skill root: a body there answers to kind
        `workflow` and to no other kind."""

        with _world() as world:
            (world["lib"] / "skills" / "kernel").mkdir(parents=True, exist_ok=True)
            (world["lib"] / "skills" / "workflows").mkdir(parents=True, exist_ok=True)

            libs = [
                path
                for ring, path in rings.item_roots("skill", project=world["project"], lib=world["lib"])
                if ring == "lib"
            ]

            self.assertEqual([world["lib"] / "skills" / "kernel"], libs)

    def test_a_reusable_workflow_resolves_as_a_workflow_and_not_as_a_skill(self):
        """The cross-kind seam: one body, one kind. The refusal names the
        workflow it is, because "does not resolve" alone sends the caller
        hunting a file that is right there."""

        with _world() as world:
            _item(world["lib"] / "skills" / "workflows", "workflow", "demo-flow")

            record = rings.resolve(
                "workflow", "demo-flow", project=world["project"], lib=world["lib"],
            )
            self.assertEqual(
                str(world["lib"] / "skills" / "workflows" / "demo-flow" / "SKILL.md"),
                record["path"],
            )

            with self.assertRaises(rings.RingError) as raised:
                rings.resolve(
                    "skill", "demo-flow", project=world["project"], lib=world["lib"],
                )

            self.assertEqual("unresolved", raised.exception.code)
            self.assertIn("workflow", raised.exception.detail)
            self.assertIn(
                str(world["lib"] / "skills" / "workflows" / "demo-flow" / "SKILL.md"),
                raised.exception.detail,
            )

    def test_a_name_nowhere_keeps_the_plain_unresolved_refusal(self):
        """The workflow clause is a fact about this name, not a sentence
        every miss now carries."""

        with _world() as world:
            with self.assertRaises(rings.RingError) as raised:
                rings.resolve(
                    "skill", "demo-flow", project=world["project"], lib=world["lib"],
                )

            self.assertEqual(
                "skill does not resolve: demo-flow", raised.exception.detail,
            )

    def test_a_skill_sublayer_beside_the_workflow_home_still_resolves(self):
        with _world() as world:
            _item(world["lib"] / "skills" / "kernel", "skill", "orch-do")

            record = rings.resolve(
                "skill", "orch-do", project=world["project"], lib=world["lib"],
            )

            self.assertEqual(
                str(world["lib"] / "skills" / "kernel" / "orch-do" / "SKILL.md"),
                record["path"],
            )

    def test_a_bare_standards_ancestor_directory_is_not_a_root(self):
        """The divergence S3 named: `<dir>/standards` used to be checked before
        `<dir>/.orchflows/standards`, so admission and execution could read two
        different files as one standard."""

        with _world() as world:
            _item(world["project"] / "standards", "standard", "loose")

            with self.assertRaises(rings.RingError) as raised:
                rings.resolve(
                    "standard", "loose", start=world["project"], lib=world["lib"],
                )

            self.assertEqual("unresolved", raised.exception.code)

    def test_the_home_ring_is_never_read_as_a_project_ring(self):
        with _world() as world:
            self.assertIsNone(rings.project_ring(world["home"], world["home"]))

    def test_missing_home_roots_do_not_break_resolution(self):
        with _world() as world:
            for kind_dir in rings.RING_DIRS.values():
                (world["home"] / kind_dir).rmdir()
            _item(world["lib"] / "standards", "standard", "shipped")

            self.assertEqual(
                "lib",
                rings.resolve("standard", "shipped", project=world["project"], lib=world["lib"])["ring"],
            )


class ReservationAndShadowTests(unittest.TestCase):
    def test_a_reserved_ring_name_refuses_loudly_rather_than_never_running(self):
        with _world() as world:
            path = _item(world["home"] / "skills", "skill", "orch-do")

            with self.assertRaises(rings.RingError) as raised:
                rings.resolve("skill", "orch-do", project=world["project"], lib=world["lib"])

            self.assertEqual("reserved-name", raised.exception.code)
            self.assertIn(str(path), raised.exception.detail)
            self.assertIn("orch-", raised.exception.detail)

    def test_a_reserved_name_refuses_even_when_the_library_also_holds_it(self):
        with _world() as world:
            _item(world["lib"] / "standards", "standard", "orch-code")
            _item(world["project"] / ".orchflows" / "standards", "standard", "orch-code")

            with self.assertRaises(rings.RingError) as raised:
                rings.resolve("standard", "orch-code", project=world["project"], lib=world["lib"])

            self.assertEqual("reserved-name", raised.exception.code)

    def test_the_library_keeps_its_own_reserved_names(self):
        with _world() as world:
            _item(world["lib"] / "standards", "standard", "orch-code")

            record = rings.resolve(
                "standard", "orch-code", project=world["project"], lib=world["lib"],
            )

            self.assertEqual("lib", record["ring"])

    def test_a_non_reserved_collision_wins_nearest_and_names_both_paths(self):
        with _world() as world:
            near = _item(world["home"] / "skills", "skill", "digest")
            far = _item(world["lib"] / "skills" / "kernel", "skill", "digest")

            record = rings.resolve(
                "skill", "digest", project=world["project"], lib=world["lib"],
            )

            self.assertEqual("home", record["ring"])
            self.assertEqual(str(near), record["path"])
            self.assertEqual(
                [f"shadow: skill 'digest' resolves from the home ring at {near} "
                 f"and shadows lib {far}"],
                record["notices"],
            )


class TrustTests(unittest.TestCase):
    def test_a_project_ring_refuses_until_the_user_grants_trust(self):
        with _world() as world:
            _item(world["project"] / ".orchflows" / "standards", "standard", "team-standard")

            with self.assertRaises(rings.RingError) as raised:
                rings.resolve("standard", "team-standard", project=world["project"], lib=world["lib"])

            self.assertEqual("bundle-untrusted", raised.exception.code)
            self.assertIn("orchflows trust", raised.exception.detail)

    def test_the_ledger_never_lives_inside_a_repository(self):
        with _world() as world:
            _item(world["project"] / ".orchflows" / "standards", "standard", "team-standard")
            rings_trust.grant(world["project"] / ".orchflows")

            self.assertEqual(world["home"] / "trust.json", rings_trust.ledger_path())
            self.assertFalse((world["project"] / "trust.json").exists())
            self.assertFalse((world["project"] / ".orchflows" / "trust.json").exists())

    def test_a_repo_supplied_ledger_grants_nothing(self):
        """FM-2: the policy that decides whether to trust a file is never
        readable from that file."""

        with _world() as world:
            bundle = world["project"] / ".orchflows"
            _item(bundle / "standards", "standard", "team-standard")
            (bundle / "trust.json").write_text(
                json.dumps({
                    "version": 1,
                    "trusted": [{
                        "bundle": str(bundle),
                        "digest": rings_trust.bundle_digest(bundle),
                    }],
                }),
                encoding="utf-8",
            )

            with self.assertRaises(rings.RingError) as raised:
                rings.resolve("standard", "team-standard", project=world["project"], lib=world["lib"])

            self.assertEqual("bundle-untrusted", raised.exception.code)

    def test_an_edit_outside_the_ring_directories_does_not_re_prompt(self):
        with _world() as world:
            bundle = world["project"] / ".orchflows"
            _item(bundle / "standards", "standard", "team-standard")
            rings_trust.grant(bundle)
            (world["project"] / "README.md").write_text("changed\n", encoding="utf-8")
            (bundle / "notes.md").write_text("changed\n", encoding="utf-8")

            record = rings.resolve(
                "standard", "team-standard", project=world["project"], lib=world["lib"],
            )

            self.assertEqual("project", record["ring"])

    def test_revoke_drops_both_halves_of_the_two_step(self):
        with _world() as world:
            bundle = world["project"] / ".orchflows"
            _item(bundle / "standards", "standard", "team-standard")
            rings_trust.grant(bundle, once=True)
            rings_trust.grant(bundle)

            self.assertTrue(rings_trust.state(bundle)["trusted"])
            rings_trust.revoke(bundle)
            self.assertFalse(rings_trust.state(bundle)["trusted"])

    def test_line_endings_do_not_change_a_bundle_digest(self):
        with _world() as world:
            bundle = world["project"] / ".orchflows"
            path = _item(bundle / "standards", "standard", "team-standard")
            before = rings_trust.bundle_digest(bundle)
            path.write_bytes(path.read_bytes().replace(b"\n", b"\r\n"))

            self.assertEqual(before, rings_trust.bundle_digest(bundle))


class InventoryTests(unittest.TestCase):
    def test_inventory_reports_ring_shadows_and_trust_for_every_kind(self):
        with _world() as world:
            _item(world["home"] / "skills", "skill", "digest")
            _item(world["lib"] / "skills" / "kernel", "skill", "digest")
            _item(world["project"] / ".orchflows" / "workflows", "workflow", "team-flow")

            records = {
                (item["kind"], item["name"]): item
                for item in rings.inventory(project=world["project"], lib=world["lib"])
            }

            self.assertEqual("home", records[("skill", "digest")]["ring"])
            self.assertEqual(1, len(records[("skill", "digest")]["shadows"]))
            self.assertEqual("inherent", records[("skill", "digest")]["trust"])
            self.assertEqual("untrusted", records[("workflow", "team-flow")]["trust"])
            rings_trust.grant(world["project"] / ".orchflows")
            regraded = {
                (item["kind"], item["name"]): item
                for item in rings.inventory(project=world["project"], lib=world["lib"])
            }
            self.assertEqual("trusted", regraded[("workflow", "team-flow")]["trust"])

    def test_inventory_reports_a_reserved_ring_item_rather_than_hiding_it(self):
        with _world() as world:
            _item(world["home"] / "standards", "standard", "orch-code")

            record = next(
                item
                for item in rings.inventory(("standard",), project=world["project"], lib=world["lib"])
                if item["name"] == "orch-code"
            )

            self.assertTrue(record["reserved"])
            self.assertIn("reserved", record["refusal"])


class SuperResearchGoalTests(unittest.TestCase):
    """R.03 Goal clauses 1 and 4, read from this checkout rather than a
    synthetic world -- the ring item under test is this repository's own.
    Home is pointed at an empty scratch directory so neither reading picks
    up whatever a real machine's own home ring happens to hold."""

    def test_the_workflow_resolves_from_the_lib_ring_by_bare_name(self):
        """Clause 1, the actual build: at arrival this raised RingError
        (R.03's Context); `example-workflows/super-research/` is what
        makes it resolve."""

        with tempfile.TemporaryDirectory(prefix="orchflows-empty-home-") as empty_home:
            home = Path(empty_home)
            record = rings.resolve("workflow", "super-research", start=ROOT, home=home)
            names = {
                item["name"]
                for item in rings.inventory(("workflow",), start=ROOT, home=home)
            }

        self.assertEqual("lib", record["ring"])
        self.assertIn("super-research", names)

    def test_the_skill_stays_resolvable_as_a_project_ring_skill(self):
        """Clause 4, under U7d's rename: the acquisition skill is
        `research-acquire`, and it still resolves from this repository's own
        project ring. Read without mutating the tree under test, per the
        standard's Evidence section, rather than left to have happened to
        keep working."""

        with tempfile.TemporaryDirectory(prefix="orchflows-empty-home-") as empty_home:
            record = rings.resolve(
                "skill", "research-acquire", trust=False, start=ROOT, home=Path(empty_home),
            )

        self.assertEqual("project", record["ring"])
        self.assertEqual(
            str(ROOT / ".orchflows" / "skills" / "research-acquire"), record["dir"],
        )

    def test_the_workflow_name_no_longer_names_a_skill_as_well(self):
        """U7d Goal's last clause -- no two items share a name. Before the
        rename this resolved to the project ring's own skill directory, so
        one name meant a skill here and a workflow there and the generated
        adapters collided by suffix."""

        with tempfile.TemporaryDirectory(prefix="orchflows-empty-home-") as empty_home:
            with self.assertRaises(rings.RingError) as raised:
                rings.resolve(
                    "skill", "super-research", trust=False, start=ROOT,
                    home=Path(empty_home),
                )

        self.assertEqual("unresolved", raised.exception.code)


if __name__ == "__main__":
    unittest.main()
