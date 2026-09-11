from tests.test_adapters_cases.x_routes import *  # noqa: F401,F403
from tests.test_adapters import _next_data

UNREADABLE_SYNDICATION_INSTANT = "9 Aug 2026 07:00 GMT"


def syndication_entry(created_at, item_id="1799990000000000001"):
    """One whole roster row off this route, with only its instant varying.

    ``created_at=None`` omits the key, which is the shape the origin not
    sending it has. Every other field its roster row names is present, so a
    loss on the record can only be about the instant.
    """

    tweet = {
        "id_str": item_id,
        "conversation_id_str": item_id,
        "full_text": "Ran the same eleven prompts through the new local build this morning.",
        "favorite_count": 412,
        "retweet_count": 57,
        "reply_count": 23,
        "quote_count": 4,
        "lang": "en",
        "user": {"screen_name": "simonw", "name": "Simon Willison", "followers_count": 61234},
    }
    if created_at is not None:
        tweet["created_at"] = created_at
    return {"type": "tweet", "entry_id": "tweet-" + item_id, "content": {"tweet": tweet}}


def syndication_record(created_at):
    """The one record this route's parser makes of one entry carrying that instant."""

    page, _ = adapter_page(x_syndication, 200, _next_data([syndication_entry(created_at)]))
    return page.records[0]


class SyndicationUnreadableInstantIsTypedTest(unittest.TestCase):
    """`D1a`: an instant this package cannot read is a typed loss, never a bare empty field.

    Measured, not supposed. The first live read of this route
    (`liveness.md`, read 5) answered `200` with 100 entries, `loss none`, and
    `published_at` on **none** of them. `field_omitted` is computed against
    `tweet.get(name) is None` over the payload, so `loss none` is itself the
    proof that `created_at` was present and non-`None` on all 100: a value the
    origin sent became an empty field, and nothing said so.

    That is a typed failure arriving as an empty success at field level, which
    is the one shape this package refuses — and it is what made the wrong
    format string silent for ten tickets and a thousand offline tests. The row
    stands on its own: it is right whatever spelling the origin turns out to
    use, because it is about the parser returning nothing rather than about
    what it returns nothing for.

    `field_omitted` is the code because it is the one this package already
    attaches to exactly this fact. `instagram_public._missing` and
    `github_rest._missing` both run over the row **after** conversion, so an
    instant they cannot read is `field_omitted` there today; `x_syndication`
    tested the payload instead of the record, which is the whole of the
    difference. What the code does not do is separate "the origin omitted it"
    from "the origin sent a spelling this package cannot read" — that
    distinction would need a code the vocabulary does not have, which is the
    caller's ruling and not this ticket's.
    """

    def test_the_parser_rejects_the_spelling_these_rows_stand_on(self):
        # The premise, asserted rather than assumed: a parser that later learns
        # to read this value reddens here instead of leaving the rows below
        # passing on a premise that stopped holding.
        self.assertEqual(
            x_syndication.route_instant_to_utc_iso(UNREADABLE_SYNDICATION_INSTANT), ""
        )

    def test_an_instant_the_parser_cannot_read_is_typed_and_not_a_bare_empty_field(self):
        record = syndication_record(UNREADABLE_SYNDICATION_INSTANT)

        self.assertEqual(record.published_at, "")
        self.assertEqual(record.loss, ("field_omitted",))

    def test_an_instant_the_origin_sent_empty_is_typed_the_same_way(self):
        # The other shape `liveness.md` read 5 still admitted: an empty string
        # is not `None`, so the payload-side test passed it through untyped too.
        record = syndication_record("")

        self.assertEqual(record.published_at, "")
        self.assertEqual(record.loss, ("field_omitted",))

    def test_an_instant_the_origin_never_sent_stays_the_omission_it_always_was(self):
        record = syndication_record(None)

        self.assertEqual(record.published_at, "")
        self.assertEqual(record.loss, ("field_omitted",))

    def test_an_instant_the_parser_reads_carries_no_loss_at_all(self):
        # The half that keeps the typing honest: typing every instant is easy,
        # typing only the unreadable ones is the property.
        record = syndication_record("2026-08-09T07:00:00.000Z")

        self.assertEqual(record.published_at, "2026-08-09T07:00:00Z")
        self.assertEqual(record.loss, ())


# Measured 2026-08-12 on the one read this ticket was authorized to make
# (`liveness.md`, "The sixteenth request"): the exact bytes this route sent as
# `created_at` for entry 1944260043001737216 of `simonw`'s timeline. Copied out
# of that transcript, not reconstructed from a description of it — the whole
# reason the read was spent is that a spelling nobody had seen is what produced
# `D1`.
CAPTURED_SYNDICATION_INSTANT = "Sun Jul 13 04:58:11 +0000 2025"


