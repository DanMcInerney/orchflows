"""Ticket store support."""

from __future__ import annotations
import json
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path
from datetime import datetime, timezone
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
if __package__:
    from .tickets_format import GIT_WORKSPACE_MECHANISMS, PACK_WORKSPACE_MECHANISMS, SCRIPT_EXECUTOR_PREFIX, _parse_frontmatter, _read_utf8
else:
    from tickets_format import GIT_WORKSPACE_MECHANISMS, PACK_WORKSPACE_MECHANISMS, SCRIPT_EXECUTOR_PREFIX, _parse_frontmatter, _read_utf8

UTC_STAMP = '%Y-%m-%dT%H:%M:%SZ'
RUN_IDENTITY_NAME = 'run.json'
RUN_LOCKS_DIR = 'locks'
SINK_CONVENTION = 2
NO_SINK_ERROR = 'cannot resolve the state sink: no $ORCHFLOWS_STATE_HOME and no home directory'
RUN_STATE_TREES = ('runs', 'research', 'improvement', 'handoffs')
DEFAULT_RUN_STATE_TREE = 'runs'
RUN_NOTES_NAME = 'notes.md'
WINDOWS_LOCK_RETRY_SECONDS = 0.05


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


def normalized_isolation(declared) -> str:
    """contracts/work-item.md's `isolation`, read one way by both scripts.

    Absent or empty reads `none`. Backticks are ordinary frontmatter
    punctuation here, stripped exactly as `_normalized_scope` and the
    executor check strip them, so the value this script emits an
    establishment step for is the value `scripts/workspace.py` grades.
    Normalizing it in two places is how an emitted step and a skipped
    grade can disagree behind a green suite.
    """
    return str(declared or 'none').strip().strip('`').strip() or 'none'
def _executor_script(executor: str):
    """The path a ``script:<path>`` executor names, or ``None``.

    One reader, so nothing else in this file has to know the prefix's
    spelling to tell a script node from a skill.
    """
    text = str(executor or '').strip().strip('`').strip()
    if not text.startswith(SCRIPT_EXECUTOR_PREFIX):
        return None
    return text[len(SCRIPT_EXECUTOR_PREFIX):].strip() or None
def establishes_a_git_workspace(pack) -> bool:
    """Whether `pack`'s workspace cell names a mechanism this script can
    establish a workspace in.

    A pack absent from the table answers yes. The table is only as current as
    its last sync, and the two mistakes are not equal: a child handed a step
    its mechanism has no meaning for fails at its first act, in the open,
    while a child not handed one it needed works in the shared tree and loses
    that work at the join with nothing to see.
    """
    name = str(pack or '').strip().strip('`').strip()
    if PACK_WORKSPACE_MECHANISMS is None:
        # The table is `None` in `tickets_format` until `scripts/tickets.py`
        # binds it, and this module took its copy by `from`-import at load, so
        # an importer that never touches the facade reaches here unbound. Not
        # degraded into the absent-pack fallback below: that answers yes for
        # every pack, which is the safe answer to a question the table could
        # not answer and the wrong answer to one nobody asked it.
        raise RuntimeError(
            'PACK_WORKSPACE_MECHANISMS is unbound: import scripts/tickets.py, '
            'which owns the table, before reaching establishes_a_git_workspace')
    mechanism = PACK_WORKSPACE_MECHANISMS.get(name)
    return mechanism is None or mechanism in GIT_WORKSPACE_MECHANISMS
_main_checkout_root = state_root.main_checkout_root
_find_repo_root = state_root.find_repo_root
def _cwd() -> Path:
    """The directory this invocation is standing in.

    Every question that starts from the caller's location asks here, so the
    location has one source rather than one per caller. Sink paths do not go
    through it at all — those are user-scope and the same from anywhere; what
    the caller's directory decides is only who is writing, and from which
    workspace of them.
    """
    return Path.cwd().resolve()
def _tickets_root():
    """The sink's ticket tree, or ``None`` when no root can be resolved."""
    try:
        return state_root.tickets_root()
    except Exception:
        return None
def _runs_root():
    """The sink's run tree, or ``None`` when no root can be resolved."""
    try:
        return state_root.runs_root()
    except Exception:
        return None
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
def _improvement_root():
    """The sink's improvement tree, or ``None`` when no root can be resolved."""
    try:
        return state_root.improvement_root()
    except Exception:
        return None
