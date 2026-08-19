"""Test package. Importing it installs the guards the whole suite needs.

Two of them, for two hazards a single test cannot be trusted to remember:

- ``ensure_temporary_sink`` points ``$ORCHFLOWS_STATE_HOME`` at one
  per-process temporary directory, removed at exit and inherited by every
  subprocess a test launches, so no test can reach the user's real
  evidence history. ``scripts/state_root.py`` otherwise resolves durable
  run state to ``~/.orchflows/state``. It is a guard, not a convention: a
  test that forgets to build its own sink writes into the temporary one
  and is merely useless, never destructive. ``tools/suite_check.py``
  watches the real sink from outside the suite process and reports any
  run that touched it anyway. A test that needs the *unset* case clears
  the variable for the one call it wraps and restores it, never for the
  rest of the process.
- ``_windows_semantics.install`` makes POSIX refuse the directory
  deletions Windows refuses, so CI's one Windows leg stops being the
  first place that shape is seen.

Neither is reached by importing this package alone, because
``unittest discover -s tests`` — the check ``AGENTS.md`` requires — makes
``tests/`` the top-level directory and never imports the package at all.
``tests/test_state_root.py`` and ``tests/test_windows_semantics.py``
each import it by name for that reason. Discovery imports every module
before running any test, so one such module is enough to cover a whole
run whatever its alphabetical position.
"""

import atexit
import os
import tempfile
from pathlib import Path

from . import _windows_semantics

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
_windows_semantics.install()
