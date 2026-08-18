from .common import *

class AccessClassDeclarationTest(unittest.TestCase):
    """Criterion 2: one class per adapter, out of one closed ladder.

    The roster half and the closed-set half are separate claims. An adapter
    could declare a class that is on the ladder and wrong for its route, or a
    class that is right for its route and on no ladder at all; only the first
    is a roster question.
    """

    def test_the_ladder_is_the_one_the_schema_seam_owns(self):
        self.assertEqual(schema.ACCESS_CLASSES, LADDER)

    def test_the_core_lists_exactly_the_rosters_adapters(self):
        self.assertEqual(sorted(runner.ADAPTER_IDS), sorted(ROSTER))

    def test_every_adapter_declares_the_class_the_roster_gives_it(self):
        for adapter_id, access_class in sorted(ROSTER.items()):
            with self.subTest(adapter=adapter_id):
                descriptor = runner.descriptor_for(adapter_id)

                self.assertIsNotNone(descriptor)
                self.assertEqual(descriptor.access_class, access_class)
                self.assertIn(descriptor.access_class, LADDER)

    def test_every_surface_an_adapter_reaches_declares_that_same_one_class(self):
        assert_one_class_per_adapter(self, shipped_roster())
        for adapter_id, access_class in sorted(ROSTER.items()):
            for surface in runner.surface_descriptors(adapter_id):
                with self.subTest(adapter=adapter_id, route=surface.route_id):
                    self.assertEqual(surface.access_class, access_class)
                    self.assertEqual(surface.adapter_id, adapter_id)

    def test_exactly_one_class_is_declared_and_it_is_a_single_ladder_name(self):
        # "Exactly one" is a claim about the value, not about the field: a
        # descriptor holds one string, and the string has to be one whole class
        # name rather than a pair somebody spelled with a separator.
        for adapter_id in sorted(ROSTER):
            with self.subTest(adapter=adapter_id):
                declared = runner.descriptor_for(adapter_id).access_class

                self.assertEqual([name for name in LADDER if name == declared], [declared])


class KeylessCapabilityTest(unittest.TestCase):
    """Criterion 3: no first-release capability is reachable only through `K5`.

    Stated over the roster the core has actually registered, so a later adapter
    is inside the law the moment it is reachable rather than when somebody
    remembers to list it here.
    """

    def setUp(self):
        self.roster = shipped_roster()

    def test_the_roster_the_law_reads_is_every_surface_the_core_can_reach(self):
        # The law is only as wide as its input, so the input is pinned: the
        # twenty adapters' thirty-six distinct routes, which is now every route
        # in the table. One of them is the guest-token activation, which
        # used to sit outside the roster on the reasoning that the opener
        # minted for itself — and sat outside every budget with it.
        self.assertEqual(len(self.roster), 36)
        self.assertEqual(
            sorted({surface.route_id for surface in self.roster}),
            sorted(transport.ROUTE_CONSTANTS),
        )
        self.assertEqual(
            len({surface.route_id for surface in self.roster}), len(self.roster)
        )
        self.assertEqual(
            sorted({surface.adapter_id for surface in self.roster}), sorted(ROSTER)
        )

    def test_every_listed_adapter_reaches_at_least_one_surface(self):
        # An adapter with no surface is a capability with no route: the law
        # below would have nothing to say about it, so it is refused here.
        for adapter_id in sorted(ROSTER):
            with self.subTest(adapter=adapter_id):
                self.assertTrue(runner.surface_descriptors(adapter_id))

    def test_no_capability_in_the_roster_needs_a_credential(self):
        assert_the_access_ladder_holds(self, self.roster)

    def test_nothing_in_the_roster_declares_the_credentialed_class(self):
        # The plain statement behind the law, kept beside it: the run measured
        # that only two capabilities genuinely need a credential and deferred
        # both, so the class exists on the ladder and nothing is in it.
        self.assertEqual(
            sorted({surface.access_class for surface in self.roster}),
            ["K0", "K1", "K2", "K3", "K4", "offline"],
        )
        self.assertIn(CREDENTIALED, schema.ACCESS_CLASSES)

    def test_every_adapter_turned_credentialed_is_rejected(self):
        # Fourteen rosters, each the shipped one with one adapter's every
        # surface relabelled. This is the check reading each adapter in turn:
        # an adapter it skipped would pass here while credentialed.
        for adapter_id in sorted(ROSTER):
            routes = {
                surface.route_id for surface in runner.surface_descriptors(adapter_id)
            }
            with self.subTest(adapter=adapter_id):
                with self.assertRaisesRegex(
                    AssertionError, "adapter {0} is reachable only".format(adapter_id)
                ):
                    assert_the_access_ladder_holds(self, credentialed(self.roster, routes))

    def test_every_single_surface_turned_credentialed_is_rejected(self):
        # Seventeen rosters, each with exactly one route relabelled. An adapter
        # reading one route fails the reachability half; an adapter reading two
        # fails the one-class half, which is why both are laws and not one.
        for surface in self.roster:
            with self.subTest(route=surface.route_id):
                with self.assertRaisesRegex(
                    AssertionError,
                    "reachable only with a credential|answers at more than one access class",
                ):
                    assert_the_access_ladder_holds(
                        self, credentialed(self.roster, {surface.route_id})
                    )
