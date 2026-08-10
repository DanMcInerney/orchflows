"""CLI seam: the package's operations, named one by one and closed.

Three operations and nothing else — list the roster, smoke one adapter, report
what the smokes have proven. There is no operation that takes an address, a
route, a command, or a manifest from a caller: the one argument the whole
surface accepts is an adapter id off a closed list, and everything a smoke
sends is a route constant :mod:`.transport` owns applied to a probe declared in
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
    held = read_ledger(ledger_path)
    ledger = ledger_after(held, observation, at)
    # A read that recorded nothing leaves the file alone rather than rewriting
    # it with what it already said.
    if ledger != held:
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

    held = LEDGER_PATH if ledger_path is None else ledger_path
    try:
        # Inside the guard, because a usage error is one of the ways a run
        # ends: argparse raises on one, and a token minted by whatever ran
        # before would otherwise outlive the process's last operation.
        parsed = build_parser().parse_args(argv)
        if parsed.operation == "smoke":
            code, lines = run_smoke(probe_for(parsed.adapter), carrier, clock, now, held)
        elif parsed.operation == "status":
            code, lines = (EXIT_OK, status_lines(read_ledger(held), now()))
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
