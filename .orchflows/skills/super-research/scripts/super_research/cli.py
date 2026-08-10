"""CLI seam: the package's operations, named one by one and closed.

Three operations and nothing else — list the roster, smoke one adapter, report
what the smokes have proven. There is no operation that takes an address, a
route, a command, or a manifest from a caller: the one argument the whole
surface accepts is an adapter id off a closed list, and everything a smoke
sends is a route constant :mod:`.transport` owns applied to a probe declared
here. That is what keeps a convenience entry point from becoming the generic
HTTP or exec primitive the spec's non-goals refuse.

*The smoke.* One adapter, one bounded read, and one claim: the record it
returns carries the field set that adapter's roster row names. Thirteen live
adapters, thirteen probes, and the offline adapter deliberately has none — a
smoke for ``fake`` would report this suite's health as a platform's.

*What a smoke may conclude.* Two dispositions, ``verified`` and ``unverified``,
and no third. Nothing here can reject a platform: a read that did not satisfy
its field set says so and leaves the adapter unverified, which is a statement
about evidence rather than about a capability. The one branch that matters most
reads ``loss`` and never ``outcome`` — a response this host's own network
appliance produced comes back ``failed`` like any other blocked read, and only
the loss code says the origin was never reached. Recording that as a platform
gap is the exact error findings.md §0 exists to prevent.

Reliability bar: nothing here reaches the network by itself. The carrier is
injected and defaults to the real one, the clock is injected, and the whole
suite exercises this module with both replaced.
"""

from __future__ import annotations

import argparse
import json
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from tempfile import gettempdir
from typing import Any, Callable, Dict, List, Optional, Tuple

from . import runner, schema, transport

# The adapter that reads a fixture rather than an origin, and so is the one
# member of the roster with no smoke.
OFFLINE_ADAPTER = "fake"

# How a declared field name is read off a record. A bare name is a record
# field; the two prefixes reach the two places a route's own vocabulary lands.
ENGAGEMENT_PREFIX = "engagement:"
ATTRIBUTE_PREFIX = "attribute:"
NO_RECORD_OF_THIS_KIND = "no record of this kind"

# Who answered. The verdict itself is `transport`'s and reaches here as the
# loss code T02b put on the page, which is the only thing that separates a
# local block from the origin's own refusal.
ANSWERED_BY_ORIGIN = "origin"
ANSWERED_BY_LOCAL_NETWORK = "local_network"

# What a smoke can conclude about an adapter, and there is no third word. A
# read that did not carry its row leaves the adapter unverified, which is a
# statement about what has been proven; rejecting a platform is not something
# this package does from one read.
VERIFIED = "verified"
UNVERIFIED = "unverified"
SMOKE_DISPOSITIONS = (VERIFIED, UNVERIFIED)

FRESH_SUCCESS = "fresh_success"
NEVER_SMOKED = "never_smoked"
STALE_SUCCESS = "stale_success"
UNREADABLE_LAST_SUCCESS = "unreadable_last_success"
LAST_SUCCESS_AHEAD_OF_NOW = "last_success_ahead_of_now"
SMOKE_REASONS = (
    FRESH_SUCCESS,
    NEVER_SMOKED,
    STALE_SUCCESS,
    UNREADABLE_LAST_SUCCESS,
    LAST_SUCCESS_AHEAD_OF_NOW,
)

# How long one live read stands for. A week, because every route in the roster
# depends on markup or on a vendor identifier that rotates without notice, and
# evidence older than that is a claim about a platform as it used to be. The
# spec's own words for this posture: re-proved rather than assumed.
SMOKE_MAX_AGE_SECONDS = 7 * 24 * 60 * 60
LEDGER_STAMP_FORMAT = "%Y-%m-%dT%H:%M:%SZ"

