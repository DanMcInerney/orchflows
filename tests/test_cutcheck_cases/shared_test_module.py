"""Cutcheck behavioral cases loaded explicitly by tests.test_cutcheck."""

from tests.test_cutcheck import *  # noqa: F401,F403

from scripts import cutcheck_graph  # noqa: E402  the pairwise reading's own owner
from tests.test_cutcheck import _graded_with  # noqa: E402  private to the facade's star

try:
    del load_tests
except NameError:
    pass

# A tree holding no `tools/affected_tests.py`: the resolver is the graded
# revision's, so a revision without it resolves nothing. The harness's own
# baseline clone is exactly that tree, which is why the pinned fixture
# verdicts are unmoved by this reading.
NO_RESOLVER = "tests"

# Assembled rather than written whole, and this is not fussiness: the resolver
# reads string literals, so a scope path spelled here as one literal makes this
# very module an edge of it and hands `tests.test_cutcheck` to every scope the
# module names. The one case that asks for two disjoint sets has to keep out of
# its own answer -- and the split falls before the suffix, because a bare base
# name is one of the literal forms a scope path is recognized by.
UNSHARED = "docs/vocabulary" + ".md"


def item(*scope, depends_on=()):
    return {
        "executor": "orch-tdd",
        "pack": "orch-code-pack",
        "depends_on": list(depends_on),
        "write_scope": list(scope),
    }


def paired(siblings, tree=None):
    """Every family-4 finding this sibling set draws, graded against ``tree``."""

    return cutcheck_graph._pairwise(siblings, {}, tree=tree)


def shared(siblings, tree=None):
    """The shared-test-module details alone, keyed by the item they name."""

    return {
        left: detail
        for left, _, klass, detail in paired(siblings, tree)
        if klass == cutcheck.SHARED_TEST_MODULE
    }


class SharedTestModuleTest(unittest.TestCase):
    """Two items free to run at once whose evidence is one process's."""

    def test_two_siblings_scoped_to_one_module_share_its_tests(self):
        found = shared(
            {
                "01-left": item("scripts/tickets_format.py"),
                "02-right": item("scripts/tickets_format.py"),
            },
            tree=ROOT,
        )
        self.assertEqual(["01-left"], sorted(found))
        self.assertIn("with 02-right", found["01-left"])
        self.assertIn("tests.test_tickets", found["01-left"])

    def test_siblings_reaching_different_modules_share_nothing(self):
        """The can-fail direction: scopes whose shard sets do not meet."""

        self.assertEqual(
            {},
            shared(
                {
                    "01-left": item("scripts/cutcheck_graph.py"),
                    "02-right": item(UNSHARED),
                },
                tree=ROOT,
            ),
        )

    def test_scopes_that_never_collide_can_still_share_a_shard(self):
        """The reading's whole reason: path disjointness proves nothing here."""

        siblings = {
            "01-left": item("scripts/cutcheck_graph.py"),
            "02-right": item("scripts/cutcheck_search.py"),
        }
        classes = {klass for _, _, klass, _ in paired(siblings, tree=ROOT)}
        self.assertNotIn(cutcheck.SCOPE_COLLISION, classes)
        self.assertIn("tests.test_cutcheck", shared(siblings, tree=ROOT)["01-left"])

    def test_an_ordered_pair_is_not_read_at_all(self):
        """Staging is what makes a shared shard safe, as it is for a shared path."""

        self.assertEqual(
            {},
            shared(
                {
                    "01-left": item("scripts/tickets_format.py"),
                    "02-right": item(
                        "scripts/tickets_format.py", depends_on=["01-left"]
                    ),
                },
                tree=ROOT,
            ),
        )

    def test_a_revision_without_the_resolver_reports_nothing(self):
        """`tools/` is repo-only, so an installed copy grades trees without it.

        The reading is skipped there rather than guessed at, and skipped in
        silence: a per-run note would be a report line, and a report line is
        what every downstream filter selects on.
        """

        siblings = {
            "01-left": item("scripts/tickets_format.py"),
            "02-right": item("scripts/tickets_format.py"),
        }
        for tree in (None, ROOT / NO_RESOLVER):
            self.assertEqual({}, shared(siblings, tree=tree), tree)
        self.assertIsNone(
            cutcheck_graph._affected_modules(
                ROOT / NO_RESOLVER, ["scripts/tickets_format.py"]
            )
        )


class SharedTestModuleReportTest(unittest.TestCase):
    """The class's standing in the report, end to end over a real cut."""

    def setUp(self):
        real = cutcheck_graph._pairwise

        def against_this_checkout(siblings, reads, region_prover=None, tree=None):
            # The same reading, handed a revision that carries the resolver.
            # The harness's baseline predates `tools/affected_tests.py`, so
            # nothing else supplies one and the class would never be reported.
            return real(siblings, reads, region_prover=region_prover, tree=ROOT)

        with mock.patch.object(cutcheck, "_pairwise", against_this_checkout):
            self.code, self.output = _graded_with(
                self, ["cutcheck-graph", "--baseline", BASELINE]
            )
        self.recorded = json.loads(VERDICTS.read_text(encoding="utf-8"))["cutcheck-graph"]

    def test_the_class_is_family_four_and_advisory(self):
        self.assertEqual(
            cutcheck.FAMILY_4, cutcheck.FAMILY_OF[cutcheck.SHARED_TEST_MODULE]
        )
        self.assertIn(cutcheck.SHARED_TEST_MODULE, cutcheck.ADVISORY)

    def test_the_finding_is_reported_under_the_advisory_heading(self):
        lines = self.output.splitlines()
        self.assertIn(cutcheck.ADVISORY_HEADING, lines, self.output)
        found = [
            line for line in lines if cutcheck.SHARED_TEST_MODULE in line
        ]
        self.assertTrue(found, self.output)
        heading = lines.index(cutcheck.ADVISORY_HEADING)
        for line in found:
            self.assertGreater(lines.index(line), heading, line)
            self.assertIn(cutcheck.FAMILY_4, line)

    def test_the_advisory_moves_neither_the_status_nor_the_shape(self):
        lines = self.output.splitlines()
        pinned = self.recorded["lines"]
        self.assertEqual(self.recorded["exit"], self.code, self.output)
        self.assertEqual(cutcheck.CLEAN, self.code, self.output)
        self.assertEqual(
            pinned[pinned.index(cutcheck.GRAPH_HEADING):],
            lines[lines.index(cutcheck.GRAPH_HEADING):],
        )
        self.assertEqual(cutcheck.NO_FINDING_OUTSIDE, lines[-1], self.output)


if __name__ == "__main__":
    unittest.main()
