"""Rosters beside the tree: the ways a capability could come to need a credential.

Eleven of them: eight things going wrong, the empty roster that proves nothing
either way, and the two that say what the law is for.

The keyless law is true of the shipped roster by construction — nothing in it
is `K5` — so a check that only ever sees that roster passes over an empty set
and would keep passing the day somebody lands a credentialed route. These are
the rosters that day would produce, written here so the law can be shown to
reject each one now.

Every roster is the shipped surfaces plus named ones, so a rejection is
attributable to the surfaces added and nothing under test was mutated. The
added surfaces name routes the route table does not contain, deliberately: a
fixture that had to be a real route would be this file editing `transport.py`,
and the law under test reads declarations, not endpoints.

The last two are the ones that say what the law is *for*. A keyless adapter
added to the roster is admitted, because the law has to let the package grow.
A credentialed surface added beside a keyless one — the shape the spec calls
an optional throughput upgrade — is not, and the reason is worth reading: a
class belongs to how a read is authorized, one adapter's routes are all
authorized the same way, and a caller naming an adapter gets that adapter and
never a substitute. So a credentialed route in this package is necessarily a
whole credentialed adapter, and a whole credentialed adapter is one a caller
without a credential is refused. That is why both `K5` members of the spec's
ladder are deferred rather than shipped behind a flag.

Nothing in the package imports this file and no discovery pattern matches it.
"""

from __future__ import annotations

from super_research import runner
from super_research.adapters import AdapterDescriptor

CREDENTIALED = "K5"


def shipped():
    """Every surface the core can reach today, in ``ADAPTER_IDS`` order."""

    return tuple(
        surface
        for adapter_id in runner.ADAPTER_IDS
        for surface in runner.surface_descriptors(adapter_id)
    )


def surface(adapter_id, access_class, route_id, platform, namespace, representation):
    """One declared surface. Only the six fields the keyless law reads are set."""

    return AdapterDescriptor(
        adapter_id=adapter_id,
        adapter_version="1",
        access_class=access_class,
        route_id=route_id,
        platform=platform,
        native_identity_namespace=namespace,
        representation_kind=representation,
    )


def roster_with(*added):
    return shipped() + added


# 1. The plainest violation: a credentialed adapter of its own. Its capability
#    — Reddit posts at native representation — is one `reddit_archive` already
#    serves keylessly, so only the adapter is unreachable. Naming it in a step
#    is `auth_required` and there is no second surface to fall to, which is
#    exactly what "absence of a credential is never a refusal" forbids.
CREDENTIAL_ONLY_ADAPTER = roster_with(
    surface("reddit_oauth", CREDENTIALED, "reddit_oauth_listing", "reddit", "reddit", "native")
)

# 2. A credentialed surface whose capability nothing keyless serves, on an
#    adapter that is otherwise perfectly reachable. This is the failure an
#    adapter-by-adapter reading alone would miss: the adapter answers, a caller
#    can name it, and the one thing it can say about a transcript it can only
#    say with a credential.
#    The capability is `youtube/youtube/feed`: a keyless surface of this
#    roster says plenty about a YouTube video — `native` from InnerTube,
#    `transcript` from the timed-text route since 2026-08-17 — and none of them
#    says this one, which is what makes it the case an adapter-by-adapter law
#    would wave through.
CREDENTIAL_ONLY_CAPABILITY = roster_with(
    surface("youtube_captions", "K0", "youtube_captions_list", "youtube", "youtube", "index"),
    surface(
        "youtube_captions", CREDENTIALED, "youtube_data_api", "youtube", "youtube", "feed"
    ),
)

# 3. A credentialed surface twinned only by another credentialed surface. A law
#    that asked "does anything else serve this capability?" without asking at
#    what class would take these two for each other's answer.
CREDENTIALED_TWINS = roster_with(
    surface("mastodon_home", "K0", "mastodon_public", "mastodon", "mastodon", "index"),
    surface("mastodon_home", CREDENTIALED, "mastodon_home", "mastodon", "mastodon", "native"),
    surface("mastodon_home", CREDENTIALED, "mastodon_backfill", "mastodon", "mastodon", "native"),
)

