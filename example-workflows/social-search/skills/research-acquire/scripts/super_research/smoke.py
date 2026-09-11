"""Smoke seam: make one probe's read, and decide what it means.

Two halves, and the order between them is the whole design. First an
observation, which says only what came back — the outcome, the loss, who
answered, and whether the record carried the field set its roster row names.
Then a disposition, which says what that leaves the adapter at, and is a
function of the ledger and the clock rather than of the read just made.

Keeping them apart is what makes "a smoke degrades nothing" checkable. An
observation cannot lower anything, because it decides nothing; the ledger only
ever gains an entry; and a success expires by the window passing rather than by
a later read revoking it.

Two dispositions, ``verified`` and ``unverified``, and no third. Nothing here
can reject a platform: a read that did not carry its row says so and leaves the
adapter unverified, which is a statement about evidence rather than about a
capability. The one branch that matters most reads ``loss`` and never
``outcome`` — a response this host's own network appliance produced comes back
``failed`` like any other blocked read, and only the loss code says the origin
was never reached. Recording that as a platform gap is the exact error
evidence.md's captive-portal caveat exists to prevent.

Two records, and the second is why the first can be believed. The ledger holds
successes and only ever gains one, so the absence of a stamp there used to be
the only thing ``status`` had to go on and got *named* ``never_smoked`` — false
about every adapter an origin answered without carrying its row. Beside it sits
one stamp per read that reached an origin and went unmet, which is the fact the
ledger cannot hold, and neither record can be mistaken for the other because a
read only ever lands in one of them.

Reliability bar: the carrier is injected and defaults to the real one, the
clock and the moment are injected, and the only files this module touches are
the two stamp records, both derived from the one path it is handed.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from tempfile import gettempdir
from typing import Any, Callable, Dict, List, Optional, Tuple

from . import runner, schema, transport
from ._support.smoke_plan import probe_window_start
from .probes import ATTRIBUTE_PREFIX, ENGAGEMENT_PREFIX, SmokeProbe

# What a kind's whole list is missing when the read returned no row of it at all.
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
READ_AND_ROW_UNMET = "read_and_row_unmet"
STALE_SUCCESS = "stale_success"
UNREADABLE_LAST_SUCCESS = "unreadable_last_success"
LAST_SUCCESS_AHEAD_OF_NOW = "last_success_ahead_of_now"
SMOKE_REASONS = (
    FRESH_SUCCESS,
    NEVER_SMOKED,
    READ_AND_ROW_UNMET,
    STALE_SUCCESS,
    UNREADABLE_LAST_SUCCESS,
    LAST_SUCCESS_AHEAD_OF_NOW,
)

# What a smoke costs the origin, and the number is the whole point. One read
# per adapter is what the spec authorizes a liveness check to spend, so the step
# below declares it: the core reads one page and stops, whatever cursor the
# index came back offering. It is set here rather than on a probe because it is
# what a smoke *is* — a probe added to the table later cannot spend more, and a
# run's ordinary discovery steps, which declare no bound at all, still page to
# `runner.MAX_PAGES_PER_STEP` as they should.
PAGES_PER_SMOKE = 1

# How long one live read stands for. A week, because every route in the roster
# depends on markup or on a vendor identifier that rotates without notice, and
# evidence older than that is a claim about a platform as it used to be. The
# spec's own words for this posture: re-proved rather than assumed.
SMOKE_MAX_AGE_SECONDS = 7 * 24 * 60 * 60
LEDGER_STAMP_FORMAT = schema.INSTANT_FORMAT

# Where the last-success stamps are kept. Outside every working tree on
# purpose: a smoke is run by hand from wherever the operator happens to be, and
# a state file that appeared inside a checkout would read as an uncommitted
# change to whoever looked next. It is a constant, so no argument can point
# this anywhere; the suite reaches it by parameter and never writes this path.
LEDGER_PATH = Path(gettempdir()) / "super-research" / "smoke-ledger.json"

# What the second record's name is made of. It sits beside the ledger it
# qualifies and is derived from it, so one path is still the only thing a
# caller hands in and a suite pointing that at a temporary directory cannot
# reach the real one by writing the other half.
UNMET_SUFFIX = "-unmet"


@dataclass(frozen=True)
class SmokeObservation:
    """What one smoke saw, and nothing about what it means.

    ``missing`` is empty exactly when the read satisfied its roster row, and
    ``facts`` is the evidence it was satisfied against — the declared names
    with the values the route actually returned, so the claim is auditable in
    the smoke's own output rather than only in this suite.

    ``warnings`` is the step's own account of the read, carried verbatim from
    the page. A loss code tells an operator which kind of thing happened; the
    warning is the part that says which container moved or which identifier
    needs renewing, and a smoke whose whole purpose is re-proving a perishable
    route is the one place that sentence is worth most.
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
    warnings: Tuple[str, ...] = ()


