from .archive import ARCHIVE_REQUEST, ARCHIVE_STEP, FEED_REQUEST, FEED_STEP, records_from
from .common import *
from .public_client import k1_manifest, k1_run

class UnclassedDescriptorTest(unittest.TestCase):
    """The teeth under criterion 2: a class nothing names never gets built.

    Audited at the reader, an unclassed descriptor is a route that answers with
    an access class no rule in the package has an opinion about — the router
    admits it, `time_confidence_for` calls its times authoritative, and the
    artifact reports a class no caller can interpret. Refused at construction,
    it is an import-time error in the module that declared it.
    """

    def test_a_class_the_ladder_does_not_name_is_refused_at_construction(self):
        for wrong in UNCLASSED:
            with self.subTest(access_class=wrong):
                with self.assertRaises(adapters.AdapterError):
                    shipped_descriptor(access_class=wrong)

    def test_the_refusal_names_the_adapter_and_the_class_it_refused(self):
        with self.assertRaisesRegex(adapters.AdapterError, "reddit_feed.*'k5'"):
            shipped_descriptor(access_class="k5")

    def test_every_class_on_the_ladder_still_constructs(self):
        # The other direction, so the law is a filter rather than a wall: all
        # seven build, `K5` included. Whether a credentialed route may exist is
        # the keyless law's question, two classes below; this one refuses only
        # a class the ladder does not name.
        for access_class in LADDER:
            with self.subTest(access_class=access_class):
                self.assertEqual(
                    shipped_descriptor(access_class=access_class).access_class, access_class
                )

    def test_the_shipped_roster_survives_the_law_it_is_held_to(self):
        for adapter_id in sorted(ROSTER):
            for surface in runner.surface_descriptors(adapter_id):
                with self.subTest(adapter=adapter_id, route=surface.route_id):
                    self.assertEqual(dataclasses.replace(surface), surface)


