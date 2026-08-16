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

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "router"
PACKAGE_DIR = Path(__file__).resolve().parent.parent / "scripts" / "super_research"
# Where the measured payloads each surface was built against live. Read rather
# than copied: what an archive labels, and what a credentialed route's artifact
# ends up holding, have to be proven on the bytes the origin actually sent and
# not on a shape written to make the point.
TRACER_FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "tracer"
REDDIT_FEED_FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "reddit_feed"
YOUTUBE_FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "youtube"
INSTAGRAM_FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "instagram"
X_FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "x"
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
    "web_search": "K4",
    "public_page": "K0",
    "reddit_archive": "K3",
    "reddit_feed": "K0",
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


class AccessClassDeclarationTest(unittest.TestCase):
    """Criterion 2: one class per adapter, out of one closed ladder.

    The roster half and the closed-set half are separate claims. An adapter
    could declare a class that is on the ladder and wrong for its route, or a
    class that is right for its route and on no ladder at all; only the first
    is a roster question.
    """

    def test_the_ladder_is_the_one_the_schema_seam_owns(self):
        self.assertEqual(schema.ACCESS_CLASSES, LADDER)

    def test_the_core_lists_exactly_the_rosters_adapters(self):
        self.assertEqual(sorted(runner.ADAPTER_IDS), sorted(ROSTER))

    def test_every_adapter_declares_the_class_the_roster_gives_it(self):
        for adapter_id, access_class in sorted(ROSTER.items()):
            with self.subTest(adapter=adapter_id):
                descriptor = runner.descriptor_for(adapter_id)

                self.assertIsNotNone(descriptor)
                self.assertEqual(descriptor.access_class, access_class)
                self.assertIn(descriptor.access_class, LADDER)

    def test_every_surface_an_adapter_reaches_declares_that_same_one_class(self):
        assert_one_class_per_adapter(self, shipped_roster())
        for adapter_id, access_class in sorted(ROSTER.items()):
            for surface in runner.surface_descriptors(adapter_id):
                with self.subTest(adapter=adapter_id, route=surface.route_id):
                    self.assertEqual(surface.access_class, access_class)
                    self.assertEqual(surface.adapter_id, adapter_id)

    def test_exactly_one_class_is_declared_and_it_is_a_single_ladder_name(self):
        # "Exactly one" is a claim about the value, not about the field: a
        # descriptor holds one string, and the string has to be one whole class
        # name rather than a pair somebody spelled with a separator.
        for adapter_id in sorted(ROSTER):
            with self.subTest(adapter=adapter_id):
                declared = runner.descriptor_for(adapter_id).access_class

                self.assertEqual([name for name in LADDER if name == declared], [declared])


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


