from tests.test_adapters_cases.github_write_safety import *  # noqa: F401,F403

HN_ROUTES = (transport.HN_FIREBASE_ITEM_ROUTE, transport.HN_ALGOLIA_SEARCH_ROUTE)
GITHUB_ROUTES = (transport.GITHUB_REST_ROUTE, transport.GITHUB_SEARCH_ROUTE)


def assert_one_answer_costs_one_call(case, adapter_id, rows, run, routes):
    """Row 3's oracle: one bounded call in, exactly one page out, on one route.

    ``run`` answers one case with the page an adapter produced and the opener
    that saw what left. Two adapters here read two origins each, so "one page
    per call" is not only about pagination and retries: an adapter that
    answered a search by also reading the item it found would be two reads
    charged to one page, on two budgets, with one observation time — and the
    core, which owns pacing and sequence, would never see the second.
    """

    for row in rows:
        name = row["case_name"]
        page, opener = run(row)
        detail = " {0} case {1}".format(adapter_id, name)
        if not isinstance(page, adapters.NativePage):
            case.fail("an answer was not one NativePage:" + detail)
        if len(opener.opened) != 1:
            case.fail(
                "one answer cost {0} calls rather than one:{1}".format(
                    len(opener.opened), detail
                )
            )
        if opener.opened[0].route_id != page.route_id:
            case.fail(
                "the page names route {0} and the call went to {1}:{2}".format(
                    page.route_id, opener.opened[0].route_id, detail
                )
            )
        if page.route_id not in routes:
            case.fail(
                "an answer came back on a route this adapter never declared: {0}{1}".format(
                    page.route_id, detail
                )
            )


def hn_status_rows():
    """The four statuses every route can answer with, as case rows."""

    return tuple(
        {
            "case_name": "http_{0}".format(status),
            "query": "",
            "target_id": HN_STORY_ID,
            "cursor": "",
            "status": status,
            "body_fixture": "firebase_reshaped.json",
        }
        for status in (404, 429, 500, 503)
    )


def github_status_rows():
    return tuple(
        {
            "case_name": "http_{0}".format(status),
            "query": "",
            "target_id": GITHUB_TARGET,
            "cursor": "",
            "status": status,
            "body_fixture": "not_found.json",
        }
        for status in (404, 429, 500, 503)
    )


def run_hn_case(module=None):
    def run(row):
        return hn_page(
            row["body_fixture"],
            status=row["status"],
            query=row["query"],
            target_id=row["target_id"],
            cursor=row["cursor"],
            content_type=(
                "text/html" if row["body_fixture"].endswith(".txt") else "application/json"
            ),
            module=module,
        )

    return run


def run_github_case(module=None):
    def run(row):
        return gh_page(
            row["body_fixture"],
            status=row["status"],
            query=row["query"],
            target_id=row["target_id"],
            cursor=row["cursor"],
            module=module,
        )

    return run


def portal_page(module, request, seeded):
    """One captive-portal 503 through an adapter, on every route it can reach."""

    portal = TRANSPORT_FIXTURE_DIR.joinpath("captive_portal.html").read_text(
        encoding="utf-8"
    )
    clock = helpers.FakeClock()
    carrier, opener = helpers.offline_transport(
        clock, {route_id: (503, portal, "text/html") for route_id in seeded}
    )
    return (module.fetch_native_page(carrier, request), opener)


