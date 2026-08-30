"""Exclusive and atomic write mechanics for the ticket store.

One concern: how a write to the state sink is made exclusive against other
writers and indivisible to readers. The run lock and its Windows retry, the
replace-through-a-temporary primitives, and the exclusive create all answer
that one question, and the store facade above re-exports every name so no
caller has to learn where the mechanics moved.

Nothing here imports the store: this is the lower half of the split, so the
direction is store -> writes and never back.
"""

from __future__ import annotations
import json
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path
try:
    from scripts import state_root
except ImportError:
    import state_root
try:
    import msvcrt
except ImportError:
    msvcrt = None
try:
    import fcntl
except ImportError:
    fcntl = None

RUN_IDENTITY_NAME = 'run.json'
RUN_LOCKS_DIR = 'locks'
WINDOWS_LOCK_RETRY_SECONDS = 0.05
REPLACE_BUDGET_SECONDS = 2.0
REPLACE_RETRY_SECONDS = 0.005


def _lock_windows_byte(handle):
    """Wait for the run's byte lock without ``LK_LOCK``'s finite retry cap.

    ``msvcrt.LK_LOCK`` stops retrying after ten attempts, unlike the blocking
    ``flock`` used on POSIX.  Polling the non-blocking operation preserves the
    same wait-until-acquired contract on Windows while still surfacing errors
    that are not lock contention.
    """

    while True:
        try:
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            return
        except PermissionError:
            time.sleep(WINDOWS_LOCK_RETRY_SECONDS)


@contextmanager
def _run_lock(run: str):
    """Hold the one process lock protecting a physical run's mutations.

    Atomic replace protects readers from partial files, but it cannot make a
    read/check/write invariant atomic.  Every command that can move a run's
    tickets or identity therefore holds this lock from its first state read
    through its final write.  The lock lives outside the run payload trees so
    a refused command does not create a ticket, worklog, or run identity.
    """
    try:
        sink = state_root.state_root()
        lock_dir = sink / RUN_LOCKS_DIR
        lock_dir.mkdir(parents=True, exist_ok=True)
        path = lock_dir / (run + '.lock')
        handle = open(path, 'a+b')
    except OSError as error:
        raise OSError(f"unable to lock run '{run}': {error}") from error
    locked = False
    try:
        handle.seek(0, 2)
        if handle.tell() == 0:
            handle.write(b'\x00')
            handle.flush()
        handle.seek(0)
        if msvcrt is not None:
            _lock_windows_byte(handle)
        elif fcntl is not None:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        else:
            raise OSError('this host provides neither msvcrt nor fcntl locking')
        locked = True
        yield
    finally:
        try:
            if locked:
                handle.seek(0)
                if msvcrt is not None:
                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                elif fcntl is not None:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        finally:
            handle.close()


def _waiting_out_windows(action):
    """Run ``action``, retrying only the refusal only Windows raises.

    ``PermissionError`` alone, never ``OSError``: a missing file and an
    unreachable directory are answers, and waiting two seconds for one of
    those on every run that has yet to open would cost the ordinary path
    to spare the rare one.

    No facade import here, nor anywhere else in this family: a helper that
    reaches back up to ``tickets.py`` closes an import cycle to re-point
    whatever seam the facade held, and this one paid it per atomic write.
    """
    deadline = time.monotonic() + REPLACE_BUDGET_SECONDS
    while True:
        try:
            return action()
        except PermissionError:
            if msvcrt is None or time.monotonic() >= deadline:
                raise
            time.sleep(REPLACE_RETRY_SECONDS)


def _replace_atomically(temporary: Path, target: Path) -> None:
    """Move ``temporary`` onto ``target``, waiting out a transient refusal."""
    _waiting_out_windows(lambda: temporary.replace(target))


def _write_identity(run_dir: Path, document: dict) -> None:
    """Whole-file, and atomically.

    The run id partitions this document, but two workspaces of one project
    still open it at once, and a reader must never meet a half-written one.
    Written beside the target and moved over it, so the move is the only
    thing a concurrent reader can observe.
    """
    handle = tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', newline='\n', dir=str(run_dir), prefix=RUN_IDENTITY_NAME + '.', suffix='.tmp', delete=False)
    temporary = Path(handle.name)
    try:
        with handle:
            handle.write(json.dumps(document, ensure_ascii=False, indent=2) + '\n')
        _replace_atomically(temporary, run_dir / RUN_IDENTITY_NAME)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def _write_text_atomically(path: Path, text: str) -> None:
    """Replace one existing text artifact without exposing a partial file."""
    if not isinstance(path, Path):
        path.write_text(text, encoding='utf-8')
        return
    if path.exists():
        with open(path, 'r+', encoding='utf-8'):
            pass
    handle = tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', newline='\n', dir=str(path.parent), prefix=path.name + '.', suffix='.tmp', delete=False)
    temporary = Path(handle.name)
    try:
        with handle:
            handle.write(text)
        _replace_atomically(temporary, path)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def _create_text_exclusively(path: Path, text: str) -> None:
    """Create one immutable identity, losing rather than replacing a race."""
    with open(path, 'x', encoding='utf-8', newline='\n') as handle:
        handle.write(text)


__all__ = (
    'REPLACE_BUDGET_SECONDS', 'REPLACE_RETRY_SECONDS', 'RUN_IDENTITY_NAME',
    'RUN_LOCKS_DIR', 'WINDOWS_LOCK_RETRY_SECONDS', '_create_text_exclusively',
    '_lock_windows_byte', '_replace_atomically', '_run_lock',
    '_waiting_out_windows', '_write_identity', '_write_text_atomically',
)
