"""Lineage, grouping, and never-merge law cases."""

from .support import *  # noqa: F403

class K4HybridNeverMergesTest(unittest.TestCase):
    """Completion criterion 1: the pair stays two linked records, in both shapes."""

    def test_reddit_pair_is_linked_and_never_merged(self):
        artifact, _, _ = run_tracer(TRACER_MANIFEST)

        assert_linked_never_merged(self, artifact, REDDIT_THREAD_LOCATOR, "reddit")

    def test_x_pair_is_linked_and_never_merged(self):
        artifact, _, _ = run_tracer(TRACER_X_MANIFEST)

        assert_linked_never_merged(self, artifact, X_POST_LOCATOR, "x")

    def test_a_root_relative_redirect_wrapper_still_yields_the_target_locator(self):
        # The wrapper arrives in three shapes and `unwrap_result_url` unwrapped
        # only the two that name a host, so `/l/?uddg=` was published unchanged
        # as the canonical locator. `normalized_locator` keeps a host-less
        # string host-less, `link_discovery_hydration` matches exactly, and the
        # edge this criterion is about silently never forms — as an absence, so
        # no merge test would have caught it, on the one route it protects.
        rewritten = read_fixture("ddg_html_results.html").replace(
            'href="//duckduckgo.com/l/?uddg=', 'href="/l/?uddg='
        )
        self.assertIn('href="/l/?uddg=', rewritten)
        responses = dict(tracer_responses(), ddg_html=(200, rewritten, "text/html"))
        carrier, _ = tracer_transport(responses)

        artifact = runner.run_acquisition(schema.parse_manifest(TRACER_MANIFEST), carrier)

        assert_linked_never_merged(self, artifact, REDDIT_THREAD_LOCATOR, "reddit")

    def test_hydration_happens_even_though_a_hit_already_names_that_locator(self):
        artifact, carrier, _ = run_tracer(TRACER_MANIFEST)

        # wrong_merge_law rule 2: locator equality never authorizes reuse in
        # place of hydration, and the discovery edge is still emitted.
        self.assertEqual(
            [call.route_id for call in carrier.calls], ["ddg_html", "arctic_shift_posts_ids"]
        )
        self.assertEqual(len(artifact.edges), 1)

    def test_a_selection_that_matches_no_hit_produces_no_invented_edge(self):
        hit = {"discovery_locator": "https://www.reddit.com/r/other/comments/zzz/", "target_id": "zzz"}
        steps = [
            TRACER_MANIFEST["steps"][0],
            dict(TRACER_MANIFEST["steps"][1], selected_hits=[hit]),
        ]
        artifact, _, _ = run_tracer(dict(TRACER_MANIFEST, steps=steps))

        self.assertTrue(
            [record for record in artifact.records if record.step_id == "s2-hydrate"]
        )
        self.assertEqual(artifact.edges, ())


def gap_carriers(artifact):
    """Every record in one artifact that says its discovery went unrecorded."""

    return [
        record.record_id
        for record in artifact.records
        if DISCOVERY_NOT_RECORDED in record.loss
    ]


