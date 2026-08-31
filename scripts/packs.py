#!/usr/bin/env python3
"""Resolve pack data and return the four cells every verb reads.

Pack files are Markdown at the authoring boundary, but the resolved value is
one closed JSON object.  The resolver is deliberately the only reader of a
pack: callers do not need to know how cells are encoded or which references
are part of their identity.  A digest is derived from the resolved cells,
every local reference's bytes, the signature contract, and this resolver's
version.  Scope and filesystem paths are observations, not
part of identity, so identical project and canonical packs resolve to one
digest.

The module is stdlib-only and works both from ``scripts/`` in a checkout and
from the flat ``bin/`` directory produced by ``install.py``.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Optional, Sequence

if __package__:
    from . import console
    from . import packs_support as _support
else:  # pragma: no cover - direct/installed script path
    import console
    import packs_support as _support


# Public exports keep the checkout and installed import seams flat.
RESOLVER_VERSION = _support.RESOLVER_VERSION
PACK_CELLS = _support.PACK_CELLS
TYPED_CELLS = _support.TYPED_CELLS
PackError = _support.PackError
ADAPTER_REGISTRY = _support.ADAPTER_REGISTRY


def resolve_pack(
    pack: str,
    *,
    canonical_root: Optional[Path] = None,
    project_root: Optional[Path] = None,
    user_root: Optional[Path] = None,
) -> Dict[str, object]:
    """Resolve one pack through the same-family implementation."""

    return _support.resolve_pack(
        pack,
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
    """Return one resolved digest's cells through the same-family implementation."""

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
        prog="packs.py",
        description=__doc__,
        allow_abbrev=False,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    resolve = subparsers.add_parser(
        "resolve",
        help="resolve a pack and emit its digest",
        allow_abbrev=False,
    )
    resolve.add_argument("pack")
    cells = subparsers.add_parser(
        "cells",
        help="return the cells of a resolved digest",
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
            result = resolve_pack(args.pack, **common)
        else:
            result = cells_for(args.digest, **common)
    except PackError as error:
        print(json.dumps({"error": {"code": error.code, "detail": error.detail}}, ensure_ascii=False))
        return 1
    except (OSError, ValueError) as error:
        print(json.dumps({"error": {"code": "packs-error", "detail": str(error)}}, ensure_ascii=False))
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(console.run(main))
