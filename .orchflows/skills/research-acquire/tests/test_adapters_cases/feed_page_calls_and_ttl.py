from tests.test_adapters_cases.public_page_claims import *  # noqa: F401,F403

PAGE_ROUTES = (
    transport.PUBLIC_PAGE_ARTICLE_ROUTE,
    transport.PUBLIC_PAGE_CONTROL_ROUTE,
)
FEED_PAGE_ADAPTERS = ("public_page", "reddit_feed", "rss_atom")
HTTP_STATUSES_EVERY_ROUTE_CAN_ANSWER = (404, 429, 500, 503)


def status_rows(body_fixture, extra):
    """The four statuses every route can answer with, as case rows."""

    return tuple(
        dict(extra, case_name="http_{0}".format(status), status=status,
             body_fixture=body_fixture)
        for status in HTTP_STATUSES_EVERY_ROUTE_CAN_ANSWER
    )


def run_feed_case(module=None):
    def run(row):
        return feed_page(
            row["body_fixture"],
            status=row["status"],
            subreddit=row["subreddit"],
            module=module,
        )

    return run


def run_rss_case(module=None):
    def run(row):
        return rss_atom_page(row["body_fixture"], status=row["status"], module=module)

    return run


def run_page_case(module=None):
    def run(row):
        return selected_page(
            row["body_fixture"], status=row["status"], target=row["target"], module=module
        )

    return run


def feed_page_portal(module, request, seeded):
    """One captive-portal 503 through an adapter, on every route it can reach."""

    portal = TRANSPORT_FIXTURE_DIR.joinpath("captive_portal.html").read_text(
        encoding="utf-8"
    )
    clock = helpers.FakeClock()
    carrier, opener = helpers.offline_transport(
        clock, {route_id: (503, portal, "text/html") for route_id in seeded}
    )
    return (module.fetch_native_page(carrier, request), opener)


