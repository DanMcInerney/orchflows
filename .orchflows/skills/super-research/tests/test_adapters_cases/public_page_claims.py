from tests.test_adapters_cases.public_page_read import *  # noqa: F401,F403

class PublicPageIsSelectedNotGenericTest(unittest.TestCase):
    """Row 2: the one adapter that could have been an HTTP primitive, and is not.

    The spec's non-goals forbid "any generic HTTP/CLI/exec primitive". Every
    other adapter here honours that by construction — a caller cannot point
    `github_rest` at Wikipedia because the route shape is GitHub's. This one is
    the only one where the constraint had to be built rather than inherited,
    and if it leaked, every other constraint in this package would be
    decorative: any route at all could be reached through it.
    """

    def test_the_reachable_target_set_is_selected_and_enumerable(self):
        assert_the_target_set_is_selected_and_enumerable(self, "public_page", public_page)

    def test_the_selection_set_is_exactly_the_roster_row_and_nothing_wider(self):
        self.assertEqual(sorted(public_page.PAGE_SELECTIONS), sorted(PAGE_ROSTER_SELECTIONS))
        self.assertEqual(
            sorted(
                descriptor.route_id
                for descriptor in runner.surface_descriptors("public_page")
            ),
            [transport.PUBLIC_PAGE_ARTICLE_ROUTE, transport.PUBLIC_PAGE_CONTROL_ROUTE],
        )

    def test_the_manifest_can_name_a_selection_and_can_express_nothing_else(self):
        # "Constrained by the manifest" from the other end: a caller writes a
        # manifest, so the manifest cannot be what limits it — what limits it is
        # that every string a manifest can carry resolves to a selection or to
        # a refusal, and a refusal costs the origin nothing.
        clock = helpers.FakeClock()
        carrier, opener = helpers.offline_transport(
            clock,
            {
                route_id: (200, read_public_page("article.html"), "text/html")
                for route_id in transport.ROUTE_CONSTANTS
            },
        )
        manifest = schema.AcquisitionManifest(
            manifest_id="m-page",
            mode="staged",
            as_of="2026-08-10T09:05:00Z",
            steps=(
                schema.AcquisitionStep(
                    step_id="s1-selected",
                    kind="hydration",
                    adapter_id="public_page",
                    selected_hits=(
                        schema.SelectedHit(
                            discovery_locator=ARTICLE_LOCATOR, target_id=ARTICLE_TARGET
                        ),
                        schema.SelectedHit(
                            discovery_locator="https://evil.example/x",
                            target_id="https://evil.example/x",
                        ),
                    ),
                    max_items=10,
                ),
            ),
        )

        artifact = runner.run_acquisition(manifest, carrier, clock=clock.monotonic)

        # Two hits, one document: the one that named a selection was read and
        # the one that named an address was refused before any socket.
        self.assertEqual(len(artifact.records), 1)
        self.assertEqual(len(opener.opened), 1)
        self.assertEqual(artifact.records[0].canonical_locator, ARTICLE_LOCATOR)
        self.assertEqual(artifact.steps[0].outcome, "partial")

    def test_no_cli_shell_or_exec_surface_is_reachable_through_it(self):
        source = ADAPTER_DIR / "public_page.py"
        imported = {
            name
            for owner in adapter_owner_paths(source)
            for name in helpers.imported_names(owner)
        }
        attributes = {
            name
            for owner in adapter_owner_paths(source)
            for name in helpers.attribute_names(owner)
        }
        strings = code_strings(source)

        for module_name in EXECUTION_MODULES:
            with self.subTest(module=module_name):
                self.assertNotIn(module_name, imported)
        for name in EXECUTION_NAMES:
            with self.subTest(name=name):
                self.assertEqual(
                    [spelled for spelled in attributes if spelled.endswith("." + name)], []
                )
        # And no string here could become a command, an argument vector, or a
        # scheme that runs something.
        for dangerous in ("sh -c", "/bin/", "cmd.exe", "javascript:", "data:", "file:"):
            with self.subTest(spelling=dangerous):
                self.assertEqual(
                    [spelling for spelling in strings if dangerous in spelling], []
                )

    def test_it_runs_to_completion_with_every_file_socket_and_wait_forbidden(self):
        clock = helpers.FakeClock()
        carrier, _ = helpers.offline_transport(
            clock,
            {
                transport.PUBLIC_PAGE_ARTICLE_ROUTE: (
                    200,
                    read_public_page("article.html"),
                    "text/html",
                )
            },
        )

        with helpers.forbid_io():
            with helpers.forbid_sleep():
                page = public_page.fetch_native_page(carrier, page_request(ARTICLE_TARGET))

        self.assertEqual(page.outcome, "ok")

    def test_a_refused_target_is_a_refusal_and_never_a_missing_credential(self):
        page, opener = selected_page("article.html", target="https://evil.example/x")

        self.assertEqual(page.outcome, "refused")
        self.assertEqual(page.loss, (public_page.UNSELECTED_TARGET,))
        self.assertEqual(opener.opened, [])
        self.assertNotIn(public_page.AUTH_REQUIRED, page.loss)
        self.assertIn("selection", " ".join(page.warnings))

    def test_the_code_for_a_missing_credential_is_declared_and_never_produced(self):
        self.assertEqual(public_page.AUTH_REQUIRED, "auth_required")
        self.assertEqual(names_read(ADAPTER_DIR / "public_page.py", "AUTH_REQUIRED"), 0)

    def test_a_refusal_names_the_selection_the_caller_asked_for(self):
        # A two-surface adapter can charge a refusal to a surface nobody named:
        # the core reads `page.route_id` into the step and into the work
        # ledger, so a refused `control` would otherwise be recorded against
        # the article route — a read attributed to an origin that was never
        # asked, which is the defect a two-surface adapter makes visible.
        refused_control, _ = selected_page("control.html", target="control:something")
        refused_article, _ = selected_page("article.html", target="article:a/b")
        refused_unknown, _ = selected_page("article.html", target="https://evil.example/x")

        self.assertEqual(refused_control.outcome, "refused")
        self.assertEqual(refused_control.route_id, transport.PUBLIC_PAGE_CONTROL_ROUTE)
        self.assertEqual(refused_article.route_id, transport.PUBLIC_PAGE_ARTICLE_ROUTE)
        # A target naming no selection at all is the primary's to report: there
        # is no better answer, and the warning says what was asked for.
        self.assertEqual(refused_unknown.route_id, transport.PUBLIC_PAGE_ARTICLE_ROUTE)

    def test_a_refusal_reaches_the_work_ledger_charged_to_no_read(self):
        clock = helpers.FakeClock()
        carrier, opener = helpers.offline_transport(
            clock,
            {
                route_id: (200, read_public_page("control.html"), "text/html")
                for route_id in transport.ROUTE_CONSTANTS
            },
        )
        run = runner.run_scheduled(
            schema.AcquisitionManifest(
                manifest_id="m-refused",
                mode="staged",
                as_of="2026-08-10T09:05:00Z",
                steps=(
                    schema.AcquisitionStep(
                        step_id="s1-refused",
                        kind="hydration",
                        adapter_id="public_page",
                        selected_hits=(
                            schema.SelectedHit(
                                discovery_locator=CONTROL_LOCATOR,
                                target_id="control:something",
                            ),
                        ),
                        max_items=5,
                    ),
                ),
            ),
            carrier,
            clock=clock.monotonic,
        )

        self.assertEqual(opener.opened, [])
        self.assertEqual(run.artifact.records, ())
        self.assertEqual(run.artifact.steps[0].outcome, "refused")
        self.assertEqual(
            [event.route_id for event in runner.planned_operations(run.ledger)],
            [transport.PUBLIC_PAGE_CONTROL_ROUTE],
        )
        # A page was produced and no call was spent, which is exactly what a
        # refusal costs.
        self.assertEqual(runner.ledger_sums(run.ledger)["calls"], 0)
        self.assertEqual(runner.ledger_sums(run.ledger)["pages"], 1)