class HackerNewsGithubOneCallOnePageTest(unittest.TestCase):
    """Row 3: one call, one page, one route, whatever comes back."""

    def test_every_hacker_news_answer_costs_one_call_on_one_of_its_two_routes(self):
        assert_one_answer_costs_one_call(
            self,
            "hacker_news",
            hacker_news_cases() + hn_status_rows(),
            run_hn_case(),
            HN_ROUTES,
        )

    def test_every_github_answer_costs_one_call_on_one_of_its_two_routes(self):
        assert_one_answer_costs_one_call(
            self,
            "github_rest",
            github_cases() + github_status_rows(),
            run_github_case(),
            GITHUB_ROUTES,
        )

    def test_a_search_reads_the_index_and_an_item_read_reads_the_item_store(self):
        # The two surfaces are two calls: a search never also hydrates what it
        # found, and an item read never also searches for it. Which to do next
        # is the core's decision, and it can only make it if it sees both.
        _, searched = hn_page("algolia_search_by_date.json", query="local models")
        _, read = hn_page("firebase_story.json", target_id=HN_STORY_ID)

        self.assertEqual(
            [call.route_id for call in searched.opened], [transport.HN_ALGOLIA_SEARCH_ROUTE]
        )
        self.assertEqual(
            [call.route_id for call in read.opened], [transport.HN_FIREBASE_ITEM_ROUTE]
        )

    def test_a_github_search_and_a_repository_read_spend_their_own_buckets(self):
        _, searched = gh_page("search_repositories.json", query="gpu benchmark")
        _, read = gh_page("repo.json", target_id=GITHUB_TARGET)

        self.assertEqual(
            [call.route_id for call in searched.opened], [transport.GITHUB_SEARCH_ROUTE]
        )
        self.assertEqual([call.route_id for call in read.opened], [transport.GITHUB_REST_ROUTE])

    def test_neither_adapter_names_another_adapter_or_the_cores_dispatch(self):
        for module_name, own_id in (
            ("hacker_news.py", "hacker_news"),
            ("github_rest.py", "github_rest"),
        ):
            with self.subTest(module=module_name):
                self.assertEqual(adapters_named(ADAPTER_DIR / module_name, own_id), [])
                self.assertNotIn(
                    "call_adapter", adapter_owner_source(ADAPTER_DIR / module_name)
                )

    def test_neither_adapter_reads_a_file_opens_a_socket_or_waits(self):
        cases = (
            (hacker_news, transport.HN_FIREBASE_ITEM_ROUTE,
             read_hacker_news("firebase_story.json"), hn_request(target_id=HN_STORY_ID)),
            (github_rest, transport.GITHUB_REST_ROUTE,
             read_github("repo.json"), gh_request(target_id=GITHUB_TARGET)),
        )

        for module, route_id, body, request in cases:
            with self.subTest(adapter=module.DESCRIPTOR.adapter_id):
                clock = helpers.FakeClock()
                carrier, _ = helpers.offline_transport(
                    clock, {route_id: (200, body, "application/json")}
                )

                with helpers.forbid_io():
                    with helpers.forbid_sleep():
                        page = module.fetch_native_page(carrier, request)

                self.assertEqual(page.outcome, "ok")

    def test_a_local_block_is_never_recorded_as_a_platform_gap(self):
        # Inherited from the protocol by writing nothing: `fetch_one_page`
        # reads the channel verdict ahead of any status test either adapter
        # runs, so a captive portal's 503 is `network_intercepted` and never an
        # absent item, a search with no matches, or a spent GitHub hour.
        cases = (
            (hacker_news, hn_request(target_id=HN_STORY_ID), HN_ROUTES),
            (hacker_news, hn_request(query="local models"), HN_ROUTES),
            (github_rest, gh_request(target_id=GITHUB_TARGET), GITHUB_ROUTES),
            (github_rest, gh_request(query="gpu benchmark"), GITHUB_ROUTES),
        )

        for module, request, seeded in cases:
            with self.subTest(adapter=module.DESCRIPTOR.adapter_id, request=request):
                page, opener = portal_page(module, request, seeded)

                self.assertEqual(page.loss, (transport.NETWORK_INTERCEPTED,))
                self.assertEqual(page.outcome, "failed")
                self.assertEqual(page.records, ())
                self.assertEqual(len(opener.opened), 1)

    def test_a_refusal_to_slow_down_is_typed_and_never_substituted(self):
        # 429 is the one refusal the protocol types for every adapter, and it
        # is never answered by trying the other surface: an origin asking for
        # fewer requests is not an invitation to spend a different budget.
        cases = (
            (hacker_news, run_hn_case(), HN_STORY_ID, "firebase_reshaped.json"),
            (github_rest, run_github_case(), GITHUB_TARGET, "not_found.json"),
        )

        for module, run, target, fixture in cases:
            with self.subTest(adapter=module.DESCRIPTOR.adapter_id):
                page, opener = run(
                    {
                        "case_name": "rate_limited",
                        "query": "",
                        "target_id": target,
                        "cursor": "",
                        "status": transport.RATE_LIMITED_STATUS,
                        "body_fixture": fixture,
                    }
                )

                self.assertEqual(page.loss, (transport.RATE_LIMITED,))
                self.assertEqual(page.outcome, "failed")
                self.assertEqual(len(opener.opened), 1)


