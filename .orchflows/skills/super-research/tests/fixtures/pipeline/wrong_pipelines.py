"""Governors and fused paths that are wrong, each in exactly one way.

This file is not part of the package. Nothing imports it, no discovery pattern
matches it, and ``tests/test_pipeline.py`` loads it by path. It exists so the
oracles there can be shown to reject a wrong result without mutating the tree
under test: every governor below is the real one with a single method
overridden, and every fused path below runs the real one and then spoils
exactly one property of its output.

Each is a plausible mistake rather than an absurd one. A governor that never
waits is what "make the suite faster" looks like; a governor that stamps a
served answer with the moment it served it is what "keep the timestamps
current" looks like; a fused path that folds a hit into the target it found is
what "fused should not emit the same thing twice" looks like. All three would
pass a suite that only counted records.
"""

import time
from dataclasses import replace

from super_research import normalize, runner


class UnpacedGovernor(runner.RateGovernor):
    """Reads whenever it is asked to: every declared interval is ignored."""

    def _ready_at(self, route_id, budget):
        return 0


class RotatingGovernor(runner.RateGovernor):
    """Becomes a different client on every read, which is the one thing forbidden.

    It respects every interval and every cooldown. That is the point: evasion
    does not look like impatience, it looks like a scheduler that waits
    politely under a name it keeps changing.
    """

    def _paced_fetch(self, request):
        rotated = replace(
            request,
            headers=tuple(
                (name, "{0}-{1}".format(value, len(self.log)))
                if name.lower() == "user-agent"
                else (name, value)
                for name, value in request.headers
            ),
        )
        return runner.RateGovernor._paced_fetch(self, rotated)


class RestampingGovernor(runner.RateGovernor):
    """Hands a served answer the moment it served it, in place of the moment it was read."""

    def __init__(self, carrier, now, run_cache=None, clock=time.monotonic, sleep=time.sleep):
        runner.RateGovernor.__init__(
            self, carrier, run_cache=run_cache, clock=clock, sleep=sleep
        )
        self._now = now

    def fetch(self, request):
        response = runner.RateGovernor.fetch(self, request)
        if not response.cache_hit:
            return response
        return replace(response, observed_at=self._now())


class UnmarkedGovernor(runner.RateGovernor):
    """Serves from memory without saying so: the answer is right, its provenance is not."""

    def fetch(self, request):
        response = runner.RateGovernor.fetch(self, request)
        return replace(response, cache_hit=False)


def correct(carrier, run_cache, clock):
    """The real governor, so every rejection below is attributable to one override."""

    return runner.RateGovernor(
        carrier, run_cache=run_cache, clock=clock.monotonic, sleep=clock.sleep
    )


def unpaced(carrier, run_cache, clock):
    return UnpacedGovernor(
        carrier, run_cache=run_cache, clock=clock.monotonic, sleep=clock.sleep
    )


def restamping(carrier, run_cache, clock):
    return RestampingGovernor(
        carrier,
        now=clock.stamp,
        run_cache=run_cache,
        clock=clock.monotonic,
        sleep=clock.sleep,
    )


def unmarked(carrier, run_cache, clock):
    return UnmarkedGovernor(
        carrier, run_cache=run_cache, clock=clock.monotonic, sleep=clock.sleep
    )


def merged_fused_run(manifest, carrier, clock):
    """Folds every discovery hit into the target it found: one record for one thing."""

    run = runner.run_scheduled(manifest, carrier, clock=clock.monotonic)
    hydrated = [
        record for record in run.artifact.records if record.representation_kind == "native"
    ]
    kept = tuple(
        record
        for record in run.artifact.records
        if not (
            record.representation_kind == "index"
            and any(
                target.discovery_locator == record.normalized_locator for target in hydrated
            )
        )
    )
    return runner.ScheduledRun(
        artifact=replace(
            run.artifact,
            records=kept,
            edges=normalize.link_discovery_hydration(kept),
            groups=normalize.group_records(kept),
        ),
        ledger=run.ledger,
    )


def unlinked_fused_run(manifest, carrier, clock):
    """Keeps both records and drops the edge between them: lineage lost without a merge."""

    run = runner.run_scheduled(manifest, carrier, clock=clock.monotonic)
    return runner.ScheduledRun(artifact=replace(run.artifact, edges=()), ledger=run.ledger)


def serialized_fused_run(manifest, carrier, clock):
    """Calls itself fused and schedules like staged: the label without the collapse."""

    run = runner.run_scheduled(replace(manifest, mode="staged"), carrier, clock=clock.monotonic)
    return runner.ScheduledRun(
        artifact=replace(run.artifact, mode="fused"), ledger=run.ledger
    )