# 4. A twin differing only in identity namespace. Same platform, same
#    representation, a different space of item ids — the one difference
#    `wrong_merge_law` never lets a caller paper over, so it is not the same
#    capability answered twice.
CREDENTIALED_TWIN_IN_ANOTHER_NAMESPACE = roster_with(
    surface("reddit_oauth", "K0", "reddit_oauth_about", "reddit", "reddit_oauth", "index"),
    surface(
        "reddit_oauth", CREDENTIALED, "reddit_oauth_listing", "reddit", "reddit_oauth", "native"
    ),
)

# 5. A twin differing only in representation. This was the measured captions
#    case until 2026-08-17, when the timed-text route made `transcript` keyless
#    and the shipped roster started serving it — so the pair is stated at
#    `feed`, which nothing keyless here says about a YouTube video. The point
#    is unchanged: video metadata is reachable, and another thing to be able to
#    say about the same video is a different capability.
CREDENTIALED_TWIN_IN_ANOTHER_REPRESENTATION = roster_with(
    surface("youtube_captions", "K0", "youtube_captions_list", "youtube", "youtube", "native"),
    surface(
        "youtube_captions", CREDENTIALED, "youtube_data_api", "youtube", "youtube", "feed"
    ),
)

# 6. A twin on another platform. Keyless Instagram says nothing whatever about
#    Threads, and a law comparing only classes and counts would not notice.
#    Threads, because it must be a platform the live roster never reaches
#    keylessly — TikTok held this seat until 2026-09-01, when `tiktok_public`
#    made tiktok/tiktok/native a real keyless capability and the twin here
#    quietly became satisfiable.
CREDENTIALED_TWIN_ON_ANOTHER_PLATFORM = roster_with(
    surface("threads_private", "K0", "threads_oembed", "instagram", "instagram", "native"),
    surface("threads_private", CREDENTIALED, "threads_api", "threads", "threads", "native"),
)

# 7. Every surface of one adapter credentialed, each capability twinned
#    keylessly elsewhere in the roster. The capabilities survive; the adapter
#    does not, and a caller who names it is refused.
EVERY_SURFACE_CREDENTIALED = roster_with(
    surface("reddit_oauth", CREDENTIALED, "reddit_oauth_listing", "reddit", "reddit", "native"),
    surface("reddit_oauth", CREDENTIALED, "reddit_oauth_comments", "reddit", "reddit", "feed"),
)

# 8. The degenerate roster: one credentialed adapter and nothing else. Every
#    half of the law fails at once, which is what a first release built the
#    other way round would look like.
ONLY_A_CREDENTIALED_ADAPTER = (
    surface("reddit_oauth", CREDENTIALED, "reddit_oauth_listing", "reddit", "reddit", "native"),
)

# 9. A roster with nothing in it. A law quantified over "every capability" is
#    silent here, and silence is the failure mode this whole file exists to
#    close, so the oracle refuses it rather than passing.
NO_ROSTER_AT_ALL = ()

# The shape the spec calls an optional throughput upgrade: `reddit_archive`
# keeps its keyless surface and gains a credentialed one answering the same
# question — same platform, same identity namespace, same representation —
# faster. It is refused, and the refusal is the finding: one adapter's routes
# are all authorized the same way, so this adapter now answers at two classes
# and a caller reading its pages cannot tell which one produced what. The
# lawful version of this upgrade is a credentialed *adapter*, and roster 1 is
# what happens to that.
CREDENTIALED_UPGRADE_BESIDE_A_KEYLESS_SURFACE = roster_with(
    surface(
        "reddit_archive", CREDENTIALED, "reddit_oauth_listing", "reddit", "reddit", "native"
    )
)

# And the growth the law must not stand in the way of: one more keyless adapter,
# a platform nothing else in the roster reads, admitted without ceremony. A law
# that rejected this would be a wall rather than a filter, and the suite would
# have proved only that it says no.
KEYLESS_ADDITION = roster_with(
    surface("lobsters", "K0", "lobsters_hottest", "lobsters", "lobsters", "native")
)