class SyndicationReadsTheStampTheRouteSendsTest(unittest.TestCase):
    """`D1`: the format string, against the spelling the origin was measured sending.

    The route sends `%a %b %d %H:%M:%S %z %Y` and this module was written for
    `%Y-%m-%dT%H:%M:%S`, so `route_instant_to_utc_iso` returned nothing for
    every entry of every live read — 100 of 100 on `liveness.md` read 5, and
    100 of 100 again on the capture read, where the empty result was at last
    typed. One captured value licenses one spelling and no more, which is why
    the unreadable-instant rows above are the load-bearing half: a second
    spelling this parser has never seen announces itself as a typed loss rather
    than as a timeline with no times in it.
    """

    def test_the_captured_literal_parses_to_the_instant_it_states(self):
        self.assertEqual(
            x_syndication.route_instant_to_utc_iso(CAPTURED_SYNDICATION_INSTANT),
            "2025-07-13T04:58:11Z",
        )

    def test_a_record_carrying_the_captured_literal_carries_its_whole_roster_row(self):
        record = syndication_record(CAPTURED_SYNDICATION_INSTANT)

        self.assertEqual(record.published_at, "2025-07-13T04:58:11Z")
        self.assertEqual(record.loss, ())

    def test_the_stamp_the_offline_corpus_is_written_in_is_still_read(self):
        # No live entry has ever been seen in this spelling: it is the one this
        # module was written against and the one every fixture under
        # `fixtures/x/` carries. It is kept because dropping it would redden a
        # corpus this ticket may not rewrite, and that retention is a statement
        # for the caller rather than a measurement of the route.
        self.assertEqual(
            x_syndication.route_instant_to_utc_iso("2026-08-09T07:00:00.000Z"),
            "2026-08-09T07:00:00Z",
        )

    def test_an_offset_is_converted_and_never_relabelled(self):
        # A property of the parser, not a measurement of the route: every one
        # of the 100 entries measured carried `+0000`. The stamp states an
        # offset, so reading one and then stamping the result `Z` unconverted
        # would move the instant by the offset and say nothing about it.
        self.assertEqual(
            x_syndication.route_instant_to_utc_iso("Sun Jul 13 04:58:11 +0200 2025"),
            "2025-07-13T02:58:11Z",
        )

    def test_a_process_locale_does_not_decide_whether_this_route_can_be_read(self):
        # `%a` and `%b` read their names out of `LC_TIME`, so a `strptime`
        # spelled that way returns nothing for X's own English stamp under any
        # non-English locale — every record on the page losing its time, for a
        # reason that has nothing to do with the origin. The ordering contract
        # already refuses to let a locale decide an order; it may not decide a
        # time either.
        previous = locale.setlocale(locale.LC_TIME)
        try:
            try:
                locale.setlocale(locale.LC_TIME, "de_DE.UTF-8")
            except locale.Error:
                self.skipTest("no non-English LC_TIME available on this host")
            self.assertEqual(
                x_syndication.route_instant_to_utc_iso(CAPTURED_SYNDICATION_INSTANT),
                "2025-07-13T04:58:11Z",
            )
        finally:
            locale.setlocale(locale.LC_TIME, previous)


class SyndicationDescriptorTest(unittest.TestCase):
    """The descriptor T04's seam reads: measured ceiling, class, declared metric."""

    def test_the_route_is_paced_by_the_interval_the_evidence_measured(self):
        # The 2026-08-10 probes (X): 2.5 s per request. No refusal was observed on
        # this route, so burst and cooldown keep the conservative defaults
        # rather than a number nobody measured.
        descriptor = x_syndication.DESCRIPTOR

        self.assertEqual(descriptor.min_interval_ms, 2500)
        self.assertEqual(descriptor.burst, adapters.DEFAULT_BURST)
        self.assertEqual(descriptor.cooldown_ms, adapters.DEFAULT_COOLDOWN_MS)
        self.assertEqual(
            runner.route_budgets()[transport.X_SYNDICATION_TIMELINE_ROUTE],
            runner.RouteBudget(min_interval_ms=2500, burst=1, cooldown_ms=60000),
        )

    def test_it_declares_the_reply_metric_it_reports_and_no_comment_metric(self):
        # X reports one metric for replies and none named for comments.
        # Declaring the reply count under both names would make two of the five
        # named views silently identical on a number the platform reported once.
        self.assertEqual(x_syndication.DESCRIPTOR.reply_count_metric, "reply_count")
        self.assertEqual(x_syndication.DESCRIPTOR.comment_count_metric, "")

    def test_the_core_can_reach_it_by_both_of_its_literal_branches(self):
        self.assertIn("x_syndication", runner.ADAPTER_IDS)
        self.assertIs(runner.descriptor_for("x_syndication"), x_syndication.DESCRIPTOR)

        clock = helpers.FakeClock()
        carrier, opener = helpers.offline_transport(
            clock,
            {
                transport.X_SYNDICATION_TIMELINE_ROUTE: (
                    200,
                    read_fixture("syndication_timeline.html"),
                    "text/html",
                )
            },
        )
        page = runner.call_adapter("x_syndication", carrier, PROFILE_REQUEST)

        self.assertEqual(len(page.records), 100)
        self.assertEqual(len(opener.opened), 1)


