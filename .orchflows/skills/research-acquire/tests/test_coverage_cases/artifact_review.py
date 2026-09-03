"""Artifact-review and step-identity checks for the coverage seam."""

from __future__ import annotations

import dataclasses
import json
import unittest
from dataclasses import replace

from super_research import coverage, runner, schema, transport
from tests import helpers
from tests.test_coverage_cases.common import (
    YOUTUBE_DISCOVERED_AS,
    YOUTUBE_TRANSCRIPT_AS,
    artifact,
    codes,
    manifest,
    record,
    step,
    step_result,
    subjects,
)


class ReviewArtifactTest(unittest.TestCase):
    def artifact(self, steps=(), records=()):
        return artifact(steps=steps, records=records)

    def result(self, step_id, outcome="ok", loss=()):
        return step_result(step_id, "bluesky", "discovery", "search:x", outcome, loss)

    def test_a_typed_loss_is_named_as_something_the_report_must_state(self):
        found = coverage.review_artifact(
            self.artifact(steps=[self.result("bs", "failed", ("auth_required",))])
        )

        self.assertEqual(codes(found), [coverage.STEP_CARRIED_LOSS])
        self.assertIn("not an absence", found[0].message)

    def test_a_truncated_recall_gets_one_advisory_and_not_two(self):
        """Two advisories for one loss is how a reader learns to skim them."""

        found = coverage.review_artifact(
            self.artifact(steps=[self.result("x", "partial", ("recall_window_partial",))])
        )

        self.assertEqual(codes(found), [coverage.RECALL_WAS_A_WINDOW])

    def test_a_run_that_discovered_and_never_deepened_says_so(self):
        found = coverage.review_artifact(
            self.artifact(
                steps=[step_result("s1", "reddit_shreddit", "discovery", "search:btc")],
                records=[record("r1", "reddit_shreddit")],
            )
        )

        self.assertEqual(subjects(found, coverage.NOTHING_HYDRATED), ["reddit_shreddit"])

    def test_a_run_that_hydrated_what_it_discovered_draws_nothing(self):
        found = coverage.review_artifact(
            self.artifact(
                steps=[
                    step_result("s1", "reddit_shreddit", "discovery", "search:btc"),
                    step_result("cm", "reddit_shreddit", "hydration", "comments"),
                ],
                records=[
                    record("r1", "reddit_shreddit"),
                    record(
                        "r2",
                        "reddit_shreddit",
                        step_id="cm",
                        discovery_locator="https://example.invalid/a",
                        representation_kind="native",
                    ),
                ],
            )
        )

        self.assertEqual(found, ())


