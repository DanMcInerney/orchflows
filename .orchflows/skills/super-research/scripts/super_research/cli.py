"""CLI seam: the package's operations, named one by one and closed.

Three operations and nothing else — list the roster, smoke one adapter, report
what the smokes have proven. There is no operation that takes an address, a
route, a command, or a manifest from a caller: the one argument the whole
surface accepts is an adapter id off a closed list, and everything a smoke
sends is a route constant :mod:`.routes` owns applied to a probe declared in
:mod:`.probes`. That is what keeps a convenience entry point from becoming the
generic HTTP or exec primitive the spec's non-goals refuse.

Two concerns this module used to own were moved to one-read-size siblings and
are re-exported below under the names they have always had — :mod:`.probes` for
the thirteen probe declarations and the field-name grammar they are written in,
and :mod:`.smoke` for making one read and deciding what it leaves an adapter
at. Each name still has exactly one definition; this module stays the one
address the suite reaches them at, and the one `python3 -m` entry point.

*What this module itself owns.* Which operations exist, what each may be asked,
what a run prints, and what it says on the way out. Everything a human reads
comes from here, which is why the wording of the local-network line lives here
too: an operator who mistakes this network's block for a platform's gap has
been misled by a sentence, not by a branch.

Reliability bar: nothing here reaches the network by itself. The carrier, the
clock, the moment, the ledger's path and the output stream are all parameters
of :func:`main` with the real defaults, and none of them is reachable from a
command line.
"""

from __future__ import annotations

