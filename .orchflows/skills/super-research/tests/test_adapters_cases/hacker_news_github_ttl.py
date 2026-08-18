from tests.test_adapters_cases.hacker_news_github_calls import *  # noqa: F401,F403

class HackerNewsGithubRouteTtlTest(unittest.TestCase):
    """How long each of the four answers may stand in for a fresh read.

    A TTL belongs to a route's own volatility, and `cache.py`'s default is
    deliberately short — a route nobody has measured is not one to trust for
    long. So every window declared here is proven from both sides: a re-read
    inside it that the inherited default would have sent back to the origin,
    and one outside it that goes back.

    The GitHub pair is the one where the argument is not only volatility.
    The 2026-08-10 probes recorded the anonymous ceiling at 60/hr per bucket — the
    tightest in the roster after Reddit's feed — so a repeat read there costs a
    minute of the hour rather than a second of latency, and that is a different
    kind of expensive from the 2.9 s Instagram profile.
    """

    def _served(self, clock, route_id, body):
        carrier, opener = helpers.offline_transport(
            clock, {route_id: (200, body, "application/json")}
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

    def test_a_search_reread_inside_its_window_is_answered_from_memory(self):
        self._window(
            transport.HN_ALGOLIA_SEARCH_ROUTE,
            read_hacker_news("algolia_search_by_date.json"),
            hacker_news,
            hn_request(query="local models"),
            inside=120,
            outside=200,
        )

    def test_an_item_reread_inside_its_window_is_answered_from_memory(self):
        self._window(
            transport.HN_FIREBASE_ITEM_ROUTE,
            read_hacker_news("firebase_story.json"),
            hacker_news,
            hn_request(target_id=HN_STORY_ID),
            inside=90,
            outside=150,
        )

    def test_a_repository_reread_inside_its_window_is_answered_from_memory(self):
        self._window(
            transport.GITHUB_REST_ROUTE,
            read_github("repo.json"),
            github_rest,
            gh_request(target_id=GITHUB_TARGET),
            inside=500,
            outside=700,
        )

    def test_a_repository_search_reread_inside_its_window_is_answered_from_memory(self):
        self._window(
            transport.GITHUB_SEARCH_ROUTE,
            read_github("search_repositories.json"),
            github_rest,
            gh_request(query="gpu benchmark"),
            inside=240,
            outside=400,
        )

    def test_the_list_of_each_pair_is_held_for_less_time_than_the_thing_it_lists(self):
        # An item's counts move while nobody edits anything, and an index's
        # answer changes as stories arrive: within HN the store is the one that
        # cannot be held long. Within GitHub it is the other way round, because
        # a repository's own row changes on a human timescale while a ranked
        # search moves whenever anything in it does.
        self.assertLess(
            cache.ttl_seconds(transport.HN_FIREBASE_ITEM_ROUTE),
            cache.ttl_seconds(transport.HN_ALGOLIA_SEARCH_ROUTE),
        )
        self.assertLess(
            cache.ttl_seconds(transport.GITHUB_SEARCH_ROUTE),
            cache.ttl_seconds(transport.GITHUB_REST_ROUTE),
        )

    def test_the_tightest_budget_in_the_roster_earns_the_longest_of_these_four(self):
        # Not a preference: at 60/hr one repeat read costs a full minute of the
        # hour, where the roster's other routes cost seconds of latency. Every
        # other window here is shorter, and every one of the four is longer
        # than the window a route nobody has measured gets.
        declared = {
            route_id: cache.ttl_seconds(route_id)
            for route_id in (HN_ROUTES + GITHUB_ROUTES)
        }

        self.assertEqual(
            max(declared, key=lambda route_id: declared[route_id]),
            transport.GITHUB_REST_ROUTE,
        )
        for route_id, window in sorted(declared.items()):
            with self.subTest(route=route_id):
                self.assertGreater(window, cache.DEFAULT_TTL_SECONDS)

    def test_all_four_answers_are_small_enough_for_a_window_to_mean_anything(self):
        # A window on a body over the entry cap would never bind. These four
        # answer in kilobytes, so nothing here is served through and every
        # window above binds on the body the fixture holds.
        for fixture, read in (
            ("algolia_search_by_date.json", read_hacker_news),
            ("firebase_story.json", read_hacker_news),
            ("repo.json", read_github),
            ("search_repositories.json", read_github),
        ):
            with self.subTest(body=fixture):
                self.assertLess(
                    len(read(fixture).encode("utf-8")), cache.MAX_ENTRY_BYTES
                )
        self.assertEqual(cache.MAX_ENTRY_BYTES, 1024 * 1024)


HN_KID_ID = "44831402"


def hacker_news_github_manifest():
    """One dispatch reading four surfaces, and HN twice about one story."""

    return schema.AcquisitionManifest(
        manifest_id="m-hn-gh",
        mode="staged",
        # After the reads this dispatch makes, because a frozen horizon that
        # fell before its own observations would replay to nothing.
        as_of="2026-08-10T09:05:00Z",
        steps=(
            schema.AcquisitionStep(
                step_id="s1-search",
                kind="discovery",
                adapter_id="hacker_news",
                query="local models",
                max_items=20,
            ),
            schema.AcquisitionStep(
                step_id="s2-story",
                kind="hydration",
                adapter_id="hacker_news",
                selected_hits=(
                    schema.SelectedHit(
                        discovery_locator=HN_PERMALINK + HN_STORY_ID,
                        target_id=HN_STORY_ID,
                    ),
                ),
                max_items=5,
            ),
            schema.AcquisitionStep(
                step_id="s3-kid",
                kind="hydration",
                adapter_id="hacker_news",
                # One id out of the story's own `kids`, chosen by the caller.
                # The traversal is the core's: the adapter handed back the ids
                # and made no second call of its own.
                selected_hits=(
                    schema.SelectedHit(
                        discovery_locator=HN_PERMALINK + HN_KID_ID,
                        target_id=HN_KID_ID,
                    ),
                ),
                max_items=5,
            ),
            schema.AcquisitionStep(
                step_id="s4-repository",
                kind="hydration",
                adapter_id="github_rest",
                selected_hits=(
                    schema.SelectedHit(
                        discovery_locator="https://github.com/" + GITHUB_TARGET,
                        target_id=GITHUB_TARGET,
                    ),
                ),
                max_items=5,
            ),
            schema.AcquisitionStep(
                step_id="s5-issues",
                kind="hydration",
                adapter_id="github_rest",
                selected_hits=(
                    schema.SelectedHit(
                        discovery_locator="https://github.com/" + GITHUB_TARGET + "/issues",
                        target_id="issues:" + GITHUB_TARGET,
                    ),
                ),
                max_items=20,
            ),
            schema.AcquisitionStep(
                step_id="s6-search",
                kind="discovery",
                adapter_id="github_rest",
                query="gpu benchmark",
                max_items=20,
            ),
        ),
    )


