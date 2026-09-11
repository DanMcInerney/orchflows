from tests.test_adapters import *  # noqa: F401,F403

class XRouteConstantTest(unittest.TestCase):
    """Both X routes name a path the evidence measured, owned by transport."""

    def test_the_syndication_route_spends_the_handle_as_a_path_segment(self):
        request = transport.build_transport_request(
            transport.X_SYNDICATION_TIMELINE_ROUTE, {"screen_name": "simonw"}
        )

        # The 2026-08-10 probes (X): syndication.twitter.com/srv/timeline-profile/
        # screen-name/<u> returned 200 with 100 timeline entries.
        self.assertEqual(
            request.url,
            "https://syndication.twitter.com/srv/timeline-profile/screen-name/simonw",
        )
        self.assertEqual(request.method, "GET")

    def test_the_guest_graphql_route_spends_the_query_id_and_operation_as_segments(self):
        request = transport.build_transport_request(
            transport.X_GUEST_GRAPHQL_ROUTE,
            {
                "query_id": GUEST_QUERY_ID,
                "operation_name": "UserTweets",
                "variables": '{"userId":"44196397"}',
            },
        )

        # A rotating query id lives in the path, which is why a stale one is a
        # 404 rather than an error inside a 200 body.
        self.assertEqual(
            request.url,
            "https://api.twitter.com/graphql/"
            + GUEST_QUERY_ID
            + "/UserTweets?variables=%7B%22userId%22%3A%2244196397%22%7D",
        )
        self.assertEqual(request.method, "GET")

    def test_a_route_whose_path_segments_are_unsupplied_still_builds_its_base_url(self):
        request = transport.build_transport_request(transport.X_GUEST_GRAPHQL_ROUTE)

        self.assertEqual(request.url, "https://api.twitter.com/graphql")

    def test_both_x_routes_are_keyless_and_read_only(self):
        for route_id in (
            transport.X_SYNDICATION_TIMELINE_ROUTE,
            transport.X_GUEST_GRAPHQL_ROUTE,
        ):
            with self.subTest(route=route_id):
                route = transport.route_constant(route_id)

                self.assertTrue(transport.route_admissions()[route_id])
                self.assertEqual(transport.admitted_methods(route_id), transport.READ_METHODS)
                self.assertEqual(route.operator_identity, "x")

    def test_the_guest_route_carries_the_public_bearer_and_the_syndication_route_none(self):
        self.assertIs(
            transport.route_credential(transport.X_GUEST_GRAPHQL_ROUTE),
            transport.PUBLIC_CLIENT_CREDENTIALS[transport.X_GUEST_PUBLIC_BEARER],
        )
        self.assertIsNone(
            transport.route_credential(transport.X_SYNDICATION_TIMELINE_ROUTE)
        )


