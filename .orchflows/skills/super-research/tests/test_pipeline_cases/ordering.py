"""Artifact ordering and replay cases."""

from tests.test_pipeline_cases.common import *
from tests.test_pipeline_cases.artifact import fused_run


def replay_seeds():
    return json.loads(
        FIXTURE_DIR.joinpath("engagement_as_of_replay.json").read_text(encoding="utf-8")
    )


def seeded_record(row):
    return schema.AcquisitionRecord(
        record_id="seed#" + row["case"],
        artifact_id="artifact:ordering",
        manifest_id="ordering",
        step_id="s1-seed",
        adapter_id=row["adapter_id"],
        adapter_version="1",
        route_id="",
        access_class="",
        operator_identity="",
        platform=row["platform"],
        native_identity_namespace=row["native_identity_namespace"],
        group_scope=row["platform"],
        representation_kind=row["representation_kind"],
        canonical_content_kind=row["canonical_content_kind"],
        native_item_id=row["native_item_id"],
        native_parent_id="",
        canonical_locator="",
        normalized_locator="",
        exact_content_hash="",
        title="",
        body="",
        author="",
        community="",
        published_at=row["published_at"],
        observed_at=helpers.FROZEN_START,
        time_confidence="reported" if row["published_at"] else "unknown",
        usable_basis_time=row["published_at"],
        engagement=tuple(
            schema.EngagementSnapshot(
                metric_name=name, value=value, observed_at=observed
            )
            for name, value, observed in row["engagement"]
        ),
        page_index=0,
        list_index=0,
        native_position=row["native_position"],
        discovery_locator="",
        outcome="ok",
        loss=(),
    )


def seeded_records():
    return tuple(seeded_record(row) for row in replay_seeds()["records"])


def cases_of(records):
    return [record.record_id.split("#", 1)[1] for record in records]


DECLARING_DESCRIPTORS = {"web_search": runner.descriptor_for("web_search")}


def declaring_descriptors():
    return dict(
        DECLARING_DESCRIPTORS,
        reddit_archive=dataclasses.replace(
            runner.descriptor_for("reddit_archive"),
            comment_count_metric="num_comments",
            reply_count_metric="reply_count",
        ),
    )


class OrderingContractTest(unittest.TestCase):
    def setUp(self):
        self.seeds = replay_seeds()
        self.records = seeded_records()
        self.as_of = self.seeds["as_of"]
        self.native = tuple(
            record for record in self.records if record.representation_kind == "native"
        )
        self.descriptors = declaring_descriptors()

    def ordered(self, order, records=None):
        return cases_of(
            runner.order_records(
                self.native if records is None else records,
                order,
                self.as_of,
                descriptors=self.descriptors,
            )
        )

    def test_newest_ranks_by_usable_basis_time_with_the_untimed_terminal(self):
        self.assertEqual(
            self.ordered("newest"),
            ["future", "changing", "missing", "wrong_name", "stale", "equal_time", "untimed"],
        )

    def test_native_top_ranks_by_the_routes_own_ordinal_lower_first(self):
        self.assertEqual(
            self.ordered("native_top"),
            ["stale", "changing", "future", "equal_time", "missing", "wrong_name", "untimed"],
        )

    def test_most_commented_replays_engagement_against_the_frozen_as_of(self):
        self.assertEqual(
            self.ordered("most_commented"),
            ["stale", "changing", "equal_time", "future", "missing", "wrong_name", "untimed"],
        )

    def test_two_readings_at_one_moment_resolve_to_the_earlier_position(self):
        equal_time = next(
            record
            for record, seed in zip(self.records, self.seeds["records"])
            if seed["case"] == "equal_time"
        )
        resolved = runner.eligible_snapshot(equal_time, "num_comments", self.as_of)
        self.assertEqual([snapshot.value for snapshot in equal_time.engagement], [40, 41])
        self.assertEqual(resolved.value, 40)
        self.assertEqual(resolved, equal_time.engagement[0])

    def test_a_tie_is_broken_by_position_and_never_by_how_a_position_is_spelled(self):
        source = next(
            record
            for record, seed in zip(self.records, self.seeds["records"])
            if seed["case"] == "equal_time"
        )
        crowded = dataclasses.replace(
            source,
            engagement=tuple(
                schema.EngagementSnapshot(
                    metric_name="num_comments",
                    value=100 - index,
                    observed_at="2026-08-08T00:00:00Z",
                )
                for index in range(11)
            ),
        )
        resolved = runner.eligible_snapshot(crowded, "num_comments", self.as_of)
        self.assertEqual(resolved.value, 100)
        self.assertEqual(sorted(["r#e2", "r#e10"]), ["r#e10", "r#e2"])

    def test_most_replied_uses_its_own_declared_metric_and_never_the_other(self):
        self.assertEqual(
            self.ordered("most_replied"),
            ["changing", "stale", "future", "missing", "wrong_name", "equal_time", "untimed"],
        )

    def test_cross_source_chronology_crosses_roles_and_keeps_one_total_order(self):
        self.assertEqual(
            cases_of(
                runner.order_records(
                    self.records,
                    "cross_source_chronology",
                    self.as_of,
                    descriptors=self.descriptors,
                )
            ),
            [
                "future", "changing", "missing", "wrong_name", "stale",
                "equal_time", "hit_reddit", "hit_x", "untimed",
            ],
        )

    def test_a_metric_name_is_never_inferred_from_the_snapshot_that_carries_it(self):
        for record in self.native:
            self.assertEqual(
                runner.ordering_key(
                    record, "most_commented", self.as_of, DECLARING_DESCRIPTORS
                )[0],
                runner.MISSING,
            )
        with self.assertRaisesRegex(runner.OrderingError, "no eligible metric"):
            runner.order_records(
                self.native,
                "most_commented",
                self.as_of,
                descriptors=DECLARING_DESCRIPTORS,
            )

    def test_a_family_scoped_order_refuses_to_compare_across_families(self):
        for order in ("newest", "native_top", "most_commented", "most_replied"):
            with self.subTest(order=order):
                with self.assertRaises(runner.OrderingError):
                    runner.order_records(
                        self.records, order, self.as_of, descriptors=self.descriptors
                    )

    def test_an_order_the_contract_does_not_name_is_refused(self):
        self.assertEqual(
            runner.ORDERING_CONTRACT,
            (
                "newest", "cross_source_chronology", "native_top",
                "most_commented", "most_replied",
            ),
        )
        with self.assertRaises(runner.OrderingError):
            runner.order_records(self.native, "most_upvoted", self.as_of)

    def test_no_wall_clock_participates_and_the_replay_is_repeatable(self):
        first = self.ordered("most_commented")
        again = self.ordered("most_commented")
        self.assertEqual(first, again)
        self.assertEqual(
            sources_naming(("datetime.now", "time.time", "utcnow"), package_sources()),
            [("transport.py", "datetime.now")],
        )

    def test_the_artifacts_own_record_order_is_step_then_page_then_list(self):
        fused = fused_run()
        positions = [
            (
                [step.step_id for step in fused.artifact.steps].index(record.step_id),
                record.page_index,
                record.list_index,
            )
            for record in fused.artifact.records
        ]
        self.assertEqual(positions, sorted(positions))
