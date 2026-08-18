"""Access-class suite: the ladder is law, not documentation.

Four claims, and the first two are the run's whole thesis stated twice.

The first is that every adapter declares exactly one class out of the ladder
``schema`` owns, and that the class is the one the measured roster gives it. A
class is not decoration: it decides whether the router admits a step at all,
whether a record's time is `authoritative` or `reported`, and whether the
answer is the platform speaking. A descriptor declaring nothing, or `k5`, or
two classes in one string, would carry that decision quietly past all three,
so the declaration is refused where it is made rather than audited where it is
read.

The second is that no first-release capability is reachable only through `K5`.
That is trivially true today — nothing in the roster is `K5` — and a check that
can only pass over an empty set proves nothing. So the law is stated over a
roster it is handed rather than over the one that ships, and eleven rosters
written beside the tree are put through it: a credentialed adapter with no
keyless surface, a credentialed surface whose capability nothing keyless
serves, a credentialed route twinned only by another credentialed one, and
the two that say what the law is for — one more keyless adapter, admitted,
and the shape the spec calls an optional throughput upgrade, refused.

Two narrower claims sit beside them. A `K1` public client credential is a
route constant ``transport.py`` owns, and it reaches no manifest and no
artifact: checked against every string the emitted artifact actually carries,
never against the module that holds the constants. And every `K3` record
carries `third_party_archive` loss and names its operator, because Arctic
Shift is a volunteer-run archive and not Reddit speaking.
"""

from __future__ import annotations

import dataclasses
import importlib.util
import unittest
from pathlib import Path

from super_research import adapters, normalize, runner, schema, transport
from tests import helpers

TESTS_DIR = Path(__file__).resolve().parent.parent
FIXTURE_DIR = TESTS_DIR / "fixtures" / "router"
PACKAGE_DIR = TESTS_DIR.parent / "scripts" / "super_research"
# Where the measured payloads each surface was built against live. Read rather
# than copied: what an archive labels, and what a credentialed route's artifact
# ends up holding, have to be proven on the bytes the origin actually sent and
# not on a shape written to make the point.
TRACER_FIXTURE_DIR = TESTS_DIR / "fixtures" / "tracer"
REDDIT_FEED_FIXTURE_DIR = TESTS_DIR / "fixtures" / "reddit_feed"
YOUTUBE_FIXTURE_DIR = TESTS_DIR / "fixtures" / "youtube"
INSTAGRAM_FIXTURE_DIR = TESTS_DIR / "fixtures" / "instagram"
X_FIXTURE_DIR = TESTS_DIR / "fixtures" / "x"
ADAPTER_DIR = PACKAGE_DIR / "adapters"

ARCHIVED_POST_ID = "1abc234"
REDDIT_SUBREDDIT = "LocalLLaMA"
INSTAGRAM_USERNAME = "harbourlight.optics"
X_TWEET_TARGET = "tweet:1799990000000000001"

# The ladder's roster, transcribed from the spec's own table rather than
# derived from the code under test. `test_adapters.RosterIsCompleteTest` keeps
# its own transcription for its own claim; two independent copies of one spec
# table disagree loudly the moment either is edited alone, which is the point
# of not deriving it.
ROSTER = {
    "bluesky": "K0",
    "web_search": "K4",
    "x_fxtwitter": "K3",
    "public_page": "K0",
    "prediction_markets": "K0",
    "reddit_archive": "K3",
    "reddit_feed": "K0",
    "reddit_shreddit": "K2",
    "stocktwits": "K0",
    "open_page": "K0",
    "x_syndication": "K2",
    "x_guest": "K1",
    "linkedin_public": "K2",
    "linkedin_jobs": "K0",
    "youtube_innertube": "K1",
    "instagram_public": "K1",
    "hacker_news": "K0",
    "github_rest": "K0",
    "rss_atom": "K0",
    "fake": "offline",
}

# The ladder itself, in the order `schema` declares it, so a class added or
# removed there is visible here rather than silently admitted.
LADDER = ("K0", "K1", "K2", "K3", "K4", "K5", "offline")

# Every way a declaration can name something that is not one class of the
# ladder. `k5` is the one worth naming twice: a check written as
# `access_class != "K5"` admits it, and it would carry a credentialed route
# past every keyless law in this file.
UNCLASSED = ("", " ", "K", "K6", "k5", "K5 ", "K0/K5", "offline ", "unknown", "None")


# The one class whose read needs a credential the user supplies. `transport`
# spells it in `route_admissions`, which answers False for it and True for
# every other class; here it is what the keyless law is quantified against.
CREDENTIALED = "K5"


