from tests.test_adapters_cases.hacker_news_claims import *  # noqa: F401,F403

GITHUB_FIXTURE_DIR = TEST_DIR / "fixtures" / "github"

GITHUB_TARGET = GITHUB_OWNER + "/" + GITHUB_REPO
# The roster row's four capabilities, named as the spec names them. The
# enumeration in the next section reads this tuple: an operation set that
# covers fewer of them is a capability this ticket did not deliver, and one
# that covers more is a surface nobody measured.
GITHUB_ROSTER_CAPABILITIES = ("repo", "issues", "releases", "search")


def read_github(name):
    """Read one offline GitHub fixture."""

    return GITHUB_FIXTURE_DIR.joinpath(name).read_text(encoding="utf-8")


def github_cases():
    """The measured case table: a request, a status, a body, and what it means."""

    return tuple(json.loads(read_github("github_cases.json"))["cases"])


def gh_request(query="", target_id="", cursor=""):
    return adapters.AdapterRequest(
        step_id="s1-gh",
        query=query,
        target_ids=(target_id,) if target_id else (),
        cursor=cursor,
    )


def gh_page(fixture, status=200, query="", target_id="", cursor="", module=None):
    """Run the adapter over one canned answer, with both buckets seeded."""

    clock = helpers.FakeClock()
    answer = (status, read_github(fixture), "application/json")
    carrier, opener = helpers.offline_transport(
        clock,
        {transport.GITHUB_REST_ROUTE: answer, transport.GITHUB_SEARCH_ROUTE: answer},
    )
    reading = github_rest if module is None else module
    return (
        reading.fetch_native_page(carrier, gh_request(query, target_id, cursor)),
        opener,
    )


