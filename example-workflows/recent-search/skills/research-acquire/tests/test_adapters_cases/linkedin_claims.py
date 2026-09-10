from tests.test_adapters_cases.linkedin_jobs_and_profile import *  # noqa: F401,F403

def profile_manifest():
    """One dispatch reading one public profile."""

    return schema.AcquisitionManifest(
        manifest_id="m-li",
        mode="staged",
        as_of="2026-08-10T09:00:00Z",
        steps=(
            schema.AcquisitionStep(
                step_id="s1-profile",
                kind="hydration",
                adapter_id="linkedin_public",
                selected_hits=(
                    schema.SelectedHit(
                        discovery_locator="https://www.linkedin.com/in/" + PROFILE_SLUG,
                        target_id=PROFILE_SLUG,
                    ),
                ),
                max_items=5,
            ),
        ),
    )


class NamedAttributeCarrierTest(unittest.TestCase):
    """The one protocol extension this pair needed, and the law it carries.

    Four of `linkedin_public`'s six roster fields are named string facts, three
    of them repeated, and no other record field means any of them. Forcing them
    into `community` or `title` would alias a field that means a subreddit on
    one adapter into meaning a city on another, which is the same error the
    descriptor's metric law forbids for engagement counts. So they travel under
    their own names, and nothing else about a record moves.
    """

    def _artifact(self):
        clock = helpers.FakeClock()
        carrier, _ = helpers.offline_transport(
            clock,
            {
                transport.LINKEDIN_PUBLIC_PROFILE_ROUTE: (
                    200,
                    read_linkedin("profile_person.html"),
                    "text/html",
                )
            },
        )
        return runner.run_acquisition(profile_manifest(), carrier, clock=clock.monotonic)

    def test_a_repeated_named_fact_reaches_the_artifact_in_the_blocks_own_order(self):
        # The claim closes where a caller keeps it. A page-level assertion
        # would leave the artifact free to drop the whole family.
        artifact = self._artifact()
        carried = profile_roster_row(artifact.records[0])

        self.assertEqual(len(artifact.records), 1)
        self.assertEqual(
            carried["jobTitle"], ["Principal Reliability Engineer", "Board Advisor"]
        )
        self.assertEqual(carried["worksFor"], ["Northwind Analytics", "Kestrel Systems"])
        self.assertEqual(artifact.records[0].time_confidence, "unknown")
        self.assertEqual(artifact.records[0].access_class, "K2")

    def test_a_record_from_a_route_reporting_no_named_fact_carries_none(self):
        # Defaulted and additive: every adapter that reported nothing under a
        # name still reports nothing, and no existing record grew a field with
        # something in it.
        page, _ = adapter_page(
            x_syndication, 200, read_fixture("syndication_timeline.html")
        )

        self.assertEqual(page.records[0].attributes, ())

    def test_a_named_fact_that_is_not_a_string_is_refused_rather_than_coerced(self):
        # Same bar as an engagement snapshot: the exact value as reported, or
        # nothing. A number stringified here would be a fact this package made.
        native = adapters.NativeRecord(
            canonical_content_kind="profile",
            canonical_locator="https://example.test/x",
            attributes=(("jobTitle", 7),),
        )

        with self.assertRaises(normalize.NormalizeError):
            normalize.normalize_page(
                adapters.build_native_page(linkedin_public.DESCRIPTOR, (native,)),
                profile_manifest().steps[0],
                "artifact:m-li",
                "m-li",
            )


SCHEMA_DRIFT = "schema_drift"

WRONG_LINKEDIN_ADAPTERS = (
    "chrome_as_authwall_adapter",
    "absent_block_as_empty_adapter",
    "every_page_as_drift_adapter",
)


def linkedin_chrome_cases():
    """The measured case table: a status, a body, and the loss its evidence names."""

    return tuple(json.loads(read_linkedin("authwall_chrome_cases.json"))["cases"])


def typed_profile_pages(module):
    """Type every measured case through one adapter's own ``fetch_native_page``."""

    return {
        row["case_name"]: adapter_page(
            module,
            row["status"],
            read_linkedin(row["body_fixture"]),
            content_type="text/html",
            request=adapters.AdapterRequest(step_id="s1-li", target_ids=(row["slug"],)),
        )[0]
        for row in linkedin_chrome_cases()
    }