class GuestTokenAttachTest(unittest.TestCase):
    """The attach lives here, at send time, so an adapter stays a one-read shape.

    A guest token is a credential the origin issues rather than one the vendor
    publishes, and it goes on the wire exactly where the published bearer goes
    — at send time, by the opener — and never earlier. That keeps one adapter
    call at one ``carrier.fetch``, and keeps the token off every value the run
    keeps.

    The *mint* is not here and is not the opener's: it is one paced call the
    governor makes, and `test_transport.GuestMintIsOnePacedRecordedCallTest`
    owns it. What this suite pins is the other half — what the wire carries
    when the run holds a token, and what it carries when the run holds none.
    """

    def setUp(self):
        transport.GUEST_TOKENS.clear()
        self.addCleanup(transport.GUEST_TOKENS.clear)

    def _sent(self, requests, answers=()):
        opener = RoutingUrlopen(answers)
        results = []
        with mock.patch.object(urllib.request, "urlopen", opener):
            for request in requests:
                results.append(transport.urlopen_response(request))
        return results, opener

    def test_a_read_carries_the_token_the_run_is_holding(self):
        transport.GUEST_TOKENS.remember(
            transport.X_GUEST_ACTIVATE_ROUTE, MINTED_GUEST_TOKEN
        )

        _, opener = self._sent([guest_read_request()])

        # One request, not two: the activation that produced this token was the
        # governor's, and by send time it has already happened.
        self.assertEqual(len(opener.requests), 1)
        self.assertIn("/graphql/", opener.urls()[0])
        self.assertEqual(
            opener.headers_of(0)[transport.GUEST_TOKEN_HEADER], MINTED_GUEST_TOKEN
        )

    def test_the_one_token_is_spent_on_every_later_read(self):
        transport.GUEST_TOKENS.remember(
            transport.X_GUEST_ACTIVATE_ROUTE, MINTED_GUEST_TOKEN
        )

        _, opener = self._sent([guest_read_request(), guest_read_request()])

        self.assertEqual(len(opener.requests), 2)
        self.assertEqual(
            [opener.headers_of(index)[transport.GUEST_TOKEN_HEADER] for index in (0, 1)],
            [MINTED_GUEST_TOKEN, MINTED_GUEST_TOKEN],
        )

    def test_a_keyless_route_never_carries_one(self):
        transport.GUEST_TOKENS.remember(
            transport.X_GUEST_ACTIVATE_ROUTE, MINTED_GUEST_TOKEN
        )

        _, opener = self._sent(
            [transport.build_transport_request(transport.DDG_HTML_ROUTE, {"q": "probe"})]
        )

        self.assertEqual(len(opener.requests), 1)
        self.assertNotIn(transport.GUEST_TOKEN_HEADER, opener.headers_of(0))

    def test_a_run_holding_no_token_sends_the_read_unauthorized(self):
        # A process that never minted — because nothing paced it, or because
        # the origin refused the activation — still sends the read, once, with
        # no token on it. The origin's own 401 or 403 is then what the adapter
        # records as the platform's refusal. Inventing a token, or turning a
        # failed mint into a retry, are the two wrong answers.
        results, opener = self._sent(
            [guest_read_request()], [("/graphql/", 401, "unauthorized", "application/json")]
        )

        self.assertEqual(transport.GUEST_TOKENS._tokens, {})
        self.assertEqual(len(opener.requests), 1)
        self.assertNotIn(transport.GUEST_TOKEN_HEADER, opener.headers_of(0))
        self.assertEqual(results[0][0], 401)

    def test_the_token_the_run_holds_reaches_no_request_the_run_records(self):
        transport.GUEST_TOKENS.remember(
            transport.X_GUEST_ACTIVATE_ROUTE, MINTED_GUEST_TOKEN
        )
        opener = RoutingUrlopen([])
        carrier = transport.Transport(now=lambda: "2026-08-10T09:00:00Z")

        with mock.patch.object(urllib.request, "urlopen", opener):
            response = carrier.fetch(guest_read_request())

        # It is on the wire and nowhere else: the request the run recorded and
        # the response it kept both have to be free of it.
        self.assertIn(
            transport.GUEST_TOKEN_HEADER, opener.headers_of(0)
        )
        self.assertNotIn(MINTED_GUEST_TOKEN, repr(carrier.calls))
        self.assertNotIn(MINTED_GUEST_TOKEN, repr(response))
        self.assertEqual(len(carrier.calls), 1)