def _run_state_root(tree: str):
    """One of the sink's run-state trees, or ``None`` when unresolvable.

    ``--tree`` names the tree; the set is closed and checked by the
    caller, so anything reaching here is one of ``RUN_STATE_TREES``.
    """
    try:
        return state_root.state_root() / tree
    except Exception:
        return None
def _segment_error(kind: str, value: str):
    """Refuse, by name, anything that is not one path segment under the root."""
    if not value or not value.strip():
        return {'error': f'{kind} is empty'}
    if '/' in value or '\\' in value or '..' in value or (value == '.'):
        return {'error': f"unsafe {kind} '{value}': one path segment only, with no path separator and no '..'"}
    return None
def _iter_run_dirs(tickets_root: Path, run_filter):
    if tickets_root is None or not tickets_root.is_dir():
        return []
    if run_filter:
        candidate = tickets_root / run_filter
        return [candidate] if candidate.is_dir() else []
    return sorted((p for p in tickets_root.iterdir() if p.is_dir()))
def _origin_url(main_root: Path):
    """The ``origin`` remote's url, read out of ``<main_root>/.git/config``.

    Read, never asked for. This script shells out to nothing — that is what
    lets a child in a workspace it may not run ``git`` in reach the sink at
    all — so git's config is parsed here in the small, the way frontmatter
    is: the ``[remote "origin"]`` section, its ``url`` key, nothing else.
    Both spellings of the header are accepted because git accepts both.
    """
    try:
        text = (main_root / '.git' / 'config').read_text(encoding='utf-8', errors='replace')
    except OSError:
        return None
    in_origin = False
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped[0] in '#;':
            continue
        if stripped.startswith('[') and stripped.endswith(']'):
            inner = stripped[1:-1].replace('.', ' ')
            in_origin = [part.strip('"') for part in inner.split()] == ['remote', 'origin']
            continue
        if in_origin:
            key, separator, value = stripped.partition('=')
            if separator and key.strip().lower() == 'url':
                return value.strip() or None
    return None
def _normalized_origin(origin) -> str:
    """One remote, one spelling.

    A trailing ``/`` and a trailing ``.git`` are the two ways one transport
    writes one url, so both come off. Nothing tries to canonicalize ssh
    against https: guessing that two spellings mean one repository is how a
    run silently acquires a second project, which is what this exists to
    refuse. Empty for a repository with no remote.
    """
    text = str(origin or '').strip().rstrip('/')
    if text.endswith('.git'):
        text = text[:-len('.git')]
    return text.rstrip('/')
def _project_key(project: dict) -> str:
    """The name a project is refused by: its origin url, else its root."""
    return _normalized_origin(project.get('origin')) or str(project.get('root'))
def _same_project(recorded: dict, writing: dict) -> bool:
    """Whether two writes belong to one project.

    Origin first: two clones of one origin are one project with two
    workspaces, wherever on disk they sit. When either side has no origin
    there is nothing to compare but the main checkout root — so two
    repositories with no remote are two projects, and one repository that
    gained or lost its remote after the run opened is still itself rather
    than an impostor locked out of its own run.
    """
    theirs = _normalized_origin(recorded.get('origin'))
    mine = _normalized_origin(writing.get('origin'))
    if theirs and mine:
        return theirs == mine
    return str(recorded.get('root')) == str(writing.get('root'))
def _workspace_root(start: Path):
    """The checkout the caller is standing in, *not* dereferenced.

    ``state_root.find_repo_root`` owns the other half of a run's identity —
    which project — and follows a linked worktree's pointer to the main
    checkout to answer it. This one stops at the first ``.git`` instead of
    following it, because two worktrees of one project are exactly what
    ``workspaces[]`` distinguishes. The walk bound is the resolver's, never
    a second one.
    """
    current = Path(start).resolve()
    for _ in range(state_root.MAX_WALK_UP):
        if (current / '.git').exists():
            return current
        if current.parent == current:
            break
        current = current.parent
    return None
