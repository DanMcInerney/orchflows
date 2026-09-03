"""Ticket store support."""

from __future__ import annotations
import json
from contextlib import contextmanager
from pathlib import Path
from datetime import datetime, timezone
try:
    from scripts import state_root
except ImportError:
    import state_root
if __package__:
    from .orchflows_home import RECEIPT_FILENAME
    from .tickets_format import SCRIPT_EXECUTOR_PREFIX, _parse_frontmatter, _read_utf8, dequote
    from .tickets_store_writes import (
        REPLACE_BUDGET_SECONDS, REPLACE_RETRY_SECONDS, RUN_IDENTITY_NAME,
        RUN_LOCKS_DIR, WINDOWS_LOCK_RETRY_SECONDS, _create_text_exclusively,
        _lock_windows_byte, _replace_atomically, _run_lock,
        _waiting_out_windows, _write_identity, _write_text_atomically,
    )
else:
    from orchflows_home import RECEIPT_FILENAME
    from tickets_format import SCRIPT_EXECUTOR_PREFIX, _parse_frontmatter, _read_utf8, dequote
    from tickets_store_writes import (
        REPLACE_BUDGET_SECONDS, REPLACE_RETRY_SECONDS, RUN_IDENTITY_NAME,
        RUN_LOCKS_DIR, WINDOWS_LOCK_RETRY_SECONDS, _create_text_exclusively,
        _lock_windows_byte, _replace_atomically, _run_lock,
        _waiting_out_windows, _write_identity, _write_text_atomically,
    )

UTC_STAMP = '%Y-%m-%dT%H:%M:%SZ'
SINK_CONVENTION = 2
NO_SINK_ERROR = f'cannot resolve the state sink: no ${state_root.ENV_VAR} and no home directory'
RUN_STATE_TREES = ('runs', 'research', 'improvement', 'handoffs')
DEFAULT_RUN_STATE_TREE = 'runs'
RUN_NOTES_NAME = 'notes.md'


def normalized_isolation(declared) -> str:
    """contracts/work-item.md's `isolation`, read one way by both scripts."""
    return dequote(declared) or 'none'
def _executor_script(executor: str):
    """The path a ``script:<path>`` executor names, or ``None``."""
    text = dequote(executor)
    if not text.startswith(SCRIPT_EXECUTOR_PREFIX):
        return None
    return text[len(SCRIPT_EXECUTOR_PREFIX):].strip() or None
_main_checkout_root = state_root.main_checkout_root
_find_repo_root = state_root.find_repo_root
def _cwd() -> Path:
    """The directory this invocation is standing in."""
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
def _improvement_root():
    """The sink's improvement tree, or ``None`` when no root can be resolved."""
    try:
        return state_root.improvement_root()
    except Exception:
        return None
def _run_state_root(tree: str):
    """One of the sink's run-state trees, or ``None`` when unresolvable."""
    try:
        return state_root.state_root() / tree
    except Exception:
        return None
def _segment_error(kind: str, value: str):
    """Refuse, by name, anything that is not one path segment under the root."""
    defect = state_root.segment_defect(kind, value)
    return None if defect is None else {'error': defect}
class TicketWriteRefused(Exception):
    """A structured refusal raised before any lock is opened or byte written."""

    def __init__(self, payload: dict):
        super().__init__(str(payload.get('error') or ''))
        self.payload = payload
def segment_refusal(run: str, ticket_id: str):
    """Refuse either half of a ticket's identity that is not one segment."""
    for kind, value in (('run id', run), ('ticket id', ticket_id)):
        invalid = _segment_error(kind, value)
        if invalid is not None:
            return invalid
    return None