# Where the last-success stamps are kept. Outside every working tree on
# purpose: a smoke is run by hand from wherever the operator happens to be, and
# a state file that appeared inside a checkout would read as an uncommitted
# change to whoever looked next. It is a constant, so no argument can point
# this anywhere; the suite reaches it by parameter and never writes this path.
LEDGER_PATH = Path(gettempdir()) / "super-research" / "smoke-ledger.json"


@dataclass(frozen=True)
class SmokeProbe:
    """One adapter's liveness read, spelled completely and frozen.

    ``target`` is a query for a discovery probe and a target id for a
    hydration one — the same two shapes a manifest step carries, because a
    smoke is one ordinary step and not a private path into an adapter.

    ``field_sets`` is the roster row, by the content kind each part of it
    describes. Most rows describe one kind; Instagram's row describes two, a
    profile and the posts under it, and no single record carries both halves.

    ``target_recovery`` is how to obtain a current target when this one stops
    resolving. A query never goes stale and declares none; a named item, slug
    or channel id can, and a probe target that has quietly rotted would
    otherwise report a working platform as a gap. Same shape, and the same
    reason, as an adapter's ``volatile_identifiers``.
    """

    adapter_id: str
    kind: str
    target: str
    route_id: str
    field_sets: Tuple[Tuple[str, Tuple[str, ...]], ...]
    target_recovery: str = ""
    # Set above every page size the roster measured, so a whole answer is never
    # reported as a truncated one. The bound on a smoke is that it makes one
    # call; this only says how much of that one answer is kept.
    max_items: int = 200


