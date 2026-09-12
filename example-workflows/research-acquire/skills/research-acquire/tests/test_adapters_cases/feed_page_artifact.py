from tests.test_adapters_cases.feed_page_calls_and_ttl import *  # noqa: F401,F403

TRACER_FIXTURE_DIR = TEST_DIR / "fixtures" / "tracer"
ARCHIVED_POST_ID = "1abc234"

# Explicit roster oracle: eight live adapters and the offline fixture.
ROSTER = {'fake': 'offline', 'github_rest': 'K0', 'hacker_news': 'K0', 'open_page': 'K0', 'reddit_archive': 'K3', 'reddit_shreddit': 'K2', 'rss_atom': 'K0', 'scholarly': 'K0', 'x_fxtwitter': 'K3'}
