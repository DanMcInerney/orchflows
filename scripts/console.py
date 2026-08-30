#!/usr/bin/env python3
"""The console discipline every entrypoint in this directory takes first.

Two ways a script loses its own report, and neither is a fault of the work
it did. A Windows console left on a legacy code page (cp1252) cannot encode
a path, a ticket's prose, or a diagnostic quoting an em dash, and a script
that raises while printing its verdict reports none of it -- five green
required checks were lost once to a crash inside their own output. And a
caller that stops reading -- ``| head``, a closed pager, a consumer that
exited -- leaves the next write on a broken pipe, which CPython turns into
a traceback at interpreter shutdown and exit status 120, as though the tool
itself had failed.

``harden`` answers the first: stdout and stderr are reconfigured to UTF-8
with ``errors="replace"``, so the console's own codec is never consulted
and an unencodable character costs one glyph instead of the whole report.
``run`` answers the second: a closed stdout is the reader's decision and
not this tool's error, so the remaining writes go to the null device and
the process exits 0 with nothing on stderr.

Stdlib only, Python 3.9 and up, and it imports nothing else from this
directory on purpose: it runs before a script has read its own arguments,
so anything it pulled in would be imported before that script could refuse.
"""

from __future__ import annotations

import errno
import os
import sys

STREAM_ENCODING = "utf-8"
STREAM_ERRORS = "replace"
# What "nobody is reading this any more" is spelled as. POSIX raises EPIPE,
# which CPython hands over as `BrokenPipeError`; Windows answers a write to
# an anonymous pipe whose reader is gone with EINVAL through the C runtime
# and no `winerror` at all, so the platform's own spelling has to be
# accepted here or the discipline would hold on POSIX alone -- and Windows
# is the host this whole module exists for.
CLOSED_READER_ERRNOS = frozenset(
    {errno.EPIPE} | ({errno.EINVAL} if sys.platform == "win32" else set())
)


def harden(streams=None) -> None:
    """Put stdout and stderr on UTF-8, replacing what they cannot encode.

    Every failure is swallowed by design. A stream with no ``reconfigure``
    -- a test's ``StringIO``, a detached or already-wrapped stream -- takes
    whatever codec it has, which is a mangled glyph rather than a lost
    report, and a script that could not harden its console still has a
    verdict to print.
    """

    for stream in ((sys.stdout, sys.stderr) if streams is None else streams):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding=STREAM_ENCODING, errors=STREAM_ERRORS)
        except (AttributeError, LookupError, OSError, ValueError):
            pass


def closed_reader(error: OSError) -> bool:
    """Whether ``error`` says the reader of this stream has gone away.

    Narrow on purpose: a disk that filled up (``ENOSPC``) while a caller
    redirected stdout to a file is a real failure and has to stay one.
    """

    return isinstance(error, BrokenPipeError) or error.errno in CLOSED_READER_ERRNOS


def _silenced() -> int:
    """Point stdout's descriptor at the null device and answer 0.

    The explicit flush in ``run`` is not enough on its own: the interpreter
    flushes again on the way out, and a second write to the broken pipe is
    the "Exception ignored in: <_io.TextIOWrapper ...>" line plus exit 120
    that this exists to stop. Replacing the descriptor makes that last
    flush a write nobody reads, which is what the caller asked for.
    """

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
    """``main``'s exit code, with this console's discipline around it.

    ``SystemExit`` is caught rather than allowed through because argparse
    leaves that way for ``--help``: the status is argparse's to choose, but
    the flush that follows is still this module's to answer for, and a
    ``--help`` piped into a closed reader is exactly the call a caller
    makes. The hardening is repeated here rather than trusted to ``main``
    so a script whose ``main`` a test also calls in-process hardens on both
    paths; reconfiguring a stream twice costs nothing.
    """

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
