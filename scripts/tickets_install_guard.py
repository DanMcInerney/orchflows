"""Serialize pin creation with publication, before acquiring any run lock.

The lock lives outside replaced lib/bin trees. Nested mint -> dispatch calls
reuse it in one thread; another thread or process must wait. No state is
inferred from lock-file existence, so a crashed owner cannot strand a lease.
"""

from __future__ import annotations

from contextlib import contextmanager
import os
from pathlib import Path
import threading
import time

if __package__:
    from . import state_root
else:
    import state_root

_LOCAL_LOCK = threading.RLock()
_HELD = threading.local()
LOCK_TIMEOUT_SECONDS = 120


def guarded_dispatch_open(rest, *, _lock_held=False):
    if __package__:
        from .tickets_attempts import _dispatch_open
    else:
        from tickets_attempts import _dispatch_open
    if _lock_held:
        return _dispatch_open(rest, _lock_held=True)
    try:
        with installation_lock():
            return _dispatch_open(rest)
    except OSError as error:
        return {"error": f"unable to guard dispatch open: {error}"}


def guarded_dispatch_replace(rest):
    if __package__:
        from .tickets_attempts import _dispatch_replace
    else:
        from tickets_attempts import _dispatch_replace
    try:
        with installation_lock():
            return _dispatch_replace(rest)
    except OSError as error:
        return {"error": f"unable to guard dispatch replacement: {error}"}


@contextmanager
def installation_lock(home=None):
    """Hold the shared installation lock; order is installation then run."""
    root = Path(home) if home is not None else state_root.orchflows_home()
    path = root.resolve() / ".install.lock"
    deadline = time.monotonic() + LOCK_TIMEOUT_SECONDS
    if not _LOCAL_LOCK.acquire(timeout=LOCK_TIMEOUT_SECONDS):
        raise OSError(f"timed out waiting for installation lock {path}")
    handle = None
    acquired = False
    try:
        held = getattr(_HELD, "paths", set())
        if path in held:
            yield
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        handle = path.open("a+b")
        if path.stat().st_size == 0:
            handle.write(b"\0")
            handle.flush()
        while True:
            try:
                handle.seek(0)
                if os.name == "nt":
                    import msvcrt
                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                acquired = True
                break
            except OSError:
                if time.monotonic() >= deadline:
                    raise OSError(f"timed out waiting for installation lock {path}")
                time.sleep(0.05)
        _HELD.paths = held | {path}
        try:
            yield
        finally:
            _HELD.paths = held
    finally:
        if handle is not None:
            try:
                if acquired:
                    handle.seek(0)
                    if os.name == "nt":
                        import msvcrt
                        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                    else:
                        import fcntl
                        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            finally:
                handle.close()
        _LOCAL_LOCK.release()
