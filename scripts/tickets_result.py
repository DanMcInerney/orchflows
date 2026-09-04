"""Ticket result support."""

from __future__ import annotations
import json
import os
import sys
from pathlib import Path
from datetime import datetime, timezone
try:
    import msvcrt
except ImportError:
    msvcrt = None
try:  # in-repo; the installed copy sits flat beside state_root.py
    from scripts import state_root
except ImportError:  # pragma: no cover - the installed copy's path
    import state_root
if __package__:
    from .tickets_format import REPORT_SECTION, TERMINAL_STATES, TicketFormatError, _extract_flag, _parse_frontmatter, _read_utf8, _section_body, _write_section, dequote, lease_of
else:
    from tickets_format import REPORT_SECTION, TERMINAL_STATES, TicketFormatError, _extract_flag, _parse_frontmatter, _read_utf8, _section_body, _write_section, dequote, lease_of
if __package__:
    from .tickets_store import DEFAULT_RUN_STATE_TREE, NO_SINK_ERROR, RUN_IDENTITY_NAME, RUN_NOTES_NAME, RUN_STATE_TREES, SINK_CONVENTION, UTC_STAMP, TicketWriteRefused, _identity_update, _lock_windows_byte, _run_lock, _run_state_root, _runs_root, _segment_error, _tickets_root, _waiting_out_windows, _write_identity, _write_text_atomically, _writer_identity, locked_run_write
else:
    from tickets_store import DEFAULT_RUN_STATE_TREE, NO_SINK_ERROR, RUN_IDENTITY_NAME, RUN_NOTES_NAME, RUN_STATE_TREES, SINK_CONVENTION, UTC_STAMP, TicketWriteRefused, _identity_update, _lock_windows_byte, _run_lock, _run_state_root, _runs_root, _segment_error, _tickets_root, _waiting_out_windows, _write_identity, _write_text_atomically, _writer_identity, locked_run_write
if __package__:
    from .tickets_project import recorded_project
else:
    from tickets_project import recorded_project
if __package__:
    from .tickets_attempts import PROTOCOL, _commit_record
    from .tickets_shapes import (
        DISPATCH_RESULT_PROJECTION_FIELDS, DISPATCH_RESULT_RECORD_FIELDS,
        DISPATCH_RESULT_SUCCESS_FIELDS,
    )
    from .tickets_transitions import CLAIMED
else:
    from tickets_attempts import PROTOCOL, _commit_record
    from tickets_shapes import (
        DISPATCH_RESULT_PROJECTION_FIELDS, DISPATCH_RESULT_RECORD_FIELDS,
        DISPATCH_RESULT_SUCCESS_FIELDS,
    )
    from tickets_transitions import CLAIMED

TERMINAL_HEADING = '## terminal'
RESULT_ATTRIBUTION_PREFIX = '### Written by '
RESULT_USAGE = f'result <run> <id> --assignment-seal <seal> --dispatch-id <id> --record-id <id> --by <writer> (--file <path> | --text <string>); every record is fenced to one dispatch-v1 attempt and appends to ## {REPORT_SECTION}'
RUN_STATE_USAGE = 'run-state <run> [--tree <name>] (--note <line> | (--artifact <name> [--replace] | --terminal <state>) (--file <path> | --text <string>))'
IMPROVEMENT_USAGE = 'improvement (--proposal <name> (--file <path> | --text <string>) | --covered <line>)'
PROPOSALS_DIR = 'proposals'
COVERAGE_RECORD_NAME = 'covered.jsonl'
# rules/visibility.md §6: the sink channel `frame-open`, `frame-close`,
# `land` and `stalled` append one line each to, sharded the same way
# `friction/<yyyy-mm>.jsonl` is.
EVENTS_SUBDIR = 'events'
_EVENT_SESSION_ENV_VARS = (
    'CLAUDE_SESSION_ID', 'CLAUDE_CODE_SESSION_ID', 'CODEX_SESSION_ID', 'SESSION_ID',
)


def _cmd_result(rest):
    return _result_under_run_lock(rest)


