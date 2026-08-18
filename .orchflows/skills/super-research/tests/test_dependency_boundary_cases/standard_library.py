"""Standard-library and host-mirror boundary checks."""

import sys
import unittest

from .source_roster_support import (
    DESCRIPTION_BUDGET,
    HOST_MIRROR,
    OWNER_SKILL,
    frontmatter_description,
)
from .support import (
    STANDARD_LIBRARY_IMPORTS,
    THIRD_PARTY_SURFACES,
    absolute_imports,
    imports_naming,
    outside_the_standard_library,
    package_sources,
)

class StandardLibraryOnlyTest(unittest.TestCase):
    """Criterion 2, dependency half: nothing outside the 3.9 standard library."""

    def test_the_package_takes_exactly_these_modules_from_outside_itself(self):
        taken = set()
        for path in package_sources():
            taken |= absolute_imports(path)

        self.assertEqual(tuple(sorted(taken)), STANDARD_LIBRARY_IMPORTS)

    def test_every_one_of_them_resolves_inside_this_interpreters_own_stdlib(self):
        self.assertEqual(outside_the_standard_library(STANDARD_LIBRARY_IMPORTS), [])

    def test_the_floor_this_was_resolved_against_is_the_declared_one(self):
        # The resolution above is a fact about the interpreter that ran it, so
        # the interpreter is asserted rather than assumed.
        self.assertEqual(sys.version_info[:2], (3, 9))

    def test_no_module_names_an_sdk_a_driver_or_a_downloader(self):
        self.assertEqual(imports_naming(package_sources(), THIRD_PARTY_SURFACES), [])



class TheHostMirrorResolvesFromAnyCheckoutTest(unittest.TestCase):
    """The Claude adapter mirror's include lands on the owner, wherever the clone is.

    The stub is hand-written and committed — `install.py --project` writes no
    `.claude` — so an absolute path in it is a path to one machine's filesystem
    and resolves nowhere else: another user, another OS, another repository
    name, and nowhere at all at a revision built in a worktree. It carried one,
    plus ten lines apologizing for it. `scopes.md` now asks a project stub for a
    path relative to itself, and this is the check that the path it carries
    actually reaches the owner from where the stub sits.

    Whether a Claude host expands a relative `@` in a project stub was not
    settled by any ablation this item could run, so the stub carries one line
    under the include naming the owner in plain words. That line is a second
    place a machine-specific path could arrive, which is why absoluteness is
    checked over the whole stub and not over the include alone.

    Skipped rather than failed when the pair is not where a project-scope item
    puts them, because the item can be read from a copy and this suite's
    reliability bar is that it passes offline from anywhere.
    """

    def setUp(self):
        if not HOST_MIRROR.exists():
            self.skipTest("no project-scope host mirror beside this item")

    def test_the_include_is_relative_and_reaches_the_owner(self):
        include = [
            line
            for line in HOST_MIRROR.read_text(encoding="utf-8").splitlines()
            if line.startswith("@")
        ]

        self.assertEqual(len(include), 1)
        target = include[0][1:].strip()
        self.assertFalse(target.startswith("/"), "a committed stub names one machine")
        self.assertFalse(target[1:2] == ":", "a committed stub names one machine")
        # Resolved the way a host resolves it: against the stub's own directory.
        self.assertEqual((HOST_MIRROR.parent / target).resolve(), OWNER_SKILL)

    def test_no_line_of_the_stub_names_one_machine(self):
        # The include is not the only place a path can arrive: the line under it
        # names the owner for a host that did not expand the include, and a path
        # spelled from a root would be the same defect wearing prose.
        body = HOST_MIRROR.read_text(encoding="utf-8")

        for token in body.replace("`", " ").split():
            with self.subTest(token=token):
                self.assertFalse(token.lstrip("@").startswith("/"))
                self.assertNotRegex(token.lstrip("@"), r"^[A-Za-z]:[\\/]")

    def test_the_stub_names_the_owner_for_a_host_that_did_not_expand(self):
        # The one thing the fallback line has to carry, and the reason it is a
        # line rather than a paragraph: where to read instead.
        body = HOST_MIRROR.read_text(encoding="utf-8")
        after_include = body.split("\n@", 1)[1].split("\n", 1)[1]

        self.assertIn(".orchflows/skills/super-research/SKILL.md", after_include)

    def test_the_owner_and_the_mirror_describe_the_item_with_one_string(self):
        # A Claude host routes on the mirror's copy and never reads the owner's,
        # so drift here costs the item every invocation while both files still
        # read correctly on their own — the one failure nobody thinks to check.
        # Nothing else pins the pair: the assertion above is about the include,
        # and `tools/validate.py` does not walk this tree.
        owner = frontmatter_description(OWNER_SKILL)

        self.assertIsNotNone(owner, "the owner's frontmatter names no description")
        self.assertEqual(frontmatter_description(HOST_MIRROR), owner)
        self.assertLessEqual(len(owner), DESCRIPTION_BUDGET)
