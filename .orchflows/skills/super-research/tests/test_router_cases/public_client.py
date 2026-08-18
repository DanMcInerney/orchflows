from .common import *

def k1_seeds():
    """The three credentialed routes, each answering with its measured payload."""

    return {
        transport.YOUTUBE_INNERTUBE_ROUTE: (
            200,
            # Without the continuation token the capture carries. That token is
            # InnerTube's claim that the search holds another page, and this
            # double cannot serve one: it answers every read of the route with
            # the one canned page. No page two of this route has ever been
            # measured, so the seed stands for a search whose one page is its
            # last, and the three reads below stay this dispatch's three.
            YOUTUBE_FIXTURE_DIR.joinpath("search_results.json")
            .read_text(encoding="utf-8")
            .replace(
                '"continuationCommand": {"token": "EpcDEgxsb2NhbCBtb2RlbHMaggNTQlNDQVE"}',
                '"continuationCommand": {}',
            ),
            "application/json",
        ),
        transport.INSTAGRAM_WEB_PROFILE_ROUTE: (
            200,
            INSTAGRAM_FIXTURE_DIR.joinpath("web_profile_info.json").read_text(
                encoding="utf-8"
            ),
            "application/json",
        ),
        transport.X_GUEST_GRAPHQL_ROUTE: (
            200,
            X_FIXTURE_DIR.joinpath("guest_tweet_result.json").read_text(encoding="utf-8"),
            "application/json",
        ),
    }


def k1_manifest():
    """One dispatch over every credentialed route in the roster."""

    return schema.AcquisitionManifest(
        manifest_id="m-k1",
        mode="staged",
        as_of="2026-08-10T09:05:00Z",
        steps=(
            schema.AcquisitionStep(
                step_id="s1-youtube",
                kind="discovery",
                adapter_id="youtube_innertube",
                query="local models",
                max_items=25,
            ),
            schema.AcquisitionStep(
                step_id="s2-instagram",
                kind="hydration",
                adapter_id="instagram_public",
                selected_hits=(
                    schema.SelectedHit(
                        discovery_locator="https://www.instagram.com/"
                        + INSTAGRAM_USERNAME
                        + "/",
                        target_id=INSTAGRAM_USERNAME,
                    ),
                ),
                max_items=25,
            ),
            schema.AcquisitionStep(
                step_id="s3-x",
                kind="hydration",
                adapter_id="x_guest",
                selected_hits=(
                    schema.SelectedHit(
                        discovery_locator="https://x.com/simonw", target_id=X_TWEET_TARGET
                    ),
                ),
                max_items=5,
            ),
        ),
    )


CREDENTIALED_ROUTES = (
    transport.YOUTUBE_INNERTUBE_ROUTE,
    transport.INSTAGRAM_WEB_PROFILE_ROUTE,
    transport.X_GUEST_GRAPHQL_ROUTE,
    transport.X_GUEST_ACTIVATE_ROUTE,
)


def k1_run():
    """One offline dispatch over the three credentialed routes."""

    clock = helpers.FakeClock()
    carrier, opener = helpers.offline_transport(clock, k1_seeds())
    return runner.run_scheduled(k1_manifest(), carrier, clock=clock.monotonic), carrier, opener


class PublicClientCredentialTest(unittest.TestCase):
    """Criterion 4: a `K1` credential is a route constant and reaches nothing kept.

    The transport suite proves the credential is attached at send time and is
    absent from the request and the response. This is the other end of that
    argument, checked rather than reasoned: the artifact three credentialed
    routes actually produced, walked string by string at whatever depth they
    sit, against every secret ``transport`` holds.
    """

    def setUp(self):
        self.manifest = k1_manifest()
        self.run, self.carrier, self.opener = k1_run()

    def test_the_run_read_every_credentialed_route_and_kept_what_they_said(self):
        # A scan of an artifact nothing wrote is a scan of nothing.
        self.assertEqual(self.run.artifact.outcome, "ok")
        self.assertEqual(len(self.opener.opened), 3)
        self.assertEqual(
            sorted({record.access_class for record in self.run.artifact.records}), ["K1"]
        )
        self.assertEqual(
            sorted({record.route_id for record in self.run.artifact.records}),
            sorted(k1_seeds()),
        )

    def test_every_credentialed_route_really_sends_a_secret(self):
        # Which is what makes every absence below mean something: the value is
        # nonempty, it is on the wire, and it is on the wire only there.
        for route_id in CREDENTIALED_ROUTES:
            with self.subTest(route=route_id):
                credential = transport.route_credential(route_id)
                request = transport.build_transport_request(route_id, helpers.probe_params(route_id))

                self.assertIsNotNone(credential)
                self.assertTrue(credential.value)
                self.assertIn(
                    credential.value,
                    transport.credentialed_url(request.url, credential)
                    + repr(transport.credentialed_headers(request.headers, credential)),
                )
                self.assertNotIn(credential.value, request.url + repr(request.headers))

    def test_no_credential_reaches_the_artifact(self):
        assert_no_credential_reaches_what_the_run_keeps(
            self, self.run.artifact, public_client_secrets()
        )

    def test_no_credential_reaches_the_manifest_the_caller_wrote(self):
        assert_no_credential_reaches_what_the_run_keeps(
            self, self.manifest, public_client_secrets()
        )

    def test_no_credential_reaches_the_work_ledger(self):
        assert_no_credential_reaches_what_the_run_keeps(
            self, self.run.ledger, public_client_secrets()
        )

    def test_no_credential_reaches_the_call_log_the_run_leaves_behind(self):
        assert_no_credential_reaches_what_the_run_keeps(
            self, tuple(self.carrier.calls), public_client_secrets()
        )

    def test_the_scan_reads_the_whole_artifact_and_not_a_field_list(self):
        # The scan's own coverage, stated as numbers: every record family, the
        # steps, the groups, and the strings nested two tuples deep inside an
        # attribute pair are all in what it walked.
        paths = [path for path, _ in strings_in(self.run.artifact)]

        self.assertGreater(len(paths), 700)
        for expected in (
            "emitted.records[0].canonical_locator",
            "emitted.records[0].attributes[0][1]",
            "emitted.steps[0].step_id",
            "emitted.groups[0].key[0]",
        ):
            with self.subTest(path=expected):
                self.assertTrue([path for path in paths if path.startswith(expected)])

    def test_no_adapter_on_a_credentialed_route_publishes_the_answering_address(self):
        # `final_url` is the one string in the package that can hold a
        # query-placed credential: the address an origin answered from is the
        # url the key was appended to. One adapter publishes it, and that
        # adapter's routes carry no credential — checked, because the day a
        # credentialed route publishes it the key is in the artifact.
        for adapter_id in sorted(ROSTER):
            source = ADAPTER_DIR / (adapter_id + ".py")
            if "final_url" not in source.read_text(encoding="utf-8"):
                continue
            for surface in runner.surface_descriptors(adapter_id):
                with self.subTest(adapter=adapter_id, route=surface.route_id):
                    self.assertEqual(
                        transport.route_constant(surface.route_id).credential_id, ""
                    )