class FeedPageOneCallOnePageTest(unittest.TestCase):
    """Row 4: one bounded call in, exactly one page out, on one declared route.

    The three adapters here are the roster's last, and two of them are the kind
    that invites a second read. A feed states a window onto recent entries and a
    caller always wants the next one; a page carries links and a page reader is
    one loop away from being a crawler. Neither happens: the core owns
    pagination and stop, so a caller that wants more says so, and an adapter
    that followed a link would turn one bounded call into a walk whose size
    nobody declared.
    """

    def test_every_reddit_feed_answer_costs_one_call_on_its_own_route(self):
        assert_one_answer_costs_one_call(
            self,
            "reddit_feed",
            reddit_feed_cases()
            + status_rows("refused.html", {"subreddit": REDDIT_SUBREDDIT}),
            run_feed_case(),
            (transport.REDDIT_FEED_ROUTE,),
        )

    def test_every_rss_atom_answer_costs_one_call_on_its_own_route(self):
        assert_one_answer_costs_one_call(
            self,
            "rss_atom",
            rss_atom_cases() + status_rows("not_a_feed.html", {}),
            run_rss_case(),
            (transport.YOUTUBE_CHANNEL_FEED_ROUTE,),
        )

    def test_every_public_page_answer_costs_one_call_on_one_of_its_selections(self):
        assert_one_answer_costs_one_call(
            self,
            "public_page",
            page_cases() + status_rows("article_absent.html", {"target": ARTICLE_TARGET}),
            run_page_case(),
            PAGE_ROUTES,
        )

    def test_none_of_the_three_paginates_or_surfaces_a_cursor_to_follow(self):
        # None of these three documents states a next page, so none is derived.
        # A feed publishes a window and a page is one document; inventing a
        # cursor from either would make the adapter the thing that decides
        # there is more.
        answers = (
            feed_page("subreddit_new.xml")[0],
            rss_atom_page("youtube_channel_feed.xml")[0],
            selected_page("article.html")[0],
        )

        for page in answers:
            with self.subTest(adapter=page.adapter_id):
                self.assertEqual(page.cursor_out, "")

    def test_none_of_the_three_names_another_adapter_or_the_cores_dispatch(self):
        for module_name, own_id in (
            ("public_page.py", "public_page"),
            ("reddit_feed.py", "reddit_feed"),
            ("rss_atom.py", "rss_atom"),
        ):
            with self.subTest(module=module_name):
                self.assertEqual(adapters_named(ADAPTER_DIR / module_name, own_id), [])
                self.assertNotIn(
                    "call_adapter", adapter_owner_source(ADAPTER_DIR / module_name)
                )

    def test_none_of_the_three_touches_the_carrier_itself(self):
        # The channel verdict is read in one place for every adapter there will
        # ever be, and these three inherit it by calling `fetch_one_page`
        # instead of the carrier. An adapter that called `carrier.fetch` would
        # be the one adapter a local block could be recorded as a platform gap
        # through.
        for module_name in ("public_page.py", "reddit_feed.py", "rss_atom.py"):
            with self.subTest(module=module_name):
                source = ADAPTER_DIR / module_name
                attributes = {
                    name
                    for owner in adapter_owner_paths(source)
                    for name in helpers.attribute_names(owner)
                }
                imported = {
                    name
                    for owner in adapter_owner_paths(source)
                    for name in helpers.imported_names(owner)
                }

                self.assertNotIn("carrier.fetch", attributes)
                self.assertEqual(
                    sorted(name for name in attributes if name.endswith(".fetch")), []
                )
                # And the thing it calls instead is really imported, so the
                # absence above is a delegation rather than an adapter that
                # never reads at all.
                self.assertTrue(
                    any(name.endswith("fetch_one_page") for name in imported),
                    sorted(imported),
                )

    def test_the_same_scan_finds_the_carrier_where_one_is_touched(self):
        # Shown to discriminate rather than to match nothing: the wrong adapter
        # beside the tree reaches the carrier directly, which is exactly how an
        # adapter would end up reading a local block as a platform gap.
        attributes = helpers.attribute_names(
            PUBLIC_PAGE_FIXTURE_DIR / "any_url_adapter.py"
        )

        self.assertIn("carrier.fetch", attributes)

    def test_none_of_the_three_reads_a_file_opens_a_socket_or_waits(self):
        cases = (
            (reddit_feed, transport.REDDIT_FEED_ROUTE,
             read_reddit_feed("subreddit_new.xml"), feed_request()),
            (rss_atom, transport.YOUTUBE_CHANNEL_FEED_ROUTE,
             read_rss_atom("youtube_channel_feed.xml"), syndication_request()),
            (public_page, transport.PUBLIC_PAGE_ARTICLE_ROUTE,
             read_public_page("article.html"), page_request(ARTICLE_TARGET)),
        )

        for module, route_id, body, request in cases:
            with self.subTest(adapter=module.DESCRIPTOR.adapter_id):
                clock = helpers.FakeClock()
                carrier, _ = helpers.offline_transport(
                    clock, {route_id: (200, body, "text/html")}
                )

                with helpers.forbid_io():
                    with helpers.forbid_sleep():
                        page = module.fetch_native_page(carrier, request)

                self.assertEqual(page.outcome, "ok")

    def test_a_local_block_is_never_recorded_as_a_platform_gap(self):
        # Inherited from the protocol by writing nothing. It matters most on
        # this trio: a 503 login portal answering a feed looks exactly like a
        # subreddit with nothing in it, and answering a page read it looks
        # exactly like a document that moved.
        cases = (
            (reddit_feed, feed_request(), (transport.REDDIT_FEED_ROUTE,)),
            (rss_atom, syndication_request(), (transport.YOUTUBE_CHANNEL_FEED_ROUTE,)),
            (public_page, page_request(ARTICLE_TARGET), PAGE_ROUTES),
            (public_page, page_request("control"), PAGE_ROUTES),
        )

        for module, request, seeded in cases:
            with self.subTest(adapter=module.DESCRIPTOR.adapter_id, request=request):
                page, opener = feed_page_portal(module, request, seeded)

                self.assertEqual(page.loss, (transport.NETWORK_INTERCEPTED,))
                self.assertEqual(page.outcome, "failed")
                self.assertEqual(page.records, ())
                self.assertEqual(len(opener.opened), 1)

    def test_a_refusal_to_slow_down_is_typed_and_never_substituted(self):
        # The one refusal the protocol types for every adapter, and the one
        # this trio meets most: Reddit's feed refuses at the second read inside
        # thirty seconds. It is an outcome, never an invitation to ask a
        # different host — and for Reddit there is no other host to ask.
        cases = (
            (reddit_feed, feed_request(), (transport.REDDIT_FEED_ROUTE,)),
            (rss_atom, syndication_request(), (transport.YOUTUBE_CHANNEL_FEED_ROUTE,)),
            (public_page, page_request(ARTICLE_TARGET), PAGE_ROUTES),
        )

        for module, request, seeded in cases:
            with self.subTest(adapter=module.DESCRIPTOR.adapter_id):
                clock = helpers.FakeClock()
                carrier, opener = helpers.offline_transport(
                    clock,
                    {
                        route_id: (transport.RATE_LIMITED_STATUS, "slow down", "text/plain")
                        for route_id in seeded
                    },
                )

                page = module.fetch_native_page(carrier, request)

                self.assertEqual(page.loss, (transport.RATE_LIMITED,))
                self.assertEqual(page.outcome, "failed")
                self.assertEqual(len(opener.opened), 1)

    def test_every_route_all_three_can_reach_declares_a_budget(self):
        # T08's seam, inherited: `public_page` is the second two-surface
        # adapter, and a surface the core cannot see here is a route the
        # governor refuses to pace — loudly, but at the first live read rather
        # than here.
        budgets = runner.route_budgets()
        reachable = sorted(
            descriptor.route_id
            for adapter_id in FEED_PAGE_ADAPTERS
            for descriptor in runner.surface_descriptors(adapter_id)
        )

        self.assertEqual([route for route in reachable if route not in budgets], [])
        self.assertEqual(len(reachable), len(set(reachable)))
        self.assertEqual(len(reachable), 4)

    def test_the_second_selection_is_paced_rather_than_refused(self):
        clock = helpers.FakeClock()
        carrier, opener = helpers.offline_transport(
            clock,
            {
                transport.PUBLIC_PAGE_CONTROL_ROUTE: (
                    200,
                    read_public_page("control.html"),
                    "text/html",
                )
            },
        )
        governor = runner.RateGovernor(carrier, clock=clock.monotonic, sleep=clock.sleep)
        request = page_request("control")

        with helpers.forbid_sleep():
            public_page.fetch_native_page(governor, request)
            public_page.fetch_native_page(governor, request)

        self.assertEqual(len(opener.opened), 2)
        self.assertEqual(
            governor.log[1].at_us - governor.log[0].at_us,
            adapters.DEFAULT_MIN_INTERVAL_MS * 1000,
        )

    def test_the_reddit_feeds_second_read_waits_the_measured_thirty_seconds(self):
        # The pacing proof that matters, in microseconds of real time rather
        # than in thirty real seconds: a fake clock's sleep moves time without
        # spending any.
        clock = helpers.FakeClock()
        carrier, opener = helpers.offline_transport(
            clock,
            {
                transport.REDDIT_FEED_ROUTE: (
                    200,
                    read_reddit_feed("subreddit_new.xml"),
                    "application/atom+xml",
                )
            },
        )
        governor = runner.RateGovernor(carrier, clock=clock.monotonic, sleep=clock.sleep)

        with helpers.forbid_sleep():
            reddit_feed.fetch_native_page(governor, feed_request("LocalLLaMA"))
            reddit_feed.fetch_native_page(governor, feed_request("MachineLearning"))

        self.assertEqual(len(opener.opened), 2)
        self.assertEqual(governor.log[0].waited_us, 0)
        self.assertEqual(
            governor.log[1].at_us - governor.log[0].at_us,
            test_pipeline.REDDIT_FEED_BUDGET.min_interval_ms * 1000,
        )