def probe_step(probe: SmokeProbe, as_of: str) -> schema.AcquisitionStep:
    """One ordinary manifest step, bounded to one page.

    A smoke has no private path into an adapter: this is the same step kind a
    manifest names, run by the same core. The one thing it says that a
    manifest's step cannot is :data:`PAGES_PER_SMOKE` — how many pages it
    wants — and that is what holds a liveness read to the single call this
    module's callers have always been told it makes. Declared on both kinds,
    though only a discovery step can page, so the bound is a property of the
    step a smoke builds rather than of the branch it took.

    ``window_start`` carries a probe's own declared window, open-ended so a
    live account's most recent activity always stays inside it; a probe
    that declares none leaves this the empty string, the same default an
    unwindowed step has always carried.
    """

    window_start = probe_window_start(probe.window_days, as_of)
    if probe.kind == "discovery":
        return schema.AcquisitionStep(
            step_id="smoke",
            kind="discovery",
            adapter_id=probe.adapter_id,
            query=probe.target,
            max_items=probe.max_items,
            max_pages=PAGES_PER_SMOKE,
            window_start=window_start,
        )
    return schema.AcquisitionStep(
        step_id="smoke",
        kind="hydration",
        adapter_id=probe.adapter_id,
        selected_hits=(
            schema.SelectedHit(discovery_locator=probe.target, target_id=probe.target),
        ),
        max_items=probe.max_items,
        max_pages=PAGES_PER_SMOKE,
        window_start=window_start,
    )


def probe_manifest(probe: SmokeProbe, as_of: str) -> schema.AcquisitionManifest:
    return schema.AcquisitionManifest(
        manifest_id="smoke-" + probe.adapter_id,
        mode="staged",
        as_of=as_of,
        steps=(probe_step(probe, as_of),),
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

    Two codes answer the same way and for one reason. An appliance answering
    instead of the origin and nobody answering at all are both statements about
    this host's connection: no origin was read, so nothing about the platform
    can be concluded and no standing may move. What differs is only what the
    operator is told, which is `cli`'s.
    """

    if transport.NETWORK_INTERCEPTED in loss or transport.UNREACHABLE in loss:
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

    No carrier is the real case, and the core composes it: a rate governor over
    a run-local cache, built at call time so importing this module reaches
    nothing. A smoke is one read, so it never waits and never hits — but it is
    the only live path the package itself drives, and building a bare carrier
    here was how the delivery came to pace nothing at all.
    """

    artifact = runner.run_acquisition(probe_manifest(probe, now()), carrier, clock=clock)
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
        warnings=step.warnings,
    )
@dataclass(frozen=True)
class Disposition:
    """What one adapter's smokes have proven, as of one moment.

    ``last_success`` is kept even when it is too old to count. "Unverified"
    asks for a re-proof, and a renderer that erased the stamp would leave
    nobody able to say how long ago the last one was.

    ``last_unmet_read`` is the other half of the same courtesy, and it is why
    ``never_smoked`` can be believed: an adapter the origin answered without
    carrying its row has an instant, so the reason can say the read happened
    instead of denying it. Both are carried at once when both are known —
    which is which never has to be guessed, because each has its own field.
    """

    adapter_id: str
    state: str
    reason: str
    last_success: str
    last_unmet_read: str = ""


