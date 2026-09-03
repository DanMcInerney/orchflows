#!/usr/bin/env python3
"""The ring commands, and the one question a returning driver asks.

Eight ring verbs over ``scripts/rings.py``'s one resolution order, plus
``resume``:

    orchflows sync [--project]         make a ring whole, render its adapters,
                                       settle every item's declared dependencies
    orchflows add <git-url>@<pin>      pin one external bundle
    orchflows new {skill|pack|sheet|workflow} <name>
    orchflows new bundle [<name>]      the manifest of the ring at hand
    orchflows list [--kind K]          every item resolvable from here
    orchflows check [<ring-dir>]       grade a ring's items, exit 1 on a refusal
    orchflows env <kind> <name>        the interpreter an item's scripts run through
    orchflows trust [--once] <bundle>  allow one project ring's content
    orchflows untrust <bundle>         withdraw both halves of that grant
    orchflows resume [--now <iso>]     this project's open workflow frames

``list`` reports through the resolver runtime resolution uses, so an item
that appears here is an item that runs. ``resume`` reads the state sink and
nothing else. Output is plain text: orchflows has no interactive surface.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__:
    from . import (
        console, orchflows_adapters, orchflows_check, orchflows_envs,
        orchflows_home, orchflows_node, orchflows_scaffold, orchflows_tools,
        rings, rings_trust, state_root,
    )
else:  # pragma: no cover - direct/installed flat script path
    import console
    import orchflows_adapters
    import orchflows_check
    import orchflows_envs
    import orchflows_home
    import orchflows_node
    import orchflows_scaffold
    import orchflows_tools
    import rings
    import rings_trust
    import state_root


# `new`'s one non-item target: a bundle is the ring itself, not something
# in it, so it is refused everywhere a ring kind is resolved.
BUNDLE_KIND = "bundle"
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


def cmd_check(args) -> int:
    """Grade one ring with the library compiler's own item checks."""

    ring = orchflows_check.ring_at(args.ring)
    if not ring.is_dir():
        print(
            f"error: no ring at {ring}; run orchflows sync to make one",
            file=sys.stderr,
        )
        return 1
    diag, counted = orchflows_check.check(ring)
    print(f"ring: {ring}")
    print(", ".join(f"{kind} {counted[kind]}" for kind in rings.KINDS))
    for line in diag.lines():
        print(line)
    return 1 if diag.has_errors else 0


def cmd_resume(args) -> int:
    """Every open frame of this project, newest first, as one table."""

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
    _report_dependencies()
    return 0


def _sync_project() -> int:
    """Render the project ring's committed adapters into the project."""

    bundle = rings.project_ring()
    if bundle is None:
        print("error: no project ring here; run orchflows new first", file=sys.stderr)
        return 1
    project = bundle.parent
    print(f"project ring: {bundle}")
    _report(orchflows_adapters.write("project", project=project, start=project))
    print(f"wrote {orchflows_home.ensure_project_ignores(project)}")
    _report_dependencies()
    return 0


def _report(result: dict) -> None:
    for path in result["written"]:
        print(f"adapter {path}")
    for path in result["removed"]:
        print(f"removed {path}")


def _report_dependencies() -> None:
    """Settle every declared dependency resolvable from here, and say so."""

    records = rings.inventory()
    for outcome in orchflows_envs.sync(records):
        if outcome["action"] == "skipped":
            print(f"env {outcome['kind']} '{outcome['name']}': skipped; {outcome['detail']}")
        else:
            print(
                f"env {outcome['kind']} '{outcome['name']}': "
                f"{outcome['action']} {outcome['interpreter']}"
            )
    for outcome in orchflows_envs.prune(records):
        print(f"env {outcome['kind']} '{outcome['name']}': pruned {outcome['env']}")
    for report in orchflows_tools.check_inventory(records):
        where = (
            "" if report["line"] is None
            else f" ({orchflows_tools.TOOLS_NAME} line {report['line']})"
        )
        print(f"tools {report['kind']} '{report['name']}': {report['detail']}{where}")
    for outcome in orchflows_node.sync(records):
        if outcome["action"] == "skipped":
            print(f"node {outcome['kind']} '{outcome['name']}': skipped; {outcome['detail']}")
        else:
            print(
                f"node {outcome['kind']} '{outcome['name']}': "
                f"{outcome['action']} {outcome['modules']}"
            )


def cmd_env(args) -> int:
    record = orchflows_envs.resolve_interpreter(args.kind, args.name)
    print(record["interpreter"])
    return 0


def cmd_add(args) -> int:
    record = orchflows_home.add(args.reference)
    print(f"imported {record['name']} @ {record['pin']} from {record['url']}")
    print(f"cloned to {record['path']}")
    for required in record["required"]:
        print(
            f"required {required['name']} @ {required['pin']} "
            f"from {required['url']}"
        )
    print(f"pinned in {record['lock']}")
    return 0


def _new_ring():
    """``(ring, bundle directory)`` a new item or manifest is written into:
    the project ring when you stand in a project, else the home ring."""

    bundle = rings.project_ring()
    if bundle is not None:
        return "project", bundle
    repo = state_root.find_repo_root(Path.cwd())
    if repo is not None:
        return "project", repo / rings.BUNDLE_DIR
    return "home", rings.home_ring()


def _new_target(kind: str):
    """``(ring, directory)`` for a new item of ``kind``."""

    ring, bundle = _new_ring()
    return ring, bundle / rings.RING_DIRS[kind]


def _bundle_name(directory: Path) -> str:
    """The name a manifest takes when the author names none."""

    try:
        return rings.item_name(Path(directory).resolve().parent.name)
    except rings.RingError:
        raise rings.RingError(
            "bundle-unnamed",
            f"{directory} gives a bundle no name to take: run "
            "orchflows new bundle <name>.",
        )


def cmd_new_bundle(args) -> int:
    """Scaffold the manifest of the ring at hand (contracts/bundle.md)."""

    ring, directory = _new_ring()
    name = rings.item_name(args.name) if args.name else _bundle_name(directory)
    path = orchflows_scaffold.write_bundle(directory, name)
    print(f"new bundle '{name}' in the {ring} ring")
    print(f"wrote {path}")
    return 0


def cmd_new(args) -> int:
    if args.kind == BUNDLE_KIND:
        return cmd_new_bundle(args)
    if not args.name:
        print(f"error: orchflows new {args.kind} needs a name", file=sys.stderr)
        return 1
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
    created = subparsers.add_parser(
        "new", help="scaffold one item, or this ring's bundle manifest",
        allow_abbrev=False,
    )
    created.add_argument("kind", choices=(*rings.KINDS, BUNDLE_KIND))
    created.add_argument("name", nargs="?", help="required for every kind but bundle")
    created.set_defaults(handler=cmd_new)
    checked = subparsers.add_parser(
        "check", help="grade a ring's items", allow_abbrev=False,
    )
    checked.add_argument(
        "ring", nargs="?", metavar="<ring-dir>",
        help="the ring to grade; default this project's, else the home ring",
    )
    checked.set_defaults(handler=cmd_check)
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