# Thirteen probes, one per live adapter, each asserting the field set its row
# in the spec's adapter roster names. Two rows name a field the artifact
# contract cannot carry and are noted where they occur; nothing else is
# omitted, and nothing is asserted that the row does not name.
SMOKE_PROBES = (
    SmokeProbe(
        adapter_id="web_search",
        kind="discovery",
        target="rate limiting",
        route_id=transport.DDG_HTML_ROUTE,
        field_sets=(("web_hit", ("title", "canonical_locator", "body")),),
    ),
    SmokeProbe(
        adapter_id="public_page",
        kind="hydration",
        # The selection and the one document inside it, in this adapter's own
        # grammar. Nothing here is an address: the host belongs to the route.
        target="article:Rate_limiting",
        route_id=transport.PUBLIC_PAGE_ARTICLE_ROUTE,
        field_sets=(
            (
                "web_page",
                (
                    "body",
                    "exact_content_hash",
                    "observed_at",
                    ATTRIBUTE_PREFIX + "content_type",
                    ATTRIBUTE_PREFIX + "link",
                    # The row's "redirects", which is these two facts: what was
                    # asked, and what answered.
                    ATTRIBUTE_PREFIX + "requested_url",
                    ATTRIBUTE_PREFIX + "final_url",
                ),
            ),
        ),
        target_recovery=(
            "Any article title this route's own origin serves; the selection"
            " table in adapters/public_page.py names the two selections and"
            " refuses anything shaped like an address."
        ),
    ),
    SmokeProbe(
        adapter_id="reddit_archive",
        kind="hydration",
        # A long-archived post rather than a recent one: this is an archive,
        # and an old submission is the target least likely to be absent from it.
        target="z1c9z",
        route_id=transport.ARCTIC_SHIFT_POSTS_ROUTE,
        field_sets=(
            (
                "post",
                (
                    "title",
                    "author",
                    "community",
                    "canonical_locator",
                    "published_at",
                    ENGAGEMENT_PREFIX + "score",
                    ENGAGEMENT_PREFIX + "num_comments",
                ),
            ),
        ),
        # The row also names `upvote_ratio` and `selftext`. Neither is asserted:
        # a ratio is a float and the artifact admits only exact integer metrics,
        # and a link submission has no self text, so requiring it would fail a
        # healthy read.
        target_recovery=(
            "Any base-36 submission id; one comes back on the canonical_locator"
            " of every reddit_feed record."
        ),
    ),
    SmokeProbe(
        adapter_id="reddit_feed",
        kind="discovery",
        target="programming",
        route_id=transport.REDDIT_FEED_ROUTE,
        field_sets=(("post", ("title", "author", "canonical_locator", "published_at")),),
    ),
    SmokeProbe(
        adapter_id="x_syndication",
        kind="hydration",
        target="simonw",
        route_id=transport.X_SYNDICATION_TIMELINE_ROUTE,
        field_sets=(
            (
                "post",
                (
                    "body",
                    "published_at",
                    "native_parent_id",
                    ENGAGEMENT_PREFIX + "favorite_count",
                    ENGAGEMENT_PREFIX + "retweet_count",
                    ENGAGEMENT_PREFIX + "reply_count",
                    ENGAGEMENT_PREFIX + "quote_count",
                ),
            ),
        ),
        target_recovery="Any public account's handle.",
    ),
    SmokeProbe(
        adapter_id="x_guest",
        kind="hydration",
        # The account operation rather than the post one: a handle outlives any
        # single post id, and reaching it at all is what proves the guest token
        # still activates and still authorizes a read.
        target="user:simonw",
        route_id=transport.X_GUEST_GRAPHQL_ROUTE,
        field_sets=(
            (
                "profile",
                (
                    "native_item_id",
                    "title",
                    "author",
                    "canonical_locator",
                    "published_at",
                    ENGAGEMENT_PREFIX + "followers_count",
                ),
            ),
        ),
        target_recovery=(
            "Any public account's handle, prefixed `user:`. The three"
            " operations this route serves are named in adapters/x_guest.py."
        ),
    ),
    SmokeProbe(
        adapter_id="linkedin_public",
        kind="hydration",
        target="williamhgates",
        route_id=transport.LINKEDIN_PUBLIC_PROFILE_ROUTE,
        field_sets=(
            (
                "profile",
                (
                    "title",
                    "body",
                    ATTRIBUTE_PREFIX + "jobTitle",
                    ATTRIBUTE_PREFIX + "addressLocality",
                    ATTRIBUTE_PREFIX + "worksFor",
                    ATTRIBUTE_PREFIX + "alumniOf",
                ),
            ),
        ),
        target_recovery=(
            "Any public profile slug — the last path segment of a"
            " linkedin.com/in/ address. A profile whose owner published no"
            " locality or schooling carries fewer fields than the row names."
        ),
    ),
    SmokeProbe(
        adapter_id="linkedin_jobs",
        kind="discovery",
        target="reliability engineer",
        route_id=transport.LINKEDIN_JOBS_GUEST_SEARCH_ROUTE,
        field_sets=(
            ("job_posting", ("native_item_id", "title", "author", "published_at")),
        ),
    ),
    SmokeProbe(
        adapter_id="youtube_innertube",
        kind="hydration",
        target="dQw4w9WgXcQ",
        route_id=transport.YOUTUBE_INNERTUBE_ROUTE,
        field_sets=(
            (
                "video",
                ("title", "published_at", ENGAGEMENT_PREFIX + "viewCount"),
            ),
        ),
        target_recovery="Any public video id; the row's fields are the player answer's.",
    ),
    SmokeProbe(
        adapter_id="instagram_public",
        kind="hydration",
        target="instagram",
        route_id=transport.INSTAGRAM_WEB_PROFILE_ROUTE,
        field_sets=(
            (
                "profile",
                ("title", "author", "body", ENGAGEMENT_PREFIX + "edge_followed_by.count"),
            ),
            (
                "post",
                (
                    "native_item_id",
                    "published_at",
                    ENGAGEMENT_PREFIX + "edge_liked_by.count",
                    ENGAGEMENT_PREFIX + "edge_media_to_comment.count",
                ),
            ),
        ),
        target_recovery=(
            "Any public account's username. An account that hides its like"
            " counts carries fewer fields than the row names."
        ),
    ),
    SmokeProbe(
        adapter_id="hacker_news",
        kind="discovery",
        # This adapter reads two surfaces and a smoke makes one call. Search is
        # the one the row leads with and the capability the prior spec's
        # adapter did not have at all; the Firebase surface the row also names
        # is reached by a hydration step, not by this probe.
        target="python",
        route_id=transport.HN_ALGOLIA_SEARCH_ROUTE,
        field_sets=(
            (
                "story",
                (
                    "title",
                    "author",
                    "published_at",
                    ENGAGEMENT_PREFIX + "points",
                    ENGAGEMENT_PREFIX + "num_comments",
                ),
            ),
        ),
    ),
    SmokeProbe(
        adapter_id="github_rest",
        kind="hydration",
        # The repository surface rather than the search one, for the same
        # reason in reverse: an anonymous hour is sixty reads, and this is the
        # surface whose answer carries the row's counts.
        target="python/cpython",
        route_id=transport.GITHUB_REST_ROUTE,
        field_sets=(
            (
                "repository",
                (
                    "title",
                    "body",
                    "author",
                    "published_at",
                    ENGAGEMENT_PREFIX + "stargazers_count",
                    ENGAGEMENT_PREFIX + "forks_count",
                    ENGAGEMENT_PREFIX + "open_issues_count",
                ),
            ),
        ),
        target_recovery="Any public owner/name pair.",
    ),
    SmokeProbe(
        adapter_id="rss_atom",
        kind="discovery",
        target="UC_x5XG1OV2P6uZZ5FSM9Ttw",
        route_id=transport.YOUTUBE_CHANNEL_FEED_ROUTE,
        field_sets=(
            (
                "feed_entry",
                ("native_item_id", "title", "author", "canonical_locator", "published_at"),
            ),
        ),
    ),
)