class PublicPageOracleCanFailTest(unittest.TestCase):
    """Row 5: the oracle above rejects an adapter a caller can point anywhere."""

    def _wrong(self, name):
        return load_adapter_fixture(name, directory=PUBLIC_PAGE_FIXTURE_DIR)

    def test_an_adapter_that_takes_a_url_from_its_caller_fails_the_oracle(self):
        with self.assertRaisesRegex(AssertionError, "caller chose the host a read went to"):
            assert_the_target_set_is_selected_and_enumerable(
                self, WRONG_PAGE_ADAPTERS[0], self._wrong(WRONG_PAGE_ADAPTERS[0])
            )

    def test_an_adapter_that_selects_nothing_at_all_fails_the_oracle(self):
        # The vacuity direction. Without this clause the oracle would be
        # perfectly satisfied by an adapter with no capability whatsoever,
        # which is the cheapest way to pass a "cannot be pointed anywhere"
        # check.
        with self.assertRaisesRegex(AssertionError, "reaches none of the roster's"):
            assert_the_target_set_is_selected_and_enumerable(
                self, WRONG_PAGE_ADAPTERS[1], self._wrong(WRONG_PAGE_ADAPTERS[1])
            )

    def test_the_url_adapter_would_really_have_read_a_host_nobody_selected(self):
        # The rejection above is not a technicality about a declaration: the
        # call this fixture makes is recorded on the carrier with a host no
        # route in this package declares, which is exactly what a generic HTTP
        # primitive is.
        wrong = self._wrong(WRONG_PAGE_ADAPTERS[0])
        _, opener = selected_page(
            "article.html", target="https://evil.example/x", module=wrong
        )

        self.assertEqual([call.url for call in opener.opened], ["https://evil.example/x"])
        self.assertEqual(
            sorted(
                {
                    urllib.parse.urlsplit(route.origin).netloc
                    for route in transport.ROUTE_CONSTANTS.values()
                    if urllib.parse.urlsplit(route.origin).netloc == "evil.example"
                }
            ),
            [],
        )

    def test_the_same_oracle_passes_on_the_shipped_adapter(self):
        assert_the_target_set_is_selected_and_enumerable(self, "public_page", public_page)

    def test_nothing_in_the_package_can_reach_either_wrong_adapter(self):
        named = sorted(
            path.name
            for path in PACKAGE_DIR.rglob("*.py")
            for wrong in WRONG_PAGE_ADAPTERS
            if wrong in path.read_text(encoding="utf-8")
        )

        self.assertEqual(named, [])