def _writer_identity():
    """``(project, workspace)`` for the caller: who is writing, from where."""
    cwd = _cwd()
    root = state_root.find_repo_root(cwd)
    workspace = _workspace_root(cwd) or cwd
    if root is None:
        return ({'root': str(cwd), 'origin': None, 'name': cwd.name}, str(workspace))
    return ({'root': str(root), 'origin': _origin_url(root), 'name': root.name}, str(workspace))
def _installed_orchflows_metadata() -> dict:
    """The installer receipt fields a new run freezes, explicitly nullable.

    The receipt is user-scope beside the state sink. It is an observation,
    never a repair target: missing, unreadable, non-object and legacy shapes
    all say that exact installed identity is unavailable, so no repository
    revision is guessed in its place.
    """
    missing = {'receipt_version': None, 'source_commit': None}
    try:
        receipt_path = state_root.state_root().parent / 'receipt.json'
        receipt = json.loads(receipt_path.read_text(encoding='utf-8'))
    except (OSError, UnicodeDecodeError, ValueError):
        return missing
    if not isinstance(receipt, dict):
        return missing
    version = receipt.get('version')
    if isinstance(version, bool) or not isinstance(version, int):
        version = None
    commit = receipt.get('source_commit')
    if not isinstance(commit, str) or not commit.strip():
        commit = None
    return {'receipt_version': version, 'source_commit': commit}
REPLACE_BUDGET_SECONDS = 2.0
REPLACE_RETRY_SECONDS = 0.005
def _waiting_out_windows(action):
    """Run ``action``, retrying only the refusal only Windows raises.

    ``PermissionError`` alone, never ``OSError``: a missing file and an
    unreachable directory are answers, and waiting two seconds for one of
    those on every run that has yet to open would cost the ordinary path
    to spare the rare one.
    """
    if __package__:
        from .tickets import _sync_seams
    else:
        from tickets import _sync_seams
    _sync_seams()
    deadline = time.monotonic() + REPLACE_BUDGET_SECONDS
    while True:
        try:
            return action()
        except PermissionError:
            if msvcrt is None or time.monotonic() >= deadline:
                raise
            time.sleep(REPLACE_RETRY_SECONDS)
def _read_identity(path: Path):
    """``(document, error)``: the run's identity, ``(None, None)`` when absent.

    A corrupt identity is refused rather than replaced. Overwriting it would
    attribute the run to whoever wrote last, which is the confusion the
    document exists to prevent.
    """
    try:
        text = _waiting_out_windows(lambda: path.read_text(encoding='utf-8'))
    except (FileNotFoundError, NotADirectoryError):
        return (None, None)
    except (OSError, UnicodeDecodeError) as error:
        return (None, {'error': f'unreadable run identity {path}: {error}'})
    try:
        data = json.loads(text)
    except ValueError as parse_error:
        reason = str(parse_error)
    else:
        if isinstance(data, dict):
            return (data, None)
        reason = 'the document is not an object'
    return (None, {'error': f"run identity {path} is unreadable ({reason}); repair or remove it. Refusing to overwrite a run's identity with a guess"})