class DepthReviewTest(unittest.TestCase):
    """Depth planned the paging way is depth, and neither review may deny it.

    Both advisories were written when every depth operation was a hydration
    step. A `next` or `transcript` step is a discovery step now, so a review
    that still counts hydration steps and hydration records would call the
    deepest manifest this module can build "no depth planned" — and a warning
    that fires on the fix is worse than one that never fired.

    What each review reads is the step: the manifest one reads its
    `AcquisitionStep`s and the artifact one reads the `StepResult` each record
    names. Every earlier attempt read record shape instead, and shape cannot
    answer this — a paging depth step's records look exactly like a search
    step's, which is what the first case below asserts by handing the same rows
    to both and demanding two different answers.
    """

    def test_a_manifest_planning_paging_depth_draws_none(self):
        planned = coverage.plan_depth(
            [record("y1", "youtube_innertube", native_item_id="vid")],
            "youtube_innertube",
            "next",
            "nx",
            max_items=200,
        )

        found = coverage.review_manifest(
            manifest(
                step("yt", "discovery", "youtube_innertube", query="search:btc"),
                *planned.steps
            )
        )

        self.assertNotIn(coverage.DEPTH_NOT_PLANNED, codes(found))

    def test_depth_is_read_off_the_step(self):
        """One set of records, three steps, three answers.

        The discriminating case, and the one no record-shape test can be: the
        rows are byte-identical across all three artifacts — same
        representation kind, no parent, no `discovery_locator` — so every
        proxy that could be inspected says the same thing about all of them.
        The only thing that differs is what the step they came from states it
        was, and the review has to move with it in both directions.
        """

        rows = [
            record(
                "y1",
                "youtube_innertube",
                native_item_id="vid",
                representation_kind=YOUTUBE_DISCOVERED_AS,
            )
        ]

        def under(kind, query):
            return coverage.review_artifact(
                artifact(
                    steps=[step_result("s1", "youtube_innertube", kind, query)], records=rows
                )
            )

        # `search:` names no depth operation, so this one discovered.
        self.assertEqual(
            subjects(under("discovery", "search:btc"), coverage.NOTHING_HYDRATED),
            ["youtube_innertube"],
        )
        # `next:` and `transcript:` are the rows `DEPTH_TARGETS` declares as
        # paging depth, and a paging depth step is a discovery step by kind —
        # which is exactly why the kind alone was never enough to read.
        self.assertNotIn(coverage.NOTHING_HYDRATED, codes(under("discovery", "next:vid")))
        self.assertNotIn(coverage.NOTHING_HYDRATED, codes(under("discovery", "transcript:vid")))
        self.assertNotIn(coverage.NOTHING_HYDRATED, codes(under("hydration", "player")))
        # Naming a depth operation is not enough: `_is_depth` asks
        # `DEPTH_TARGETS` which *kind* that operation is, and only a
        # paging one rides a discovery step. `player` answers in one call,
        # so a discovery step naming it holds a continuation nothing
        # publishes and deepens nothing — the near miss a hand-written or
        # hand-amended manifest reaches, and the reason the row's `kind`
        # column exists. Held here because the clause is now one rule read
        # from both sides, so a wrong answer is wrong in both reviews.
        self.assertEqual(
            subjects(under("discovery", "player:vid"), coverage.NOTHING_HYDRATED),
            ["youtube_innertube"],
        )

    def test_a_depth_only_artifact_draws_none(self):
        """The 57-comment case, in the shape `plan_depth`'s own steps return it.

        A `next` step is its own dispatch over records a discovery run already
        returned, so this artifact holds the comments and **not** the videos
        they name — those are in artifact one. Every proxy the old clause
        reached for is therefore absent: no `discovery_locator`, because the
        core sets one only on a hydration step's own calls, and no parent this
        artifact holds. Asking the records for it is what told a caller who had
        just acquired 57 comment records that nothing had deepened anything,
        measured 2026-08-17. The step says `next:vid`, and that is the read.
        """

        found = coverage.review_artifact(
            artifact(
                steps=[step_result("nx-1", "youtube_innertube", "discovery", "next:vid")],
                records=[
                    record(
                        "c1",
                        "youtube_innertube",
                        step_id="nx-1",
                        native_item_id="UgyyGmQ",
                        representation_kind=YOUTUBE_DISCOVERED_AS,
                        locator="https://example.invalid/c1",
                    ),
                    record(
                        "c2",
                        "youtube_innertube",
                        step_id="nx-1",
                        native_item_id="UgyralckD",
                        representation_kind=YOUTUBE_DISCOVERED_AS,
                        locator="https://example.invalid/c2",
                    ),
                ],
            )
        )

        self.assertEqual(found, ())

    def test_an_artifact_fusing_the_discovery_and_the_depth_draws_none(self):
        """A caller may also fuse both dispatches into one artifact.

        Three steps of three shapes in one artifact, each record read against
        its own: the search rows are not deepened by sitting beside a
        transcript, and the transcript is not undeepened by sitting beside
        them. One adapter deepened something, so the advisory stays quiet.
        """

        found = coverage.review_artifact(
            artifact(
                steps=[
                    step_result("yt", "youtube_innertube", "discovery", "search:btc"),
                    step_result("nx-1", "youtube_innertube", "discovery", "next:vid"),
                    step_result("tx-1", "youtube_innertube", "discovery", "transcript:vid"),
                ],
                records=[
                    record(
                        "y1",
                        "youtube_innertube",
                        step_id="yt",
                        native_item_id="vid",
                        representation_kind=YOUTUBE_DISCOVERED_AS,
                    ),
                    record(
                        "c1",
                        "youtube_innertube",
                        step_id="nx-1",
                        native_item_id="UgyyGmQ",
                        native_parent_id="vid",
                        locator="https://example.invalid/c1",
                    ),
                    record(
                        "t1",
                        "youtube_innertube",
                        step_id="tx-1",
                        native_item_id="vid",
                        representation_kind=YOUTUBE_TRANSCRIPT_AS,
                    ),
                ],
            )
        )

        self.assertNotIn(coverage.NOTHING_HYDRATED, codes(found))

    def test_a_search_only_artifact_still_draws_it(self):
        """Silence has to be earned, or the cases above prove only that it is easy.

        A run that called `search:` and stopped: this is the advisory's whole
        reason to exist, and the change above must not have bought its quiet by
        going quiet everywhere.
        """

        found = coverage.review_artifact(
            artifact(
                steps=[step_result("yt", "youtube_innertube", "discovery", "search:btc")],
                records=[
                    record(
                        "y1",
                        "youtube_innertube",
                        step_id="yt",
                        native_item_id="vid",
                        representation_kind=YOUTUBE_DISCOVERED_AS,
                    ),
                    record(
                        "y2",
                        "youtube_innertube",
                        step_id="yt",
                        native_item_id="vid2",
                        representation_kind=YOUTUBE_DISCOVERED_AS,
                    ),
                ],
            )
        )

        self.assertEqual(subjects(found, coverage.NOTHING_HYDRATED), ["youtube_innertube"])

    def test_a_record_whose_step_this_artifact_does_not_hold_is_read_as_neither(self):
        """When the step cannot answer, the answer is to say nothing.

        The failure this whole change removes was a review that, unable to read
        the step, reached for the nearest thing a record looked like. So the one
        case where the join finds nothing — a hand-assembled artifact, or a
        `StepResult` built without a kind — draws neither the advisory nor its
        silence-by-proxy. Both readings are asserted, because a record that
        counted as discovery would re-draw the false advisory and one that
        counted as depth would suppress the true one.

        Holding both is what decides the fixture's shape, and an artifact of
        one adapter and one unreadable record cannot: it comes back `()`
        whether that record reads as depth or as neither, so the suppression
        half — the half this replacement inherited from the clause it replaced
        — would be claimed here and asserted nowhere. So each fixture carries a
        real search-only step of its own, which puts a true `nothing_hydrated`
        for `youtube_innertube` on the table where a record read as depth
        suppresses it; and each unreadable record is doubled, one on that same
        adapter and one on `reddit_shreddit`, which nothing else in the
        artifact mentions and which a record read as discovery would draw a
        second advisory for. One assertion, red in both directions.
        """

        # At the kind this adapter's discovery answers on and naming no parent:
        # a search row, which is the shape the old clause read as discovery.
        row = record(
            "y1", "youtube_innertube", step_id="yt", native_item_id="vid",
            representation_kind=YOUTUBE_DISCOVERED_AS,
        )
        searched = step_result("yt", "youtube_innertube", "discovery", "search:btc")
        same_adapter = replace(row, record_id="y2", native_item_id="vid2")
        other_adapter = record("r1", "reddit_shreddit", native_item_id="post")
        # A `StepResult` built the way a caller builds one by hand: every
        # required field given, `kind` left to its default.
        by_hand = dict(route_id="r", pages=1, records_received=1, records_kept=1, outcome="ok")

        orphaned = artifact(
            steps=[searched],
            records=[
                row,
                replace(same_adapter, step_id="gone"),
                replace(other_adapter, step_id="gone"),
            ],
        )
        kindless = artifact(
            steps=[
                searched,
                schema.StepResult(step_id="s1", adapter_id="youtube_innertube", **by_hand),
                schema.StepResult(step_id="s2", adapter_id="reddit_shreddit", **by_hand),
            ],
            records=[
                row,
                replace(same_adapter, step_id="s1"),
                replace(other_adapter, step_id="s2"),
            ],
        )

        self.assertEqual(
            subjects(coverage.review_artifact(orphaned), coverage.NOTHING_HYDRATED),
            ["youtube_innertube"],
        )
        self.assertEqual(
            subjects(coverage.review_artifact(kindless), coverage.NOTHING_HYDRATED),
            ["youtube_innertube"],
        )