def _result_under_run_lock(rest):
    """Commit one attributed report record and its replay receipt together."""
    args = list(rest)
    assignment_seal = _extract_flag(args, '--assignment-seal')
    dispatch_id = _extract_flag(args, '--dispatch-id')
    record_id = _extract_flag(args, '--record-id')
    written_by = _extract_flag(args, '--by')
    file_arg = _extract_flag(args, '--file')
    text_arg = _extract_flag(args, '--text')
    stray = next((arg for arg in args if arg.startswith('-')), None)
    if stray is not None:
        return {'error': f'result does not accept {stray}: it writes body sections only, never frontmatter — commit the reserved outcome envelope, then let the caller land it. usage: {RESULT_USAGE}'}
    if len(args) != 2:
        return {'error': f'usage: {RESULT_USAGE}'}
    run, ticket_id = args
    for kind, value in (('run id', run), ('ticket id', ticket_id)):
        invalid = _segment_error(kind, value)
        if invalid is not None:
            return invalid
    if not all((assignment_seal, dispatch_id, record_id, (written_by or '').strip())):
        return {'error': f'result requires assignment seal, dispatch id, record id, and writer. usage: {RESULT_USAGE}'}
    written_by = written_by.strip()
    if any(mark in written_by for mark in ('`', '\r', '\n')):
        return {'error': 'result --by contains a character that cannot form one canonical writer attribution: backticks and line breaks are refused'}
    if file_arg is not None and text_arg is not None:
        return {'error': 'result takes one of --file <path> or --text <string>, not both'}
    if file_arg is None and text_arg is None:
        return {'error': f'result requires --file <path> or --text <string>. usage: {RESULT_USAGE}'}
    if file_arg is not None:
        body, failure = _read_utf8(file_arg, 'body file')
        if failure is not None:
            return failure
    else:
        body = text_arg
    if body is None:
        return {"error": f"result requires a readable body from --file <path> or --text <string>. usage: {RESULT_USAGE}"}
    # A level-2 heading in the body is the writer's, not a sibling section:
    # `tickets_markdown` indent-quotes it on the way in and takes the quote
    # off on the way out, so `## Findings` inside `## Report` is filed as
    # written and read back byte for byte.
    if any((line.startswith(RESULT_ATTRIBUTION_PREFIX) for line in body.splitlines())):
        return {'error': f"a result body may not contain the canonical writer attribution prefix '{RESULT_ATTRIBUTION_PREFIX}': tickets.py adds exactly one for this write"}
    tickets_root = _tickets_root()
    if tickets_root is None:
        return {'error': NO_SINK_ERROR}
    ticket_path = tickets_root / run / f'{ticket_id}.md'
    content = {
        'assignment_seal': assignment_seal, 'body': body,
        'operation': 'result', 'writer': written_by,
    }
    if set(content) != set(DISPATCH_RESULT_RECORD_FIELDS):
        return {"error": "result record shape is not the generated dispatch result shape"}

    def mutate(text, data, attempt, _state):
        recorded = (str(data.get('run') or '').strip(), str(data.get('id') or '').strip())
        if recorded != (run, ticket_id):
            return text, None, {'error': f'ticket identity does not match result target {run}/{ticket_id}: frontmatter records {recorded[0] or "<missing>"}/{recorded[1] or "<missing>"}'}
        status = dequote(data.get('status'))
        if status != CLAIMED:
            return text, None, {'error': f"result requires a claimed ticket and writes no lifecycle state; {run}/{ticket_id} is '{status or '<missing>'}'"}
        if lease_of(data)[0] != written_by:
            return text, None, {'code': 'identity-mismatch', 'error': 'result writer does not match the current ticket claimant', 'protocol': PROTOCOL}
        prior = _section_body(text, REPORT_SECTION)
        try:
            rendered = _write_section(
                text, REPORT_SECTION,
                f'{RESULT_ATTRIBUTION_PREFIX}`{written_by}`\n\n{body}',
                bool(prior),
            )
        except TicketFormatError as error:
            return text, None, {'error': f'{error}. ticket: {ticket_path}'}
        success = {'result': {
            'protocol': PROTOCOL, 'run': run, 'id': ticket_id,
            'path': str(ticket_path),
            'by': written_by, 'assignment_seal': assignment_seal,
            'dispatch_id': dispatch_id, 'record_id': record_id,
        }}
        if set(success) != set(DISPATCH_RESULT_SUCCESS_FIELDS) or set(success['result']) != set(DISPATCH_RESULT_PROJECTION_FIELDS):
            return text, None, {'error': 'result success shape is not the generated dispatch result shape'}
        return rendered, success, None

    return _commit_record(
        run, ticket_id, dispatch_id, record_id, content, mutate=mutate,
        expected_seal=assignment_seal, expected_owner=written_by,
        record_kind="result",
    )
def _is_terminal_heading(line: str) -> bool:
    """Whether one line closes a run's notes."""
    stripped = line.strip()
    if not stripped.lower().startswith(TERMINAL_HEADING):
        return False
    remainder = stripped[len(TERMINAL_HEADING):]
    return remainder == '' or remainder.startswith(':')
