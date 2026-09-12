"""Artifact-review and step-identity checks for the coverage seam."""

from __future__ import annotations

import dataclasses
import json
import unittest
from super_research import coverage, runner, schema, transport
from tests import helpers
from tests.test_coverage_cases.common import (
    artifact,
    codes,
    manifest,
    record,
    step,
    step_result,
)


class ReviewArtifactTest(unittest.TestCase):
    def artifact(self, steps=(), records=()):
        return artifact(steps=steps, records=records)

    def result(self, step_id, outcome, loss):
        return step_result(step_id, "hacker_news", outcome=outcome, loss=loss)

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

    def test_no_hydration_does_not_establish_missing_content(self):
        found = coverage.review_artifact(
            self.artifact(
                steps=[step_result("s1", "reddit_shreddit", "discovery", "search:btc")],
                records=[record("r1", "reddit_shreddit")],
            )
        )

        self.assertEqual(found, ())

    def test_selected_fxtwitter_conversation_is_present_after_one_discovery_read(self):
        root = {"id": "101", "url": "https://x.com/researcher/status/101", "text": "An opening claim.",
                "author": {"screen_name": "researcher"}, "created_timestamp": 1660000000}
        reply = dict(root, id="102", url="https://x.com/researcher/status/102",
                     text="A reply with counterevidence.", replying_to={"status": "101"})
        payload = json.dumps({"code": 200, "status": root, "replies": [reply]})
        chosen = manifest(step("conversation", "discovery", "x_fxtwitter", query="conversation:101"))
        self.assertEqual(coverage.review_manifest(chosen), ())
        clock = helpers.FakeClock()
        carrier, opener = helpers.offline_transport(clock,
            {transport.FXTWITTER_API_ROUTE: (200, payload, "application/json")})
        result = runner.run_acquisition(chosen, carrier, clock=clock.monotonic)
        self.assertEqual(len(opener.opened), 1)
        self.assertEqual([row.body for row in result.records], [root["text"], reply["text"]])
        self.assertEqual(result.records[1].native_parent_id, "101")
        self.assertTrue(all("third_party_archive" in row.loss for row in result.records))
        self.assertEqual(coverage.review_artifact(result), ())

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




class StepIdentityTest(unittest.TestCase):
    """Every result echoes the requested kind and query, including refusals."""

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
            query="tree:101", max_items=10,
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
                ("discovery", "tree:101"),
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
