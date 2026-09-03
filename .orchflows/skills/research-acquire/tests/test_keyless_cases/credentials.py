"""Keyless credential-boundary and failure-oracle behavior."""

import os
import unittest
from pathlib import Path

from .support import (
    CREDENTIAL_STORE_NAMES,
    FEED_REQUEST,
    FEED_STEP,
    PACKAGE_DIR,
    ROUTER_FIXTURE_DIR,
    SENTINEL,
    artifact_from,
    assert_nothing_wanted_a_credential,
    helpers,
    keyless_run,
    load_beside_the_tree,
    no_credentials_anywhere,
    package_sources,
    roster_seeds,
)


class EnvironmentIsEmptyTest(unittest.TestCase):
    """The half that makes the rest evidence: the emptiness is made here.

    A keyless claim proven under whatever this host exports is a claim about
    the host. These are the checks that the guard the dispatch runs inside
    really removes everything, and that the package could not read a
    credential from anywhere else even if the guard let it.
    """

    def test_the_guard_empties_the_environment_it_is_handed(self):
        os.environ[SENTINEL] = "a key this run must not see"
        try:
            with no_credentials_anywhere():
                self.assertEqual(dict(os.environ), {})
                self.assertNotIn(SENTINEL, os.environ)
                self.assertIsNone(os.environ.get("HOME"))
        finally:
            os.environ.pop(SENTINEL, None)

    def test_the_environment_comes_back_afterwards(self):
        # The guard is a guard and not a demolition: a suite that emptied the
        # environment for everything after it would make every later test's
        # result a fact about the order they ran in.
        os.environ[SENTINEL] = "restored"
        try:
            with no_credentials_anywhere():
                pass

            self.assertEqual(os.environ.get(SENTINEL), "restored")
        finally:
            os.environ.pop(SENTINEL, None)

    def test_no_file_can_be_read_inside_the_guard(self):
        with no_credentials_anywhere():
            with self.assertRaises(AssertionError):
                open(str(PACKAGE_DIR / "transport.py"), encoding="utf-8").read()

    def test_no_package_module_can_reach_a_credential_store(self):
        found = sorted(
            (path.name, name)
            for path in package_sources()
            for name in CREDENTIAL_STORE_NAMES
            if name in path.read_text(encoding="utf-8")
        )

        self.assertEqual(found, [])

    def test_the_scan_for_a_credential_store_can_find_one(self):
        # Pointed at the support source that names them in order to forbid
        # them, the scan finds every one.
        support_source = Path(__file__).with_name("support.py")
        found = sorted(
            name
            for name in CREDENTIAL_STORE_NAMES
            if name in support_source.read_text(encoding="utf-8")
        )

        self.assertEqual(found, sorted(CREDENTIAL_STORE_NAMES))

    def test_no_package_module_imports_the_environment_at_all(self):
        for path in package_sources():
            with self.subTest(module=path.name):
                imported = helpers.imported_names(path)

                self.assertNotIn("os", imported)
                self.assertNotIn("os.path", imported)
                self.assertNotIn("netrc", imported)
                self.assertNotIn("getpass", imported)
                self.assertNotIn("subprocess", imported)
                self.assertNotIn("http.cookiejar", imported)


class OracleCanFailTest(unittest.TestCase):
    """Criterion 6, keyless half: the oracle rejects a run that wanted a key.

    Three adapters beside the tree, each Reddit's own feed with one property of
    its answer spoiled, plus the run that leaves an adapter out entirely.
    """

    def setUp(self):
        self.wrong = load_beside_the_tree(ROUTER_FIXTURE_DIR / "credentialed_adapters.py")

    def test_an_adapter_that_reads_the_environment_is_rejected(self):
        # The headline case: with nothing exported it refuses, and the oracle
        # says so rather than reporting a keyless run.
        with self.assertRaisesRegex(AssertionError, "was refused: auth_required"):
            assert_nothing_wanted_a_credential(
                self, artifact_from(self.wrong.environment_reading), ("reddit_feed",)
            )

    def test_the_same_adapter_answers_when_a_key_is_exported(self):
        # Which is what makes the rejection above a fact about the empty
        # environment and not about a broken fixture — and is exactly the run
        # that would have passed on a laptop with the key set.
        os.environ[self.wrong.TOKEN_VARIABLE] = "a token this run must not need"
        try:
            clock = helpers.FakeClock()
            carrier, _ = helpers.offline_transport(clock, roster_seeds())

            page = self.wrong.environment_reading(carrier, FEED_REQUEST)

            self.assertEqual(page.outcome, "ok")
            self.assertEqual(page.loss, ())
            self.assertEqual(len(page.records), 3)
        finally:
            os.environ.pop(self.wrong.TOKEN_VARIABLE, None)

    def test_an_adapter_that_says_auth_required_outright_is_rejected(self):
        with self.assertRaisesRegex(AssertionError, "reported auth_required"):
            assert_nothing_wanted_a_credential(
                self, artifact_from(self.wrong.always_auth_required), ("reddit_feed",)
            )

    def test_an_adapter_that_comes_back_empty_and_calls_it_success_is_rejected(self):
        # No refusal, no loss code, no failed outcome — and no capability
        # either. "Nobody said auth_required" is satisfied perfectly here.
        with self.assertRaisesRegex(
            AssertionError, "reddit_feed reached no part of its declared capability"
        ):
            assert_nothing_wanted_a_credential(
                self, artifact_from(self.wrong.empty_success), ("reddit_feed",)
            )

    def test_a_run_that_never_ran_an_adapter_at_all_is_rejected(self):
        with self.assertRaisesRegex(AssertionError, "x_guest never ran"):
            assert_nothing_wanted_a_credential(
                self, artifact_from(self.wrong.correct), ("reddit_feed", "x_guest")
            )

    def test_a_run_nobody_expected_anything_of_is_refused_rather_than_passed(self):
        with self.assertRaisesRegex(AssertionError, "no adapter was expected to answer"):
            assert_nothing_wanted_a_credential(self, artifact_from(self.wrong.correct), ())

    def test_the_same_oracle_accepts_the_fixtures_own_correct_adapter(self):
        assert_nothing_wanted_a_credential(
            self, artifact_from(self.wrong.correct), ("reddit_feed",)
        )

    def test_the_harness_that_builds_these_agrees_with_the_run_that_ships(self):
        # The wrong artifacts are assembled here rather than dispatched, so the
        # assembly is pinned against the real thing: same rows, same outcome,
        # same loss, for the same adapter on the same step of the real run.
        assembled = artifact_from(self.wrong.correct).steps[0]
        dispatched = [
            step for step in keyless_run()[0].steps if step.step_id == FEED_STEP.step_id
        ]

        self.assertEqual(len(dispatched), 1)
        self.assertEqual(assembled.records_kept, dispatched[0].records_kept)
        self.assertEqual(assembled.outcome, dispatched[0].outcome)
        self.assertEqual(assembled.loss, dispatched[0].loss)
        self.assertEqual(assembled.route_id, dispatched[0].route_id)

    def test_nothing_in_the_package_can_reach_a_wrong_adapter(self):
        found = sorted(
            (path.name, name)
            for path in package_sources()
            for name in (
                "credentialed_adapters",
                "environment_reading",
                "always_auth_required",
                "empty_success",
                self.wrong.TOKEN_VARIABLE,
            )
            if name in path.read_text(encoding="utf-8")
        )

        self.assertEqual(found, [])
