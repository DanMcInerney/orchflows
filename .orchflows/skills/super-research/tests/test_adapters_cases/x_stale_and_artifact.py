from tests.test_adapters_cases.x_stamps import *  # noqa: F401,F403

class StaleIdentifierTest(unittest.TestCase):
    """Criterion 2: a rotated query id is typed, and never mistaken for the other thing.

    This is the ticket's spine. X rotates these ids on its own release
    schedule, so the day one goes stale is a day this package must say what
    happened — not return nothing, and not blame a credential it does not use.
    """

    def test_every_measured_case_is_typed_as_its_evidence_says(self):
        assert_stale_identifier_is_typed(self, "x_guest", typed_pages(x_guest))

    def test_a_stale_query_id_names_the_id_and_the_way_back_to_a_current_one(self):
        page, opener = guest_page(read_fixture("guest_stale_query_id.json"), status=404)
        warning = " ".join(page.warnings)

        self.assertEqual(page.loss, ("stale_identifier",))
        self.assertEqual(page.outcome, "failed")
        self.assertEqual(page.records, ())
        self.assertIn("TweetResultByRestId", warning)
        self.assertIn(x_guest.GUEST_QUERY_IDS["TweetResultByRestId"], warning)
        self.assertIn("import map", warning)
        # And it cost one call: a stale id is an answer, not a reason to look
        # somewhere else.
        self.assertEqual(len(opener.opened), 1)

    def test_the_one_legitimate_empty_says_why_it_is_empty(self):
        # A result the graph holds but has no profile in it is a real empty —
        # a suspended account, not a rotated id and not a page that moved. It
        # still may not be silent: an empty nobody explained is the shape every
        # other case here exists to keep this adapter out of.
        page, _ = guest_page(
            read_fixture("guest_user_unavailable.json"), target_id="user:simonw"
        )

        self.assertEqual(page.outcome, "empty")
        self.assertEqual(page.loss, ())
        self.assertEqual(page.records, ())
        self.assertIn("UserUnavailable", " ".join(page.warnings))
        self.assertIn("UserByScreenName", " ".join(page.warnings))

    def test_a_refusal_is_the_platforms_and_never_a_rotated_id(self):
        page, _ = guest_page(read_fixture("guest_blocked_operation.json"), status=403)

        self.assertEqual(page.loss, ("auth_required",))
        self.assertNotIn("stale_identifier", page.loss)

    def test_no_x_route_returns_auth_required_with_an_empty_credential_store(self):
        # Criterion 1's other half. Both routes are keyless: the only way
        # `auth_required` can appear is the origin's own 401 or 403, never the
        # absence of something this package was supposed to have.
        for module, body, content_type in (
            (x_syndication, read_fixture("syndication_timeline.html"), "text/html"),
            (x_guest, read_fixture("guest_tweet_result.json"), "application/json"),
        ):
            with self.subTest(adapter=module.DESCRIPTOR.adapter_id):
                page, _ = adapter_page(
                    module,
                    200,
                    body,
                    content_type=content_type,
                    request=adapters.AdapterRequest(
                        step_id="s1-x", target_ids=("tweet:1799990000000000001",)
                    ),
                )

                self.assertNotIn("auth_required", page.loss)
                self.assertEqual(page.outcome, "ok")
                self.assertTrue(transport.route_admissions()[module.DESCRIPTOR.route_id])


class StaleIdentifierOracleCanFailTest(unittest.TestCase):
    """Criterion 5: the oracle above rejects a wrong result, in either direction.

    Both adapters here are written beside the tree and loaded by path. Each is
    ``x_guest`` with exactly one status branch replaced, which is what makes a
    rejection attributable to that branch and to nothing else. Nothing in the
    package produces them and nothing under test is mutated to obtain them.
    """

    def _assert_oracle_rejects(self, name, reason):
        wrong = load_adapter_fixture(name)

        with self.assertRaises(AssertionError) as caught:
            assert_stale_identifier_is_typed(self, name, typed_pages(wrong))

        self.assertIn(reason, str(caught.exception))

    def test_an_adapter_that_answers_a_stale_id_with_nothing_fails_the_oracle(self):
        # Row 5's named case: the 404 comes back as a result set with no rows
        # in it, so a caller reads "this account has no posts" off a page the
        # origin never served.
        self._assert_oracle_rejects(
            "stale_id_as_empty_adapter",
            "a stale query id was recorded as an empty success",
        )

    def test_an_adapter_that_calls_a_stale_id_a_credential_problem_fails_the_oracle(self):
        self._assert_oracle_rejects(
            "stale_id_as_auth_required_adapter",
            "a stale query id was recorded as an authorization failure",
        )

    def test_an_adapter_that_calls_every_refusal_a_stale_id_fails_the_oracle(self):
        # The opposite error. Without this side the oracle could be satisfied
        # by typing everything stale, which would send a reader after a bundle
        # walk over an operation the origin simply will not serve a guest.
        self._assert_oracle_rejects(
            "blocked_as_stale_adapter",
            "a response naming no stale identifier was recorded as one",
        )

    def test_the_same_oracle_passes_on_the_shipped_adapter(self):
        assert_stale_identifier_is_typed(self, "x_guest", typed_pages(x_guest))