class FusedSurfaceOracleCanFailTest(unittest.TestCase):
    """The oracle rejects an adapter that answers one call with two reads."""

    def test_an_adapter_that_hydrates_what_it_found_fails_the_oracle(self):
        fused = load_adapter_fixture("fused_surfaces_adapter", directory=HN_FIXTURE_DIR)

        with self.assertRaisesRegex(AssertionError, "cost 2 calls rather than one"):
            assert_one_answer_costs_one_call(
                self,
                "fused_surfaces_adapter",
                hacker_news_cases(),
                run_hn_case(module=fused),
                HN_ROUTES,
            )

    def test_the_same_oracle_passes_on_the_shipped_adapter(self):
        assert_one_answer_costs_one_call(
            self, "hacker_news", hacker_news_cases(), run_hn_case(), HN_ROUTES
        )

    def test_nothing_in_the_package_can_reach_the_fused_adapter(self):
        named = sorted(
            path.name
            for path in PACKAGE_DIR.rglob("*.py")
            if "fused_surfaces_adapter" in path.read_text(encoding="utf-8")
        )

        self.assertEqual(named, [])


class SecondSurfaceIsPacedTest(unittest.TestCase):
    """Every route an adapter can reach has a budget, and the governor spends it.

    A two-surface adapter is the first thing in this package that could reach a
    route no descriptor declares a ceiling for. The governor refuses to pace
    such a route rather than reading it freely, so the failure would be loud —
    but it would be loud at the first live search, which is too late.
    """

    def _paced(self, route_id, body):
        clock = helpers.FakeClock()
        carrier, opener = helpers.offline_transport(
            clock, {route_id: (200, body, "application/json")}
        )
        governor = runner.RateGovernor(carrier, clock=clock.monotonic, sleep=clock.sleep)
        return (governor, opener, clock)

    def test_every_route_any_adapter_can_reach_declares_a_budget(self):
        budgets = runner.route_budgets()
        reachable = sorted(
            descriptor.route_id
            for adapter_id in runner.ADAPTER_IDS
            for descriptor in runner.surface_descriptors(adapter_id)
        )

        self.assertEqual([route for route in reachable if route not in budgets], [])
        # And the second surfaces are really in there rather than the primaries
        # being counted twice.
        self.assertIn(transport.HN_ALGOLIA_SEARCH_ROUTE, budgets)
        self.assertIn(transport.GITHUB_SEARCH_ROUTE, budgets)
        self.assertEqual(len(reachable), len(set(reachable)))

    def test_a_search_on_the_second_surface_is_paced_and_never_refused(self):
        governor, opener, _ = self._paced(
            transport.HN_ALGOLIA_SEARCH_ROUTE, read_hacker_news("algolia_search_by_date.json")
        )
        request = hn_request(query="local models")

        with helpers.forbid_sleep():
            hacker_news.fetch_native_page(governor, request)
            hacker_news.fetch_native_page(governor, request)

        self.assertEqual(len(opener.opened), 2)
        self.assertEqual(
            governor.log[1].at_us - governor.log[0].at_us,
            adapters.DEFAULT_MIN_INTERVAL_MS * 1000,
        )

    def test_githubs_hour_leaves_sixty_at_once_and_then_refills_one_a_minute(self):
        # The 2026-08-10 probes: 60/hr anonymous, spent as one bucket. The declared
        # burst is what lets a run do useful work at all under a ceiling that
        # tight, and the interval is what stops it doing so twice.
        governor, opener, _ = self._paced(
            transport.GITHUB_REST_ROUTE, read_github("repo.json")
        )
        budget = runner.route_budgets()[transport.GITHUB_REST_ROUTE]
        request = gh_request(target_id=GITHUB_TARGET)

        with helpers.forbid_sleep():
            for _ in range(budget.burst):
                github_rest.fetch_native_page(governor, request)

        self.assertEqual(len(opener.opened), budget.burst)
        self.assertEqual([read.waited_us for read in governor.log], [0] * budget.burst)

        github_rest.fetch_native_page(governor, request)

        self.assertEqual(len(opener.opened), budget.burst + 1)
        self.assertGreater(governor.log[budget.burst].waited_us, 0)
