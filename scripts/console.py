#!/usr/bin/env python3
"""The console discipline every entrypoint in this directory takes first.

``harden`` puts stdout and stderr on UTF-8 with ``errors="replace"``, so a
console left on a legacy code page costs one glyph instead of the whole
report. ``run`` answers the other loss: a closed stdout is the reader's
decision, so the remaining writes go to the null device and the process
exits 0 rather than raising at interpreter shutdown.

Stdlib only, Python 3.9 and up, and it imports nothing else from this
directory: it runs before a script has read its own arguments.
"""

from __future__ import annotations

import errno
import os
import sys

STREAM_ENCODING = "utf-8"
STREAM_ERRORS = "replace"
# What "nobody is reading this any more" is spelled as. POSIX raises EPIPE,
# which CPython hands over as `BrokenPipeError`; Windows answers a write to
# an anonymous pipe whose reader is gone with EINVAL and no `winerror`, so
# both spellings have to be accepted here.
CLOSED_READER_ERRNOS = frozenset(
    {errno.EPIPE} | ({errno.EINVAL} if sys.platform == "win32" else set())
)


def harden(streams=None) -> None:
    """Put stdout and stderr on UTF-8, replacing what they cannot encode."""

    for stream in ((sys.stdout, sys.stderr) if streams is None else streams):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding=STREAM_ENCODING, errors=STREAM_ERRORS)
        except (AttributeError, LookupError, OSError, ValueError):
            pass


def closed_reader(error: OSError) -> bool:
    """Whether ``error`` says the reader of this stream has gone away."""

    return isinstance(error, BrokenPipeError) or error.errno in CLOSED_READER_ERRNOS


def _silenced() -> int:
    """Point stdout's descriptor at the null device and answer 0."""

    try:
        descriptor = sys.stdout.fileno()
    except (AttributeError, OSError, ValueError):  # not a real file
        return 0
    try:
        null = os.open(os.devnull, os.O_WRONLY)
    except OSError:  # pragma: no cover - no null device on this host
        return 0
    try:
        os.dup2(null, descriptor)
    except OSError:  # pragma: no cover - the descriptor went away too
        pass
    finally:
        os.close(null)
    return 0


def _flushed(stream) -> bool:
    """Whether ``stream`` took what was written to it. False: reader gone."""

    try:
        stream.flush()
    except OSError as error:
        if not closed_reader(error):
            raise
        return False
    return True


def run(main, *arguments):
    """``main``'s exit code, with this console's discipline around it."""

    harden()
    try:
        code = main(*arguments)
    except SystemExit as leaving:
        code = leaving.code
    except OSError as error:
        if not closed_reader(error):
            raise
        return _silenced()
    if not _flushed(sys.stdout):
        return _silenced()
    _flushed(sys.stderr)
    return 0 if code is None else code


__all__ = (
    "CLOSED_READER_ERRNOS", "STREAM_ENCODING", "STREAM_ERRORS",
    "closed_reader", "harden", "run",
)