class KeylessCapabilityTest(unittest.TestCase):
    """Criterion 3: no first-release capability is reachable only through `K5`.

    Stated over the roster the core has actually registered, so a later adapter
    is inside the law the moment it is reachable rather than when somebody
    remembers to list it here.
    """

    def setUp(self):
        self.roster = shipped_roster()

    def test_the_roster_the_law_reads_is_every_surface_the_core_can_reach(self):
        # The law is only as wide as its input, so the input is pinned: the
        # fourteen adapters' eighteen distinct routes, which is now every route
        # in the table. The eighteenth is the guest-token activation, which
        # used to sit outside the roster on the reasoning that the opener
        # minted for itself — and sat outside every budget with it.
        self.assertEqual(len(self.roster), 18)
        self.assertEqual(
            sorted({surface.route_id for surface in self.roster}),
            sorted(transport.ROUTE_CONSTANTS),
        )
        self.assertEqual(
            len({surface.route_id for surface in self.roster}), len(self.roster)
        )
        self.assertEqual(
            sorted({surface.adapter_id for surface in self.roster}), sorted(ROSTER)
        )

    def test_every_listed_adapter_reaches_at_least_one_surface(self):
        # An adapter with no surface is a capability with no route: the law
        # below would have nothing to say about it, so it is refused here.
        for adapter_id in sorted(ROSTER):
            with self.subTest(adapter=adapter_id):
                self.assertTrue(runner.surface_descriptors(adapter_id))

    def test_no_capability_in_the_roster_needs_a_credential(self):
        assert_the_access_ladder_holds(self, self.roster)

    def test_nothing_in_the_roster_declares_the_credentialed_class(self):
        # The plain statement behind the law, kept beside it: the run measured
        # that only two capabilities genuinely need a credential and deferred
        # both, so the class exists on the ladder and nothing is in it.
        self.assertEqual(
            sorted({surface.access_class for surface in self.roster}),
            ["K0", "K1", "K2", "K3", "K4", "offline"],
        )
        self.assertIn(CREDENTIALED, schema.ACCESS_CLASSES)

    def test_every_adapter_turned_credentialed_is_rejected(self):
        # Fourteen rosters, each the shipped one with one adapter's every
        # surface relabelled. This is the check reading each adapter in turn:
        # an adapter it skipped would pass here while credentialed.
        for adapter_id in sorted(ROSTER):
            routes = {
                surface.route_id for surface in runner.surface_descriptors(adapter_id)
            }
            with self.subTest(adapter=adapter_id):
                with self.assertRaisesRegex(
                    AssertionError, "adapter {0} is reachable only".format(adapter_id)
                ):
                    assert_the_access_ladder_holds(self, credentialed(self.roster, routes))

    def test_every_single_surface_turned_credentialed_is_rejected(self):
        # Seventeen rosters, each with exactly one route relabelled. An adapter
        # reading one route fails the reachability half; an adapter reading two
        # fails the one-class half, which is why both are laws and not one.
        for surface in self.roster:
            with self.subTest(route=surface.route_id):
                with self.assertRaisesRegex(
                    AssertionError,
                    "reachable only with a credential|answers at more than one access class",
                ):
                    assert_the_access_ladder_holds(
                        self, credentialed(self.roster, {surface.route_id})
                    )


def archive_seeds():
    """The two Reddit surfaces, each answering with the bytes it was measured on."""

    return {
        transport.ARCTIC_SHIFT_POSTS_ROUTE: (
            200,
            TRACER_FIXTURE_DIR.joinpath("arctic_shift_posts_ids.json").read_text(
                encoding="utf-8"
            ),
            "application/json",
        ),
        transport.REDDIT_FEED_ROUTE: (
            200,
            REDDIT_FEED_FIXTURE_DIR.joinpath("subreddit_new.xml").read_text(encoding="utf-8"),
            "application/atom+xml",
        ),
    }


def reddit_manifest():
    """One dispatch over one post, seen by the archive and by Reddit's own feed.

    Both steps, rather than the archive alone, because half of the `K3` law is
    that the label means something: a keyless route on the same platform,
    about the same post, in the same artifact, has to come back without it.
    """

    return schema.AcquisitionManifest(
        manifest_id="m-k3",
        mode="staged",
        as_of="2026-08-10T09:05:00Z",
        steps=(
            schema.AcquisitionStep(
                step_id="s1-archive",
                kind="hydration",
                adapter_id="reddit_archive",
                selected_hits=(
                    schema.SelectedHit(
                        discovery_locator="https://www.reddit.com/r/LocalLLaMA/comments/"
                        + ARCHIVED_POST_ID
                        + "/what_is_the_best_local_model_right_now/",
                        target_id=ARCHIVED_POST_ID,
                    ),
                ),
                max_items=5,
            ),
            schema.AcquisitionStep(
                step_id="s2-feed",
                kind="discovery",
                adapter_id="reddit_feed",
                query=REDDIT_SUBREDDIT,
                max_items=20,
            ),
        ),
    )


def records_from(fetch, step, request):
    """Run one adapter — shipped or written beside the tree — into artifact records."""

    clock = helpers.FakeClock()
    carrier, _ = helpers.offline_transport(clock, archive_seeds())
    page = fetch(carrier, request)
    return normalize.normalize_page(page, step, "artifact:m-k3", "m-k3")


ARCHIVE_STEP = reddit_manifest().steps[0]
FEED_STEP = reddit_manifest().steps[1]
ARCHIVE_REQUEST = adapters.AdapterRequest(
    step_id=ARCHIVE_STEP.step_id, target_ids=(ARCHIVED_POST_ID,)
)
FEED_REQUEST = adapters.AdapterRequest(step_id=FEED_STEP.step_id, query=REDDIT_SUBREDDIT)