@dataclass(frozen=True)
class SmokeObservation:
    """What one smoke saw, and nothing about what it means.

    ``missing`` is empty exactly when the read satisfied its roster row, and
    ``facts`` is the evidence it was satisfied against — the declared names
    with the values the route actually returned, so the claim is auditable in
    the smoke's own output rather than only in this suite.
    """

    adapter_id: str
    route_id: str
    outcome: str
    loss: Tuple[str, ...]
    records_kept: int
    channel: str
    missing: Tuple[Tuple[str, str], ...]
    facts: Tuple[Tuple[str, str], ...]
    observed_at: str


def probe_for(adapter_id: str) -> Optional[SmokeProbe]:
    """This adapter's smoke, or nothing at all. No guessing, no default."""

    for probe in SMOKE_PROBES:
        if probe.adapter_id == adapter_id:
            return probe
    return None


def probe_step(probe: SmokeProbe) -> schema.AcquisitionStep:
    """One ordinary manifest step. A smoke has no private path into an adapter."""

    if probe.kind == "discovery":
        return schema.AcquisitionStep(
            step_id="smoke",
            kind="discovery",
            adapter_id=probe.adapter_id,
            query=probe.target,
            max_items=probe.max_items,
        )
    return schema.AcquisitionStep(
        step_id="smoke",
        kind="hydration",
        adapter_id=probe.adapter_id,
        selected_hits=(
            schema.SelectedHit(discovery_locator=probe.target, target_id=probe.target),
        ),
        max_items=probe.max_items,
    )


def probe_manifest(probe: SmokeProbe, as_of: str) -> schema.AcquisitionManifest:
    return schema.AcquisitionManifest(
        manifest_id="smoke-" + probe.adapter_id,
        mode="staged",
        as_of=as_of,
        steps=(probe_step(probe),),
    )


