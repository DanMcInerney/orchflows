"""Keyless route and roster behavior."""

import os
import unittest

from super_research import runner, transport

from .support import (
    AUTH_REQUIRED,
    ROSTER_PAYLOADS,
    assert_nothing_wanted_a_credential,
    keyless_run,
    no_credentials_anywhere,
    roster_manifest,
)


class KeylessRosterTest(unittest.TestCase):
    """Criterion 1: every live adapter, one dispatch, no credential anywhere.

    One artifact rather than a page-level check each, because "reaches its
    declared capability" is a claim about what a caller keeps, and because a
    refusal on any step would otherwise be somebody else's test's problem.
    """

    LIVE = tuple(sorted(set(runner.ADAPTER_IDS) - {"fake"}))

    def setUp(self):
        self.artifact, self.opener = keyless_run()
        self.by_adapter = {}
        for record in self.artifact.records:
            self.by_adapter.setdefault(record.adapter_id, []).append(record)

    def test_the_live_adapters_are_what_the_run_is_about(self):
        self.assertEqual(len(self.LIVE), 19)
        self.assertEqual(len(runner.ADAPTER_IDS), 20)

    def test_the_dispatch_read_every_route_the_roster_can_reach(self):
        # One step, one read and one distinct route per readable surface: the
        # oracle below cannot pass by leaving a surface out of the run.
        #
        # Reachable is not readable. A step reads a surface an adapter names as
        # the one it reads, and the guest-token activation is not one — it
        # returns a token rather than a record, and only the composed carrier
        # spends it. This dispatch hands in a bare carrier, so no activation
        # goes out here at all; `test_transport` owns that half.
        readable = sorted(
            surface.route_id
            for adapter_id in runner.ADAPTER_IDS
            for surface in runner.surface_descriptors(adapter_id)
            if surface.route_id not in transport.TOKEN_ACTIVATION_ROUTES
        )

        self.assertEqual(len(roster_manifest().steps), 34)
        self.assertEqual(sorted(request.route_id for request in self.opener.opened), readable)
        self.assertEqual(sorted(ROSTER_PAYLOADS), readable)
        self.assertEqual(transport.GUEST_TOKENS._tokens, {})

    def test_the_artifact_holds_every_row_every_step_returned(self):
        # Written out rather than summed, so a step that quietly stopped
        # answering is a red test and not a smaller number nobody reads.
        self.assertEqual(
            [step.records_kept for step in self.artifact.steps],
            [6, 1, 3, 2, 1, 1, 100, 1, 10, 1, 2, 13, 4, 1, 1, 2, 2,
             3, 3, 3, 1, 5, 3, 2, 2, 3, 6, 2, 2, 3, 8, 2, 3, 2],
        )
        self.assertEqual(len(self.artifact.records), 204)
        self.assertEqual(self.artifact.outcome, "ok")
        self.assertEqual(self.artifact.loss, ())

    def test_every_adapter_reached_its_capability_and_none_wanted_a_credential(self):
        assert_nothing_wanted_a_credential(self, self.artifact, self.LIVE)

    def test_the_offline_fixture_adapter_answered_beside_the_live_ones(self):
        # The fixture adapter is not a live capability and is checked apart
        # from them, so "every live adapter answered" stays a statement about
        # the live ones.
        assert_nothing_wanted_a_credential(self, self.artifact, ("fake",))

    def test_the_router_admitted_every_adapter_on_its_own_route(self):
        # The other end of the same claim, at the seam that decides it: the
        # admissions map is booleans only, and every adapter's route is in it
        # and true. `auth_required` is the reason it would answer otherwise.
        admissions = transport.route_admissions()
        for adapter_id in runner.ADAPTER_IDS:
            for surface in runner.surface_descriptors(adapter_id):
                with self.subTest(adapter=adapter_id, route=surface.route_id):
                    self.assertIs(admissions[surface.route_id], True)

    def test_no_string_in_the_whole_artifact_says_a_credential_was_wanted(self):
        # Belt and braces over the oracle's field-by-field reading: seven
        # adapters and the router all spell the same word, and none of them is
        # anywhere in what the run produced.
        self.assertNotIn(AUTH_REQUIRED, repr(self.artifact))

    def test_every_row_the_run_kept_came_from_an_uncredentialed_class(self):
        self.assertEqual(
            sorted({record.access_class for record in self.artifact.records}),
            ["K0", "K1", "K2", "K3", "K4", "offline"],
        )

    def test_the_whole_dispatch_ran_with_the_environment_emptied(self):
        # Not a re-run: the artifact under test was produced inside the guard,
        # and this states what the guard was. Both halves are asserted from
        # inside it, so an escape would be visible here rather than assumed.
        with no_credentials_anywhere():
            self.assertEqual(dict(os.environ), {})
            self.assertEqual(self.artifact.outcome, "ok")