@contextmanager
def locked_ticket_write(run: str, ticket_id: str):
    """Refuse, lock, then yield the one path a mutating command may write."""
    refusal = segment_refusal(run, ticket_id)
    if refusal is not None:
        raise TicketWriteRefused(refusal)
    with _run_lock(run):
        tickets_root = _tickets_root()
        if tickets_root is None:
            raise TicketWriteRefused({'error': NO_SINK_ERROR})
        yield tickets_root / run / f'{ticket_id}.md'
@contextmanager
def locked_run_write(run: str):
    """`locked_ticket_write` for a command whose subject is the run itself."""
    refusal = _segment_error('run id', run)
    if refusal is not None:
        raise TicketWriteRefused(refusal)
    with _run_lock(run):
        yield
def _iter_run_dirs(tickets_root: Path, run_filter):
    if tickets_root is None or not tickets_root.is_dir():
        return []
    if run_filter:
        candidate = tickets_root / run_filter
        return [candidate] if candidate.is_dir() else []
    return sorted((p for p in tickets_root.iterdir() if p.is_dir()))
def _origin_url(main_root: Path):
    """The ``origin`` remote's url, read out of ``<main_root>/.git/config``."""
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
    """One remote, one spelling."""
    text = str(origin or '').strip().rstrip('/')
    if text.endswith('.git'):
        text = text[:-len('.git')]
    return text.rstrip('/')
def _project_key(project: dict) -> str:
    """The name a project is refused by: its origin url, else its root."""
    return _normalized_origin(project.get('origin')) or str(project.get('root'))
def _same_project(recorded: dict, writing: dict) -> bool:
    """Whether two writes belong to one project."""
    theirs = _normalized_origin(recorded.get('origin'))
    mine = _normalized_origin(writing.get('origin'))
    if theirs and mine:
        return theirs == mine
    return str(recorded.get('root')) == str(writing.get('root'))
def _workspace_root(start: Path):
    """The checkout the caller is standing in, *not* dereferenced."""
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
    """The installer receipt fields a new run freezes, explicitly nullable."""
    missing = {'receipt_version': None, 'source_commit': None}
    try:
        receipt_path = state_root.state_root().parent / RECEIPT_FILENAME
        receipt = json.loads(receipt_path.read_text(encoding='utf-8-sig'))
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
def _read_identity(path: Path):
    """``(document, error)``: the run's identity, ``(None, None)`` when absent."""
    try:
        text = _waiting_out_windows(lambda: path.read_text(encoding='utf-8-sig'))
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
    return (None, {'error': f"run identity {path} is unreadable ({reason}). Refusing to overwrite a run's identity with a guess: run `tickets.py repair-run-identity {path.parent.name}` to quarantine it and rebuild the minimal identity from this run's ticket evidence"})
def _identity_document(run: str, path: Path, project: dict, workspace: str, now, *, authoritative: bool = False):
    """``(document_to_write, error)`` — create, extend, correct, or refuse."""
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
    # where a run has been written from.
    if __package__:
        from .tickets_project import root_ticket_project
    else:
        from tickets_project import root_ticket_project
    named = root_ticket_project(run)
    document, refusal = _identity_document(run, run_dir / RUN_IDENTITY_NAME, named or project, workspace, now, authoritative=named is not None)
    return (run_dir, document, refusal)
def _terminal_identity_update(run: str, ticket_id: str, status: str, now):
    """Prepare the one timing write for a worklog-terminal transition."""
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
INTEGRATION_KEY = 'integration'


def integration_target(run: str):
    """``{'root', 'branch', 'first_seen'}`` this run integrates into, or ``None``."""

    runs_root = _runs_root()
    if runs_root is None:
        return None
    existing, error = _read_identity(runs_root / run / RUN_IDENTITY_NAME)
    if error is not None or not isinstance(existing, dict):
        return None
    recorded = existing.get(INTEGRATION_KEY)
    if not isinstance(recorded, dict):
        return None
    root, branch = recorded.get('root'), recorded.get('branch')
    if not isinstance(root, str) or not root.strip():
        return None
    if not isinstance(branch, str) or not branch.strip():
        return None
    return {'root': root, 'branch': branch, 'first_seen': recorded.get('first_seen')}


