"""Keyless suite: the whole roster answers with nothing in the environment.

This is the run's thesis, and the prior spec's measurement is what it
overturns: eight of eleven adapters were said to require a credential, and
measurement found two capabilities that genuinely do. Both were deferred. What
is left is a roster where every adapter reaches its declared capability with
no credential of any kind, and where the absence of one is never a refusal.

The claim is easy to prove by accident, so the emptiness is made rather than
assumed. A run that passed because this developer happened to have no keys
exported would be evidence about a laptop. So the environment is emptied for
the length of the dispatch and shown to be empty, a variable set outside the
guard is shown to be invisible inside it, every filesystem primitive is
refused for the duration so no credential file on disk can be read, and the
package is scanned for any name that could reach a credential store at all —
it imports `os` nowhere, so there is nothing to reach one with.

Then the roster runs: seventeen steps, fourteen adapters, every route the core
can reach, one artifact. Every step keeps rows, no step is refused, and the
string `auth_required` — which seven adapters and the router all know how to
say — appears in nothing the run produced.

Four adapters written beside the tree hold the oracle honest: one that reads
the environment for a key and refuses when it finds none, one that says
`auth_required` outright, one that comes back empty while claiming success,
and one that simply is not run. Each is rejected, and the run that ships is
accepted.
"""

from __future__ import annotations

import contextlib
import importlib.util
import os
import unittest
from pathlib import Path
from unittest import mock

from super_research import adapters, normalize, runner, schema, transport
from tests import helpers

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures"
ROUTER_FIXTURE_DIR = FIXTURE_DIR / "router"
PACKAGE_DIR = Path(__file__).resolve().parent.parent / "scripts" / "super_research"

AUTH_REQUIRED = "auth_required"

# Every name a module would have to spell to read a credential from anywhere
# outside itself: the environment, a dotfile a library reads on its own, a
# keychain, a prompt, a browser's cookie jar, or another process. None of them
# is a judgment call — each is a way to acquire a secret this package has no
# use for, and the package imports `os` in no module at all.
CREDENTIAL_STORE_NAMES = (
    "os.environ",
    "os.getenv",
    "environb",
    "getenv",
    "netrc",
    "keyring",
    "getpass",
    "HTTPPasswordMgr",
    "HTTPBasicAuthHandler",
    "HTTPDigestAuthHandler",
    "install_opener",
    "build_opener",
    "cookiejar",
    "CookieJar",
    "expanduser",
    "Path.home",
    "subprocess",
    "load_dotenv",
)

# The measured payloads every roster row was built against, by the route that
# answered with them. Read rather than copied: "reaches its declared
# capability" has to be proven on the bytes the origin actually sent.
ROSTER_PAYLOADS = {
    "ddg_html": ("tracer/ddg_html_results.html", "text/html"),
    "arctic_shift_posts_ids": ("tracer/arctic_shift_posts_ids.json", "application/json"),
    "reddit_feed": ("reddit_feed/subreddit_new.xml", "application/atom+xml"),
    "youtube_channel_feed": ("rss_atom/youtube_channel_feed.xml", "application/atom+xml"),
    "public_page_article": ("public_page/article.html", "text/html"),
    "public_page_control": ("public_page/control.html", "text/html"),
    "x_syndication_timeline": ("x/syndication_timeline.html", "text/html"),
    "x_guest_graphql": ("x/guest_tweet_result.json", "application/json"),
    "linkedin_jobs_guest_search": ("linkedin/jobs_search_page.html", "text/html"),
    "linkedin_public_profile": ("linkedin/profile_person.html", "text/html"),
    "youtube_innertube": ("youtube/search_results.json", "application/json"),
    "instagram_web_profile": ("instagram/web_profile_info.json", "application/json"),
    "hn_algolia_search": ("hacker_news/algolia_search_by_date.json", "application/json"),
    "hn_firebase_item": ("hacker_news/firebase_story.json", "application/json"),
    "github_rest": ("github/repo.json", "application/json"),
    "github_search": ("github/search_repositories.json", "application/json"),
    "fake_offline": ("tracer/fake_x_native_page.json", "application/json"),
}

ARCHIVED_POST_ID = "1abc234"
REDDIT_SUBREDDIT = "LocalLLaMA"
REDDIT_PERMALINK = (
    "https://www.reddit.com/r/LocalLLaMA/comments/"
    + ARCHIVED_POST_ID
    + "/what_is_the_best_local_model_right_now/"
)
FEED_CHANNEL_ID = "UCharbourlight0000000000"
ARTICLE_TITLE = "Rate_limiting"
PROFILE_SLUG = "avery-lindqvist-8a41b207"
INSTAGRAM_USERNAME = "harbourlight.optics"
HN_STORY_ID = "44831234"
GITHUB_TARGET = "harbourlight/gpu-bench"
X_POST_ID = "1799990000000000001"

