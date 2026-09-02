#!/usr/bin/env python3
"""The ring commands, and the one question a returning driver asks.

Seven ring verbs over ``scripts/rings.py``'s one resolution order, plus
``resume``:

    orchflows sync [--project]         make a ring whole, render its adapters,
                                       build every declared item environment
    orchflows add <git-url>@<pin>      pin one external bundle
    orchflows new {skill|pack|workflow} <name>
    orchflows list [--kind K]          every item resolvable from here
    orchflows env <kind> <name>        the interpreter an item's scripts run through
    orchflows trust [--once] <bundle>  allow one project ring's content
    orchflows untrust <bundle>         withdraw both halves of that grant
    orchflows resume [--now <iso>]     this project's open workflow frames

``list`` reports through the same resolver runtime resolution uses, so an
item that appears here is an item that runs, and one shadowed here is one
shadowed at dispatch. ``resume`` reads the state sink and nothing else: it
is pull-based, resident in nothing, and it shows a stale frame's age rather
than deciding for the reader that the driver is gone. Output is plain text:
this command is read by a person, and orchflows has no interactive surface
of its own.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__:
    from . import (
        console, orchflows_adapters, orchflows_envs, orchflows_home,
        orchflows_scaffold, rings, rings_trust, state_root,
    )
else:  # pragma: no cover - direct/installed flat script path
    import console
    import orchflows_adapters
    import orchflows_envs
    import orchflows_home
    import orchflows_scaffold
    import rings
    import rings_trust
    import state_root


COLUMNS = ("kind", "name", "ring", "trust", "path")
RESUME_COLUMNS = ("frame", "run", "age", "journal", "children", "leases", "goal")


def _table(columns, rows) -> str:
    widths = [
        max(len(str(row[index])) for row in ([columns] + list(rows)))
        for index in range(len(columns))
    ]
    lines = []
    for row in [columns] + list(rows):
        cells = [str(value).ljust(widths[index]) for index, value in enumerate(row)]
        lines.append("  ".join(cells).rstrip())
    return "\n".join(lines)


def cmd_list(args) -> int:
    kinds = (args.kind,) if args.kind else rings.KINDS
    records = rings.inventory(kinds)
    if not records:
        print("no skills, packs or workflows resolve from here")
        return 0
    rows = [
        (
            record["kind"],
            record["name"],
            "refused" if record.get("reserved") else record["ring"],
            record["trust"],
            record["path"],
        )
        for record in records
    ]
    print(_table(COLUMNS, rows))
    notices = [
        notice
        for record in records
        for notice in list(record.get("notices") or [])
        + ([record["refusal"]] if record.get("reserved") else [])
    ]
    for notice in notices:
        print(notice)
    return 0


def cmd_resume(args) -> int:
    """Every open frame of this project, newest first, as one table.

    The one question a driver asks on coming back -- its own, after a crash
    or a compaction, or somebody else's the next morning. The row is
    deliberately not a verdict: age says how long the frame has been open
    and the reader decides whether that means abandoned, because a driver
    that is merely slow and a driver that died look identical from here.

    Nothing here writes, and the tickets family is reached at call time --
    ``orchflows`` binds rings, and this one read of the sink should not put
    the whole ticket trunk into its import graph.
    """

    if __package__:
        from . import tickets_frame
    else:  # pragma: no cover - direct/installed flat script path
        import tickets_frame

    now = tickets_frame.resume_now(args.now)
    if now is None and args.now is not None:
        print(f"error: unreadable --now: {args.now}", file=sys.stderr)
        return 1
    frames = tickets_frame.open_frames(now)
    if not frames:
        print("no open frames for this project")
        return 0
    rows = [
        (
            frame["id"], frame["run"], frame["age"],
            "yes" if frame["journal"] else "no",
            frame["children"], frame["leases"], frame["goal"],
        )
        for frame in frames
    ]
    print(_table(RESUME_COLUMNS, rows))
    return 0


def cmd_sync(args) -> int:
    if args.project:
        return _sync_project()
    layout = orchflows_home.ensure()
    print(f"home ring: {layout['home']}")
    for path in layout["created"]:
        print(f"created {path}")
    print(f"wrote {layout['lib_version']}")
    print(f"wrote {layout['gitignore']}")
    for record in orchflows_home.restore():
        detail = f" ({record['detail']})" if record.get("detail") else ""
        print(f"import {record['name']} @ {record['pin']}: {record['action']}{detail}")
    _report(orchflows_adapters.write("home"))
    _report_envs()
    return 0


def _sync_project() -> int:
    """Render the project ring's committed adapters into the project.

    A separate flag rather than a second guess: the home ring is what
    ``sync`` is for, and writing into somebody's repository is a thing they
    ask for by name.
    """

    bundle = rings.project_ring()
    if bundle is None:
        print("error: no project ring here; run orchflows new first", file=sys.stderr)
        return 1
    project = bundle.parent
    print(f"project ring: {bundle}")
    _report(orchflows_adapters.write("project", project=project, start=project))
    _report_envs()
    return 0


def _report(result: dict) -> None:
    for path in result["written"]:
        print(f"adapter {path}")
    for path in result["removed"]:
        print(f"removed {path}")


def _report_envs() -> None:
    """Build every declared item environment resolvable from here, and say so.

    Both ``sync`` forms end here: an environment is machine-local under the
    home ring whichever ring declared it, and the inventory is the same
    resolver a launch reads, so what is built is what can run.
    """

    for outcome in orchflows_envs.sync(rings.inventory()):
        if outcome["action"] == "skipped":
            print(f"env {outcome['kind']} '{outcome['name']}': skipped; {outcome['detail']}")
        else:
            print(
                f"env {outcome['kind']} '{outcome['name']}': "
                f"{outcome['action']} {outcome['interpreter']}"
            )


def cmd_env(args) -> int:
    record = orchflows_envs.resolve_interpreter(args.kind, args.name)
    print(record["interpreter"])
    return 0


def cmd_add(args) -> int:
    record = orchflows_home.add(args.reference)
    print(f"imported {record['name']} @ {record['pin']} from {record['url']}")
    print(f"cloned to {record['path']}")
    print(f"pinned in {record['lock']}")
    return 0


def _new_target(kind: str):
    """``(ring, directory)`` for a new item: the project ring when you stand
    in a project, else the home ring.

    The write target follows the shared file rather than a local overlay:
    an author standing in a repository means that repository's ring, and a
    repository that has no ring yet is one this command may open.
    """

    bundle = rings.project_ring()
    if bundle is not None:
        return "project", bundle / rings.RING_DIRS[kind]
    repo = state_root.find_repo_root(Path.cwd())
    if repo is not None:
        return "project", repo / rings.BUNDLE_DIR / rings.RING_DIRS[kind]
    return "home", rings.home_ring() / rings.RING_DIRS[kind]


def cmd_new(args) -> int:
    kind = rings.kind_of(args.kind)
    name = rings.item_name(args.name)
    if name.startswith(rings.RESERVED_PREFIX):
        raise rings.RingError(
            "reserved-name",
            f"'{name}' takes the reserved '{rings.RESERVED_PREFIX}' prefix, "
            "which is the library's mechanical floor. No ring item may carry "
            "it; choose another name.",
        )
    ring, directory = _new_target(kind)
    existing = rings.locate(kind, name)
    if any(hit["ring"] == ring for hit in existing):
        print(f"error: {kind} '{name}' is already in the {ring} ring", file=sys.stderr)
        return 1
    written = orchflows_scaffold.write(directory, kind, name)
    print(f"new {kind} '{name}' in the {ring} ring")
    for path in written:
        print(f"wrote {path}")
    if ring == "project":
        print(
            f"trust it before it resolves: orchflows trust "
            f"{directory.parent}"
        )
    for hit in existing:
        print(f"note: {kind} '{name}' also resolves from the {hit['ring']} ring at {hit['path']}")
    return 0


def cmd_trust(args) -> int:
    record = rings_trust.grant(args.bundle, once=args.once)
    kept = "for this one use" if args.once else "until its ring content changes"
    print(f"trusted {record['bundle']} {kept}")
    print(f"digest {record['digest']}")
    print(f"recorded in {record['ledger']}")
    return 0


def cmd_untrust(args) -> int:
    record = rings_trust.revoke(args.bundle)
    print(f"withdrew {record['removed']} grant(s) for {record['bundle']}")
    print(f"recorded in {record['ledger']}")
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="orchflows.py", description=__doc__, allow_abbrev=False,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    listed = subparsers.add_parser("list", help="every resolvable item", allow_abbrev=False)
    listed.add_argument("--kind", choices=rings.KINDS)
    listed.set_defaults(handler=cmd_list)
    synced = subparsers.add_parser("sync", help="make the home ring whole", allow_abbrev=False)
    synced.add_argument(
        "--project", action="store_true",
        help="render this project ring's committed adapters instead",
    )
    synced.set_defaults(handler=cmd_sync)
    added = subparsers.add_parser("add", help="pin one external bundle", allow_abbrev=False)
    added.add_argument("reference", metavar="<git-url>@<pin>")
    added.set_defaults(handler=cmd_add)
    created = subparsers.add_parser("new", help="scaffold one item", allow_abbrev=False)
    created.add_argument("kind", choices=rings.KINDS)
    created.add_argument("name")
    created.set_defaults(handler=cmd_new)
    environment = subparsers.add_parser(
        "env", help="the interpreter an item's scripts run through", allow_abbrev=False,
    )
    environment.add_argument("kind", choices=rings.KINDS)
    environment.add_argument("name")
    environment.set_defaults(handler=cmd_env)
    trusted = subparsers.add_parser("trust", help="allow one project bundle", allow_abbrev=False)
    trusted.add_argument("--once", action="store_true", help="allow one use, record nothing standing")
    trusted.add_argument("bundle")
    trusted.set_defaults(handler=cmd_trust)
    untrusted = subparsers.add_parser("untrust", help="withdraw a grant", allow_abbrev=False)
    untrusted.add_argument("bundle")
    untrusted.set_defaults(handler=cmd_untrust)
    resumed = subparsers.add_parser(
        "resume", help="this project's open workflow frames", allow_abbrev=False,
    )
    resumed.add_argument(
        "--now", metavar="<absolute-iso>",
        help="read ages against this instant instead of the clock",
    )
    resumed.set_defaults(handler=cmd_resume)
    return parser


def main(argv=None) -> int:
    console.harden()
    args = _parser().parse_args(argv)
    try:
        return args.handler(args)
    except rings.RingError as error:
        print(f"error: {error.detail}", file=sys.stderr)
        return 1
    except (OSError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(console.run(main))