def record_facts(record: schema.AcquisitionRecord) -> Dict[str, str]:
    """Every declarable name this record carries, with the value it carries.

    Spelled out rather than reflected: the ten fields below are the ones a
    roster row can name, and reading a field whose name was computed would make
    the field set a string this module resolves at run time instead of a list
    a reader can see.
    """

    facts = {
        "title": record.title,
        "body": record.body,
        "author": record.author,
        "community": record.community,
        "published_at": record.published_at,
        "observed_at": record.observed_at,
        "canonical_locator": record.canonical_locator,
        "native_item_id": record.native_item_id,
        "native_parent_id": record.native_parent_id,
        "exact_content_hash": record.exact_content_hash,
    }
    for snapshot in record.engagement:
        # A count of zero is a count the route reported, so the value is the
        # number as a string and presence is what the field set asks about.
        facts[ENGAGEMENT_PREFIX + snapshot.metric_name] = str(snapshot.value)
    for name, value in record.attributes:
        facts.setdefault(ATTRIBUTE_PREFIX + name, value)
    return facts


def _shortfall(record: schema.AcquisitionRecord, names: Tuple[str, ...]) -> List[str]:
    facts = record_facts(record)
    return [name for name in names if not facts.get(name)]


def field_set_report(
    records: Tuple[schema.AcquisitionRecord, ...],
    field_sets: Tuple[Tuple[str, Tuple[str, ...]], ...],
) -> Tuple[Tuple[Tuple[str, str], ...], Tuple[Tuple[str, str], ...]]:
    """What the roster row asked for, and what this read actually carried.

    One record has to satisfy a kind's whole list — a row assembled out of
    several records would claim a completeness no single answer had. Where a
    kind is unsatisfied the nearest record is the one reported on, because
    "these three fields are absent" is a finding and "something is absent" is
    not.
    """

    missing: List[Tuple[str, str]] = []
    facts: List[Tuple[str, str]] = []
    for kind, names in field_sets:
        candidates = [record for record in records if record.canonical_content_kind == kind]
        if not candidates:
            missing.append((kind, NO_RECORD_OF_THIS_KIND))
            continue
        nearest = min(candidates, key=lambda record: len(_shortfall(record, names)))
        shortfall = _shortfall(nearest, names)
        carried = record_facts(nearest)
        for name in names:
            if name in shortfall:
                missing.append((kind, name))
            else:
                facts.append((kind + " " + name, carried[name]))
    return (tuple(missing), tuple(facts))


def channel_of(outcome: str, loss: Tuple[str, ...]) -> str:
    """Who answered: the origin, or this host's own network.

    Both halves of the result are in hand and only ``loss`` decides. That is
    the whole rule, and the parameter it does not read is why it is spelled
    out: a blocked route reports ``failed`` because the outcome vocabulary has
    no member for "the origin was never reached", so an outcome cannot tell an
    intercepted read from a platform's own refusal and a reader who assumed it
    could would find nothing here to correct them.
    """

    if transport.NETWORK_INTERCEPTED in loss:
        return ANSWERED_BY_LOCAL_NETWORK
    return ANSWERED_BY_ORIGIN


def satisfied(observation: SmokeObservation) -> bool:
    """Whether this read carried the whole roster row. Nothing else counts."""

    return not observation.missing


def observe(
    probe: SmokeProbe,
    carrier: Optional[transport.Transport] = None,
    clock: Callable[[], float] = time.monotonic,
    now: Callable[[], str] = transport.utc_now_iso,
) -> SmokeObservation:
    """Make this adapter's one bounded read and report what came back.

    The carrier defaults to the real one and is built here rather than at
    import, so importing this module reaches nothing.
    """

    reached = transport.Transport() if carrier is None else carrier
    artifact = runner.run_acquisition(probe_manifest(probe, now()), reached, clock=clock)
    step = artifact.steps[0]
    missing, facts = field_set_report(artifact.records, probe.field_sets)
    return SmokeObservation(
        adapter_id=probe.adapter_id,
        route_id=step.route_id or probe.route_id,
        outcome=artifact.outcome,
        loss=artifact.loss,
        records_kept=len(artifact.records),
        channel=channel_of(artifact.outcome, artifact.loss),
        missing=missing,
        facts=facts,
        observed_at=artifact.records[0].observed_at if artifact.records else now(),
    )