class StepIdentityTest(unittest.TestCase):
    """A `StepResult` states what its step was, so no reader re-derives it.

    The two facts that decide whether a step was depth — its kind and its query
    — lived only on the manifest, and an artifact does not carry one. Every
    reader downstream therefore guessed from record shape, which is the defect
    `DepthReviewTest` below measures. Both construction sites fill them, the
    refusal included: a step the core would not run is still a step whose kind
    and query are known, and the artifact that most needs explaining is exactly
    the one that would otherwise be unable to say what it asked for.
    """

    def offline(self, step, pages=1):
        """``step`` run against canned offline answers, and its result alone."""

        payload = json.dumps(
            {
                "platform": "fixture",
                "cursor_out": "",
                "records": [
                    {
                        "canonical_content_kind": "post",
                        "canonical_locator": "https://fixture.invalid/p/0",
                        "native_item_id": "0",
                        "title": "row 0",
                    }
                ],
            }
        )
        clock = helpers.FakeClock()
        carrier, _ = helpers.offline_transport(
            clock,
            {transport.FAKE_OFFLINE_ROUTE: [(200, payload, "application/json")] * pages},
        )
        return runner.run_step(step, carrier, "artifact:m", "m", clock=clock.monotonic)[0]

    def test_every_step_result_carries_its_kind_and_query(self):
        discovery = schema.AcquisitionStep(
            step_id="d", kind="discovery", adapter_id="fake",
            query="search:btc", max_items=10,
        )
        hydration = schema.AcquisitionStep(
            step_id="h", kind="hydration", adapter_id="fake", query="comments",
            selected_hits=(schema.SelectedHit("https://fixture.invalid/p/0", "0"),),
            max_items=10,
        )
        # The core declares no such adapter, so `run_step` refuses before it
        # reaches the carrier — which is why this one is handed none.
        refused = schema.AcquisitionStep(
            step_id="x", kind="discovery", adapter_id="no_such_adapter",
            query="transcript:vid", max_items=10,
        )

        results = (
            self.offline(discovery),
            self.offline(hydration),
            runner.run_step(refused, None, "artifact:m", "m")[0],
        )

        self.assertEqual(results[2].outcome, "refused")
        self.assertEqual(
            [(held.kind, held.query) for held in results],
            [
                ("discovery", "search:btc"),
                ("hydration", "comments"),
                ("discovery", "transcript:vid"),
            ],
        )

    def test_the_older_shape_still_constructs_and_still_crosses_as_a_mapping(self):
        """The two fields are additive, which is what lets an artifact travel.

        `dataclasses.asdict` is how an artifact crosses a ticket, so a field
        that arrived without a default would break every caller that names its
        fields by keyword — and one that never reached the mapping would leave
        the reader on the far side back where it started.
        """

        older = schema.StepResult(
            step_id="s", adapter_id="fake", route_id="r", pages=1,
            records_received=1, records_kept=1, outcome="ok",
        )

        self.assertEqual((older.kind, older.query), ("", ""))
        self.assertEqual(dataclasses.asdict(older)["kind"], "")
        self.assertEqual(dataclasses.asdict(older)["query"], "")