def names_read(path, name):
    """How many times one source reads a name, its own definition excluded.

    A constant a module declares and never reads is a statement that the module
    has seen the thing and does not act on it. That is exactly what
    ``NAVIGATION_CHROME`` is for, and a count is the only way to check it from
    outside — a string scan would count the module's own prose.

    Both ways of reaching it are counted: bare, as the declaring module would,
    and through its module, as anything else would. A scan that counted only
    the first would pass any module that imported the constant instead.
    """

    read = 0
    for owner in adapter_owner_paths(path):
        for node in ast.walk(ast.parse(owner.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Name) and node.id == name:
                read += 1 if isinstance(node.ctx, ast.Load) else 0
            elif isinstance(node, ast.Attribute) and node.attr == name:
                read += 1
    return read


def assert_chrome_is_never_an_authwall(case, adapter_id, pages):
    """The row-2 and row-3 oracle: the chrome decides nothing, and drift is typed.

    ``pages`` maps a measured case name to the ``NativePage`` some adapter
    produced for it. Four confusions are called out by name, because each is a
    different wrong thing to believe. Chrome read as an authwall re-creates the
    999 assumption the measurement overturned and puts a keyless route back
    outside the roster. A populated block read as empty loses a profile the
    origin served. A missing block read as an authwall blames a credential
    nobody withheld, and read as an empty profile says a member has nothing on
    a page that never said so. And typing drift onto answers that carry no
    structural evidence sends an operator hunting a markup change that did not
    happen.
    """

    for row in linkedin_chrome_cases():
        name = row["case_name"]
        case.assertIn(name, pages, "{0} produced no page for case {1}".format(adapter_id, name))
        page = pages[name]
        loss = tuple(page.loss)
        detail = " {0} typed case {1} as outcome {2} loss {3}".format(
            adapter_id, name, page.outcome, loss
        )
        if row["expected_outcome"] == "ok":
            if linkedin_public.AUTH_REQUIRED in loss:
                case.fail("navigation chrome was recorded as an authwall:" + detail)
            # Ordered most specific first: a good page typed as drift is also a
            # page with no records on it, and naming the cause beats naming the
            # symptom.
            if SCHEMA_DRIFT in loss:
                case.fail(
                    "a populated ld+json block was recorded as a page that changed"
                    " shape:" + detail
                )
            if not page.records:
                case.fail(
                    "a populated ld+json block was recorded as an empty profile:" + detail
                )
        elif row["expected_loss"] == SCHEMA_DRIFT:
            if linkedin_public.AUTH_REQUIRED in loss:
                case.fail("a missing ld+json block was recorded as an authwall:" + detail)
            if page.records or page.outcome != "failed":
                case.fail(
                    "a missing ld+json block was recorded as an empty profile:" + detail
                )
            if SCHEMA_DRIFT not in loss:
                case.fail("a missing ld+json block was not recorded as one:" + detail)
        elif SCHEMA_DRIFT in loss:
            case.fail(
                "an answer carrying no structural evidence was recorded as drift:" + detail
            )
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


class ChromeIsNotAnAuthwallTest(unittest.TestCase):
    """Criteria 2 and 3: this pair's spine, and the finding it exists to protect.

    The superseded spec placed LinkedIn entirely outside the roster on an
    assumed 999 authwall. Measured, ``linkedin.com/in/<slug>`` answers 200 with
    a complete Person block and the sign-in strings sit in that same page as
    navigation chrome. An adapter that reads them re-creates the false negative
    the evidence overturned; one that answers a missing block with silence
    loses the drift that a ``K2`` route is exposed to by construction.
    """

    def test_every_measured_case_is_typed_as_its_evidence_says(self):
        assert_chrome_is_never_an_authwall(
            self, "linkedin_public", typed_profile_pages(linkedin_public)
        )

    def test_the_bodies_that_claim_to_carry_the_chrome_really_do(self):
        # Without this the whole table could be satisfied by fixtures that
        # quietly have no chrome in them, and the claim would be about nothing.
        carrying = 0
        for row in linkedin_chrome_cases():
            body = read_linkedin(row["body_fixture"]).lower()
            present = all(marker in body for marker in linkedin_public.NAVIGATION_CHROME)

            self.assertEqual(present, row["chrome_present"], row["body_fixture"])
            carrying += 1 if present else 0

        self.assertGreater(carrying, 1)

    def test_the_shipped_adapter_never_reads_the_chrome_it_names(self):
        # The structural half. The module declares the two strings so a reader
        # knows it has seen them, and reads the constant nowhere: no branch, no
        # filter, no warning. A count of zero is the statement.
        self.assertEqual(
            names_read(ADAPTER_DIR / "linkedin_public.py", "NAVIGATION_CHROME"), 0
        )

    def test_the_same_bytes_at_two_statuses_are_two_different_answers(self):
        # The sharpest form of the rule. One body, twice: at 200 it is a page
        # that changed shape, at 403 it is the origin refusing. Nothing in the
        # body moved, so nothing in the body decided.
        drifted, _ = profile_page("profile_chrome_only.html")
        refused, _ = profile_page("profile_chrome_only.html", status=403)

        self.assertEqual(drifted.loss, (SCHEMA_DRIFT,))
        self.assertEqual(refused.loss, (linkedin_public.AUTH_REQUIRED,))

    def test_a_refusal_carrying_no_chrome_at_all_still_fails(self):
        # The mirror of the first row: chrome does not make a refusal, and its
        # absence does not make an answer. Only the status did.
        page, _ = profile_page("profile_request_denied_999.html", status=999)

        self.assertEqual(page.outcome, "failed")
        self.assertEqual(page.loss, ("http_status",))
        self.assertIn("999", " ".join(page.warnings))

    def test_a_reshaped_block_names_what_it_looked_for(self):
        page, _ = profile_page("profile_reshaped_graph.html")
        warning = " ".join(page.warnings)

        self.assertIn(linkedin_public.PERSON_TYPE, warning)
        self.assertIn(linkedin_public.NODE_TYPE_KEY, warning)

    def test_no_linkedin_route_returns_auth_required_with_an_empty_credential_store(self):
        # Criterion 1's other half. Both routes are keyless: the only way
        # `auth_required` can appear is the origin's own 401 or 403, never the
        # absence of something this package was supposed to have.
        for module, fixture, request in (
            (linkedin_public, "profile_person.html", LINKEDIN_PROFILE_REQUEST),
            (linkedin_jobs, "jobs_search_page.html", JOBS_REQUEST),
        ):
            with self.subTest(adapter=module.DESCRIPTOR.adapter_id):
                page, _ = adapter_page(
                    module,
                    200,
                    read_linkedin(fixture),
                    content_type="text/html",
                    request=request,
                )

                self.assertNotIn("auth_required", page.loss)
                self.assertEqual(page.outcome, "ok")
                self.assertTrue(transport.route_admissions()[module.DESCRIPTOR.route_id])
                self.assertIsNone(transport.route_credential(module.DESCRIPTOR.route_id))


class ChromeOracleCanFailTest(unittest.TestCase):
    """Criterion 5: the oracle above rejects a wrong result, in every direction.

    All three adapters here are written beside the tree and loaded by path.
    Each is ``linkedin_public`` with exactly one branch replaced, which is what
    makes a rejection attributable to that branch and to nothing else. Nothing
    in the package produces them and nothing under test is mutated to obtain
    them.
    """

    def _assert_oracle_rejects(self, name, reason):
        wrong = load_adapter_fixture(name, directory=LINKEDIN_FIXTURE_DIR)

        with self.assertRaises(AssertionError) as caught:
            assert_chrome_is_never_an_authwall(self, name, typed_profile_pages(wrong))

        self.assertIn(reason, str(caught.exception))

    def test_an_adapter_that_reads_the_chrome_as_an_authwall_fails_the_oracle(self):
        # Row 5's named case: the strings the measurement called navigation
        # chrome are read as a refusal, so a keyless route with a complete
        # block on it comes back credentialed and LinkedIn drops out of the
        # roster again.
        self._assert_oracle_rejects(
            "chrome_as_authwall_adapter", "navigation chrome was recorded as an authwall"
        )

    def test_an_adapter_that_answers_a_missing_block_with_nothing_fails_the_oracle(self):
        self._assert_oracle_rejects(
            "absent_block_as_empty_adapter",
            "a missing ld+json block was recorded as an empty profile",
        )

    def test_an_adapter_that_calls_every_page_drift_fails_the_oracle(self):
        # The opposite error. Without this side the oracle could be satisfied
        # by typing everything as drift, which would report a page that changed
        # shape every time a profile was read successfully.
        self._assert_oracle_rejects(
            "every_page_as_drift_adapter",
            "a populated ld+json block was recorded as a page that changed shape",
        )

    def test_the_same_oracle_passes_on_the_shipped_adapter(self):
        assert_chrome_is_never_an_authwall(
            self, "linkedin_public", typed_profile_pages(linkedin_public)
        )

    def test_the_chrome_scan_can_fail(self):
        # Which is what makes the shipped adapter's count of zero worth
        # anything: a module beside the tree that does read the constant is
        # named by the same scan.
        self.assertGreater(
            names_read(
                LINKEDIN_FIXTURE_DIR / "chrome_as_authwall_adapter.py", "NAVIGATION_CHROME"
            ),
            0,
        )

    def test_nothing_in_the_package_can_reach_a_wrong_linkedin_adapter(self):
        named = [
            path.name
            for path in PACKAGE_DIR.rglob("*.py")
            for name in WRONG_LINKEDIN_ADAPTERS
            if name in path.read_text(encoding="utf-8")
        ]

        self.assertEqual(named, [])


class LinkedInOneCallOnePageTest(unittest.TestCase):
    """Criterion 4: one bounded call in, exactly one page out, whatever comes back."""

    def _every_case(self):
        for row in linkedin_chrome_cases():
            yield (
                "linkedin_public/" + row["case_name"],
                linkedin_public,
                row["status"],
                read_linkedin(row["body_fixture"]),
                adapters.AdapterRequest(step_id="s1-li", target_ids=(row["slug"],)),
            )
        jobs = (
            ("search_page", 200, "jobs_search_page.html"),
            ("empty_list", 200, "jobs_empty_list.html"),
            ("reshaped", 200, "jobs_reshaped_markup.html"),
            ("partial_card", 200, "jobs_partial_card.html"),
        )
        for name, status, fixture in jobs:
            yield (
                "linkedin_jobs/" + name,
                linkedin_jobs,
                status,
                read_linkedin(fixture),
                JOBS_REQUEST,
            )
        for status in (429, 503, 999):
            yield (
                "linkedin_jobs/http_{0}".format(status),
                linkedin_jobs,
                status,
                "<html><body>no</body></html>",
                JOBS_REQUEST,
            )

    def test_every_answer_costs_one_call_on_the_adapters_own_route(self):
        for name, module, status, body, request in self._every_case():
            with self.subTest(case=name):
                page, opener = adapter_page(
                    module, status, body, content_type="text/html", request=request
                )

                self.assertEqual(len(opener.opened), 1)
                self.assertEqual(
                    [call.route_id for call in opener.opened], [module.DESCRIPTOR.route_id]
                )
                self.assertEqual(page.route_id, module.DESCRIPTOR.route_id)
                self.assertIsInstance(page, adapters.NativePage)

    def test_neither_adapter_names_another_adapter_or_the_cores_dispatch(self):
        for module_name, own_id in (
            ("linkedin_jobs.py", "linkedin_jobs"),
            ("linkedin_public.py", "linkedin_public"),
        ):
            with self.subTest(module=module_name):
                self.assertEqual(adapters_named(ADAPTER_DIR / module_name, own_id), [])
                self.assertNotIn(
                    "call_adapter", adapter_owner_source(ADAPTER_DIR / module_name)
                )

    def test_neither_adapter_reads_a_file_opens_a_socket_or_waits(self):
        cases = (
            (linkedin_public, "profile_person.html", LINKEDIN_PROFILE_REQUEST),
            (linkedin_jobs, "jobs_search_page.html", JOBS_REQUEST),
        )

        for module, fixture, request in cases:
            with self.subTest(adapter=module.DESCRIPTOR.adapter_id):
                clock = helpers.FakeClock()
                carrier, _ = helpers.offline_transport(
                    clock,
                    {module.DESCRIPTOR.route_id: (200, read_linkedin(fixture), "text/html")},
                )

                with helpers.forbid_io():
                    with helpers.forbid_sleep():
                        page = module.fetch_native_page(carrier, request)

                self.assertEqual(page.outcome, "ok")

    def test_a_local_block_is_never_recorded_as_a_platform_gap(self):
        # Inherited from the protocol by writing nothing: `fetch_one_page`
        # reads the channel verdict ahead of any status test either adapter
        # runs, so a captive portal's 503 is `network_intercepted` and not a
        # LinkedIn authwall.
        portal = TRANSPORT_FIXTURE_DIR.joinpath("captive_portal.html").read_text(
            encoding="utf-8"
        )

        for module, request in (
            (linkedin_public, LINKEDIN_PROFILE_REQUEST),
            (linkedin_jobs, JOBS_REQUEST),
        ):
            with self.subTest(adapter=module.DESCRIPTOR.adapter_id):
                page, _ = adapter_page(
                    module, 503, portal, content_type="text/html", request=request
                )

                self.assertEqual(page.loss, (transport.NETWORK_INTERCEPTED,))
                self.assertEqual(page.outcome, "failed")


# The 2026-08-10 probes (LinkedIn public profile): 577 KB per answer, the largest in
# the roster. Held against `MAX_ENTRY_BYTES` below, because whether a route's
# declared window can ever bind depends on it.