def record_integration_target(run: str, root: str, branch: str, now=None):
    """Write where this run's work belongs, once. Later callers only read."""

    runs_root = _runs_root()
    if runs_root is None:
        return None
    run_dir = runs_root / run
    existing, error = _read_identity(run_dir / RUN_IDENTITY_NAME)
    if error is not None:
        return None
    recorded = integration_target(run)
    if recorded is not None:
        return recorded
    now = datetime.now(timezone.utc) if now is None else now
    target = {'root': str(root), 'branch': str(branch),
              'first_seen': now.strftime(UTC_STAMP)}
    document = dict(existing or {})
    document.setdefault('run', run)
    document.setdefault('sink_convention', SINK_CONVENTION)
    document[INTEGRATION_KEY] = target
    try:
        run_dir.mkdir(parents=True, exist_ok=True)
        _write_identity(run_dir, document)
    except OSError:
        return None
    return target


REPAIR_RUN_IDENTITY_USAGE = 'repair-run-identity <run>'
CORRUPT_IDENTITY_MARKER = '.corrupt-'
QUARANTINE_STAMP = '%Y%m%dT%H%M%SZ'
def _quarantine_path(path: Path, now) -> Path:
    """A free name beside the identity for the document being set aside."""
    base = path.name + CORRUPT_IDENTITY_MARKER + now.strftime(QUARANTINE_STAMP)
    candidate = path.with_name(base)
    ordinal = 1
    while candidate.exists():
        candidate = path.with_name(f'{base}-{ordinal}')
        ordinal += 1
    return candidate
def _cmd_repair_run_identity(rest):
    """Set an unreadable ``run.json`` aside and rebuild the minimal identity."""
    if len(rest) != 1:
        return {'error': f'usage: {REPAIR_RUN_IDENTITY_USAGE}'}
    run = rest[0]
    runs_root = _runs_root()
    tickets_root = _tickets_root()
    if runs_root is None or tickets_root is None:
        return {'error': NO_SINK_ERROR}
    try:
        with locked_run_write(run):
            identity_dir = runs_root / run
            identity_path = identity_dir / RUN_IDENTITY_NAME
            existing, failure = _read_identity(identity_path)
            if failure is None and existing is not None:
                return {'repair_run_identity': {'run': run, 'outcome': 'intact', 'path': str(identity_path), 'quarantined': None}}
            run_dir = tickets_root / run
            tickets = sorted(run_dir.glob('*.md')) if run_dir.is_dir() else []
            if not tickets:
                return {'error': f"run '{run}' has no ticket evidence at {run_dir}: an identity is rebuilt from the run's own tickets and this run has none. Nothing was written"}
            now = datetime.now(timezone.utc)
            quarantined = None
            if identity_path.exists():
                quarantined = _quarantine_path(identity_path, now)
                identity_path.rename(quarantined)
            opened = min(path.stat().st_mtime for path in tickets)
            project, workspace = _writer_identity()
            document = {
                'run': run, 'sink_convention': SINK_CONVENTION,
                'opened_at': datetime.fromtimestamp(opened, timezone.utc).strftime(UTC_STAMP),
                'orchflows': _installed_orchflows_metadata(), 'project': project,
                'workspaces': [{'path': workspace, 'first_seen': now.strftime(UTC_STAMP)}],
            }
            identity_dir.mkdir(parents=True, exist_ok=True)
            _write_identity(identity_dir, document)
    except TicketWriteRefused as refused:
        return refused.payload
    except OSError as error:
        return {'error': f'unable to repair run identity: {error}'}
    return {'repair_run_identity': {'run': run, 'outcome': 'rebuilt', 'path': str(identity_path), 'quarantined': None if quarantined is None else str(quarantined), 'tickets': [path.stem for path in tickets]}}
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
