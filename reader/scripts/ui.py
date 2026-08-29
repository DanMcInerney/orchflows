#!/usr/bin/env python3
"""Launch the Observe reader's closed ``orchflows.reader.v1`` API."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
INSTALL_LIBRARY_ROOT = Path(__file__).resolve().parents[1] / "lib"
for _import_root in (REPOSITORY_ROOT, INSTALL_LIBRARY_ROOT):
    if (_import_root / "reader").is_dir() and str(_import_root) not in sys.path:
        sys.path.insert(0, str(_import_root))

from reader.scripts.ui_api import (  # noqa: E402
    PUBLIC_API_SCHEMA,
    PUBLIC_API_VERSION,
    create_application,
    create_server as _create_server,
)
from reader.scripts.ui_sessions import transcript_root  # noqa: E402
from scripts.state_root import state_root  # noqa: E402


DEFAULT_PORT = 3000


def default_root() -> Path:
    """Return the one durable state-sink root used by the reader."""

    return state_root()


def create_server(root, port: int, transcripts=None, assets=None):
    """Create the uvicorn-backed v1 reader server."""

    return _create_server(root, port, transcripts, assets)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--root",
        default=None,
        help="the state sink to view; defaults to {0}".format(default_root()),
    )
    parser.add_argument(
        "--port", type=int, default=DEFAULT_PORT, help="loopback port; 0 picks a free one"
    )
    parser.add_argument(
        "--transcripts",
        default=None,
        help="Claude Code transcript root; defaults to ~/.claude/projects",
    )
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    try:
        root = default_root() if args.root is None else Path(args.root)
        server = create_server(root, args.port, transcript_root(args.transcripts))
    except OSError as error:
        print("cannot bind port {0}: {1}".format(args.port, error), file=sys.stderr)
        return 2
    host, port = server.server_address[0], server.server_address[1]
    print(
        "orchflows reader {0} on http://{1}:{2}/ -- ctrl-c to stop".format(
            PUBLIC_API_VERSION, host, port
        )
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