class GithubReadTest(unittest.TestCase):
    """Four capabilities out of one anonymous client, and the row each returns.

    The 2026-08-10 probes recorded `api.github.com` answering anonymously and
    `rate_limit` reporting the ceiling that answer costs. The roster row names
    repos, issues, releases and search, and each is read here at the field set
    GitHub publishes it with — under GitHub's own names, because a name
    translated here would be a vocabulary this package invented.
    """

    def test_a_repository_is_asked_for_at_the_path_that_names_it(self):
        _, opener = gh_page("repo.json", target_id=GITHUB_TARGET)

        self.assertEqual(len(opener.opened), 1)
        self.assertEqual(opener.opened[0].route_id, transport.GITHUB_REST_ROUTE)
        self.assertEqual(
            urllib.parse.urlsplit(opener.opened[0].url).path, "/repos/" + GITHUB_TARGET
        )

    def test_a_repository_answer_carries_the_row_the_route_publishes(self):
        page, _ = gh_page("repo.json", target_id=GITHUB_TARGET)
        repository = page.records[0]

        self.assertEqual(len(page.records), 1)
        self.assertEqual(repository.canonical_content_kind, "repository")
        self.assertEqual(repository.native_item_id, "704212099")
        self.assertEqual(repository.title, GITHUB_TARGET)
        self.assertEqual(repository.author, GITHUB_OWNER)
        self.assertEqual(
            repository.canonical_locator, "https://github.com/" + GITHUB_TARGET
        )
        self.assertEqual(repository.published_at, "2024-11-03T09:14:22Z")
        self.assertEqual(
            counts_of(repository),
            {"stargazers_count": 8241, "forks_count": 512, "open_issues_count": 47},
        )
        self.assertEqual(attribute_pairs(repository, "language"), ("Python",))
        self.assertEqual(
            attribute_pairs(repository, "topics"), ("benchmarks", "inference", "gpu")
        )

    def test_issues_arrive_in_the_order_the_route_listed_them(self):
        page, opener = gh_page("issues.json", target_id="issues:" + GITHUB_TARGET)

        self.assertEqual(
            urllib.parse.urlsplit(opener.opened[0].url).path,
            "/repos/" + GITHUB_TARGET + "/issues",
        )
        self.assertEqual(
            [record.native_item_id for record in page.records],
            ["2411900731", "2411004488", "2409776610"],
        )
        self.assertEqual(
            sorted({record.canonical_content_kind for record in page.records}), ["issue"]
        )
        self.assertEqual([record.native_position for record in page.records], [0, 1, 2])

    def test_an_issue_carries_its_own_comment_count_and_a_zero_is_one(self):
        page, _ = gh_page("issues.json", target_id="issues:" + GITHUB_TARGET)

        self.assertEqual(
            [counts_of(record)["comments"] for record in page.records], [23, 31, 0]
        )
        # Nobody has commented on the third, and that is a count GitHub
        # reported rather than a field it left out.
        self.assertEqual(page.records[2].loss, ())
        self.assertEqual(page.records[0].author, "bramble")
        self.assertEqual(attribute_pairs(page.records[0], "number"), ("812",))
        self.assertEqual(attribute_pairs(page.records[0], "state"), ("open",))

    def test_an_issue_names_its_repository_only_the_way_the_route_does(self):
        # A listed issue states its repository as an api address and never as
        # the numeric id this package identifies a repository by. The address
        # is carried verbatim so a caller can tie the two, and no id is
        # recovered from a url — that would be this adapter inventing an
        # identity out of a string it was handed.
        page, _ = gh_page("issues.json", target_id="issues:" + GITHUB_TARGET)
        issue = page.records[0]

        self.assertEqual(issue.native_parent_id, "")
        self.assertEqual(
            attribute_pairs(issue, "repository_url"),
            ("https://api.github.com/repos/" + GITHUB_TARGET,),
        )

    def test_releases_carry_their_tag_and_the_moment_they_were_published(self):
        page, opener = gh_page("releases.json", target_id="releases:" + GITHUB_TARGET)
        first = page.records[0]

        self.assertEqual(
            urllib.parse.urlsplit(opener.opened[0].url).path,
            "/repos/" + GITHUB_TARGET + "/releases",
        )
        self.assertEqual(len(page.records), 2)
        self.assertEqual(first.canonical_content_kind, "release")
        self.assertEqual(first.title, "v0.9.0 — split-GPU runs")
        self.assertEqual(attribute_pairs(first, "tag_name"), ("v0.9.0",))
        # The release's own publication moment, not the commit's creation one.
        self.assertEqual(first.published_at, "2026-08-05T10:44:19Z")
        self.assertEqual(first.engagement, ())

    def test_search_yields_repositories_at_the_index_the_evidence_measured(self):
        page, opener = gh_page("search_repositories.json", query="gpu benchmark")
        asked = urllib.parse.urlsplit(opener.opened[0].url)

        # The 2026-08-10 probes: `api.github.com/search/repositories` answered 200
        # anonymously, and `rate_limit` counts it against its own bucket.
        self.assertEqual(opener.opened[0].route_id, transport.GITHUB_SEARCH_ROUTE)
        self.assertEqual(asked.path, "/search/repositories")
        self.assertEqual(urllib.parse.parse_qsl(asked.query), [("q", "gpu benchmark")])
        self.assertEqual(len(page.records), 2)
        self.assertEqual(
            [record.native_item_id for record in page.records], ["704212099", "512900744"]
        )
        self.assertEqual(
            sorted({record.canonical_content_kind for record in page.records}),
            ["repository"],
        )

    def test_a_search_hit_and_a_repository_read_name_the_same_thing(self):
        # One adapter, two buckets, one id space: a hit and a read of the same
        # repository will group rather than stand as two unrelated rows.
        found, _ = gh_page("search_repositories.json", query="gpu benchmark")
        read, _ = gh_page("repo.json", target_id=GITHUB_TARGET)

        self.assertEqual(found.records[0].native_item_id, read.records[0].native_item_id)
        self.assertEqual(
            found.records[0].canonical_locator, read.records[0].canonical_locator
        )
        self.assertNotEqual(found.route_id, read.route_id)

    def test_the_index_states_a_total_and_no_next_page_so_none_is_invented(self):
        # GitHub states how many repositories matched and never how many pages
        # it split them into. Turning a total into a next page needs a page
        # size this adapter did not send, so the cursor stays the caller's.
        page, _ = gh_page("search_repositories.json", query="gpu benchmark")

        self.assertEqual(page.cursor_out, "")

    def test_a_page_the_core_hands_back_is_spent_as_the_routes_own_page(self):
        _, opener = gh_page(
            "search_repositories.json", query="gpu benchmark", cursor="4"
        )
        asked = urllib.parse.urlsplit(opener.opened[0].url)

        self.assertEqual(len(opener.opened), 1)
        self.assertIn(("page", "4"), urllib.parse.parse_qsl(asked.query))

    def test_a_row_short_of_its_fields_says_so_and_a_star_count_of_zero_is_one(self):
        page, _ = gh_page("repo_partial.json", target_id="quilling/kvcache-notes")
        repository = page.records[0]

        self.assertEqual(repository.loss, ("field_omitted",))
        self.assertEqual(repository.author, "")
        self.assertEqual(repository.published_at, "")
        self.assertEqual(
            counts_of(repository),
            {"stargazers_count": 0, "forks_count": 0, "open_issues_count": 0},
        )