def _append_one_line(path: Path, block: str) -> None:
    """Append in one write, serialised where the platform does not do it."""
    with open(path, 'a', encoding='utf-8', newline='\n') as handle:
        if msvcrt is None:
            handle.write(block)
            return
        handle.seek(0)
        # `_lock_windows_byte`, not `LK_LOCK`: that mode stops retrying after
        # ten attempts and then raises, and eight appenders contending on one
        # runner outlast it. The run lock left this mode for the same reason.
        _lock_windows_byte(handle)
        try:
            handle.write(block)
            handle.flush()
        finally:
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
def _event_host() -> str:
    """Which host this process runs under, by the same env-var reading
    ``scripts/friction.py:_detect_host`` uses. Kept as its own small copy
    rather than an import: the two streams' provenance heads differ (no
    ``project_source``, ``workspace``, ``cwd`` or ``skill`` here), and the
    identity plumbing worth sharing -- project resolution -- already is,
    through ``tickets_project.recorded_project``."""
    env = os.environ
    if env.get('CLAUDECODE') or any(key.startswith('CLAUDE_') for key in env):
        return 'claude-code'
    if any(key.startswith('CODEX_') for key in env):
        return 'codex'
    return 'unknown'


def _event_session():
    for var in _EVENT_SESSION_ENV_VARS:
        value = os.environ.get(var)
        if value:
            return value
    return None


def _event_project(run: str) -> dict:
    """The project an event's ``run`` belongs to: recorded first, the
    caller's own checkout otherwise -- ``friction.py:_provenance``'s
    precedence, read through the tickets modules' own identity plumbing
    rather than a second copy of it."""
    return recorded_project(run) or _writer_identity()[0]


def _append_event(run: str, ticket_id: str, event: str, fields: dict) -> None:
    """Append one terminal machine event to ``<sink>/events/<yyyy-mm>.jsonl``."""
    try:
        now = datetime.now(timezone.utc)
        entry = {
            'sink_convention': SINK_CONVENTION,
            'ts': now.strftime(UTC_STAMP),
            'project': _event_project(run),
            'run': run,
            'ticket': ticket_id,
            'host': _event_host(),
            'session': _event_session(),
            'event': event,
        }
        entry.update(fields)
        path = state_root.state_root() / EVENTS_SUBDIR / f"{now.strftime('%Y-%m')}.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        _append_one_line(path, json.dumps(entry, ensure_ascii=False) + '\n')
    except Exception as error:  # the reliability bar above: never the transition
        print(f'events: not logged: {error}', file=sys.stderr)


def _notes_terminal(path: Path):
    """``(state, error)``: the state a run's notes closed with, ``None``
    while open, and the read failure when that could not be told."""
    try:
        text = _waiting_out_windows(lambda: path.read_text(encoding='utf-8'))
    except (FileNotFoundError, NotADirectoryError):
        return (None, None)
    except (OSError, UnicodeDecodeError) as error:
        return (None, {'error': f'unreadable run notes: {error}'})
    for line in text.splitlines():
        if _is_terminal_heading(line):
            return (line.strip()[len(TERMINAL_HEADING):].strip(' :'), None)
    return (None, None)
def _cmd_run_state(rest):
    tree = None
    if '--tree' in rest:
        index = list(rest).index('--tree')
        tree = rest[index + 1] if index + 1 < len(rest) else None
    # A named tree that is not one of the four is the body's refusal, not a
    # lock's: nothing is written, and the message names the closed set.
    if not rest or ('--tree' in rest and tree not in RUN_STATE_TREES):
        return _run_state_under_run_lock(rest)
    try:
        with locked_run_write(rest[0]):
            return _run_state_under_run_lock(rest)
    except TicketWriteRefused as refused:
        return refused.payload
    except OSError as error:
        return {'error': f'unwritable run state: {error}'}