def guest_page(body, status=200, target_id="tweet:1799990000000000001"):
    """Run ``x_guest`` over one canned answer for one named operation."""

    return adapter_page(
        x_guest,
        status,
        body,
        content_type="application/json",
        request=adapters.AdapterRequest(step_id="s1-x", target_ids=(target_id,)),
    )


class GuestOperationTest(unittest.TestCase):
    """Criterion 1, K1 half: the three operations a guest token authorizes."""

    def test_a_tweet_by_id_carries_the_platforms_own_counts(self):
        page, opener = guest_page(read_fixture("guest_tweet_result.json"))

        self.assertEqual(page.outcome, "ok")
        self.assertEqual(page.loss, ())
        self.assertEqual(len(page.records), 1)
        record = page.records[0]
        self.assertEqual(record.canonical_content_kind, "post")
        self.assertEqual(record.native_item_id, "1799990000000000001")
        self.assertEqual(record.native_parent_id, "1799990000000000001")
        self.assertEqual(record.author, "simonw")
        self.assertEqual(record.published_at, "2026-08-09T07:00:00Z")
        self.assertEqual(
            record.canonical_locator, "https://x.com/simonw/status/1799990000000000001"
        )
        self.assertEqual(
            dict(record.engagement),
            {
                "favorite_count": 412,
                "retweet_count": 57,
                "reply_count": 23,
                "quote_count": 4,
            },
        )
        self.assertEqual(len(opener.opened), 1)

    def test_a_user_by_handle_carries_the_profile_the_route_returns(self):
        page, _ = guest_page(
            read_fixture("guest_user_by_screen_name.json"), target_id="user:simonw"
        )

        self.assertEqual(page.outcome, "ok")
        self.assertEqual(len(page.records), 1)
        record = page.records[0]
        self.assertEqual(record.canonical_content_kind, "profile")
        self.assertEqual(record.native_item_id, "12497")
        self.assertEqual(record.author, "simonw")
        self.assertEqual(record.title, "Simon Willison")
        self.assertIn("local models", record.body)
        self.assertEqual(record.canonical_locator, "https://x.com/simonw")
        self.assertEqual(record.published_at, "2007-11-12T18:04:11Z")
        self.assertEqual(dict(record.engagement)["followers_count"], 61234)

    def test_a_user_timeline_carries_its_posts_and_surfaces_its_cursor(self):
        page, _ = guest_page(
            read_fixture("guest_user_tweets.json"), target_id="user_tweets:12497"
        )

        self.assertEqual(page.outcome, "ok")
        self.assertEqual(
            [record.native_item_id for record in page.records],
            ["1799990000000000001", "1799990000000000003"],
        )
        self.assertEqual([record.native_position for record in page.records], [0, 1])
        self.assertEqual(page.records[1].native_parent_id, "1799990000000000002")
        # The cursor is surfaced for the core to decide on. The adapter does
        # not follow it: one call, one page.
        self.assertEqual(page.cursor_out, "DAABCgABGel3Xxi2ZAAKAAIY6WOMSt-QAAgAAgAAAAI")

    def test_each_target_kind_names_its_own_operation_and_query_id(self):
        expected = {
            "tweet:1799990000000000001": ("TweetResultByRestId", "tweetId"),
            "user:simonw": ("UserByScreenName", "screen_name"),
            "user_tweets:12497": ("UserTweets", "userId"),
        }

        for target_id, (operation, variable) in sorted(expected.items()):
            with self.subTest(target=target_id):
                _, opener = guest_page(
                    read_fixture("guest_tweet_result.json"), target_id=target_id
                )
                url = opener.opened[0].url

                self.assertIn("/" + x_guest.GUEST_QUERY_IDS[operation] + "/", url)
                self.assertIn("/" + operation + "?", url)
                self.assertIn(variable, urllib.parse.unquote(url))

    def test_a_bare_target_id_is_a_tweet_id_and_never_a_guess_at_its_shape(self):
        _, opener = guest_page(
            read_fixture("guest_tweet_result.json"), target_id="1799990000000000001"
        )

        self.assertIn("/TweetResultByRestId?", opener.opened[0].url)

    def test_the_page_speaks_for_x_at_the_class_the_ladder_gives_it(self):
        page, _ = guest_page(read_fixture("guest_tweet_result.json"))

        self.assertEqual(page.adapter_id, "x_guest")
        self.assertEqual(page.platform, "x")
        self.assertEqual(page.native_identity_namespace, "x")
        self.assertEqual(page.access_class, "K1")
        self.assertEqual(page.representation_kind, "native")
        self.assertEqual(page.route_id, transport.X_GUEST_GRAPHQL_ROUTE)