def typed_github_pages(module):
    """Type every measured case through one adapter's own ``fetch_native_page``."""

    return {
        row["case_name"]: gh_page(
            row["body_fixture"],
            status=row["status"],
            query=row["query"],
            target_id=row["target_id"],
            cursor=row["cursor"],
            module=module,
        )[0]
        for row in github_cases()
    }


def assert_a_spent_hour_is_never_a_missing_credential(case, adapter_id, pages):
    """The oracle: nothing this route answers says a credential was needed.

    GitHub's documented answer to an anonymous client that has spent its 60/hr
    is 403 with a message about rate limits. An adapter that read that as
    `auth_required` would report the roster's tightest budget as a missing
    credential — a keyless capability recorded as a credentialed one, which is
    the exact false claim the measured access ladder exists to prevent. The
    same rule holds in the other direction for the empties: a repository with
    nothing open and a search that matched nothing are answers, not shape
    changes.
    """

    for row in github_cases():
        name = row["case_name"]
        case.assertIn(name, pages, "{0} produced no page for case {1}".format(adapter_id, name))
        page = pages[name]
        loss = tuple(page.loss)
        detail = " {0} typed case {1} as outcome {2} loss {3}".format(
            adapter_id, name, page.outcome, loss
        )
        if github_rest.AUTH_REQUIRED in loss:
            case.fail("a keyless route was recorded as needing a credential:" + detail)
        if row["answer_kind"] == "no_matches":
            if github_rest.SCHEMA_DRIFT in loss:
                case.fail(
                    "an answer stating there is nothing there was recorded as a payload"
                    " that moved:" + detail
                )
            if page.records:
                case.fail("an answer stating there is nothing there carried rows:" + detail)
        elif row["answer_kind"] == "drifted" and page.outcome != "failed":
            case.fail("a payload that moved was recorded as an answer:" + detail)
        elif row["answer_kind"] == "records" and not page.records:
            case.fail("an answer carrying rows produced none:" + detail)
        case.assertEqual(
            page.outcome,
            row["expected_outcome"],
            "case {0} came back {1}, its evidence says {2}".format(
                name, page.outcome, row["expected_outcome"]
            ),
        )
        case.assertEqual(
            loss, (row["expected_loss"],) if row["expected_loss"] else (), detail
        )


class GithubIsNeverCredentialedTest(unittest.TestCase):
    """Criterion 1 at its sharpest: the tightest budget in the roster is not a wall."""

    def test_every_measured_case_is_typed_as_its_evidence_says(self):
        assert_a_spent_hour_is_never_a_missing_credential(
            self, "github_rest", typed_github_pages(github_rest)
        )

    def test_an_hour_spent_is_the_status_it_is_and_never_a_credential_problem(self):
        page, _ = gh_page("rate_limit_exceeded.json", status=403, target_id=GITHUB_TARGET)

        self.assertEqual(page.outcome, "failed")
        self.assertEqual(page.loss, ("http_status",))
        self.assertNotIn(github_rest.AUTH_REQUIRED, page.loss)
        # The warning says which two things GitHub documents this status as, so
        # a reader is not left to parse the body for it.
        self.assertIn("403", " ".join(page.warnings))
        self.assertIn("60", " ".join(page.warnings))

    def test_a_repository_with_nothing_open_is_not_a_route_that_moved(self):
        empty, _ = gh_page("issues_none_open.json", target_id="issues:" + GITHUB_TARGET)
        moved, _ = gh_page("repo_reshaped.json", target_id=GITHUB_TARGET)

        self.assertEqual(empty.outcome, "empty")
        self.assertEqual(empty.loss, ())
        self.assertTrue(empty.warnings)
        self.assertEqual(moved.outcome, "failed")
        self.assertEqual(moved.loss, (github_rest.SCHEMA_DRIFT,))