def load_beside_the_tree(path):
    """Load one module written beside the tree, by path.

    Not a package module: nothing in the package imports it and no discovery
    pattern matches it. It exists so an oracle can be shown to reject a wrong
    result without mutating the tree under test.
    """

    spec = importlib.util.spec_from_file_location("router_fixture_" + path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def package_sources():
    return sorted(PACKAGE_DIR.rglob("*.py"))


def sources_naming(names, sources):
    """Every (source, name) pair where a source spells one of ``names``."""

    return sorted(
        (path.name, name)
        for path in sources
        for name in names
        if name in path.read_text(encoding="utf-8")
    )


def shipped_roster():
    """Every surface the core can reach, in ``ADAPTER_IDS`` order.

    The roster the laws below are held against is what the core has registered,
    not a list written beside them: an adapter reaches a route only by being in
    ``ADAPTER_IDS`` with a branch in ``surface_descriptors``, so a later route
    that no table here knows about is still read by every law in this file.
    """

    return tuple(
        surface
        for adapter_id in runner.ADAPTER_IDS
        for surface in runner.surface_descriptors(adapter_id)
    )


def capability_of(surface):
    """What one surface can answer about, in the surface's own words.

    Every page states which platform it speaks for, under which identity
    namespace, and at which representation, and that triple is the whole of
    what a declaration says a surface can do. Two surfaces sharing it answer
    the same question; two differing anywhere in it do not, and a caller
    holding one cannot get the other's answer out of it.
    """

    return (
        surface.platform,
        surface.native_identity_namespace,
        surface.representation_kind,
    )


def named(capability):
    return "/".join(part or "-" for part in capability)


def assert_one_class_per_adapter(case, roster):
    """An adapter answers at one access class, however many routes it reads.

    A class belongs to how a read is authorized, and every route one adapter
    reads is authorized the same way. Two classes under one adapter id means a
    caller who named the adapter cannot tell which class answered — and it is
    the loophole that would let a credentialed route in beside a keyless one
    while every adapter-level count still looked right.
    """

    declared = {}
    for surface in roster:
        declared.setdefault(surface.adapter_id, set()).add(surface.access_class)
    for adapter_id, classes in sorted(declared.items()):
        if len(classes) > 1:
            case.fail(
                "adapter {0} answers at more than one access class: {1}".format(
                    adapter_id, ", ".join(sorted(classes))
                )
            )


def assert_no_capability_needs_a_credential(case, roster):
    """The keyless law over one roster, in the two ways it can break.

    A capability is unreachable without a credential either because the
    adapter that answers it has no keyless surface — a caller who names it is
    refused, and this core never substitutes another adapter — or because the
    thing the credentialed surface can say is something no keyless surface in
    the roster says at all.

    An empty roster fails rather than passes. "Every capability is reachable"
    is true of no capabilities, and a check that can only ever pass is the one
    thing this law must not be.
    """

    surfaces = tuple(roster)
    if not surfaces:
        case.fail("a roster with no surfaces in it proves nothing about credentials")

    keyless = tuple(
        surface for surface in surfaces if surface.access_class != CREDENTIALED
    )
    reachable = {surface.adapter_id for surface in keyless}
    for adapter_id in sorted({surface.adapter_id for surface in surfaces} - reachable):
        case.fail("adapter {0} is reachable only with a credential".format(adapter_id))

    served = {capability_of(surface) for surface in keyless}
    withheld = {
        capability_of(surface)
        for surface in surfaces
        if surface.access_class == CREDENTIALED
    } - served
    for capability in sorted(withheld):
        case.fail(
            "capability {0} is reachable only with a credential".format(named(capability))
        )


def assert_the_access_ladder_holds(case, roster):
    """Both laws at once, which is what any roster has to satisfy."""

    assert_one_class_per_adapter(case, roster)
    assert_no_capability_needs_a_credential(case, roster)


def strings_in(value, path="emitted"):
    """Every string one emitted value holds, paired with where it sits.

    Exhaustive by construction rather than by field list. These values gain
    fields — `attributes` arrived on the record after its first release, and
    `final_url` on the response after that — and a scan written against the
    fields they had would quietly stop covering the ones they gain, which is
    the failure mode a credential leak needs to survive.
    """

    if isinstance(value, str):
        yield path, value
    elif dataclasses.is_dataclass(value):
        for field in dataclasses.fields(value):
            yield from strings_in(getattr(value, field.name), path + "." + field.name)
    elif isinstance(value, dict):
        for key, item in value.items():
            yield from strings_in(key, "{0}[{1!r}]".format(path, key))
            yield from strings_in(item, "{0}[{1!r}]".format(path, key))
    elif isinstance(value, (tuple, list)):
        for index, item in enumerate(value):
            yield from strings_in(item, "{0}[{1}]".format(path, index))


def public_client_secrets():
    """Every string that would identify this package's client to a vendor.

    The three credential values, the ids they are held under, and the two
    header names that would only ever appear in something a run kept by
    accident. Read off ``transport`` rather than transcribed: a credential
    added there is inside this law without anybody remembering to add it.
    """

    secrets = []
    for credential in transport.PUBLIC_CLIENT_CREDENTIALS.values():
        secrets.append((credential.credential_id + " value", credential.value))
        secrets.append((credential.credential_id + " id", credential.credential_id))
    secrets.append(("the instagram app id header", "x-ig-app-id"))
    secrets.append(("the guest token header", transport.GUEST_TOKEN_HEADER))
    return tuple(secrets)


def assert_no_credential_reaches_what_the_run_keeps(case, emitted, secrets):
    """A `K1` credential is a route constant, and nothing a run keeps holds one.

    The credential is applied at send time, inside the opener, so a caller
    holding a request has never had one. This says the same thing about the
    other end: every string the emitted value actually holds, at whatever
    depth, against every secret there is. An emitted value holding no strings,
    or a secret list holding nothing, fails rather than passes — both are ways
    of proving nothing while reporting a pass.
    """

    if not secrets:
        case.fail("no credential was looked for, so nothing about credentials was checked")
    held = tuple(strings_in(emitted))
    if not held:
        case.fail("nothing was scanned, so nothing about credentials was checked")
    for path, text in held:
        for name, secret in secrets:
            if secret and secret in text:
                case.fail("{0} reached {1}".format(name, path))


THIRD_PARTY_ARCHIVE = "third_party_archive"
DISCOVERY_NOT_RECORDED = "discovery_not_recorded"
ARCHIVE_CLASS = "K3"


def assert_an_archive_never_speaks_as_the_platform(case, roster, records):
    """The `K3` law, at the declaration and at the record a caller keeps.

    An archive is not the platform: it is one operator's copy of what another
    operator published, and a caller who cannot tell the two apart will read a
    volunteer mirror's gap as the platform's own. So every `K3` surface
    declares the loss and names an operator that is not the platform, every
    `K3` record carries both, and no record on any other class carries the
    label — the mark has to mean something, which it stops doing the moment
    something that is the platform speaking wears it.

    Records with no `K3` row in them fail rather than pass: this law is about
    what an archive record says, and nothing said it.
    """

    for surface in roster:
        if surface.access_class != ARCHIVE_CLASS:
            continue
        if THIRD_PARTY_ARCHIVE not in surface.standing_loss:
            case.fail(
                "archive surface {0} declares no {1} standing loss".format(
                    surface.route_id, THIRD_PARTY_ARCHIVE
                )
            )
        if not surface.operator_identity:
            case.fail("archive surface {0} names no operator".format(surface.route_id))
        if surface.operator_identity == surface.platform:
            case.fail(
                "archive surface {0} names the platform as its operator".format(
                    surface.route_id
                )
            )

    checked = 0
    for record in records:
        if record.access_class == ARCHIVE_CLASS:
            checked += 1
            if THIRD_PARTY_ARCHIVE not in record.loss:
                case.fail(
                    "archive record {0} carries no {1} loss".format(
                        record.record_id, THIRD_PARTY_ARCHIVE
                    )
                )
            if not record.operator_identity:
                case.fail("archive record {0} names no operator".format(record.record_id))
            if record.operator_identity == record.platform:
                case.fail(
                    "archive record {0} names the platform as its operator".format(
                        record.record_id
                    )
                )
            if record.published_at and record.time_confidence != "reported":
                case.fail(
                    "archive record {0} calls its time {1}, and an archive reports"
                    " a time rather than setting it".format(
                        record.record_id, record.time_confidence
                    )
                )
        elif THIRD_PARTY_ARCHIVE in record.loss:
            case.fail(
                "record {0} on a {1} route carries {2}".format(
                    record.record_id, record.access_class, THIRD_PARTY_ARCHIVE
                )
            )
    if not checked:
        case.fail("no archive record was read, so nothing about archives was checked")


def credentialed(roster, route_ids):
    """The same roster with named routes relabelled `K5` — nothing else moved."""

    return tuple(
        dataclasses.replace(surface, access_class=CREDENTIALED)
        if surface.route_id in route_ids
        else surface
        for surface in roster
    )


def shipped_descriptor(**overrides):
    """One real descriptor with named fields replaced — the tree, not a copy.

    `dataclasses.replace` re-runs `__post_init__`, so a construction law is
    proven against the same object the package ships rather than against a
    hand-built lookalike that might be missing the field under test.
    """

    return dataclasses.replace(runner.descriptor_for("reddit_feed"), **overrides)