class OneCallOnePageTest(unittest.TestCase):
    """Criterion 4: one bounded call in, exactly one page out, whatever comes back.

    An adapter that retried, paged, or reached for a second route on a bad
    answer would spend an origin's budget without anyone having asked, and the
    ledger would stop describing the work. The proof is the carrier's own
    attempt log, over every case in the table and every failure shape either
    route can answer with.
    """

    def _every_case(self):
        for row in stale_identifier_cases():
            yield (
                "x_guest/" + row["case_name"],
                x_guest,
                row["status"],
                read_fixture(row["body_fixture"]),
                "application/json",
                adapters.AdapterRequest(step_id="s1-x", target_ids=(row["target_id"],)),
            )
        syndication = (
            ("timeline", 200, "syndication_timeline.html"),
            ("no_next_data", 200, "syndication_without_next_data.html"),
            ("drifted", 200, "syndication_drifted_container.html"),
        )
        for name, status, fixture in syndication:
            yield (
                "x_syndication/" + name,
                x_syndication,
                status,
                read_fixture(fixture),
                "text/html",
                PROFILE_REQUEST,
            )
        for status in (404, 500, 503):
            yield (
                "x_syndication/http_{0}".format(status),
                x_syndication,
                status,
                "<html><body>no</body></html>",
                "text/html",
                PROFILE_REQUEST,
            )

    def test_every_answer_costs_one_call_on_the_adapters_own_route(self):
        for name, module, status, body, content_type, request in self._every_case():
            with self.subTest(case=name):
                page, opener = adapter_page(
                    module, status, body, content_type=content_type, request=request
                )

                self.assertEqual(len(opener.opened), 1)
                self.assertEqual(
                    [call.route_id for call in opener.opened], [module.DESCRIPTOR.route_id]
                )
                self.assertEqual(page.route_id, module.DESCRIPTOR.route_id)
                self.assertIsInstance(page, adapters.NativePage)

    def test_a_cursor_is_surfaced_for_the_core_and_never_followed(self):
        page, opener = guest_page(
            read_fixture("guest_user_tweets.json"), target_id="user_tweets:12497"
        )

        self.assertTrue(page.cursor_out)
        self.assertEqual(len(opener.opened), 1)

    def test_a_cursor_the_core_hands_back_is_spent_on_the_next_single_call(self):
        clock = helpers.FakeClock()
        carrier, opener = helpers.offline_transport(
            clock,
            {
                transport.X_GUEST_GRAPHQL_ROUTE: (
                    200,
                    read_fixture("guest_user_tweets.json"),
                    "application/json",
                )
            },
        )

        x_guest.fetch_native_page(
            carrier,
            adapters.AdapterRequest(
                step_id="s1-x", target_ids=("user_tweets:12497",), cursor="DAABCgABGel3"
            ),
        )

        self.assertEqual(len(opener.opened), 1)
        self.assertIn("DAABCgABGel3", urllib.parse.unquote(opener.opened[0].url))

    def test_neither_adapter_names_another_adapter_or_the_cores_dispatch(self):
        # "Never calls another adapter" as a structure. Each module speaks to
        # the transport seam and the shared protocol, and to nothing else, so
        # no adapter can quietly become a fallback for a route it does not own.
        for module_name, own_id in (
            ("x_guest.py", "x_guest"),
            ("x_syndication.py", "x_syndication"),
        ):
            with self.subTest(module=module_name):
                self.assertEqual(adapters_named(ADAPTER_DIR / module_name, own_id), [])
                self.assertNotIn(
                    "call_adapter", adapter_owner_source(ADAPTER_DIR / module_name)
                )

    def test_the_cross_adapter_scan_can_fail(self):
        # Which is what makes the case above worth anything: a module beside
        # the tree that does reach another adapter is named by the same scan.
        self.assertEqual(
            adapters_named(FIXTURE_DIR / "stale_id_as_empty_adapter.py", "stale_id_as_empty"),
            ["x_guest"],
        )

    def test_neither_adapter_reads_a_file_opens_a_socket_or_waits(self):
        cases = [
            (x_syndication, read_fixture("syndication_timeline.html"), "text/html", PROFILE_REQUEST),
            (
                x_guest,
                read_fixture("guest_user_tweets.json"),
                "application/json",
                adapters.AdapterRequest(step_id="s1-x", target_ids=("user_tweets:12497",)),
            ),
        ]

        for module, body, content_type, request in cases:
            with self.subTest(adapter=module.DESCRIPTOR.adapter_id):
                clock = helpers.FakeClock()
                carrier, _ = helpers.offline_transport(
                    clock, {module.DESCRIPTOR.route_id: (200, body, content_type)}
                )

                with helpers.forbid_io():
                    with helpers.forbid_sleep():
                        page = module.fetch_native_page(carrier, request)

                self.assertEqual(page.outcome, "ok")

    def test_nothing_in_the_package_can_reach_a_wrong_x_adapter(self):
        wrong = (
            "stale_id_as_empty_adapter",
            "stale_id_as_auth_required_adapter",
            "blocked_as_stale_adapter",
        )
        named = [
            path.name
            for path in PACKAGE_DIR.rglob("*.py")
            for name in wrong
            if name in path.read_text(encoding="utf-8")
        ]

        self.assertEqual(named, [])