def _run_state_under_run_lock(rest):
    """Write this run's state into the one user-scope state sink."""
    args = list(rest)
    note = _extract_flag(args, '--note')
    artifact = _extract_flag(args, '--artifact')
    terminal = _extract_flag(args, '--terminal')
    file_arg = _extract_flag(args, '--file')
    text_arg = _extract_flag(args, '--text')
    tree = _extract_flag(args, '--tree')
    replace = '--replace' in args
    while '--replace' in args:
        args.remove('--replace')
    stray = next((arg for arg in args if arg.startswith('-')), None)
    if stray is not None:
        return {'error': f'run-state does not accept {stray}. usage: {RUN_STATE_USAGE}'}
    if len(args) != 1:
        return {'error': f'usage: {RUN_STATE_USAGE}'}
    run = args[0]
    chosen = [name for name, value in (('--note', note), ('--artifact', artifact), ('--terminal', terminal)) if value is not None]
    if len(chosen) != 1:
        return {'error': f"run-state takes exactly one of --note <line>, --artifact <name> or --terminal <state>; got {chosen or 'none'}. usage: {RUN_STATE_USAGE}"}
    invalid = _segment_error('run id', run)
    if invalid is not None:
        return invalid
    if tree is None:
        tree = DEFAULT_RUN_STATE_TREE
    if tree not in RUN_STATE_TREES:
        return {'error': f"unknown run-state tree '{tree}': one of {list(RUN_STATE_TREES)}"}
    body = None
    if artifact is not None or terminal is not None:
        owner = '--artifact' if artifact is not None else '--terminal'
        if artifact is not None:
            invalid = _segment_error('artifact name', artifact)
            if invalid is not None:
                return invalid
        elif terminal not in TERMINAL_STATES:
            return {'error': f"unknown terminal state '{terminal}': one of {list(TERMINAL_STATES)}, the terminal set contracts/work-item.md owns"}
        if (file_arg is None) == (text_arg is None):
            carries = 'the deciding evidence' if terminal is not None else 'its body'
            return {'error': f'{owner} takes one of --file <path> or --text <string> for {carries}. usage: {RUN_STATE_USAGE}'}
        if file_arg is not None:
            body, failure = _read_utf8(file_arg, 'body file')
            if failure is not None:
                return failure
        else:
            body = text_arg
    elif file_arg is not None or text_arg is not None:
        return {'error': f'--note carries its own line; --file and --text belong to --artifact and --terminal. usage: {RUN_STATE_USAGE}'}
    elif _is_terminal_heading(note):
        return {'error': f"a note may not read as a terminal heading ('{TERMINAL_HEADING}'): close the run with --terminal <state> instead, one of {list(TERMINAL_STATES)}"}
    tree_root = _run_state_root(tree)
    runs_root = _runs_root()
    if tree_root is None or runs_root is None:
        return {'error': NO_SINK_ERROR}
    run_dir = tree_root / run
    identity_dir = runs_root / run
    if note is not None or terminal is not None:
        closed, failure = _notes_terminal(run_dir / RUN_NOTES_NAME)
        if failure is not None:
            return {'error': f"{failure['error']}; notes: {run_dir / RUN_NOTES_NAME}"}
        if closed is not None:
            attempt = 'a note' if note is not None else f"a '{terminal}' close"
            return {'error': f"these notes closed '{closed}': no note is written past a terminal section, and {attempt} would be. notes: {run_dir / RUN_NOTES_NAME}"}
    replaced = False
    if artifact is not None:
        target = run_dir / artifact
        if target.exists() and (not replace):
            return {'error': f'artifact already exists: {target}. Pass --replace to overwrite it deliberately, or write it under another name'}
        replaced = target.exists()
    identity_dir, document, refusal = _identity_update(run, datetime.now(timezone.utc), runs_root)
    if refusal is not None:
        return refusal
    identity_path = identity_dir / RUN_IDENTITY_NAME
    try:
        prior_identity = identity_path.read_bytes()
    except (FileNotFoundError, NotADirectoryError):
        prior_identity = None
    except OSError as error:
        return {'error': f'unreadable run identity {identity_path}: {error}'}
    identity_written = False
    try:
        run_dir.mkdir(parents=True, exist_ok=True)
        if document is not None:
            identity_dir.mkdir(parents=True, exist_ok=True)
            _write_identity(identity_dir, document)
            identity_written = True
        if artifact is not None:
            path = run_dir / artifact
            with open(path, 'w', encoding='utf-8', newline='\n') as handle:
                handle.write(body)
        else:
            path = run_dir / RUN_NOTES_NAME
            if note is not None:
                block = note.rstrip('\r\n') + '\n'
            else:
                evidence = body.replace('\r\n', '\n').replace('\r', '\n').strip('\n')
                block = f'\n{TERMINAL_HEADING}: {terminal}\n\n{evidence}\n'
            _append_one_line(path, block)
    except OSError as error:
        try:
            if identity_written:
                if prior_identity is None:
                    identity_path.unlink(missing_ok=True)
                else:
                    _write_text_atomically(identity_path, prior_identity.decode('utf-8'))
        except (OSError, UnicodeDecodeError) as rollback_error:
            return {'error': f'unwritable run state: {error}; identity rollback also failed: {rollback_error}'}
        return {'error': f'unwritable run state: {error}'}
    if artifact is not None:
        mode = 'artifact'
    elif terminal is not None:
        mode = 'terminal'
    else:
        mode = 'note'
    written = {'run': run, 'tree': tree, 'path': str(path), 'mode': mode}
    if artifact is not None:
        written['replaced'] = replaced
    if terminal is not None:
        written['terminal'] = terminal
    return {'run_state': written}
