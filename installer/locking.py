"""Serialize concurrent installers outside the payload directories they replace."""

from __future__ import annotations

from contextlib import contextmanager
import os
from pathlib import Path
import threading
import time

_LOCAL_LOCK = threading.RLock()
_HELD = threading.local()
LOCK_TIMEOUT_SECONDS = 120


@contextmanager
def installation_lock(home):
    """Hold installer exclusion; lock-file existence never implies ownership."""
    root = Path(home)
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