class RouteTtlTest(unittest.TestCase):
    """How long each X route's answer may stand in for a fresh read.

    A TTL belongs to a route's own volatility, and `cache.py`'s default is
    deliberately short — a route nobody has measured is not one to trust for
    long. Both of these were measured, so both declare their own, and the
    proof is behavioral: a re-read ninety seconds later, which the default
    would have sent back to the origin.
    """

    def setUp(self):
        # The guest route declares an activation route, and a governor mints
        # one per process. Cleared so this suite's reads are the same reads
        # whatever ran before it.
        transport.GUEST_TOKENS.clear()
        self.addCleanup(transport.GUEST_TOKENS.clear)

    def _paced(self, clock, route_id, body, content_type):
        carrier, opener = helpers.offline_transport(
            clock, {route_id: (200, body, content_type)}
        )
        governor = runner.RateGovernor(
            carrier,
            run_cache=cache.RunCache(clock=clock.monotonic),
            clock=clock.monotonic,
            sleep=clock.sleep,
        )
        return governor, opener

    def _origin_reads(self, opener, route_id):
        """How many times the origin was reached on one route.

        Counted per route rather than over every open, because the guest route
        spends an activation as well as the read it authorizes and a TTL is a
        claim about one route's own answers.
        """

        return [request.route_id for request in opener.opened].count(route_id)

    def test_a_timeline_reread_inside_the_window_is_answered_from_memory(self):
        clock = helpers.FakeClock()
        governor, opener = self._paced(
            clock,
            transport.X_SYNDICATION_TIMELINE_ROUTE,
            read_fixture("syndication_timeline.html"),
            "text/html",
        )

        first = x_syndication.fetch_native_page(governor, PROFILE_REQUEST)
        clock.advance(90)
        second = x_syndication.fetch_native_page(governor, PROFILE_REQUEST)

        self.assertEqual(len(opener.opened), 1)
        self.assertNotIn(cache.CACHE_HIT, first.loss)
        self.assertIn(cache.CACHE_HIT, second.loss)
        # The mark moves, the moment does not: a served page still states when
        # the origin was really read, which is what makes the saving free
        # rather than a quiet loss of freshness.
        self.assertEqual(second.observed_at, first.observed_at)
        self.assertEqual(len(second.records), 100)

    def test_the_route_serving_the_most_volatile_thing_holds_it_for_the_least_time(self):
        # One TTL per route, and the guest route serves three operations at
        # once, so it takes the volatility of the most volatile of them — a
        # tweet's counts — rather than the least. It is also the cheap read:
        # 0.5 s against 2.5 s and 378 KB, so holding an answer longer buys
        # less here than anywhere else on X.
        clock = helpers.FakeClock()
        governor, opener = self._paced(
            clock,
            transport.X_GUEST_GRAPHQL_ROUTE,
            read_fixture("guest_tweet_result.json"),
            "application/json",
        )
        request = adapters.AdapterRequest(
            step_id="s1-x", target_ids=("tweet:1799990000000000001",)
        )

        x_guest.fetch_native_page(governor, request)
        clock.advance(90)
        held = x_guest.fetch_native_page(governor, request)
        clock.advance(90)
        expired = x_guest.fetch_native_page(governor, request)

        self.assertIn(cache.CACHE_HIT, held.loss)
        self.assertNotIn(cache.CACHE_HIT, expired.loss)
        self.assertEqual(self._origin_reads(opener, transport.X_GUEST_GRAPHQL_ROUTE), 2)
        # And the activation authorizing them is one, not one per read: three
        # adapter calls, two origin reads, one mint.
        self.assertEqual(self._origin_reads(opener, transport.X_GUEST_ACTIVATE_ROUTE), 1)
        self.assertLess(
            cache.ttl_seconds(transport.X_GUEST_GRAPHQL_ROUTE),
            cache.ttl_seconds(transport.X_SYNDICATION_TIMELINE_ROUTE),
        )