class GuestDescriptorTest(unittest.TestCase):
    """Criterion 3: every rotating id names its way back, where a reader meets it."""

    def test_the_route_is_paced_by_the_interval_the_evidence_measured(self):
        descriptor = x_guest.DESCRIPTOR

        self.assertEqual(descriptor.min_interval_ms, 500)
        self.assertEqual(descriptor.burst, adapters.DEFAULT_BURST)
        self.assertEqual(descriptor.cooldown_ms, adapters.DEFAULT_COOLDOWN_MS)
        self.assertEqual(
            runner.route_budgets()[transport.X_GUEST_GRAPHQL_ROUTE],
            runner.RouteBudget(min_interval_ms=500, burst=1, cooldown_ms=60000),
        )

    def test_every_operation_declares_its_query_id_with_a_recovery_procedure(self):
        declared = x_guest.DESCRIPTOR.volatile_identifiers

        self.assertEqual(len(declared), len(x_guest.GUEST_QUERY_IDS))
        for operation, query_id in sorted(x_guest.GUEST_QUERY_IDS.items()):
            with self.subTest(operation=operation):
                naming = [
                    identifier
                    for identifier in declared
                    if operation in identifier.name and query_id in identifier.name
                ]

                self.assertEqual(len(naming), 1)
                # The procedure travels with the identifier rather than living
                # somewhere a reader would have to already know to look.
                recovery = naming[0].recovery
                self.assertIn("import map", recovery)
                self.assertIn("queryId", recovery)

    def test_a_query_id_carries_the_shape_the_route_puts_in_its_path(self):
        for operation, query_id in sorted(x_guest.GUEST_QUERY_IDS.items()):
            with self.subTest(operation=operation):
                self.assertEqual(len(query_id), 22)
                self.assertEqual(query_id, urllib.parse.quote(query_id, safe="-_"))

    def test_it_declares_the_reply_metric_it_reports_and_no_comment_metric(self):
        self.assertEqual(x_guest.DESCRIPTOR.reply_count_metric, "reply_count")
        self.assertEqual(x_guest.DESCRIPTOR.comment_count_metric, "")

    def test_the_activation_it_spends_declares_a_budget_of_its_own(self):
        # The governor refuses to pace a route no adapter declares, and an
        # activation is a request of its own — so it needs its own row. Same
        # ceiling as the reads it authorizes: the 2026-08-10 probes recorded one
        # origin at 0.5 s per request, and the activation is a request there.
        surfaces = {
            descriptor.route_id: descriptor
            for descriptor in runner.surface_descriptors("x_guest")
        }

        self.assertEqual(
            sorted(surfaces),
            sorted((transport.X_GUEST_ACTIVATE_ROUTE, transport.X_GUEST_GRAPHQL_ROUTE)),
        )
        self.assertEqual(
            runner.route_budgets()[transport.X_GUEST_ACTIVATE_ROUTE],
            runner.budget_of(x_guest.DESCRIPTOR),
        )

    def test_the_activation_surface_is_not_a_surface_a_caller_reads(self):
        # It carries a budget and nothing else: no record comes back from an
        # activation, so `descriptor_for` — the adapter's one readable surface
        # — still names the GraphQL route and only that.
        self.assertIs(runner.descriptor_for("x_guest"), x_guest.DESCRIPTOR)
        self.assertEqual(x_guest.DESCRIPTOR.route_id, transport.X_GUEST_GRAPHQL_ROUTE)
        self.assertEqual(
            x_guest.ACTIVATION_DESCRIPTOR.route_id, transport.X_GUEST_ACTIVATE_ROUTE
        )

    def test_the_core_can_reach_it_by_both_of_its_literal_branches(self):
        self.assertIn("x_guest", runner.ADAPTER_IDS)
        self.assertIs(runner.descriptor_for("x_guest"), x_guest.DESCRIPTOR)

        clock = helpers.FakeClock()
        carrier, opener = helpers.offline_transport(
            clock,
            {
                transport.X_GUEST_GRAPHQL_ROUTE: (
                    200,
                    read_fixture("guest_tweet_result.json"),
                    "application/json",
                )
            },
        )
        page = runner.call_adapter(
            "x_guest",
            carrier,
            adapters.AdapterRequest(step_id="s1-x", target_ids=("tweet:1799990000000000001",)),
        )

        self.assertEqual(len(page.records), 1)
        self.assertEqual(len(opener.opened), 1)