@dataclass(frozen=True)
class Disposition:
    """What one adapter's smokes have proven, as of one moment.

    ``last_success`` is kept even when it is too old to count. "Unverified"
    asks for a re-proof, and a renderer that erased the stamp would leave
    nobody able to say how long ago the last one was.
    """

    adapter_id: str
    state: str
    reason: str
    last_success: str


def seconds_since(stamp: str, now: str) -> Optional[int]:
    """How long ago ``stamp`` was, or nothing at all if either is unreadable.

    A stamp this module cannot parse is not a moment, and guessing one would
    turn a corrupted ledger into evidence.
    """

    try:
        then = datetime.strptime(stamp, LEDGER_STAMP_FORMAT).replace(tzinfo=timezone.utc)
        moment = datetime.strptime(now, LEDGER_STAMP_FORMAT).replace(tzinfo=timezone.utc)
    except ValueError:
        return None
    return int((moment - then).total_seconds())


def disposition_of(
    ledger: Dict[str, str],
    adapter_id: str,
    now: str,
    max_age_seconds: int = SMOKE_MAX_AGE_SECONDS,
) -> Disposition:
    """One adapter's standing, from the ledger alone.

    Every way of not holding a current success lands on ``unverified``, and
    each says which way it was. A stamp ahead of ``now`` is one of them: a
    skewed clock or a hand-edited file would otherwise read as verified for as
    long as it stayed in the future, which is the silent success this whole
    disposition exists to refuse.
    """

    def held(state: str, reason: str, last_success: str = "") -> Disposition:
        return Disposition(
            adapter_id=adapter_id, state=state, reason=reason, last_success=last_success
        )

    last_success = ledger.get(adapter_id, "")
    if not last_success:
        return held(UNVERIFIED, NEVER_SMOKED)
    age = seconds_since(last_success, now)
    if age is None:
        return held(UNVERIFIED, UNREADABLE_LAST_SUCCESS, last_success)
    if age < 0:
        return held(UNVERIFIED, LAST_SUCCESS_AHEAD_OF_NOW, last_success)
    if age > max_age_seconds:
        return held(UNVERIFIED, STALE_SUCCESS, last_success)
    return held(VERIFIED, FRESH_SUCCESS, last_success)


def ledger_after(
    ledger: Dict[str, str], observation: SmokeObservation, at: str
) -> Dict[str, str]:
    """The ledger this observation leaves behind.

    One thing can change here and it only ever adds: a read that carried its
    whole roster row, from the origin, stamps that adapter. Nothing removes an
    entry and nothing ages one — which is what "a smoke degrades nothing" means
    where it has to be true. A blocked read is not a finding about the
    platform, a failed read has not disproved a success that was already
    proven, and expiry belongs to the window in :func:`disposition_of`, where
    it happens by the clock moving rather than by a later read revoking it.
    """

    kept = dict(ledger)
    if satisfied(observation) and observation.channel == ANSWERED_BY_ORIGIN:
        kept[observation.adapter_id] = at
    return kept


def read_ledger(path: Path) -> Dict[str, str]:
    """Every last-success stamp on disk, or nothing readable at all.

    Anything unreadable answers empty, and empty means every adapter is
    unverified. That is the only safe direction: a corrupted file that reported
    thirteen working platforms would be the silent success this package is
    built to refuse, and one that reports none costs a re-proof.
    """

    if not path.exists():
        return {}
    try:
        payload: Any = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return {}
    if not isinstance(payload, dict):
        return {}
    return {
        adapter_id: stamp
        for adapter_id, stamp in payload.items()
        if isinstance(adapter_id, str) and isinstance(stamp, str)
    }


