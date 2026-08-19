"""Make POSIX refuse the directory deletions Windows refuses.

Windows cannot delete a directory that is any process's current
directory, or any ancestor of one: the open handle behind the CWD holds
it and the call fails with ``WinError 32``. POSIX carries no such
handle, so the same code deletes the tree, leaves the process sitting in
a path that no longer resolves, and passes.

That difference is invisible on this host and fatal on CI's one Windows
leg among five active CI legs. Installed on POSIX, these guards raise
before the deletion so the diagnosis is a local stack trace. On Windows
they are not installed: the platform already enforces this, and better.

Imported for effect by ``tests/__init__.py``, so every runner that can
load a test module has already installed it.
"""

from __future__ import annotations

import os
import pathlib
import shutil

SKIP_ENV = "ORCHFLOWS_NO_WINDOWS_SEMANTICS"

_installed = False


class WindowsWouldRefuse(RuntimeError):
    """A deletion this platform allows and Windows does not.

    Deliberately not an ``OSError``: a caller guarding its own cleanup
    with ``except OSError`` would swallow the very report this exists to
    make, and ``TemporaryDirectory(ignore_cleanup_errors=True)`` would
    do the same.
    """


def _holds_the_cwd(target) -> bool:
    """True when the process's current directory is at or under ``target``.

    Both sides are resolved because the two can name one directory
    differently -- a macOS temporary tree is reached as ``/var/...`` and
    reported as ``/private/var/...`` -- and a prefix test on unresolved
    names would miss every such case.
    """

    try:
        here = os.path.realpath(os.getcwd())
        there = os.path.realpath(os.fspath(target))
    except (OSError, ValueError, TypeError):
        return False  # Nothing to say about a path the OS cannot answer for.
    return here == there or here.startswith(there + os.sep)


def _refuse(target) -> None:
    raise WindowsWouldRefuse(
        "Windows would refuse to remove %s: it is, or contains, this "
        "process's current directory (%s). Restore the current directory "
        "before the tree is removed -- unittest runs cleanups last-in "
        "first-out, so an addCleanup(os.chdir, before) registered after "
        "the tree's own cleanup runs first. Set %s=1 to run without this "
        "guard." % (os.fspath(target), os.getcwd(), SKIP_ENV)
    )


def install() -> None:
    """Wrap the directory-removal entry points. Idempotent; POSIX only."""

    global _installed
    if _installed or os.name == "nt" or os.environ.get(SKIP_ENV):
        return
    _installed = True

    for module, name in ((shutil, "rmtree"), (os, "rmdir"), (os, "removedirs")):
        setattr(module, name, _guarded(getattr(module, name)))
    # Patched separately because pathlib does not always route here:
    # through 3.9 `Path.rmdir` is bound to `os.rmdir` when the class is
    # defined, so a later patch of `os.rmdir` never reaches it.
    pathlib.Path.rmdir = _guarded_method(pathlib.Path.rmdir)


def _guarded(original):
    def guarded(path, *args, **kwargs):
        if _holds_the_cwd(path):
            _refuse(path)
        return original(path, *args, **kwargs)

    guarded.__name__ = getattr(original, "__name__", "guarded")
    guarded.__doc__ = getattr(original, "__doc__", None)
    return guarded


def _guarded_method(original):
    def guarded(self, *args, **kwargs):
        if _holds_the_cwd(self):
            _refuse(self)
        return original(self, *args, **kwargs)

    guarded.__name__ = getattr(original, "__name__", "guarded")
    guarded.__doc__ = getattr(original, "__doc__", None)
    return guarded