class OracleCanFailTest(unittest.TestCase):
    """Criterion 6, access-class half: the keyless law rejects, and admits.

    Each roster is a file beside the tree — the shipped surfaces plus named
    ones — so a rejection is attributable to what was added and nothing under
    test was mutated to produce it.
    """

    def setUp(self):
        self.wrong = load_beside_the_tree(FIXTURE_DIR / "credentialed_rosters.py")
        self.archives = load_beside_the_tree(FIXTURE_DIR / "archive_adapters.py")
        self.leaks = load_beside_the_tree(FIXTURE_DIR / "leaking_artifacts.py")
        self.correct_records = records_from(
            self.archives.correct, ARCHIVE_STEP, ARCHIVE_REQUEST
        )

    def test_every_place_a_credential_could_hide_in_an_artifact_is_found(self):
        # Six fields at four depths, one artifact each, and the failure names
        # the field it was found in — because "a credential is in here
        # somewhere" is not a finding anybody can act on.
        run, _, _ = k1_run()
        secret = transport.PUBLIC_CLIENT_CREDENTIALS[
            transport.YOUTUBE_INNERTUBE_WEB_KEY
        ].value
        for where, plant in self.leaks.ARTIFACT_LEAKS:
            with self.subTest(where=where):
                with self.assertRaisesRegex(
                    AssertionError, "youtube_innertube_web_key value reached emitted"
                ):
                    assert_no_credential_reaches_what_the_run_keeps(
                        self, plant(run.artifact, secret), public_client_secrets()
                    )

    def test_every_secret_there_is_gets_looked_for_and_not_just_the_first(self):
        run, _, _ = k1_run()
        for name, secret in public_client_secrets():
            with self.subTest(secret=name):
                with self.assertRaisesRegex(AssertionError, "reached emitted.loss"):
                    assert_no_credential_reaches_what_the_run_keeps(
                        self,
                        self.leaks.in_the_artifact_loss(run.artifact, secret),
                        public_client_secrets(),
                    )

    def test_a_credential_in_the_manifest_the_caller_wrote_is_found(self):
        secret = transport.PUBLIC_CLIENT_CREDENTIALS[transport.INSTAGRAM_WEB_APP_ID].value

        with self.assertRaisesRegex(AssertionError, "reached emitted.steps"):
            assert_no_credential_reaches_what_the_run_keeps(
                self,
                self.leaks.in_a_manifest_query(k1_manifest(), secret),
                public_client_secrets(),
            )

    def test_a_credential_on_the_ledgers_stop_marker_is_found(self):
        run, _, _ = k1_run()
        secret = transport.PUBLIC_CLIENT_CREDENTIALS[transport.X_GUEST_PUBLIC_BEARER].value

        with self.assertRaisesRegex(AssertionError, "reached emitted"):
            assert_no_credential_reaches_what_the_run_keeps(
                self,
                self.leaks.in_a_ledger_reason(run.ledger, secret),
                public_client_secrets(),
            )

    def test_a_scan_that_looks_for_nothing_is_refused(self):
        run, _, _ = k1_run()

        with self.assertRaisesRegex(AssertionError, "no credential was looked for"):
            assert_no_credential_reaches_what_the_run_keeps(self, run.artifact, ())

    def test_a_scan_over_nothing_is_refused(self):
        with self.assertRaisesRegex(AssertionError, "nothing was scanned"):
            assert_no_credential_reaches_what_the_run_keeps(self, (), public_client_secrets())

    def test_the_same_scan_accepts_the_artifact_the_run_really_produced(self):
        run, _, _ = k1_run()

        assert_no_credential_reaches_what_the_run_keeps(
            self, run.artifact, public_client_secrets()
        )

    def archive_records(self, fetch):
        return records_from(fetch, ARCHIVE_STEP, ARCHIVE_REQUEST)

    def test_an_archive_that_leaves_the_label_off_the_record_is_rejected(self):
        with self.assertRaisesRegex(AssertionError, "carries no third_party_archive loss"):
            assert_an_archive_never_speaks_as_the_platform(
                self, shipped_roster(), self.archive_records(self.archives.unlabelled)
            )

    def test_an_archive_that_labels_only_the_page_is_rejected(self):
        # The one a descriptor-level check would pass: the declaration is
        # right, the page is right, and every row a caller keeps is unmarked.
        page_only = self.archive_records(self.archives.page_labelled_only)

        with self.assertRaisesRegex(AssertionError, "carries no third_party_archive loss"):
            assert_an_archive_never_speaks_as_the_platform(self, shipped_roster(), page_only)

    def test_an_archive_that_will_not_name_its_operator_is_rejected(self):
        with self.assertRaisesRegex(AssertionError, "record .* names no operator"):
            assert_an_archive_never_speaks_as_the_platform(
                self, shipped_roster(), self.archive_records(self.archives.anonymous)
            )

    def test_an_archive_answering_under_the_platforms_name_is_rejected(self):
        with self.assertRaisesRegex(
            AssertionError, "record .* names the platform as its operator"
        ):
            assert_an_archive_never_speaks_as_the_platform(
                self, shipped_roster(), self.archive_records(self.archives.as_the_platform)
            )

    def test_a_keyless_route_wearing_the_archive_label_is_rejected(self):
        wearing = records_from(
            self.archives.keyless_route_wearing_the_label, FEED_STEP, FEED_REQUEST
        )

        with self.assertRaisesRegex(
            AssertionError, "record .* on a K0 route carries third_party_archive"
        ):
            assert_an_archive_never_speaks_as_the_platform(self, shipped_roster(), wearing)

    def test_a_run_holding_no_archive_record_is_refused_rather_than_passed(self):
        # Nothing in these rows is wrong; there is simply nothing here to be
        # right about, and the archive law must not report a pass over it.
        feed_only = records_from(self.archives.keyless_route, FEED_STEP, FEED_REQUEST)

        with self.assertRaisesRegex(AssertionError, "no archive record was read"):
            assert_an_archive_never_speaks_as_the_platform(self, shipped_roster(), feed_only)

    def test_an_archive_surface_declaring_no_standing_loss_is_rejected(self):
        with self.assertRaisesRegex(
            AssertionError, "surface .* declares no third_party_archive standing loss"
        ):
            assert_an_archive_never_speaks_as_the_platform(
                self, self.archives.UNDECLARED_LOSS_ROSTER, self.correct_records
            )

    def test_an_archive_surface_naming_no_operator_is_rejected(self):
        with self.assertRaisesRegex(AssertionError, "surface .* names no operator"):
            assert_an_archive_never_speaks_as_the_platform(
                self, self.archives.ANONYMOUS_OPERATOR_ROSTER, self.correct_records
            )

    def test_an_archive_surface_naming_the_platform_as_operator_is_rejected(self):
        with self.assertRaisesRegex(
            AssertionError, "surface .* names the platform as its operator"
        ):
            assert_an_archive_never_speaks_as_the_platform(
                self, self.archives.OPERATOR_IS_THE_PLATFORM_ROSTER, self.correct_records
            )

    def test_the_same_archive_law_accepts_the_archive_that_ships(self):
        # Which is what makes the eight rejections above attributable: the
        # correct fixture is the same call with nothing overridden.
        assert_an_archive_never_speaks_as_the_platform(
            self, shipped_roster(), self.correct_records
        )

    def test_a_credentialed_adapter_of_its_own_is_rejected(self):
        with self.assertRaisesRegex(
            AssertionError, "adapter reddit_oauth is reachable only with a credential"
        ):
            assert_no_capability_needs_a_credential(self, self.wrong.CREDENTIAL_ONLY_ADAPTER)

    def test_a_capability_only_a_credentialed_surface_serves_is_rejected(self):
        # The adapter is reachable and the capability is not, which is the case
        # an adapter-by-adapter law passes and this one must not.
        with self.assertRaisesRegex(
            AssertionError,
            "capability youtube/youtube/feed is reachable only with a credential",
        ):
            assert_no_capability_needs_a_credential(
                self, self.wrong.CREDENTIAL_ONLY_CAPABILITY
            )

    def test_a_credentialed_surface_twinned_only_by_another_one_is_rejected(self):
        with self.assertRaisesRegex(
            AssertionError,
            "capability mastodon/mastodon/native is reachable only with a credential",
        ):
            assert_no_capability_needs_a_credential(self, self.wrong.CREDENTIALED_TWINS)

    def test_a_twin_in_another_identity_namespace_is_not_the_same_capability(self):
        with self.assertRaisesRegex(
            AssertionError,
            "capability reddit/reddit_oauth/native is reachable only with a credential",
        ):
            assert_no_capability_needs_a_credential(
                self, self.wrong.CREDENTIALED_TWIN_IN_ANOTHER_NAMESPACE
            )

    def test_a_twin_at_another_representation_is_not_the_same_capability(self):
        with self.assertRaisesRegex(
            AssertionError,
            "capability youtube/youtube/feed is reachable only with a credential",
        ):
            assert_no_capability_needs_a_credential(
                self, self.wrong.CREDENTIALED_TWIN_IN_ANOTHER_REPRESENTATION
            )

    def test_a_twin_on_another_platform_is_not_the_same_capability(self):
        with self.assertRaisesRegex(
            AssertionError,
            "capability tiktok/tiktok/native is reachable only with a credential",
        ):
            assert_no_capability_needs_a_credential(
                self, self.wrong.CREDENTIALED_TWIN_ON_ANOTHER_PLATFORM
            )

    def test_an_adapter_whose_every_surface_is_credentialed_is_rejected(self):
        with self.assertRaisesRegex(
            AssertionError, "adapter reddit_oauth is reachable only with a credential"
        ):
            assert_no_capability_needs_a_credential(
                self, self.wrong.EVERY_SURFACE_CREDENTIALED
            )

    def test_a_roster_that_is_one_credentialed_adapter_is_rejected(self):
        with self.assertRaisesRegex(
            AssertionError, "adapter reddit_oauth is reachable only with a credential"
        ):
            assert_no_capability_needs_a_credential(
                self, self.wrong.ONLY_A_CREDENTIALED_ADAPTER
            )

    def test_a_roster_with_nothing_in_it_is_refused_rather_than_passed(self):
        with self.assertRaisesRegex(AssertionError, "proves nothing about credentials"):
            assert_no_capability_needs_a_credential(self, self.wrong.NO_ROSTER_AT_ALL)

    def test_a_credentialed_upgrade_beside_a_keyless_surface_is_rejected(self):
        # It passes both halves of the keyless law — the adapter is reachable
        # and the capability is served keylessly — and is refused anyway, by
        # the one-class law. This is the shape the spec calls an optional
        # throughput upgrade, and the reason both `K5` members of the ladder
        # are deferred rather than shipped behind a flag.
        assert_no_capability_needs_a_credential(
            self, self.wrong.CREDENTIALED_UPGRADE_BESIDE_A_KEYLESS_SURFACE
        )
        with self.assertRaisesRegex(
            AssertionError, "adapter reddit_archive answers at more than one access class"
        ):
            assert_the_access_ladder_holds(
                self, self.wrong.CREDENTIALED_UPGRADE_BESIDE_A_KEYLESS_SURFACE
            )

    def test_one_more_keyless_adapter_is_admitted_without_ceremony(self):
        # The accept case, and what keeps the law a filter rather than a wall:
        # the roster grows by a platform nothing else reads and nothing fires.
        assert_the_access_ladder_holds(self, self.wrong.KEYLESS_ADDITION)

    def test_the_same_law_accepts_the_roster_that_ships(self):
        assert_the_access_ladder_holds(self, self.wrong.shipped())
        self.assertEqual(self.wrong.shipped(), shipped_roster())

    def test_nothing_in_the_package_can_reach_a_wrong_roster(self):
        self.assertEqual(
            sources_naming(
                (
                    "credentialed_rosters",
                    "CREDENTIAL_ONLY_ADAPTER",
                    "CREDENTIAL_ONLY_CAPABILITY",
                    "ONLY_A_CREDENTIALED_ADAPTER",
                    "reddit_oauth",
                    "youtube_captions",
                ),
                package_sources(),
            ),
            [],
        )
