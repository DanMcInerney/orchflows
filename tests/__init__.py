"""No test in this suite can reach the real state sink.

``scripts/state_root.py`` resolves durable run state to
``$ORCHFLOWS_STATE_HOME``, else ``~/.orchflows/state`` — the user's real
evidence history. ``ensure_temporary_sink`` points that variable at one
per-process temporary directory, removed at exit, and every subprocess a
test launches inherits it.

It fires from two places, because neither alone covers both ways this
suite is run:

- this module's body, for ``python -m unittest tests.test_x``, which
  imports the package;
- ``tests/test_state_root.py``, for ``python -m unittest discover -s
  tests`` — the check ``AGENTS.md`` requires — which sets the top-level
  directory to ``tests/`` and therefore never imports this package at
  all. Discovery imports every module before it runs any test, so one
  module calling this is enough to cover the whole run whatever its
  alphabetical position.

It is a guard, not a convention: a test that forgets to build its own
sink writes into the temporary one and is merely useless, never
destructive. ``tools/suite_check.py`` watches the real sink from outside
the suite process and reports any run that touched it anyway.

A test that needs the *unset* case clears the variable for the one call
it wraps and restores it, never for the rest of the process.
"""

import atexit
import os
import tempfile
from pathlib import Path

STATE_HOME_ENV_VAR = "ORCHFLOWS_STATE_HOME"

_SINK = None


def ensure_temporary_sink() -> str:
    """Point the sink at a per-process temporary directory. Idempotent.

    Resolved before it is published: a macOS tempdir is reached through a
    ``/var`` symlink, so an unresolved value makes a script's reported
    path and a test's own path two spellings of one file.
    """

    global _SINK
    if _SINK is None:
        _SINK = tempfile.TemporaryDirectory(prefix="orchflows-test-sink-")
        atexit.register(_SINK.cleanup)
    resolved = str(Path(_SINK.name).resolve())
    os.environ[STATE_HOME_ENV_VAR] = resolved
    return resolved


ensure_temporary_sink()