class GithubDescriptorTest(unittest.TestCase):
    """Two buckets, measured apart, declared apart, and paced apart."""

    def test_the_core_bucket_declares_the_ceiling_the_evidence_measured(self):
        # The 2026-08-10 probes: `api.github.com/rate_limit` reported the anonymous
        # ceiling as 60/hr. GitHub spends that as one hourly bucket, so sixty
        # reads may leave at once and one refills per minute. T04 seeded these
        # three numbers as a replay constant before this route existed; the
        # shipped descriptor is that seed, which is what ties the scheduler's
        # arithmetic to the route it paces.
        self.assertEqual(
            runner.route_budgets()[transport.GITHUB_REST_ROUTE],
            runner.RouteBudget(min_interval_ms=60000, burst=60, cooldown_ms=3600000),
        )
        self.assertEqual(
            runner.route_budgets()[transport.GITHUB_REST_ROUTE],
            test_pipeline.GITHUB_REST_BUDGET,
        )

    def test_the_search_bucket_declares_its_own_hour(self):
        # `rate_limit` reported core and code_search separately, at 60/hr each.
        # Two buckets, so a search never spends a repository read's budget.
        self.assertEqual(
            runner.route_budgets()[transport.GITHUB_SEARCH_ROUTE],
            runner.route_budgets()[transport.GITHUB_REST_ROUTE],
        )
        self.assertNotEqual(transport.GITHUB_SEARCH_ROUTE, transport.GITHUB_REST_ROUTE)

    def test_each_surface_declares_the_route_it_reads_under_one_adapter_id(self):
        self.assertEqual(
            [descriptor.route_id for descriptor in github_rest.SURFACE_DESCRIPTORS],
            [transport.GITHUB_REST_ROUTE, transport.GITHUB_SEARCH_ROUTE],
        )
        for descriptor in github_rest.SURFACE_DESCRIPTORS:
            with self.subTest(route=descriptor.route_id):
                self.assertEqual(descriptor.adapter_id, "github_rest")
                self.assertEqual(descriptor.access_class, "K0")
                self.assertEqual(descriptor.platform, "github")
                self.assertEqual(descriptor.operator_identity, "github")
                self.assertEqual(descriptor.representation_kind, "native")
                self.assertEqual(descriptor.standing_loss, ())
                self.assertEqual(descriptor.volatile_identifiers, ())

    def test_it_declares_the_comment_count_an_issue_reports_and_no_reply_count(self):
        # An issue reports an exact count of its comments and nothing here
        # reports a count of replies, so one name is declared and one is not.
        self.assertEqual(github_rest.DESCRIPTOR.comment_count_metric, "comments")
        for descriptor in github_rest.SURFACE_DESCRIPTORS:
            with self.subTest(route=descriptor.route_id):
                self.assertEqual(descriptor.reply_count_metric, "")

    def test_the_core_reaches_it_by_both_literal_branches_and_sees_both_surfaces(self):
        self.assertIn("github_rest", runner.ADAPTER_IDS)
        self.assertIs(runner.descriptor_for("github_rest"), github_rest.DESCRIPTOR)
        self.assertEqual(
            runner.surface_descriptors("github_rest"), github_rest.SURFACE_DESCRIPTORS
        )

        clock = helpers.FakeClock()
        carrier, opener = helpers.offline_transport(
            clock,
            {transport.GITHUB_REST_ROUTE: (200, read_github("repo.json"), "application/json")},
        )
        page = runner.call_adapter("github_rest", carrier, gh_request(target_id=GITHUB_TARGET))

        self.assertEqual(len(page.records), 1)
        self.assertEqual(len(opener.opened), 1)