def write_ledger(path: Path, ledger: Dict[str, str]) -> None:
    """Record the stamps, sorted, so two identical ledgers are identical bytes."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(ledger, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


# What one invocation says on the way out. `2` is argparse's own code for a
# usage error, so nothing else here takes it. The three that are this module's
# say which of the three things happened, because "did not answer" and "was
# never asked, because this network answered instead" are not the same news.
EXIT_OK = 0
EXIT_ROW_UNMET = 1
EXIT_USAGE = 2
EXIT_LOCAL_NETWORK = 3

# How much of a returned value one line shows. A record body runs to kilobytes
# and the claim being made about it is that it is there.
FACT_WIDTH = 72


@dataclass(frozen=True)
class Operation:
    """One thing this command can be asked to do, spelled completely.

    At most one argument, and an argument is always a closed list of choices.
    That is the whole surface: there is no operation that takes an address, a
    route, a path, or anything else a caller composes, which is what keeps this
    from being the generic primitive the spec's non-goals refuse.
    """

    name: str
    summary: str
    argument: str = ""
    choices: Tuple[str, ...] = ()


OPERATIONS = (
    Operation("adapters", "list the roster, each adapter's class, and what its smoke asserts"),
    Operation(
        "smoke",
        "make one live bounded read and assert that adapter's roster field set",
        argument="--adapter",
        choices=tuple(probe.adapter_id for probe in SMOKE_PROBES),
    ),
    Operation("status", "report what the smokes have proven, reaching nothing"),
)


def build_parser() -> argparse.ArgumentParser:
    """The surface, built from :data:`OPERATIONS` and from nothing else."""

    parser = argparse.ArgumentParser(
        prog="super_research.cli",
        description=(
            "Keyless read-only acquisition. Every operation is listed here;"
            " none takes an address, a route, or a command."
        ),
    )
    subcommands = parser.add_subparsers(dest="operation", required=True)
    for operation in OPERATIONS:
        subcommand = subcommands.add_parser(operation.name, help=operation.summary)
        if operation.argument:
            subcommand.add_argument(
                operation.argument, required=True, choices=operation.choices,
                help="which adapter to read, off the live roster",
            )
    return parser


def _shortened(value: str) -> str:
    single_line = " ".join(value.split())
    if len(single_line) <= FACT_WIDTH:
        return single_line
    return single_line[:FACT_WIDTH] + "..."


def adapter_lines() -> List[str]:
    """The roster, with the field set each smoke will assert."""

    lines = ["{0} live adapters, one smoke each.".format(len(SMOKE_PROBES))]
    for probe in SMOKE_PROBES:
        descriptor = runner.descriptor_for(probe.adapter_id)
        lines.append("")
        lines.append(
            "{0}  {1}  route {2}  {3} {4!r}".format(
                probe.adapter_id,
                descriptor.access_class if descriptor else "",
                probe.route_id,
                probe.kind,
                probe.target,
            )
        )
        for kind, names in probe.field_sets:
            lines.append("  asserts on each {0}: {1}".format(kind, ", ".join(names)))
    return lines


def smoke_lines(
    probe: SmokeProbe, observation: SmokeObservation, disposition: Disposition
) -> List[str]:
    """One smoke's report: what was read, what it carried, where that leaves it."""

    lines = [
        "smoke {0}: one bounded read on route {1}".format(
            observation.adapter_id, observation.route_id
        ),
        "  outcome {0}, records kept {1}, loss {2}".format(
            observation.outcome,
            observation.records_kept,
            ", ".join(observation.loss) if observation.loss else "none",
        ),
    ]
    if observation.channel == ANSWERED_BY_LOCAL_NETWORK:
        # Nothing about the platform is said here, including about its field
        # set: there was no origin answer to assert one against, and reporting
        # the row as unmet would be this network's block written down as the
        # platform's gap.
        lines.append(
            "  answered by this host's local network, not by the platform"
            " (findings.md section 0). This is a statement about this network:"
            " nothing about the platform is concluded and nothing is degraded."
        )
        lines.append("  roster field set: not asserted, nothing from the origin to assert it on")
        lines.append(
            "  {0} keeps the standing it had: {1} ({2})".format(
                disposition.adapter_id, disposition.state, disposition.reason
            )
        )
        return lines
    lines.append("  answered by the origin")
    if satisfied(observation):
        lines.append("  roster field set: carried in full")
        for name, value in observation.facts:
            lines.append("    {0} = {1}".format(name, _shortened(value)))
    else:
        lines.append("  roster field set: not carried")
        for kind, name in observation.missing:
            lines.append("    missing on {0}: {1}".format(kind, name))
        if not observation.records_kept and probe.target_recovery:
            lines.append(
                "  the probe target {0!r} returned no row. A target that has"
                " been removed is not a platform gap; a current one: {1}".format(
                    probe.target, probe.target_recovery
                )
            )
    lines.append(
        "  {0} is {1} ({2}{3})".format(
            disposition.adapter_id,
            disposition.state,
            disposition.reason,
            ", last success " + disposition.last_success if disposition.last_success else "",
        )
    )
    return lines