def _identity_document(run: str, path: Path, project: dict, workspace: str, now, *, authoritative: bool = False):
    """``(document_to_write, error)`` — create, extend, correct, or refuse.

    ``opened_at`` is the first writer's and is never rewritten; a later
    workspace of the same project only appends itself. ``None`` for both
    means the identity is already correct and no write is owed, so an
    ordinary note does not rewrite this file every time.

    ``project`` is the first writer's *only* while nothing better is
    known. ``authoritative`` says it came from the run's root ticket
    instead, and then it corrects a disagreeing record rather than being
    refused by it: whoever wrote to the sink first does not thereby own
    which project a run belongs to, which is exactly how a run came to be
    attributed to the checkout a session happened to be standing in.
    """
    existing, error = _read_identity(path)
    if error is not None:
        return (None, error)
    stamp = now.strftime(UTC_STAMP)
    entry = {'path': workspace, 'first_seen': stamp}
    if existing is None:
        return ({'run': run, 'sink_convention': SINK_CONVENTION, 'opened_at': stamp, 'orchflows': _installed_orchflows_metadata(), 'project': project, 'workspaces': [entry]}, None)
    updated = dict(existing)
    recorded = existing.get('project')
    if isinstance(recorded, dict) and (recorded.get('root') or recorded.get('origin')):
        if not _same_project(recorded, project):
            if not authoritative:
                if __package__:
                    from .tickets_project import CREATE_REMEDY, held_by
                else:
                    from tickets_project import CREATE_REMEDY, held_by
                return (None, {'error': held_by(run, recorded, project, CREATE_REMEDY)})
            updated['project'] = project
    else:
        updated['project'] = project
        updated.setdefault('run', run)
        updated.setdefault('sink_convention', SINK_CONVENTION)
    seen = existing.get('workspaces')
    seen = list(seen) if isinstance(seen, list) else []
    if not any((isinstance(w, dict) and w.get('path') == workspace for w in seen)):
        seen.append(entry)
        updated['workspaces'] = seen
    elif not isinstance(existing.get('workspaces'), list):
        updated['workspaces'] = seen
    return (updated, None) if updated != existing else (None, None)
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
def _identity_update(run: str, now, runs_root=None):
    """Prepare this writer's one immutable run-identity update."""
    runs_root = _runs_root() if runs_root is None else runs_root
    if runs_root is None:
        return (None, None, {'error': NO_SINK_ERROR})
    run_dir = runs_root / run
    project, workspace = _writer_identity()
    # The run belongs to the project its root ticket's workspace names; the
    # caller's own directory decides only when the cut has named none. The
    # workspace entry stays the caller's either way -- `workspaces[]` answers
    # where a run has been written from, which is not the same question.
    if __package__:
        from .tickets_project import root_ticket_project
    else:
        from tickets_project import root_ticket_project
    named = root_ticket_project(run)
    document, refusal = _identity_document(run, run_dir / RUN_IDENTITY_NAME, named or project, workspace, now, authoritative=named is not None)
    return (run_dir, document, refusal)
def _terminal_identity_update(run: str, ticket_id: str, status: str, now):
    """Prepare the one timing write for a worklog-terminal transition.

    No identity means a legacy run whose real opening instant is unknown, so
    no terminal timing is fabricated. Any existing terminal field likewise
    means the transition has already been recorded (or belongs to a legacy
    partial shape) and is never rewritten or completed by guesswork.
    """
    runs_root = _runs_root()
    if runs_root is None:
        return (None, None, {'error': NO_SINK_ERROR})
    run_dir = runs_root / run
    existing, error = _read_identity(run_dir / RUN_IDENTITY_NAME)
    if error is not None:
        return (None, None, error)
    if existing is None:
        return (run_dir, None, None)
    timing_keys = ('terminal_at', 'terminal_ticket_id', 'terminal_status', 'elapsed_ms')
    if any((key in existing for key in timing_keys)):
        return (run_dir, None, None)
    opened = existing.get('opened_at')
    if not isinstance(opened, str):
        return (run_dir, None, None)
    try:
        opened_at = datetime.strptime(opened, UTC_STAMP).replace(tzinfo=timezone.utc)
    except ValueError:
        return (run_dir, None, None)
    terminal_stamp = now.strftime(UTC_STAMP)
    terminal_at = datetime.strptime(terminal_stamp, UTC_STAMP).replace(tzinfo=timezone.utc)
    updated = dict(existing)
    updated.update({'terminal_at': terminal_stamp, 'terminal_ticket_id': ticket_id, 'terminal_status': status, 'elapsed_ms': max(0, int((terminal_at - opened_at).total_seconds() * 1000))})
    return (run_dir, updated, None)
def _load_ticket(path: Path) -> dict:
    text, failure = _read_utf8(path)
    if failure is not None:
        return {'id': path.stem, 'path': str(path), 'error': failure['error']}
    try:
        data = _parse_frontmatter(text)
    except Exception:
        return {'id': path.stem, 'path': str(path), 'error': 'unparsable frontmatter'}
    ticket_id = data.get('id') or path.stem
    result = dict(data)
    result['id'] = ticket_id
    result['path'] = str(path)
    result['summary'] = {'run': data.get('run') or path.parent.name, 'id': ticket_id, 'status': data.get('status'), 'executor': data.get('executor'), 'depends_on': data.get('depends_on') or [], 'path': str(path)}
    if 'error' in result:
        result['summary']['error'] = result['error']
    return result