class ThirdPartyArchiveTest(unittest.TestCase):
    """Criterion 5: a `K3` record says whose copy it is.

    Arctic Shift is volunteer-run and has no uptime guarantee and no
    obligation to be complete. A caller who reads its answer as Reddit's own
    reads a mirror's gap as a platform gap — the mirror image of the
    interception rule the captive-portal caveat turns on — so the label and
    the operator travel on
    every row, and the row is where a caller reads them.
    """

    def setUp(self):
        clock = helpers.FakeClock()
        carrier, self.opener = helpers.offline_transport(clock, archive_seeds())
        self.artifact = runner.run_acquisition(
            reddit_manifest(), carrier, clock=clock.monotonic
        )
        self.archived = [
            record for record in self.artifact.records if record.access_class == ARCHIVE_CLASS
        ]

    def test_the_run_read_both_reddit_surfaces_and_kept_rows_from_each(self):
        # The oracle below is only worth its verdict if it read something: one
        # archived post and the feed's three entries, from two routes.
        self.assertEqual(self.artifact.outcome, "ok")
        self.assertEqual(len(self.archived), 1)
        self.assertEqual(len(self.artifact.records) - len(self.archived), 3)
        self.assertEqual(
            sorted({record.access_class for record in self.artifact.records}), ["K0", "K3"]
        )

    def test_every_archive_record_carries_the_label_and_names_its_operator(self):
        assert_an_archive_never_speaks_as_the_platform(
            self, shipped_roster(), self.artifact.records
        )

    def test_the_operator_the_records_name_is_the_archive_and_not_reddit(self):
        for record in self.archived:
            with self.subTest(record=record.record_id):
                self.assertEqual(record.operator_identity, "arctic-shift")
                self.assertEqual(record.platform, "reddit")
                self.assertEqual(
                    record.loss, (THIRD_PARTY_ARCHIVE, DISCOVERY_NOT_RECORDED)
                )
                self.assertEqual(record.time_confidence, "reported")

    def test_the_archive_row_says_this_runs_feed_did_not_discover_it(self):
        # The second code is this manifest's own shape, not an archive property.
        # One dispatch reads Reddit's feed and hydrates from the archive, and
        # `link_discovery_hydration` sources an edge from an `index` record and
        # from nothing else — a feed entry is a `feed`. So the pair is held as
        # two unlinked records, which is a real gap in the linking rule and is
        # deferred to its own spec. Deferred, now, with the gap said out loud
        # rather than legible only to a caller who counts edges.
        self.assertEqual(self.artifact.edges, ())
        self.assertEqual(
            sorted({record.representation_kind for record in self.artifact.records}),
            ["feed", "native"],
        )
        self.assertEqual(
            [
                record.record_id
                for record in self.artifact.records
                if DISCOVERY_NOT_RECORDED in record.loss
            ],
            [record.record_id for record in self.archived],
        )

    def test_reddits_own_feed_about_the_same_post_is_not_wearing_the_label(self):
        # Same platform, same post, one artifact. The feed's row states an
        # absence of its own — no engagement — and says nothing about archives.
        feed = [
            record for record in self.artifact.records if record.route_id == "reddit_feed"
        ]

        self.assertTrue(feed)
        for record in feed:
            with self.subTest(record=record.record_id):
                self.assertNotIn(THIRD_PARTY_ARCHIVE, record.loss)
                self.assertEqual(record.operator_identity, "reddit")
                self.assertEqual(record.time_confidence, "authoritative")

    def test_the_only_archive_surface_in_the_roster_is_the_one_that_declares_it(self):
        archives = [
            surface for surface in shipped_roster() if surface.access_class == ARCHIVE_CLASS
        ]

        self.assertEqual([surface.route_id for surface in archives], ["arctic_shift_posts_ids"])
        self.assertEqual(archives[0].standing_loss, (THIRD_PARTY_ARCHIVE,))
        self.assertEqual(archives[0].operator_identity, "arctic-shift")


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
                request = transport.build_transport_request(route_id)

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
            "capability youtube/youtube/transcript is reachable only with a credential",
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
            "capability youtube/youtube/transcript is reachable only with a credential",
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


if __name__ == "__main__":
    unittest.main()