# A variable no environment has, set outside the guard so its absence inside
# is a fact about the guard rather than about this host.
SENTINEL = "SUPER_RESEARCH_T10_SENTINEL"


def read_payload(name):
    return FIXTURE_DIR.joinpath(name).read_text(encoding="utf-8")


def roster_seeds():
    """One canned origin answer per route the roster can reach."""

    return {
        route_id: (200, read_payload(name), content_type)
        for route_id, (name, content_type) in ROSTER_PAYLOADS.items()
    }


def discovery(step_id, adapter_id, query, max_items=200):
    return schema.AcquisitionStep(
        step_id=step_id,
        kind="discovery",
        adapter_id=adapter_id,
        query=query,
        max_items=max_items,
    )


def hydration(step_id, adapter_id, locator, target_id, max_items=200):
    return schema.AcquisitionStep(
        step_id=step_id,
        kind="hydration",
        adapter_id=adapter_id,
        selected_hits=(
            schema.SelectedHit(discovery_locator=locator, target_id=target_id),
        ),
        max_items=max_items,
    )


def roster_manifest():
    """One dispatch over every adapter in the roster and every route it reaches.

    Seventeen steps rather than fourteen: three adapters read two surfaces
    each, and a keyless claim about an adapter that leaves one of its routes
    unread is a keyless claim about half of it.
    """

    return schema.AcquisitionManifest(
        manifest_id="m-keyless",
        mode="staged",
        # After every read this dispatch makes, so a frozen horizon never falls
        # before its own observations.
        as_of="2026-08-10T09:30:00Z",
        steps=(
            discovery("s01-web-search", "web_search", "site:reddit.com best local model"),
            hydration("s02-archive", "reddit_archive", REDDIT_PERMALINK, ARCHIVED_POST_ID),
            discovery("s03-reddit-feed", "reddit_feed", REDDIT_SUBREDDIT),
            discovery("s04-channel-feed", "rss_atom", FEED_CHANNEL_ID),
            hydration(
                "s05-article",
                "public_page",
                "https://en.wikipedia.org/wiki/" + ARTICLE_TITLE,
                "article:" + ARTICLE_TITLE,
            ),
            discovery("s06-control", "public_page", "control"),
            hydration("s07-x-timeline", "x_syndication", "https://x.com/simonw", "simonw"),
            hydration(
                "s08-x-tweet",
                "x_guest",
                "https://x.com/simonw/status/" + X_POST_ID,
                "tweet:" + X_POST_ID,
            ),
            discovery("s09-jobs", "linkedin_jobs", "reliability engineer"),
            hydration(
                "s10-profile",
                "linkedin_public",
                "https://www.linkedin.com/in/" + PROFILE_SLUG,
                PROFILE_SLUG,
            ),
            discovery("s11-youtube", "youtube_innertube", "local models"),
            hydration(
                "s12-instagram",
                "instagram_public",
                "https://www.instagram.com/" + INSTAGRAM_USERNAME + "/",
                INSTAGRAM_USERNAME,
            ),
            discovery("s13-hn-search", "hacker_news", "local models"),
            hydration(
                "s14-hn-story",
                "hacker_news",
                "https://news.ycombinator.com/item?id=" + HN_STORY_ID,
                HN_STORY_ID,
            ),
            hydration(
                "s15-repository",
                "github_rest",
                "https://github.com/" + GITHUB_TARGET,
                GITHUB_TARGET,
            ),
            discovery("s16-repo-search", "github_rest", "gpu benchmark"),
            hydration("s17-fixture", "fake", "https://x.com/simonw", X_POST_ID),
        ),
    )


@contextlib.contextmanager
def no_credentials_anywhere():
    """Empty the environment and refuse every read of a credential store.

    Two halves, because either alone is escapable. The environment is cleared
    rather than sampled, so nothing this host happens to export is in scope for
    the run. And every filesystem and socket primitive raises for the duration,
    so a credential file — a netrc, a token cache, a keychain shim — cannot be
    read even by a library that decided to look for one on its own.
    """

    with mock.patch.dict(os.environ, {}, clear=True):
        with helpers.forbid_io():
            yield