def stated_instant(disposition: Disposition) -> str:
    """The instant this disposition's own reason names, or nothing at all.

    Every reason but two is about a success and reports the success stamp;
    ``read_and_row_unmet`` is about a read that carried nothing and reports
    when that read happened; ``never_smoked`` has no instant to report, which
    is the whole of what it now claims.
    """

    return disposition.last_success or disposition.last_unmet_read


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
    unmet: Optional[Dict[str, str]] = None,
) -> Disposition:
    """One adapter's standing, from the two records and the clock.

    Every way of not holding a current success lands on ``unverified``, and
    each says which way it was. A stamp ahead of ``now`` is one of them: a
    skewed clock or a hand-edited file would otherwise read as verified for as
    long as it stayed in the future, which is the silent success this whole
    disposition exists to refuse.

    The ledger answers first and answers everything it can, so a success is
    never overruled by a later read that failed — a smoke degrades nothing.
    ``unmet`` is consulted at the one point the ledger has nothing to say,
    where the absence of a success used to be *named* ``never_smoked``: an
    adapter an origin answered without carrying its row was read, and saying it
    was not is the one thing this function may not do. A caller with no unmet
    record hands none and gets the ledger's own answer.
    """

    read_unmet = {} if unmet is None else unmet

    def held(state: str, reason: str, last_success: str = "") -> Disposition:
        return Disposition(
            adapter_id=adapter_id,
            state=state,
            reason=reason,
            last_success=last_success,
            last_unmet_read=read_unmet.get(adapter_id, ""),
        )

    last_success = ledger.get(adapter_id, "")
    if not last_success:
        if read_unmet.get(adapter_id, ""):
            return held(UNVERIFIED, READ_AND_ROW_UNMET)
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


def unmet_after(
    unmet: Dict[str, str], observation: SmokeObservation, at: str
) -> Dict[str, str]:
    """The unmet-read record this observation leaves behind.

    Kept apart from the ledger rather than folded into it, and that separation
    is the whole design: a read the origin answered without carrying its row
    stamps *this* record and never the other one, so nothing reading the ledger
    for presence can mistake a failure for a success. What this file adds is
    one fact the ledger cannot hold — that the read happened — and it is what
    lets ``never_smoked`` go back to meaning never read.

    The same two conditions as the ledger's, one of them inverted. The origin
    has to have answered, because a response this host's own appliance produced
    is not the platform being read at all and records nothing here either. And
    the row has to have gone unmet, because a read that carried it is a success
    and is already recorded as one.
    """

    kept = dict(unmet)
    if not satisfied(observation) and observation.channel == ANSWERED_BY_ORIGIN:
        kept[observation.adapter_id] = at
    return kept


def unmet_path_beside(ledger_path: Path) -> Path:
    """Where the unmet-read stamps sit for a given ledger: next to it.

    Derived rather than declared, so the one path a caller hands in still
    governs both files — a suite pointing the ledger at a temporary directory
    cannot reach the real record by writing the other half, and an operator
    finds the two facts about one adapter in one directory.
    """

    return ledger_path.with_name(ledger_path.stem + UNMET_SUFFIX + ledger_path.suffix)


def read_ledger(path: Path) -> Dict[str, str]:
    """Every stamp one of the two records holds, or nothing readable at all.

    Anything unreadable answers empty, and empty means every adapter is
    unverified. That is the only safe direction: a corrupted file that reported
    thirteen working platforms would be the silent success this package is
    built to refuse, and one that reports none costs a re-proof. An unreadable
    unmet record costs the same way and no more — an adapter falls back to
    ``never_smoked``, which is the reading that claims least.
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