class LineageGapIsTypedTest(unittest.TestCase):
    """The absence beside `test_a_selection_that_matches_no_hit_produces_no_invented_edge`.

    That test pins the right half of the call: an unmatched selection invents no
    edge. This class pins the other half — the gap is *said*, because a caller
    learns of it by counting edges otherwise, and a caller that does not count
    never learns of it at all.

    The rule has a second clause, and the last two tests here are what make it
    more than a preference. Only a run that itself discovered may report a
    hydration unaccounted for. The same hydration step, against the same frozen
    locator, carries the code when this run's discovery did not produce the hit
    and stays silent when this run performed no discovery at all — because a
    `staged` hydration dispatch missed nothing: its discovery is in the artifact
    the caller froze the selection from. Stamping it there would be a false
    claim on the ordinary staged path, which is the whole reason this rule is
    written the way it is.
    """

    def test_a_selection_that_matches_no_hit_says_so_by_type(self):
        hit = {
            "discovery_locator": "https://www.reddit.com/r/other/comments/zzz/",
            "target_id": "zzz",
        }
        steps = [
            TRACER_MANIFEST["steps"][0],
            dict(TRACER_MANIFEST["steps"][1], selected_hits=[hit]),
        ]
        artifact, _, _ = run_tracer(dict(TRACER_MANIFEST, steps=steps))

        hydrated = [r for r in artifact.records if r.step_id == "s2-hydrate"]
        self.assertTrue(hydrated)
        self.assertEqual(artifact.edges, ())
        # On the record that has the gap, and on no other: the discovery hits
        # are what the hydration failed to match, not things that failed.
        self.assertEqual(gap_carriers(artifact), [r.record_id for r in hydrated])
        for record in hydrated:
            self.assertEqual(record.loss[-1], DISCOVERY_NOT_RECORDED)

    def test_a_hydration_that_matches_its_hit_says_nothing(self):
        # The type says something, so it has to be absent when that thing is
        # false. This is the same manifest as the linked-pair tests above, whose
        # one edge is exactly what makes the silence meaningful.
        artifact, _, _ = run_tracer(TRACER_MANIFEST)

        self.assertEqual(len(artifact.edges), 1)
        self.assertEqual(gap_carriers(artifact), [])

    def test_a_run_that_hydrates_nothing_says_nothing(self):
        artifact, _, _ = run_tracer(dict(TRACER_MANIFEST, steps=[TRACER_MANIFEST["steps"][0]]))

        self.assertTrue(artifact.records)
        self.assertEqual(gap_carriers(artifact), [])

    def test_a_staged_hydration_dispatch_reports_no_gap_it_could_not_have_closed(self):
        # The staged pair: discovery is one dispatch, hydration is another, and
        # the caller carries the selection between them. The second artifact
        # holds a hydration and no discovery, so it links nothing — and that is
        # `staged` working, not a gap. Compare with the first test in this
        # class: same step, same frozen locator, opposite verdict, and the only
        # difference is whether this run discovered.
        discovery = dict(TRACER_MANIFEST, steps=[TRACER_MANIFEST["steps"][0]])
        hydration = dict(
            TRACER_MANIFEST,
            manifest_id="tracer-k4-reddit-hydrate",
            steps=[dict(TRACER_MANIFEST["steps"][1], prior_step_id="")],
        )
        first, _, _ = run_tracer(discovery)
        second, _, _ = run_tracer(hydration)

        # The caller could not have frozen a selection it never discovered.
        self.assertIn(
            normalize.normalized_locator(REDDIT_THREAD_LOCATOR),
            [record.normalized_locator for record in first.records],
        )
        self.assertTrue([r for r in second.records if r.discovery_locator])
        self.assertEqual(second.edges, ())
        self.assertEqual(gap_carriers(second), [])
        self.assertEqual(gap_carriers(first), [])


