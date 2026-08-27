"""The resolver's answers over this repository's own tests tree.

Asserted as subsets: pinning the whole map would make every new test that
touches a shared module a failure of this suite rather than of its own.
"""

from __future__ import annotations

import unittest

from tests.test_affected_tests_cases.common import ROOT

from tools import affected_tests  # noqa: E402


class LiveRepositoryCase(unittest.TestCase):
    """Resolve against the live checkout, scanning the tree once per class."""

    @classmethod
    def setUpClass(cls):
        cls.shards = affected_tests.shard_files(ROOT / "tests")[1]
        cls.for_format = affected_tests.affected(["scripts/tickets_format.py"])
        cls.for_friction = affected_tests.affected(["scripts/friction.py"])


class TestLiveEdges(LiveRepositoryCase):
    def test_a_shared_ticket_module_reaches_the_shards_that_read_it(self):
        self.assertLessEqual(
            {
                "tests.test_tickets",
                "tests.test_ticket_semantic_contract",
                "tests.test_cutcheck",
            },
            set(self.for_format["modules"]),
        )

    def test_a_file_location_import_reaches_its_shard(self):
        self.assertIn("tests.test_friction", self.for_friction["modules"])

    def test_the_resolver_dogfoods_its_own_scope(self):
        self.assertIn(
            "tests.test_affected_tests",
            affected_tests.affected(["tools/affected_tests.py"])["modules"],
        )


class TestLiveDiscrimination(LiveRepositoryCase):
    """A resolver that answered "every shard" would satisfy every subset."""

    def test_a_narrow_scope_selects_strictly_fewer_shards_than_the_suite(self):
        self.assertLess(len(self.for_friction["modules"]), len(self.shards))
        self.assertLess(len(self.for_format["modules"]), len(self.shards))

    def test_a_scope_path_no_test_names_reaches_no_shard(self):
        # Assembled at run time on purpose: spelling the path as one literal
        # here would make this very file an edge to it, and the resolver --
        # correctly -- would answer with this shard.
        absent = "docs/absent_%s.py" % "module"
        resolved = affected_tests.affected([absent])
        self.assertEqual([], resolved["modules"])
        self.assertEqual([absent], resolved["no_tests"])


class TestLiveResidue(LiveRepositoryCase):
    def test_every_shard_file_in_this_checkout_parses(self):
        # An unreadable file is skipped, so a silent parse failure would
        # quietly shrink every answer above; name it here instead.
        self.assertEqual([], self.for_friction["unreadable"])


if __name__ == "__main__":
    unittest.main()
