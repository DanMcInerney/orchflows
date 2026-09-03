"""Every registered name reaches every host's generated catalog.

The failure this exists to make impossible has happened: a curated tuple in
``installer/foundation.py`` listed the names one host got a first-class entry
for, a name was added to the tree and not to the tuple, and the host simply
could not invoke it. Nothing failed -- the install was green, the by-name
index carried the name, and only a live dispatch found the hole, at a cost of
2h50m. A rename is the same hole with a second mouth: the tree moves and a
list that spells the old name keeps pointing at nothing.

So the check runs in both directions and takes its expectation from the
registries that own the names rather than from a list of its own:

- the callable verb registry (``scripts/tickets_registry.py``),
- the pack tree, and
- the composition manifests that declare an ``entry``.

Each host catalog is then required to carry all of them, and the name is
pulled back out of an installed path through that host's *own* declared path
template, so a host that moves where the name sits in its paths cannot make
this check quietly stop reading one.
"""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import install
from installer import managed_text, packages
from installer.hosts import host_item_path, load_host_adapters
from scripts.tickets_registry import CALLABLE_EXECUTORS

from tests._repo_root import ROOT
HOSTS = ("claude", "codex", "grok")
_SENTINEL = "SENTINELNAME"

# Which plan list each host catalog is, and which installed-item template
# names its files. The templates come from `hosts/*.json`, so the extractor
# below is that host's own declaration read backwards.
CATALOGS = (
    ("Claude skill adapters", "claude_adapters", "claude", "skill"),
    ("Codex prompts", "codex_prompts", "codex", "prompt"),
    ("Codex redirect skills", "codex_skills", "codex", "skill"),
    ("Grok skills", "grok_skills", "grok", "skill"),
)
_ENV_GUARD = patch.dict(os.environ)


def setUpModule():
    """A real ``CLAUDE_CONFIG_DIR``, ``CODEX_HOME`` or ``GROK_HOME`` in the
    developer's environment would aim these plans at the home they actually
    use; the plans are never applied, but the paths they carry are read."""

    _ENV_GUARD.start()
    for variable in ("CLAUDE_CONFIG_DIR", "CODEX_HOME", "GROK_HOME"):
        os.environ.pop(variable, None)


def tearDownModule():
    _ENV_GUARD.stop()


def registered_names() -> set:
    """Every canonical name a host must be able to invoke, from its owner."""

    packs = {path.parent.name for path in sorted((ROOT / "packs").glob("*/SKILL.md"))}
    templates = {directory.name for directory, _fm, _body in install.discover_workflow_skills()}
    return set(CALLABLE_EXECUTORS) | packs | templates


def name_reader(host: str, item: str, adapters=None):
    """Return a function reading the canonical name back out of one installed
    path, derived from that host's own ``installed_items`` template."""

    adapters = load_host_adapters() if adapters is None else adapters
    probe = host_item_path(host, item, Path("probe-root"), adapters, name=_SENTINEL)
    parts = probe.parts
    index = max(i for i, part in enumerate(parts) if _SENTINEL in part)
    from_leaf = len(parts) - 1 - index
    prefix, _, suffix = parts[index].partition(_SENTINEL)

    def read(path: Path) -> str:
        part = path.parts[len(path.parts) - 1 - from_leaf]
        return part[len(prefix): len(part) - len(suffix) if suffix else None]

    return read


def catalog_names(plan) -> dict:
    """Each generated host catalog, as ``{label: set of canonical names}``."""

    adapters = load_host_adapters()
    found = {"flat by-name index": {dest.parent.name for dest, _ in plan.by_name}}
    for label, attribute, host, item in CATALOGS:
        read = name_reader(host, item, adapters)
        found[label] = {read(dest) for dest, _ in getattr(plan, attribute)}
    return found


def omissions(expected: set, found: dict) -> dict:
    """``{label: sorted missing names}`` for every catalog short a name."""

    return {
        label: sorted(expected - names)
        for label, names in sorted(found.items())
        if expected - names
    }


class CatalogCompletenessTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.home = Path(self._tmp.name)
        for directory in (".claude", ".codex", ".grok"):
            (self.home / directory).mkdir(parents=True)

    def _plan(self):
        def which(candidate: str):
            return str(Path("mock-bin") / candidate)

        with patch.object(install.Path, "home", return_value=self.home), patch.object(
            install.shutil, "which", side_effect=which
        ), patch.dict(os.environ, {"GROK_HOME": str(self.home / ".grok")}):
            return install.build_plan()

    def test_every_registered_verb_ships_as_a_discoverable_package(self):
        """The registry and the skill tree name each other or neither runs.

        Both directions: a verb whose directory moved without the registry
        following is unroutable, and a package the registry never learned is
        uninvocable. This is the pair a rename breaks first.
        """

        shipped = {
            path.parent.name
            for path in (ROOT / "skills").rglob("SKILL.md")
            if path.parent.name.startswith("orch-")
        }
        self.assertEqual(set(CALLABLE_EXECUTORS), shipped)
        discovered = {path.parent.name for path in install.discover_packages()}
        self.assertEqual(
            set(),
            set(CALLABLE_EXECUTORS) - discovered,
            "a registered verb the installer never discovers reaches no host",
        )

    def test_every_registered_name_reaches_every_host_catalog(self):
        expected = registered_names()
        # Graded before anything is compared: an expectation that came back
        # empty would make every containment below vacuously true.
        self.assertIn("orch-do", expected)
        self.assertIn("orch-code-pack", expected)
        self.assertGreaterEqual(len(expected), 11)

        found = catalog_names(self._plan())
        self.assertEqual(
            {"flat by-name index"} | {label for label, _, _, _ in CATALOGS},
            set(found),
        )
        for label, names in found.items():
            with self.subTest(catalog=label):
                self.assertTrue(names, "%s is empty" % label)
        self.assertEqual({}, omissions(expected, found))

    def test_the_check_fails_when_one_catalog_drops_one_name(self):
        """The can-fail direction (rules/verification.md §8): the omission
        this test exists for, planted one catalog at a time."""

        expected = registered_names()
        found = catalog_names(self._plan())
        self.assertEqual({}, omissions(expected, found))
        for label in sorted(found):
            with self.subTest(catalog=label):
                planted = dict(found)
                planted[label] = found[label] - {"orch-do"}
                self.assertEqual(
                    {label: ["orch-do"]}, omissions(expected, planted)
                )

    def test_the_name_reader_is_that_host_s_own_path_template(self):
        """The extractor is derived, not assumed: it must read back the name
        a host's declared template just wrote."""

        adapters = load_host_adapters()
        for host, item in (
            ("claude", "skill"), ("codex", "prompt"),
            ("codex", "skill"), ("grok", "skill"),
        ):
            with self.subTest(host=host, item=item):
                path = host_item_path(host, item, Path("root"), adapters, name="orch-do")
                self.assertEqual("orch-do", name_reader(host, item, adapters)(path))


class WorkflowHomeDiscoveryTests(unittest.TestCase):
    """Both library workflow homes mint the same name surfaces.

    A reusable, domain-blind workflow ships in `skills/workflows` and a
    domain-bearing one in `example-workflows`. Only the workflow loop
    forces `disable-model-invocation: true` onto what it mints, so a
    workflow the package loop claimed instead would reach Codex and Grok
    as a model-invocable name -- and a workflow both loops claimed would
    have one path written twice, from two plan entries that disagree.

    `registered_names` above already requires every discovered workflow in
    every host catalog; what this fixes is which directories are
    discovered, which the empty shipped `skills/workflows/` cannot show.
    """

    BODY = "\n".join((
        "---",
        "name: {name}",
        "description: a synthetic workflow",
        "disable-model-invocation: true",
        "role: planner",
        "---",
        "Require: a goal.",
        "Never: improvise.",
        "Return: the frame's close.",
        "",
    ))

    def _tree(self, tmp: str) -> Path:
        root = Path(tmp)
        for home, name in (
            ("skills/workflows", "reusable-flow"),
            ("example-workflows", "gallery-flow"),
        ):
            directory = root / home / name
            directory.mkdir(parents=True)
            (directory / "SKILL.md").write_text(
                self.BODY.format(name=name), encoding="utf-8"
            )
        kernel = root / "skills" / "kernel" / "orch-do"
        kernel.mkdir(parents=True)
        (kernel / "SKILL.md").write_text(
            self.BODY.format(name="orch-do"), encoding="utf-8"
        )
        return root

    def test_both_homes_are_discovered_in_the_resolver_s_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._tree(tmp)

            found = [
                directory.name
                for directory, _fm, _body in install.discover_workflow_skills(root)
            ]

            self.assertEqual(["reusable-flow", "gallery-flow"], found)

    def test_the_package_loop_leaves_the_workflow_home_alone(self):
        """One name, one loop: the package loop mints no manual-only flag,
        so a workflow it also claimed would install as a model-invocable
        name beside its own stub."""

        with tempfile.TemporaryDirectory() as tmp:
            root = self._tree(tmp)

            claimed = [
                path.parent.name for path in packages.discover_packages(root)
            ]

            self.assertEqual(["orch-do"], claimed)


