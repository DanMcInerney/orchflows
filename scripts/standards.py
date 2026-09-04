#!/usr/bin/env python3
"""Resolve one standard and return what every verb reads off it.

A standard is one Markdown manifest at the authoring boundary, but the
resolved value is one closed JSON object, and this resolver is its only
reader. A digest is derived from the standard's whole directory tree --
each file's directory-relative path and its bytes -- plus the declared
adapter, `contracts/standard.md`, and this resolver's version. Scope and
filesystem paths are observations, not part of identity, so identical
project and canonical standards resolve to one digest.

Stdlib-only, and works both from ``scripts/`` in a checkout and from the
flat ``bin/`` directory ``install.py`` produces.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Optional, Sequence

if __package__:
    from . import console
    from . import standards_support as _support
else:  # pragma: no cover - direct/installed script path
    import console
    import standards_support as _support


# Public exports keep the checkout and installed import seams flat.
RESOLVER_VERSION = _support.RESOLVER_VERSION
StandardError = _support.StandardError
ADAPTER_REGISTRY = _support.ADAPTER_REGISTRY
STANDARD_DEPTH_LIMIT = _support.STANDARD_DEPTH_LIMIT
STANDARD_KIND = _support.STANDARD_KIND


def resolve_chain(names, **overrides):
    """Resolve stamped names to one chain through the same-family implementation."""

    return _support.resolve_chain(names, **overrides)


def adapter_standard(names, **overrides) -> str:
    """The one resolved standard declaring the adapter, same-family."""

    return _support.adapter_standard(names, **overrides)


def resolve_standard(
    standard: str,
    *,
    canonical_root: Optional[Path] = None,
    project_root: Optional[Path] = None,
    user_root: Optional[Path] = None,
) -> Dict[str, object]:
    """Resolve one standard through the same-family implementation."""

    return _support.resolve_standard(
        standard,
        canonical_root=canonical_root,
        project_root=project_root,
        user_root=user_root,
    )


def cells_for(
    digest: str,
    *,
    canonical_root: Optional[Path] = None,
    project_root: Optional[Path] = None,
    user_root: Optional[Path] = None,
) -> Dict[str, object]:
    """Return what one resolved digest identifies, same-family."""

    return _support.cells_for(
        digest,
        canonical_root=canonical_root,
        project_root=project_root,
        user_root=user_root,
    )


def _path_arg(value: Optional[str]) -> Optional[Path]:
    return Path(value).expanduser() if value else None


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="standards.py",
        description=__doc__,
        allow_abbrev=False,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    resolve = subparsers.add_parser(
        "resolve",
        help="resolve a standard and emit its digest",
        allow_abbrev=False,
    )
    resolve.add_argument("standard")
    cells = subparsers.add_parser(
        "cells",
        help="return the standard one resolved digest identifies",
        allow_abbrev=False,
    )
    cells.add_argument("digest")
    for subparser in (resolve, cells):
        subparser.add_argument("--canonical-root", dest="canonical_root")
        subparser.add_argument("--project-root", dest="project_root")
        subparser.add_argument("--user-root", dest="user_root")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    console.harden()
    parser = _parser()
    try:
        args = parser.parse_args(argv)
        common = {
            "canonical_root": _path_arg(args.canonical_root),
            "project_root": _path_arg(args.project_root),
            "user_root": _path_arg(args.user_root),
        }
        if args.command == "resolve":
            result = resolve_standard(args.standard, **common)
        else:
            result = cells_for(args.digest, **common)
    except StandardError as error:
        print(json.dumps({"error": {"code": error.code, "detail": error.detail}}, ensure_ascii=False))
        return 1
    except (OSError, ValueError) as error:
        print(json.dumps({"error": {"code": "standards-error", "detail": str(error)}}, ensure_ascii=False))
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(console.run(main))