def keyless_run(manifest=None, seeds=None):
    """One dispatch with nothing in the environment. Payloads are read first.

    The reads happen outside the guard on purpose: a fixture on this disk is
    not a credential store, and the guard exists to prove the *package* needs
    nothing, not to prove a test can read its own inputs.
    """

    resolved = roster_manifest() if manifest is None else manifest
    clock = helpers.FakeClock()
    carrier, opener = helpers.offline_transport(
        clock, roster_seeds() if seeds is None else seeds
    )
    with no_credentials_anywhere():
        artifact = runner.run_acquisition(resolved, carrier, clock=clock.monotonic)
    return artifact, opener


def load_beside_the_tree(path):
    """Load one adapter written beside the tree, by path."""

    spec = importlib.util.spec_from_file_location("keyless_fixture_" + path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def package_sources():
    return sorted(PACKAGE_DIR.rglob("*.py"))


def assert_nothing_wanted_a_credential(case, artifact, expected_adapters):
    """The keyless oracle: every named adapter answered, and none asked for a key.

    Both halves are the claim. "Nobody said `auth_required`" is satisfied
    perfectly by a run where nothing happened, so the adapters that were
    supposed to answer are named in advance and each has to have kept a row.
    And "everybody answered" is satisfied by a run that quietly used a
    credential, so the string every refusal in this package is spelled with
    has to be absent from the steps, the records, and the artifact alike.
    """

    if not expected_adapters:
        case.fail("no adapter was expected to answer, so nothing keyless was checked")

    answered = {}
    for step in artifact.steps:
        answered.setdefault(step.adapter_id, 0)
        answered[step.adapter_id] += step.records_kept
        if step.outcome == "refused":
            case.fail(
                "step {0} on {1} was refused: {2}".format(
                    step.step_id, step.adapter_id, ", ".join(step.loss) or "no reason given"
                )
            )
        if AUTH_REQUIRED in step.loss:
            case.fail(
                "step {0} on {1} reported {2}".format(
                    step.step_id, step.adapter_id, AUTH_REQUIRED
                )
            )

    for adapter_id in sorted(expected_adapters):
        if adapter_id not in answered:
            case.fail("{0} never ran, so nothing was proven about it".format(adapter_id))
        if not answered[adapter_id]:
            case.fail(
                "{0} reached no part of its declared capability: it kept no rows".format(
                    adapter_id
                )
            )

    for record in artifact.records:
        if AUTH_REQUIRED in record.loss:
            case.fail(
                "record {0} from {1} reported {2}".format(
                    record.record_id, record.adapter_id, AUTH_REQUIRED
                )
            )
    if AUTH_REQUIRED in artifact.loss:
        case.fail("the artifact reported " + AUTH_REQUIRED)


FEED_STEP = discovery("s03-reddit-feed", "reddit_feed", REDDIT_SUBREDDIT)
FEED_REQUEST = adapters.AdapterRequest(step_id=FEED_STEP.step_id, query=REDDIT_SUBREDDIT)


def artifact_from(fetch, step=FEED_STEP, request=FEED_REQUEST):
    """One artifact out of one page produced beside the tree.

    It records what ``run_step`` records — the rows kept, the page's outcome,
    the page's loss — so a page written beside the tree reaches the oracle in
    exactly the shape a wrong adapter's would inside a real dispatch. That the
    two agree is checked rather than assumed, against the same step of the run
    that ships.
    """

    clock = helpers.FakeClock()
    carrier, _ = helpers.offline_transport(clock, roster_seeds())
    with no_credentials_anywhere():
        page = fetch(carrier, request)
    records = normalize.normalize_page(page, step, "artifact:m-wrong", "m-wrong")
    return schema.AcquisitionArtifact(
        artifact_id="artifact:m-wrong",
        manifest_id="m-wrong",
        mode="staged",
        as_of="2026-08-10T09:30:00Z",
        records=records,
        steps=(
            schema.StepResult(
                step_id=step.step_id,
                adapter_id=step.adapter_id,
                route_id=page.route_id,
                pages=1,
                records_received=len(page.records),
                records_kept=len(records),
                outcome=page.outcome,
                loss=tuple(page.loss),
            ),
        ),
        outcome=page.outcome,
        loss=tuple(page.loss),
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
        # Pointed at a source that does name them — this one, which names them
        # in order to forbid them — the scan finds every one.
        found = sorted(
            name
            for name in CREDENTIAL_STORE_NAMES
            if name in Path(__file__).resolve().read_text(encoding="utf-8")
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


class KeylessRosterTest(unittest.TestCase):
    """Criterion 1: thirteen live adapters, one dispatch, no credential anywhere.

    One artifact rather than fourteen page-level checks, because "reaches its
    declared capability" is a claim about what a caller keeps, and because a
    refusal on any step would otherwise be somebody else's test's problem.
    """

    LIVE = tuple(sorted(set(runner.ADAPTER_IDS) - {"fake"}))

    def setUp(self):
        self.artifact, self.opener = keyless_run()
        self.by_adapter = {}
        for record in self.artifact.records:
            self.by_adapter.setdefault(record.adapter_id, []).append(record)

    def test_thirteen_live_adapters_are_what_the_run_is_about(self):
        self.assertEqual(len(self.LIVE), 13)
        self.assertEqual(len(runner.ADAPTER_IDS), 14)

    def test_the_dispatch_read_every_route_the_roster_can_reach(self):
        # Seventeen steps, seventeen reads, seventeen distinct routes: the
        # oracle below cannot pass by leaving a surface out of the run.
        #
        # Reachable is not readable. A step reads a surface an adapter names as
        # the one it reads, and the guest-token activation is not one — it
        # returns a token rather than a record, and only the composed carrier
        # spends it. This dispatch hands in a bare carrier, so no activation
        # goes out here at all; `test_transport` owns that half.
        readable = sorted(
            surface.route_id
            for adapter_id in runner.ADAPTER_IDS
            for surface in runner.surface_descriptors(adapter_id)
            if surface.route_id not in transport.TOKEN_ACTIVATION_ROUTES
        )

        self.assertEqual(len(roster_manifest().steps), 17)
        self.assertEqual(sorted(request.route_id for request in self.opener.opened), readable)
        self.assertEqual(sorted(ROSTER_PAYLOADS), readable)
        self.assertEqual(transport.GUEST_TOKENS._tokens, {})

    def test_the_artifact_holds_every_row_all_seventeen_steps_returned(self):
        # Written out rather than summed, so a step that quietly stopped
        # answering is a red test and not a smaller number nobody reads.
        self.assertEqual(
            [step.records_kept for step in self.artifact.steps],
            [6, 1, 3, 2, 1, 1, 100, 1, 10, 1, 5, 13, 4, 1, 1, 2, 2],
        )
        self.assertEqual(len(self.artifact.records), 154)
        self.assertEqual(self.artifact.outcome, "ok")
        self.assertEqual(self.artifact.loss, ())

    def test_every_adapter_reached_its_capability_and_none_wanted_a_credential(self):
        assert_nothing_wanted_a_credential(self, self.artifact, self.LIVE)

    def test_the_offline_fixture_adapter_answered_beside_the_thirteen(self):
        # The fourteenth is not a live capability and is checked apart from
        # them, so "thirteen live adapters answered" stays a statement about
        # thirteen live adapters.
        assert_nothing_wanted_a_credential(self, self.artifact, ("fake",))

    def test_the_router_admitted_every_adapter_on_its_own_route(self):
        # The other end of the same claim, at the seam that decides it: the
        # admissions map is booleans only, and every adapter's route is in it
        # and true. `auth_required` is the reason it would answer otherwise.
        admissions = transport.route_admissions()
        for adapter_id in runner.ADAPTER_IDS:
            for surface in runner.surface_descriptors(adapter_id):
                with self.subTest(adapter=adapter_id, route=surface.route_id):
                    self.assertIs(admissions[surface.route_id], True)

    def test_no_string_in_the_whole_artifact_says_a_credential_was_wanted(self):
        # Belt and braces over the oracle's field-by-field reading: seven
        # adapters and the router all spell the same word, and none of them is
        # anywhere in what the run produced.
        self.assertNotIn(AUTH_REQUIRED, repr(self.artifact))

    def test_every_row_the_run_kept_came_from_an_uncredentialed_class(self):
        self.assertEqual(
            sorted({record.access_class for record in self.artifact.records}),
            ["K0", "K1", "K2", "K3", "K4", "offline"],
        )

    def test_the_whole_dispatch_ran_with_the_environment_emptied(self):
        # Not a re-run: the artifact under test was produced inside the guard,
        # and this states what the guard was. Both halves are asserted from
        # inside it, so an escape would be visible here rather than assumed.
        with no_credentials_anywhere():
            self.assertEqual(dict(os.environ), {})
            self.assertEqual(self.artifact.outcome, "ok")


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


if __name__ == "__main__":
    unittest.main()