class WorkflowHostSurfaceTests(unittest.TestCase):
    """No host surface binds a workflow to a forked child.

    A workflow is prose whoever invoked it by name drives in place, so no
    host surface may carry a fork binding for it. The two rules met the
    first time a reusable workflow landed under `skills/workflows/`: the
    tier is a skills tier, the validator then wanted a `role` there, and
    the declared role reached the composers -- the Grok one raised on it
    and planned nothing at all for that name, while the Claude adapter
    would have carried `context: fork`, running the body inside a child
    with the callables it opens one level deeper than its caller meant.
    The rule that settled it is the absence of the field:
    `tools/validate_support/packages.py`'s `validate_role` refuses a role
    in a workflow home, so there is nothing for a composer to bind and
    nothing to strip at the boundary. These cases hold the surfaces flat
    however that is achieved, and the last one is why they are not
    vacuous.
    """

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.home = Path(self._tmp.name)
        for directory in (".claude", ".codex", ".grok"):
            (self.home / directory).mkdir(parents=True)

    def _plan(self):
        def which(candidate: str):
            return str(Path("mock-bin") / candidate)

        with patch.object(install.Path, "home", return_value=self.home), patch.object(
            install.shutil, "which", side_effect=which
        ), patch.dict(os.environ, {"GROK_HOME": str(self.home / ".grok")}):
            return install.build_plan()

    def _workflows(self):
        return {
            directory.name: frontmatter
            for directory, frontmatter, _body in install.discover_workflow_skills()
        }

    def _texts(self, plan, attribute, host, item):
        read = name_reader(host, item)
        return {read(dest): text for dest, text in getattr(plan, attribute)}

    def test_the_population_is_real(self):
        """Every assertion below sweeps this set; empty, they all pass."""

        self.assertNotEqual(
            {}, self._workflows(),
            "no workflow was discovered, so the surface checks in this "
            "class sweep nothing",
        )

    def test_no_workflow_declares_a_role_to_bind(self):
        """The property the rest of the class rests on, read off the tree."""

        declared = sorted(
            name for name, frontmatter in self._workflows().items()
            if packages.frontmatter_field(frontmatter, "role")
        )
        self.assertEqual(
            [], declared,
            "a workflow declares a role, which a host composer will bind: "
            + ", ".join(declared),
        )

    def test_no_host_surface_binds_a_workflow_to_a_child(self):
        plan = self._plan()
        claude = self._texts(plan, "claude_adapters", "claude", "skill")
        grok = self._texts(plan, "grok_skills", "grok", "skill")
        for name in sorted(self._workflows()):
            with self.subTest(workflow=name):
                self.assertNotIn("context: fork", claude[name])
                self.assertNotIn("agent: orch-", claude[name])
                self.assertNotIn("spawn_subagent", grok[name])
                self.assertNotIn(packages.FORK_ARRIVAL_CLAUSE, grok[name])
                self.assertIn("follow it exactly", grok[name])

    def test_a_declared_role_is_what_would_bind_them(self):
        """The can-fail reading, taken without mutating the tree: the same
        frontmatter with a role put back is the fork binding above, and the
        Grok composer refuses to render at all. So the flat surfaces are
        the missing field's doing, not the composers' good manners."""

        for name, frontmatter in sorted(self._workflows().items()):
            with self.subTest(workflow=name):
                mutant = frontmatter.rstrip() + "\nrole: planner\n"
                self.assertIn(
                    "context: fork", packages.manual_only_frontmatter(mutant)
                )
                with self.assertRaises(ValueError):
                    managed_text.grok_skill_text(mutant, Path("X") / "SKILL.md")


if __name__ == "__main__":
    unittest.main()