import argparse
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from . import runner, transport
from .probes import (
    ATTRIBUTE_PREFIX,
    ENGAGEMENT_PREFIX,
    OFFLINE_ADAPTER,
    SMOKE_PROBES,
    SmokeProbe,
    probe_for,
)
from .smoke import (
    ANSWERED_BY_LOCAL_NETWORK,
    ANSWERED_BY_ORIGIN,
    FRESH_SUCCESS,
    LAST_SUCCESS_AHEAD_OF_NOW,
    LEDGER_PATH,
    NEVER_SMOKED,
    NO_RECORD_OF_THIS_KIND,
    READ_AND_ROW_UNMET,
    SMOKE_DISPOSITIONS,
    SMOKE_MAX_AGE_SECONDS,
    SMOKE_REASONS,
    STALE_SUCCESS,
    UNREADABLE_LAST_SUCCESS,
    UNVERIFIED,
    VERIFIED,
    Disposition,
    SmokeObservation,
    channel_of,
    disposition_of,
    ledger_after,
    observe,
    read_ledger,
    satisfied,
    seconds_since,
    stated_instant,
    unmet_after,
    unmet_path_beside,
    write_ledger,
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

# The loss codes that say the probe target was never the problem. Both name the
# origin refusing *this client* — one for want of an identity it will accept,
# one for want of an attestation this package does not perform — and neither is
# an answer about whether the thing asked for is still there. Advice to replace
# the target cannot help on either, and it printed on both.
#
# Read here rather than attached, which is why `protocol.md`'s two rows name
# this module: the codes belong to the adapters that type them, and what this
# module does with them is decide whether one sentence is worth printing.
#
# The set is closed at two on purpose. `http_status` is not in it and must not
# be: a `404` about a named target is the strongest evidence there is that a
# target has really gone, and it is the case the sentence exists for.
TARGET_NOT_THE_PROBLEM = ("auth_required", "attestation_required")


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
            # One row of that kind has to carry the whole list. A row assembled
            # out of several would claim a completeness no single answer had.
            lines.append("  asserts on one {0} row: {1}".format(kind, ", ".join(names)))
    return lines


def target_may_be_the_problem(observation: SmokeObservation) -> bool:
    """Whether a rotted probe target is still one of the ways this read failed.

    Read off the loss and never off the outcome or the record count, for the
    reason :func:`smoke.channel_of` is written the same way: a read that kept no
    records reports the same emptiness whatever emptied it, and only the code
    says who was refused what.
    """

    return not [code for code in observation.loss if code in TARGET_NOT_THE_PROBLEM]


def instant_word(disposition: Disposition) -> str:
    """What the instant this disposition reports is the instant *of*.

    A stamp with no word for what it stamps is the ambiguity this delivery is
    about: the same position once read "last success" or nothing at all, and
    an adapter whose last read carried no row had nothing to print there.
    """

    if disposition.last_success:
        return "last success"
    return "read and row unmet at"


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
    # The adapter's own account of what it read, before any reading of what it
    # means. A loss code names the kind of thing that happened; this is the
    # sentence that says which container moved or which identifier needs
    # renewing, and an operator re-proving a perishable route needs it.
    # Whole, not shortened: a warning is the recovery procedure, and FACT_WIDTH
    # exists to keep a kilobyte of record body off one line, not to clip a
    # sentence whose last clause names what to go and check.
    for warning in observation.warnings:
        lines.append("  the read reported: {0}".format(" ".join(warning.split())))
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
        if (
            not observation.records_kept
            and probe.target_recovery
            and target_may_be_the_problem(observation)
        ):
            # Said conditionally, because this line cannot tell which of the
            # two happened: a route that stopped working and a probe target
            # that was deleted both come back with no row, and only one of them
            # is news about the platform.
            lines.append(
                "  no row came back for the probe target {0!r}. A target that"
                " has been removed is not a platform gap: replace it — {1}".format(
                    probe.target, probe.target_recovery
                )
            )
    instant = stated_instant(disposition)
    lines.append(
        "  {0} is {1} ({2}{3})".format(
            disposition.adapter_id,
            disposition.state,
            disposition.reason,
            ", {0} {1}".format(instant_word(disposition), instant) if instant else "",
        )
    )
    return lines


def unreachable_lines(error: transport.TransportError) -> List[str]:
    """What to say when no answer came back at all, from anyone.

    A refused connection, an unresolvable name, or a TLS handshake that failed
    is the same news as this host's appliance answering: nothing about the
    platform was concluded, because nothing of the platform was read. It takes
    the same exit code for that reason. Reporting it as `1` would file a cable
    nobody plugged in as a row the origin declined to carry, which is the exact
    error findings.md section 0 exists to prevent, arriving by a different door.
    """

    return [
        "the read did not complete: {0}".format(error),
        "  no answer came back from anyone — not the origin, and not an"
        " appliance in front of it. This is a statement about this host's"
        " connection: nothing about the platform is concluded, nothing is"
        " degraded, and nothing was recorded.",
    ]


def status_lines(
    ledger: Dict[str, str], now: str, unmet: Optional[Dict[str, str]] = None
) -> List[str]:
    """Every live adapter's standing. It reports and never judges.

    No exit code turns on what is in here: on a fresh checkout nothing has been
    smoked, and a command that called that a failure would report this
    package's own state as thirteen broken platforms.

    The instant in the last column is the one this row's own reason names, so
    the column and the word beside it can never disagree — and an adapter with
    no instant at all is one no read has ever reached.
    """

    lines = ["as of {0}, against a {1}-day window:".format(now, SMOKE_MAX_AGE_SECONDS // 86400)]
    for probe in SMOKE_PROBES:
        disposition = disposition_of(ledger, probe.adapter_id, now, unmet=unmet)
        lines.append(
            "  {0:20} {1:11} {2:26} {3}".format(
                disposition.adapter_id,
                disposition.state,
                disposition.reason,
                stated_instant(disposition) or "-",
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
    held = read_ledger(ledger_path)
    ledger = ledger_after(held, observation, at)
    # A read that recorded nothing leaves the file alone rather than rewriting
    # it with what it already said.
    if ledger != held:
        write_ledger(ledger_path, ledger)
    # The second record, on the same terms and at the same instant. One read
    # can only ever move one of the two, so an operator reading either file
    # alone is reading one fact and never a mixture of both.
    unmet_path = unmet_path_beside(ledger_path)
    held_unmet = read_ledger(unmet_path)
    unmet = unmet_after(held_unmet, observation, at)
    if unmet != held_unmet:
        write_ledger(unmet_path, unmet)
    disposition = disposition_of(ledger, probe.adapter_id, at, unmet=unmet)
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

    held = LEDGER_PATH if ledger_path is None else ledger_path
    try:
        # Inside the guard, because a usage error is one of the ways a run
        # ends: argparse raises on one, and a token minted by whatever ran
        # before would otherwise outlive the process's last operation.
        parsed = build_parser().parse_args(argv)
        if parsed.operation == "smoke":
            code, lines = run_smoke(probe_for(parsed.adapter), carrier, clock, now, held)
        elif parsed.operation == "status":
            code, lines = (
                EXIT_OK,
                status_lines(
                    read_ledger(held), now(), read_ledger(unmet_path_beside(held))
                ),
            )
        else:
            code, lines = (EXIT_OK, adapter_lines())
    except transport.TransportError as error:
        # The one failure that reaches here rather than becoming a typed page:
        # the read never got an answer to type. Uncaught it left as a traceback
        # and exit `1`, the code that means the origin answered and the row was
        # not carried — a local network condition reported as a platform gap.
        code, lines = (EXIT_LOCAL_NETWORK, unreachable_lines(error))
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
