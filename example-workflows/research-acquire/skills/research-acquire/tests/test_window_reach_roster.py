"""Clause 3, whole roster: every declaration matches what its adapter sends.

One check over all nineteen live probes rather than one per adapter — Details'
own reasoning: this is the regression a later adapter is most likely to
introduce. For each probe, one step is built twice through the same
`smoke.probe_step` machinery every live smoke read already trusts — once
unwindowed (the untouched default: `window_days=0`) and once windowed (ten
days back, forced by `dataclasses.replace` on a local copy; distinct from
either of R.01's own two 365-day probes so this is a fresh reading, not a
repeat of one) — and run through the same `runner.run_step` a manifest step
takes, against an offline carrier seeded with one 200 answer on the probe's
own route. Only the OUTGOING request is read (`opener.opened`); the answer's
body is irrelevant and never parsed for a passing reason here, so one
placeholder body serves every route regardless of what it actually publishes.

An operation `_support.window_reach.WINDOW_REACH` declares `True` must send a
request that differs from its own unwindowed baseline; one declared `False`
must send the identical request either way — Goal clause 3, both directions,
proven off the wire rather than off the table's own say-so.

`x_guest` needs one extra seed: its route mints a guest token from a second
route this offline carrier does not serve, so its token is pre-remembered
directly (`transport.GUEST_TOKENS.remember`), the same seam
`tests/test_adapters_cases/x_routes.py` already uses offline.
"""

from __future__ import annotations

import dataclasses
import unittest

from super_research import probes, runner, schema, smoke, transport
from super_research._support import window_reach
from super_research.adapters import AdapterRequest
from tests import helpers

WINDOW_DAYS = 10
AS_OF = "2026-08-31T00:00:00Z"
FAKE_BODY = "{}"
FAKE_GUEST_TOKEN = "roster-check-token"


def probe_operation(probe):
    """The operation this probe's own target resolves to, `window_reach`'s way."""

    if probe.kind == "discovery":
        request = AdapterRequest(step_id="", query=probe.target)
    else:
        request = AdapterRequest(step_id="", target_ids=(probe.target,))
    return window_reach.operation_for(probe.adapter_id, request)


def run_probe(probe, window_days):
    clock = helpers.FakeClock()
    seeded = {probe.route_id: (200, FAKE_BODY, "application/json")}
    if probe.adapter_id == "x_guest":
        transport.GUEST_TOKENS.remember(transport.X_GUEST_ACTIVATE_ROUTE, FAKE_GUEST_TOKEN)
    carrier, opener = helpers.offline_transport(clock, seeded)
    step = smoke.probe_step(dataclasses.replace(probe, window_days=window_days), AS_OF)
    runner.run_step(step, carrier, "artifact:1", "manifest:1", clock=clock.monotonic)
    return opener


class DeclarationMatchesBehaviorAcrossTheRosterTest(unittest.TestCase):
    """Goal clause 3, one check over the whole roster, both directions."""

    def setUp(self):
        transport.GUEST_TOKENS.clear()
        self.addCleanup(transport.GUEST_TOKENS.clear)

    def test_every_declared_can_sends_a_different_request_when_windowed(self):
        for probe in probes.SMOKE_PROBES:
            operation = probe_operation(probe)
            if not window_reach.can_bound_at_origin(probe.adapter_id, operation):
                continue
            with self.subTest(adapter=probe.adapter_id, operation=operation):
                unwindowed = run_probe(probe, 0)
                windowed = run_probe(probe, WINDOW_DAYS)

                if not unwindowed.opened:
                    # The strongest form a `True` declaration can take: the
                    # bound is the request itself, so an unwindowed read has
                    # no shape at all and is refused before any call.
                    # `wikimedia_pageviews` is the measured case — its date
                    # range is two path segments — and the windowed half must
                    # still have spent exactly one real call.
                    self.assertEqual(len(windowed.opened), 1)
                    continue
                self.assertNotEqual(
                    (unwindowed.opened[0].url, unwindowed.opened[0].body),
                    (windowed.opened[0].url, windowed.opened[0].body),
                )

    def test_every_declared_cannot_sends_the_identical_request_either_way(self):
        for probe in probes.SMOKE_PROBES:
            operation = probe_operation(probe)
            if window_reach.can_bound_at_origin(probe.adapter_id, operation):
                continue
            with self.subTest(adapter=probe.adapter_id, operation=operation):
                unwindowed = run_probe(probe, 0)
                windowed = run_probe(probe, WINDOW_DAYS)

                self.assertEqual(
                    (unwindowed.opened[0].url, unwindowed.opened[0].body),
                    (windowed.opened[0].url, windowed.opened[0].body),
                )


if __name__ == "__main__":
    unittest.main()