def x_manifest():
    """One dispatch reading the same author through both X routes."""

    return schema.AcquisitionManifest(
        manifest_id="m-x",
        mode="staged",
        as_of="2026-08-10T09:00:00Z",
        steps=(
            schema.AcquisitionStep(
                step_id="s1-timeline",
                kind="hydration",
                adapter_id="x_syndication",
                selected_hits=(
                    schema.SelectedHit(
                        discovery_locator="https://x.com/simonw", target_id="simonw"
                    ),
                ),
                max_items=200,
            ),
            schema.AcquisitionStep(
                step_id="s2-tweet",
                kind="hydration",
                adapter_id="x_guest",
                selected_hits=(
                    schema.SelectedHit(
                        discovery_locator="https://x.com/simonw",
                        target_id="tweet:1799990000000000001",
                    ),
                ),
                max_items=1,
            ),
        ),
    )


class ArtifactSeamTest(unittest.TestCase):
    """The widest seam: the record a caller keeps, after normalize has run.

    Every test above reads a ``NativePage``, which is an intermediate value.
    "X reaches its measured capability" is a claim about the artifact, so it
    is closed here — including the part where one tweet observed twice, at two
    access classes, stays two records.
    """

    def setUp(self):
        clock = helpers.FakeClock()
        carrier, self.opener = helpers.offline_transport(
            clock,
            {
                transport.X_SYNDICATION_TIMELINE_ROUTE: (
                    200,
                    read_fixture("syndication_timeline.html"),
                    "text/html",
                ),
                transport.X_GUEST_GRAPHQL_ROUTE: (
                    200,
                    read_fixture("guest_tweet_result.json"),
                    "application/json",
                ),
            },
        )
        self.artifact = runner.run_acquisition(x_manifest(), carrier, clock=clock.monotonic)

    def test_the_artifact_holds_every_entry_both_routes_returned(self):
        self.assertEqual(self.artifact.outcome, "ok")
        self.assertEqual(self.artifact.loss, ())
        self.assertEqual(len(self.artifact.records), 101)
        self.assertEqual([step.records_kept for step in self.artifact.steps], [100, 1])
        self.assertEqual(len(self.opener.opened), 2)

    def test_a_record_keeps_the_platforms_own_counts_at_the_moment_they_were_read(self):
        record = self.artifact.records[0]
        snapshots = {snapshot.metric_name: snapshot for snapshot in record.engagement}

        self.assertEqual(sorted(snapshots), sorted(SYNDICATION_METRICS))
        self.assertEqual(snapshots["favorite_count"].value, 412)
        self.assertEqual(snapshots["favorite_count"].observed_at, record.observed_at)
        # The platform's own page, so its times are authoritative rather than
        # reported: nothing here is an archive speaking for X.
        self.assertEqual(record.time_confidence, "authoritative")
        self.assertEqual(record.access_class, "K2")
        self.assertEqual(record.usable_basis_time, "2026-08-09T07:00:00Z")

    def test_one_tweet_seen_at_two_access_classes_is_two_records_held_together(self):
        # wrong_merge_law rule 1: the same native identity observed twice is
        # one group of two, never one record. The K1 read and the K2 read
        # disagree about nothing here, and they would still not be folded if
        # they did.
        shared = "1799990000000000001"
        seen = [record for record in self.artifact.records if record.native_item_id == shared]
        groups = [
            group
            for group in self.artifact.groups
            if len(group.member_record_ids) > 1
        ]

        self.assertEqual([record.access_class for record in seen], ["K2", "K1"])
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0].key_kind, "strong")
        self.assertEqual(
            sorted(groups[0].member_record_ids), sorted(record.record_id for record in seen)
        )