class FeedPageRouteTtlTest(unittest.TestCase):
    """How long each of the four answers may stand in for a fresh read.

    This is the ticket where the cache stops being an optimization. Reddit's
    feed admits three reads a minute, so a run that asks twice does not run
    slowly — it spends a third of its minute on a question it already asked.
    Every window here is argued from that route's own measured cost and its own
    volatility, and proven from both sides: a re-read inside it that the
    inherited default would have sent back to the origin, and one outside it
    that goes back.

    The control is the interesting one, and it is argued the other way. Its
    whole job is to answer "is this network answering for the origin right
    now", and an answer from a run's own memory cannot answer that about now.
    So it declares a window of zero and is never served from memory — the only
    route in the table where holding an answer would defeat the read.
    """

    def _served(self, clock, route_id, body, content_type="text/html"):
        carrier, opener = helpers.offline_transport(
            clock, {route_id: (200, body, content_type)}
        )
        governor = runner.RateGovernor(
            carrier,
            run_cache=cache.RunCache(clock=clock.monotonic),
            clock=clock.monotonic,
            sleep=clock.sleep,
        )
        return (governor, opener)

    def _window(self, route_id, body, module, request, inside, outside):
        """Read, re-read inside the window, re-read past it."""

        clock = helpers.FakeClock()
        governor, opener = self._served(clock, route_id, body)

        first = module.fetch_native_page(governor, request)
        clock.advance(inside)
        held = module.fetch_native_page(governor, request)
        clock.advance(outside - inside)
        expired = module.fetch_native_page(governor, request)

        self.assertNotIn(cache.CACHE_HIT, first.loss)
        self.assertIn(cache.CACHE_HIT, held.loss)
        self.assertNotIn(cache.CACHE_HIT, expired.loss)
        self.assertEqual(len(opener.opened), 2)
        # The mark moves, the moment does not: a served page still states when
        # the origin was really read.
        self.assertEqual(held.observed_at, first.observed_at)
        self.assertEqual(len(held.records), len(first.records))
        # And the window it was held for is longer than the one an undeclared
        # route would have got, so the hit above is this table's doing.
        self.assertGreater(inside, cache.DEFAULT_TTL_SECONDS)
        self.assertLess(inside, cache.ttl_seconds(route_id))
        self.assertGreater(outside, cache.ttl_seconds(route_id))

    def test_a_subreddit_feed_reread_inside_its_window_is_answered_from_memory(self):
        self._window(
            transport.REDDIT_FEED_ROUTE,
            read_reddit_feed("subreddit_new.xml"),
            reddit_feed,
            feed_request(),
            inside=120,
            outside=200,
        )

    def test_a_channel_feed_reread_inside_its_window_is_answered_from_memory(self):
        self._window(
            transport.YOUTUBE_CHANNEL_FEED_ROUTE,
            read_rss_atom("youtube_channel_feed.xml"),
            rss_atom,
            syndication_request(),
            inside=200,
            outside=400,
        )

    def test_an_article_reread_inside_its_window_is_answered_from_memory(self):
        self._window(
            transport.PUBLIC_PAGE_ARTICLE_ROUTE,
            read_public_page("article.html"),
            public_page,
            page_request(ARTICLE_TARGET),
            inside=700,
            outside=1000,
        )

    def test_the_channel_control_is_never_answered_from_memory(self):
        # Not a short window: no window. A control read exists to say whether
        # the channel is answering, and memory cannot answer that about now. It
        # is the one route in the table where a hit would be a wrong answer
        # rather than a stale one.
        clock = helpers.FakeClock()
        governor, opener = self._served(
            clock, transport.PUBLIC_PAGE_CONTROL_ROUTE, read_public_page("control.html")
        )
        request = page_request("control")

        first = public_page.fetch_native_page(governor, request)
        again = public_page.fetch_native_page(governor, request)

        self.assertEqual(cache.ttl_seconds(transport.PUBLIC_PAGE_CONTROL_ROUTE), 0.0)
        self.assertNotIn(cache.CACHE_HIT, first.loss)
        self.assertNotIn(cache.CACHE_HIT, again.loss)
        self.assertEqual(len(opener.opened), 2)
        # And it is the shortest declared window in the whole table, by
        # construction rather than by comparison.
        self.assertEqual(min(cache.ROUTE_TTL_SECONDS.values()), 0.0)

    def test_the_freshness_probe_is_held_longer_than_the_interval_that_paces_it(self):
        # A window shorter than a route's interval could never bind: the
        # governor would already have made the caller wait longer than the
        # window before the second read arrived. Reddit's is the only route
        # where the two numbers are close enough for that to be a real risk.
        window_ms = cache.ttl_seconds(transport.REDDIT_FEED_ROUTE) * 1000

        self.assertGreater(
            window_ms, runner.route_budgets()[transport.REDDIT_FEED_ROUTE].min_interval_ms
        )
        # Six intervals: enough that a run polling several subreddits never
        # pays twice for one, and short enough that a freshness probe is still
        # about now. It is the window the roster's other "a list that has moved
        # on" route holds, for the same reason.
        self.assertEqual(
            cache.ttl_seconds(transport.REDDIT_FEED_ROUTE),
            cache.ttl_seconds(transport.HN_ALGOLIA_SEARCH_ROUTE),
        )

    def test_the_document_that_changes_only_when_edited_is_held_longest_of_the_four(self):
        # Volatility, not cost. An article carries no counter at all and
        # changes when somebody edits it, so nothing in it goes stale on a
        # run's timescale — which is the argument the roster's other
        # counter-free document is held for the same length of time on.
        declared = {
            route_id: cache.ttl_seconds(route_id) for route_id in FEED_PAGE_ROUTES
        }

        self.assertEqual(
            max(declared, key=lambda route_id: declared[route_id]),
            transport.PUBLIC_PAGE_ARTICLE_ROUTE,
        )
        self.assertEqual(
            cache.ttl_seconds(transport.PUBLIC_PAGE_ARTICLE_ROUTE),
            cache.ttl_seconds(transport.LINKEDIN_PUBLIC_PROFILE_ROUTE),
        )

    def test_three_of_the_four_are_longer_than_a_route_nobody_measured_gets(self):
        held = [
            route_id
            for route_id in FEED_PAGE_ROUTES
            if cache.ttl_seconds(route_id) > cache.DEFAULT_TTL_SECONDS
        ]

        self.assertEqual(
            sorted(held),
            [
                transport.PUBLIC_PAGE_ARTICLE_ROUTE,
                transport.REDDIT_FEED_ROUTE,
                transport.YOUTUBE_CHANNEL_FEED_ROUTE,
            ],
        )

    def test_the_bodies_these_routes_answer_with_fit_inside_the_run_footprint(self):
        # A window on a body over the entry cap would never bind. These
        # fixtures fit, so the windows above bind on them.
        for fixture, read in (
            ("subreddit_new.xml", read_reddit_feed),
            ("youtube_channel_feed.xml", read_rss_atom),
            ("article.html", read_public_page),
            ("control.html", read_public_page),
        ):
            with self.subTest(body=fixture):
                self.assertLess(len(read(fixture).encode("utf-8")), cache.MAX_ENTRY_BYTES)
        self.assertEqual(cache.MAX_ENTRY_BYTES, 1024 * 1024)

    def test_every_route_this_ticket_declares_has_a_window_argued_for_it(self):
        for route_id in sorted(FEED_PAGE_ROUTES):
            with self.subTest(route=route_id):
                self.assertIn(route_id, cache.ROUTE_TTL_SECONDS)