def status_lines(ledger: Dict[str, str], now: str) -> List[str]:
    """Every live adapter's standing. It reports and never judges.

    No exit code turns on what is in here: on a fresh checkout nothing has been
    smoked, and a command that called that a failure would report this
    package's own state as thirteen broken platforms.
    """

    lines = ["as of {0}, against a {1}-day window:".format(now, SMOKE_MAX_AGE_SECONDS // 86400)]
    for probe in SMOKE_PROBES:
        disposition = disposition_of(ledger, probe.adapter_id, now)
        lines.append(
            "  {0:20} {1:11} {2:26} {3}".format(
                disposition.adapter_id,
                disposition.state,
                disposition.reason,
                disposition.last_success or "-",
            )
        )
    return lines


def run_smoke(
    probe: SmokeProbe,
    carrier: Optional[transport.Transport],
    clock: Callable[[], float],
    now: Callable[[], str],
    ledger_path: Path,
) -> Tuple[int, List[str]]:
    """One live read, recorded, and the disposition it leaves the adapter in."""

    observation = observe(probe, carrier, clock=clock, now=now)
    at = now()
    ledger = ledger_after(read_ledger(ledger_path), observation, at)
    if ledger != read_ledger(ledger_path):
        write_ledger(ledger_path, ledger)
    disposition = disposition_of(ledger, probe.adapter_id, at)
    if observation.channel == ANSWERED_BY_LOCAL_NETWORK:
        code = EXIT_LOCAL_NETWORK
    elif satisfied(observation):
        code = EXIT_OK
    else:
        code = EXIT_ROW_UNMET
    return (code, smoke_lines(probe, observation, disposition))


def main(
    argv: Optional[List[str]] = None,
    carrier: Optional[transport.Transport] = None,
    clock: Callable[[], float] = time.monotonic,
    now: Callable[[], str] = transport.utc_now_iso,
    ledger_path: Optional[Path] = None,
    out: Optional[Any] = None,
) -> int:
    """Run one invocation. Everything below argv is a seam, and none is an argument.

    The carrier, the clock, the moment, the ledger's path and where the lines
    go are parameters so that the suite can exercise this whole path offline.
    None of them is reachable from a command line: argv names an operation and
    at most one adapter id, and the defaults are the real ones.
    """

    try:
        # Inside the guard, because a usage error is one of the ways a run
        # ends: argparse raises on one, and a token minted by whatever ran
        # before would otherwise outlive the process's last operation.
        parsed = build_parser().parse_args(argv)
        if parsed.operation == "smoke":
            code, lines = run_smoke(
                probe_for(parsed.adapter),
                carrier,
                clock,
                now,
                LEDGER_PATH if ledger_path is None else ledger_path,
            )
        elif parsed.operation == "status":
            code, lines = (
                EXIT_OK,
                status_lines(read_ledger(LEDGER_PATH if ledger_path is None else ledger_path),
                             now()),
            )
        else:
            code, lines = (EXIT_OK, adapter_lines())
    finally:
        # The run ends here, so the guest token this process may have minted
        # ends here too. It lives in a module-level store for as long as the
        # process reads, and nothing else would ever put it down.
        transport.GUEST_TOKENS.clear()
    for line in lines:
        print(line, file=out)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