class WrongMergeLawTest(unittest.TestCase):
    """Completion criterion 2: rules 1-8 over the tracer's own records."""

    def setUp(self):
        self.artifact, _, _ = run_tracer(TRACER_MANIFEST)
        self.x_artifact, _, _ = run_tracer(TRACER_X_MANIFEST)
        self.by_id = {record.record_id: record for record in self.artifact.records}

    def _group_of(self, artifact, record_id):
        for group in artifact.groups:
            if record_id in group.member_record_ids:
                return group
        raise AssertionError("record {0} belongs to no group".format(record_id))

    def test_rule_1_strong_identity_is_the_retained_triple(self):
        target = [r for r in self.artifact.records if r.representation_kind == "native"][0]

        self.assertEqual(
            normalize.strong_identity(target), ("reddit", "t3_1abc234", "post")
        )
        self.assertIsNone(normalize.strong_identity(self.by_id["s1-discover#0.0"]))

    def test_rule_1_grouping_holds_duplicates_side_by_side_without_overwriting(self):
        group = self._group_of(self.artifact, "s1-discover#0.2")

        self.assertEqual(group.member_record_ids, ("s1-discover#0.2", "s1-discover#0.3"))
        first = self.by_id["s1-discover#0.2"]
        second = self.by_id["s1-discover#0.3"]
        self.assertEqual(first.exact_content_hash, second.exact_content_hash)
        self.assertNotEqual(first.record_id, second.record_id)
        self.assertNotEqual(first.list_index, second.list_index)

    def test_rule_3_weak_key_needs_every_component(self):
        grouped = self.by_id["s1-discover#0.2"]
        snippetless = self.by_id["s1-discover#0.5"]

        self.assertEqual(len(normalize.weak_group_key(grouped)), 5)
        self.assertEqual(
            normalize.weak_group_key(grouped),
            (
                "duckduckgo",
                "index",
                grouped.normalized_locator,
                "web_hit",
                grouped.exact_content_hash,
            ),
        )
        self.assertEqual(snippetless.exact_content_hash, "")
        self.assertIsNone(normalize.weak_group_key(snippetless))
        self.assertEqual(
            self._group_of(self.artifact, snippetless.record_id).key_kind, "ungrouped"
        )

    def test_rule_4_a_reply_never_joins_its_parent_post(self):
        post = self.x_artifact.records[-2]
        reply = self.x_artifact.records[-1]

        self.assertEqual(reply.native_parent_id, post.native_item_id)
        self.assertNotIn(
            reply.record_id, self._group_of(self.x_artifact, post.record_id).member_record_ids
        )

    def test_rule_5_changed_content_at_one_locator_is_a_distinct_observation(self):
        duplicate = self.by_id["s1-discover#0.3"]
        rewritten = self.by_id["s1-discover#0.4"]

        self.assertEqual(duplicate.normalized_locator, rewritten.normalized_locator)
        self.assertNotEqual(duplicate.exact_content_hash, rewritten.exact_content_hash)
        self.assertNotIn(
            rewritten.record_id,
            self._group_of(self.artifact, duplicate.record_id).member_record_ids,
        )

    def test_rule_6_reddit_platform_identity_includes_the_fullname_prefix(self):
        target = [r for r in self.artifact.records if r.representation_kind == "native"][0]

        self.assertEqual(target.native_item_id, "t3_1abc234")
        self.assertEqual(target.native_identity_namespace, "reddit")

    def test_rule_7_no_group_spans_two_representation_kinds(self):
        for artifact in (self.artifact, self.x_artifact):
            by_id = {record.record_id: record for record in artifact.records}
            for group in artifact.groups:
                kinds = {by_id[member].representation_kind for member in group.member_record_ids}
                self.assertEqual(len(kinds), 1, "group {0} spans {1}".format(group.key, kinds))

    def test_rule_7_partitions_grouping_even_under_one_shared_strong_identity(self):
        # Built beside the tree: an index hit that wrongly claims the target's
        # own native identity. Rule 7 must still keep the two apart.
        hit = sample_record(
            record_id="hand#0.0",
            representation_kind="index",
            native_identity_namespace="reddit",
            native_item_id="t3_1abc234",
            canonical_content_kind="post",
        )
        target = sample_record(
            record_id="hand#1.0",
            representation_kind="native",
            native_identity_namespace="reddit",
            native_item_id="t3_1abc234",
            canonical_content_kind="post",
        )

        self.assertEqual(normalize.strong_identity(hit), normalize.strong_identity(target))
        groups = normalize.group_records((hit, target))
        self.assertEqual(len(groups), 2)
        for group in groups:
            self.assertEqual(len(group.member_record_ids), 1)

    def test_rule_8_a_raw_cap_counts_every_received_record(self):
        steps = [dict(TRACER_MANIFEST["steps"][0], max_items=2), TRACER_MANIFEST["steps"][1]]
        capped, _, _ = run_tracer(dict(TRACER_MANIFEST, steps=steps))

        self.assertEqual(capped.steps[0].records_received, 6)
        self.assertEqual(capped.steps[0].records_kept, 2)
        self.assertIn("recall_window_partial", capped.loss)