class SyndicationTimelineTest(unittest.TestCase):
    """Criterion 1, K2 half: 100 entries, each carrying its whole roster row."""

    def setUp(self):
        self.page, self.opener = adapter_page(
            x_syndication, 200, read_fixture("syndication_timeline.html")
        )

    def test_one_page_carries_the_hundred_entries_the_evidence_measured(self):
        self.assertEqual(self.page.outcome, "ok")
        self.assertEqual(self.page.loss, ())
        self.assertEqual(len(self.page.records), 100)
        self.assertEqual(len(self.opener.opened), 1)

    def test_every_entry_carries_every_field_its_roster_row_names(self):
        for record in self.page.records:
            with self.subTest(item=record.native_item_id):
                carried = dict(record.engagement)
                carried["full_text"] = record.body
                carried["created_at"] = record.published_at
                carried["conversation_id_str"] = record.native_parent_id

                self.assertEqual(sorted(carried), sorted(SYNDICATION_ROSTER_FIELDS))
                for name in SYNDICATION_ROSTER_FIELDS:
                    self.assertTrue(carried[name], name)
                for name in SYNDICATION_METRICS:
                    self.assertIsInstance(carried[name], int)
                self.assertEqual(record.loss, ())

    def test_an_entry_missing_a_roster_field_arrives_marked_and_never_zero_filled(self):
        page, _ = adapter_page(
            x_syndication, 200, read_fixture("syndication_partial_entry.html")
        )
        complete, partial = page.records

        self.assertEqual(page.outcome, "ok")
        self.assertEqual(complete.loss, ())
        self.assertEqual(partial.loss, ("field_omitted",))
        # Marked, and absent rather than invented: no quote count at all, and
        # no time, instead of a zero and a moment nobody observed.
        self.assertNotIn("quote_count", dict(partial.engagement))
        self.assertEqual(partial.published_at, "")
        self.assertEqual(dict(partial.engagement)["favorite_count"], 96)

    def test_an_entry_that_is_not_a_post_is_not_read_as_one(self):
        page, _ = adapter_page(
            x_syndication, 200, read_fixture("syndication_partial_entry.html")
        )

        self.assertEqual(len(page.records), 2)
        self.assertEqual(
            [record.canonical_content_kind for record in page.records], ["post", "post"]
        )

    def test_a_record_names_the_tweet_its_author_and_its_conversation(self):
        first = self.page.records[0]
        reply = self.page.records[2]

        self.assertEqual(first.canonical_content_kind, "post")
        self.assertEqual(first.native_item_id, "1799990000000000001")
        self.assertEqual(first.author, "simonw")
        self.assertEqual(
            first.canonical_locator, "https://x.com/simonw/status/1799990000000000001"
        )
        self.assertEqual(first.published_at, "2026-08-09T07:00:00Z")
        self.assertEqual(first.native_position, 0)
        # X reports the thread a post belongs to as conversation_id_str: its own
        # id for a root, the root it answers for a reply. Both are the
        # platform's own statement, so both are carried as reported.
        self.assertEqual(first.native_parent_id, first.native_item_id)
        self.assertNotEqual(reply.native_parent_id, reply.native_item_id)

    def test_the_page_speaks_for_x_at_the_class_the_ladder_gives_it(self):
        self.assertEqual(self.page.adapter_id, "x_syndication")
        self.assertEqual(self.page.platform, "x")
        self.assertEqual(self.page.native_identity_namespace, "x")
        self.assertEqual(self.page.access_class, "K2")
        self.assertEqual(self.page.representation_kind, "native")
        self.assertEqual(self.page.route_id, transport.X_SYNDICATION_TIMELINE_ROUTE)

    def test_a_page_that_embeds_no_structured_data_is_drift_and_not_an_empty_profile(self):
        page, _ = adapter_page(
            x_syndication, 200, read_fixture("syndication_without_next_data.html")
        )

        self.assertEqual(page.outcome, "failed")
        self.assertEqual(page.loss, ("schema_drift",))
        self.assertEqual(page.records, ())

    def test_a_timeline_that_moved_is_drift_and_not_an_empty_profile(self):
        page, _ = adapter_page(
            x_syndication, 200, read_fixture("syndication_drifted_container.html")
        )

        self.assertEqual(page.outcome, "failed")
        self.assertEqual(page.loss, ("schema_drift",))
        self.assertEqual(page.records, ())

    def test_the_origins_own_failure_stays_the_origins(self):
        page, _ = adapter_page(x_syndication, 404, "<html><body>Not found</body></html>")

        self.assertEqual(page.outcome, "failed")
        self.assertEqual(page.loss, ("http_status",))
        self.assertIn("404", " ".join(page.warnings))

    def test_the_handle_is_read_from_the_target_or_from_the_query(self):
        for request in (
            adapters.AdapterRequest(step_id="s1-x", target_ids=("@simonw",)),
            adapters.AdapterRequest(step_id="s1-x", query="simonw"),
        ):
            with self.subTest(request=request):
                _, opener = adapter_page(
                    x_syndication,
                    200,
                    read_fixture("syndication_timeline.html"),
                    request=request,
                )

                self.assertTrue(opener.opened[0].url.endswith("/simonw"), opener.opened[0].url)


# A spelling `route_instant_to_utc_iso` returns nothing for. It is this test's
# own construction and not a reading of the origin: what the route actually
# sends was unmeasured when this row was written, and guessing it here is the
# defect below one spelling out. The property does not depend on which
# unreadable spelling it is, so the test asserts the rejection before it
# asserts anything else.
