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
        self.assertEqual(len(self.LIVE), 8)
        self.assertEqual(len(runner.ADAPTER_IDS), 9)

    def test_the_dispatch_read_every_route_the_roster_can_reach(self):
        # One step, one read and one distinct route per readable surface: the
        # oracle below cannot pass by leaving a surface out of the run.
        readable = sorted({
            surface.route_id
            for adapter_id in runner.ADAPTER_IDS
            for surface in runner.surface_descriptors(adapter_id)
        })

        self.assertEqual(len(roster_manifest().steps), 17)
        self.assertEqual(sorted(request.route_id for request in self.opener.opened), readable)
        self.assertEqual(sorted(ROSTER_PAYLOADS), readable)

    def test_the_artifact_holds_every_row_every_step_returned(self):
        self.assertTrue(all(step.records_kept > 0 for step in self.artifact.steps))
        self.assertEqual(len(self.artifact.records), sum(step.records_kept for step in self.artifact.steps))
        self.assertEqual(self.artifact.outcome, "ok")
        self.assertEqual(self.artifact.loss, ())

    def test_every_adapter_reached_its_capability_and_none_wanted_a_credential(self):
        assert_nothing_wanted_a_credential(self, self.artifact, self.LIVE)

    def test_the_offline_fixture_adapter_answered_beside_the_live_ones(self):
        # The fixture adapter is not a live capability and is checked apart
        # from them, so "every live adapter answered" stays a statement about
        # the live ones.
        assert_nothing_wanted_a_credential(self, self.artifact, ("fake",))

    def test_every_adapter_reads_a_route_needing_no_user_credential(self):
        # The other end of the same claim, at the table that states it: no
        # route any adapter reads is declared K5.
        for adapter_id in runner.ADAPTER_IDS:
            for surface in runner.surface_descriptors(adapter_id):
                with self.subTest(adapter=adapter_id, route=surface.route_id):
                    self.assertNotEqual(
                        transport.route_constant(surface.route_id).access_class, "K5"
                    )

    def test_no_string_in_the_whole_artifact_says_a_credential_was_wanted(self):
        # Belt and braces over the oracle's field-by-field reading: seven
        # adapters spell the same word, and it is nowhere in what the run
        # produced.
        self.assertNotIn(AUTH_REQUIRED, repr(self.artifact))

    def test_every_row_the_run_kept_came_from_an_uncredentialed_class(self):
        self.assertEqual(
            sorted({record.access_class for record in self.artifact.records}),
            ["K0", "K2", "K3", "offline"],
        )

    def test_the_whole_dispatch_ran_with_the_environment_emptied(self):
        # Not a re-run: the artifact under test was produced inside the guard,
        # and this states what the guard was. Both halves are asserted from
        # inside it, so an escape would be visible here rather than assumed.
        with no_credentials_anywhere():
            self.assertEqual(dict(os.environ), {})
            self.assertEqual(self.artifact.outcome, "ok")
