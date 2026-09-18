"""Fixtures and helpers shared by the keyless credential and route seams."""

from __future__ import annotations

import contextlib
import importlib.util
import os
from pathlib import Path
from unittest import mock

from super_research import adapters, normalize, runner, schema, transport
from tests import helpers

TESTS_DIR = Path(__file__).resolve().parent.parent
FIXTURE_DIR = TESTS_DIR / "fixtures"
ROUTER_FIXTURE_DIR = FIXTURE_DIR / "router"
PACKAGE_DIR = TESTS_DIR.parent / "scripts" / "super_research"

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
ROSTER_PAYLOADS = {'arctic_shift_posts_search': ('tracer/arctic_shift_posts_ids.json', 'application/json'), 'arctic_shift_posts_ids': ('tracer/arctic_shift_posts_ids.json', 'application/json'), 'youtube_channel_feed': ('rss_atom/youtube_channel_feed.xml', 'application/atom+xml'), 'hn_algolia_search': ('hacker_news/algolia_search_by_date.json', 'application/json'), 'hn_firebase_item': ('hacker_news/firebase_story.json', 'application/json'), 'github_rest': ('github/repo.json', 'application/json'), 'github_search': ('github/search_repositories.json', 'application/json'), 'fake_offline': ('tracer/fake_x_native_page.json', 'application/json'), 'web_page_open': ('open_page/article.html', 'text/html'), 'hn_algolia_item': ('hacker_news/algolia_item_tree.json', 'application/json'), 'reddit_shreddit_listing': ('reddit_shreddit/listing.html', 'text/html'), 'reddit_shreddit_search': ('reddit_shreddit/search.html', 'text/html'), 'reddit_shreddit_subreddit_search': ('reddit_shreddit/search.html', 'text/html'), 'reddit_shreddit_comments': ('reddit_shreddit/comments.html', 'text/html'), 'fxtwitter_api': ('x_fxtwitter/conversation.json', 'application/json'), 'crossref_works': ('scholarly/crossref_works.json', 'application/json'), 'arxiv_query': ('scholarly/arxiv_query.xml', 'application/atom+xml')}

ARCHIVED_POST_ID = "1abc234"
REDDIT_SUBREDDIT = "LocalLLaMA"
REDDIT_PERMALINK = (
    "https://www.reddit.com/r/LocalLLaMA/comments/"
    + ARCHIVED_POST_ID
    + "/what_is_the_best_local_model_right_now/"
)
FEED_URL = "https://www.youtube.com/feeds/videos.xml?channel_id=UCharbourlight0000000000"
ARTICLE_TITLE = "Rate_limiting"
PROFILE_SLUG = "avery-lindqvist-8a41b207"
INSTAGRAM_USERNAME = "harbourlight.optics"
HN_STORY_ID = "44831234"
YOUTUBE_VIDEO_ID = "ggdyD2Un5zo"
GITHUB_TARGET = "harbourlight/gpu-bench"
X_POST_ID = "1799990000000000001"

# A variable no environment has, set outside the guard so its absence inside
# is a fact about the guard rather than about this host.
SENTINEL = "SUPER_RESEARCH_T10_SENTINEL"


# Some captures carry another-page claims: Algolia's `page`/`nbPages` pair
# and Reddit continuation links. Each is the origin's claim and none of them is
# this double's — it answers every read of a route with the one canned page it
# was seeded with, so a core that spends a cursor would be asking for a page
# nothing here can serve. No page two of any of these routes has ever been
# measured (the 2026-08-10 probes recorded page one), so this dispatch seeds what it
# can honestly stand for: a search whose one page is its last. The claim is what
# moves; every count below is one page's, unchanged.
NEXT_PAGE_CLAIMS = (
    ('"nbPages": 50', '"nbPages": 1'),
    ("&after=", "&spent="), ("&amp;after=", "&amp;spent="),
    ("&cursor=", "&spent="), ("&amp;cursor=", "&amp;spent="),
)


def read_payload(name):
    return FIXTURE_DIR.joinpath(name).read_text(encoding="utf-8")


def as_a_last_page(body):
    """One capture with the next-page claim it makes dropped, if it makes one."""

    for claim, replacement in NEXT_PAGE_CLAIMS:
        if claim in body:
            return body.replace(claim, replacement)
    return body


def roster_seeds():
    """One canned origin answer per route the roster can reach."""

    return {
        route_id: (200, as_a_last_page(read_payload(name)), content_type)
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


def hydration(step_id, adapter_id, locator, target_id, max_items=200,
              window_start="", window_end=""):
    return schema.AcquisitionStep(
        step_id=step_id,
        kind="hydration",
        adapter_id=adapter_id,
        selected_hits=(
            schema.SelectedHit(discovery_locator=locator, target_id=target_id),
        ),
        max_items=max_items,
        window_start=window_start,
        window_end=window_end,
    )


def roster_manifest():
    """One dispatch over every retained adapter and public route."""
    return schema.AcquisitionManifest(
        manifest_id="m-keyless", as_of="2026-08-10T09:30:00Z",
        steps=(
            discovery("s49-archive-search", "reddit_archive", "search:subreddit=LocalLLaMA"),
            hydration("s02-archive", "reddit_archive", REDDIT_PERMALINK, ARCHIVED_POST_ID),
            discovery("s04-channel-feed", "rss_atom", FEED_URL),
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
            hydration(
                "s21-open-page",
                "open_page",
                "https://www.iana.org/help/example-domains",
                "https://www.iana.org/help/example-domains",
            ),
            discovery("s22-hn-tree", "hacker_news", "tree:" + HN_STORY_ID),
            discovery("s23-shreddit-listing", "reddit_shreddit", "listing:" + REDDIT_SUBREDDIT),
            discovery("s24-shreddit-search", "reddit_shreddit", "search:local models"),
            discovery(
                "s25-shreddit-sub-search",
                "reddit_shreddit",
                "search:r/" + REDDIT_SUBREDDIT + ":local models",
            ),
            discovery(
                "s26-shreddit-comments",
                "reddit_shreddit",
                "comments:" + REDDIT_SUBREDDIT + "/" + ARCHIVED_POST_ID,
            ),
            hydration("s34-fxtwitter", "x_fxtwitter", "https://x.com/SpaceX/status/1956833185741639735", "1956833185741639735"),
            discovery("s39-crossref", "scholarly", "crossref:machine learning"),
            discovery("s40-arxiv", "scholarly", "arxiv:transformers"),
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


FEED_STEP = discovery("s04-channel-feed", "rss_atom", FEED_URL)
FEED_REQUEST = adapters.AdapterRequest(step_id=FEED_STEP.step_id, query=FEED_URL)


def artifact_from(fetch, step=FEED_STEP, request=FEED_REQUEST):
    """One artifact out of one page produced beside the tree.

    It records what ``run_step`` records — the rows kept, the page's outcome,
    the page's loss, and the step's own kind and query — so a page written
    beside the tree reaches the oracle in exactly the shape a wrong adapter's
    would inside a real dispatch. That the two agree is checked rather than
    assumed, against the same step of the run that ships.
    """

    clock = helpers.FakeClock()
    carrier, _ = helpers.offline_transport(clock, roster_seeds())
    with no_credentials_anywhere():
        page = fetch(carrier, request)
    records = normalize.normalize_page(page, step, "artifact:m-wrong", "m-wrong")
    return schema.AcquisitionArtifact(
        artifact_id="artifact:m-wrong",
        manifest_id="m-wrong",
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
                kind=step.kind,
                query=step.query,
            ),
        ),
        outcome=page.outcome,
        loss=tuple(page.loss),
    )
