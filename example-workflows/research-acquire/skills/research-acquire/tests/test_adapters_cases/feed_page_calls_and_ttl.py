from tests.test_adapters_cases.rss_atom import *  # noqa: F401,F403

PAGE_ROUTES = ()
FEED_PAGE_ADAPTERS = ("rss_atom",)
HTTP_STATUSES_EVERY_ROUTE_CAN_ANSWER = (404, 429, 500, 503)


def status_rows(body_fixture, extra):
    """The four statuses every route can answer with, as case rows."""

    return tuple(
        dict(extra, case_name="http_{0}".format(status), status=status,
             body_fixture=body_fixture)
        for status in HTTP_STATUSES_EVERY_ROUTE_CAN_ANSWER
    )




def run_rss_case(module=None):
    def run(row):
        return rss_atom_page(row["body_fixture"], status=row["status"], module=module)

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


    def test_every_rss_atom_answer_costs_one_call_on_its_own_route(self):
        assert_one_answer_costs_one_call(
            self,
            "rss_atom",
            rss_atom_cases() + status_rows("not_a_feed.html", {}),
            run_rss_case(),
            (transport.YOUTUBE_CHANNEL_FEED_ROUTE,),
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


    def test_a_channel_feed_reread_inside_its_window_is_answered_from_memory(self):
        self._window(
            transport.YOUTUBE_CHANNEL_FEED_ROUTE,
            read_rss_atom("youtube_channel_feed.xml"),
            rss_atom,
            syndication_request(),
            inside=200,
            outside=400,
        )







    def test_every_route_this_ticket_declares_has_a_window_argued_for_it(self):
        for route_id in sorted(FEED_PAGE_ROUTES):
            with self.subTest(route=route_id):
                self.assertIn(route_id, cache.ROUTE_TTL_SECONDS)
