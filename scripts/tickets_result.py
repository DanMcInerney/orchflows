"""Ticket result support."""

from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone
try:
    import msvcrt
except ImportError:
    msvcrt = None
if __package__:
    from .tickets_format import EXECUTOR_SECTIONS, EXECUTOR_SECTIONS_BY_KEY, TERMINAL_STATES, TicketFormatError, _extract_flag, _parse_frontmatter, _read_utf8, _section_body, _sections, _write_section
else:
    from tickets_format import EXECUTOR_SECTIONS, EXECUTOR_SECTIONS_BY_KEY, TERMINAL_STATES, TicketFormatError, _extract_flag, _parse_frontmatter, _read_utf8, _section_body, _sections, _write_section
if __package__:
    from .tickets_store import DEFAULT_RUN_STATE_TREE, NO_SINK_ERROR, RUN_IDENTITY_NAME, RUN_NOTES_NAME, RUN_STATE_TREES, _identity_update, _lock_windows_byte, _run_lock, _run_state_root, _runs_root, _segment_error, _tickets_root, _waiting_out_windows, _write_identity, _write_text_atomically
else:
    from tickets_store import DEFAULT_RUN_STATE_TREE, NO_SINK_ERROR, RUN_IDENTITY_NAME, RUN_NOTES_NAME, RUN_STATE_TREES, _identity_update, _lock_windows_byte, _run_lock, _run_state_root, _runs_root, _segment_error, _tickets_root, _waiting_out_windows, _write_identity, _write_text_atomically
if __package__:
    from .tickets_markdown import SECTION_SENTINEL
    from .tickets_attempts import PROTOCOL, _commit_record
else:
    from tickets_markdown import SECTION_SENTINEL
    from tickets_attempts import PROTOCOL, _commit_record

TERMINAL_HEADING = '## terminal'
RESULT_ATTRIBUTION_PREFIX = '### Written by '
RESULT_USAGE = f'result <run> <id> --assignment-seal <seal> --dispatch-id <id> --record-id <id> --by <writer> --section <name> (--file <path> | --text <string>) [--append | --replace]; every record is fenced to one dispatch-v1 attempt, and an executor-owned section is append-only except over the cut sentinel {SECTION_SENTINEL}'
RUN_STATE_USAGE = 'run-state <run> [--tree <name>] (--note <line> | (--artifact <name> [--replace] | --terminal <state>) (--file <path> | --text <string>))'
IMPROVEMENT_USAGE = 'improvement (--proposal <name> (--file <path> | --text <string>) | --covered <line>)'
PROPOSALS_DIR = 'proposals'
COVERAGE_RECORD_NAME = 'covered.jsonl'

def _cmd_result(rest):
    return _result_under_run_lock(rest)


def _result_under_run_lock(rest):
    """Commit one attributed section record and its replay receipt together."""
    args = list(rest)
    assignment_seal = _extract_flag(args, '--assignment-seal')
    dispatch_id = _extract_flag(args, '--dispatch-id')
    record_id = _extract_flag(args, '--record-id')
    written_by = _extract_flag(args, '--by')
    section = _extract_flag(args, '--section')
    file_arg = _extract_flag(args, '--file')
    text_arg = _extract_flag(args, '--text')
    append = '--append' in args
    while '--append' in args:
        args.remove('--append')
    replace = '--replace' in args
    while '--replace' in args:
        args.remove('--replace')
    if append and replace:
        return {'error': f'result takes one of --append or --replace, not both: they are the two ways to write a section that already carries content. usage: {RESULT_USAGE}'}
    stray = next((arg for arg in args if arg.startswith('-')), None)
    if stray is not None:
        return {'error': f'result does not accept {stray}: it writes body sections only, never frontmatter — terminal status is set by the join (orch-integrate) through `set-status`. usage: {RESULT_USAGE}'}
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
    if section is None:
        return {'error': f'result requires --section <name>, one of {list(EXECUTOR_SECTIONS)}'}
    canonical = EXECUTOR_SECTIONS_BY_KEY.get(section.strip().strip('#').strip().lower())
    if canonical is None:
        return {'error': f"section '{section}' is not one of the sections an executor writes: {list(EXECUTOR_SECTIONS)}"}
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
    if any((line.startswith('## ') for line in body.splitlines())):
        return {'error': f"a '## {canonical}' body may not contain a level-2 heading ('## ...'): it would be read as a sibling ticket section. Use '###' or deeper for sub-headings inside a section"}
    if any((line.startswith(RESULT_ATTRIBUTION_PREFIX) for line in body.splitlines())):
        return {'error': f"a result body may not contain the canonical writer attribution prefix '{RESULT_ATTRIBUTION_PREFIX}': tickets.py adds exactly one for this write"}
    tickets_root = _tickets_root()
    if tickets_root is None:
        return {'error': NO_SINK_ERROR}
    ticket_path = tickets_root / run / f'{ticket_id}.md'
    request_mode = 'append' if append else ('replace' if replace else 'write')
    content = {
        'assignment_seal': assignment_seal, 'body': body, 'mode': request_mode,
        'operation': 'result', 'section': canonical, 'writer': written_by,
    }

    def mutate(text, data, attempt, _state):
        recorded = (str(data.get('run') or '').strip(), str(data.get('id') or '').strip())
        if recorded != (run, ticket_id):
            return text, None, {'error': f'ticket identity does not match result target {run}/{ticket_id}: frontmatter records {recorded[0] or "<missing>"}/{recorded[1] or "<missing>"}'}
        status = str(data.get('status') or '').strip().strip('`')
        if status != 'claimed':
            return text, None, {'error': f"result requires a claimed ticket and writes no lifecycle state; {run}/{ticket_id} is '{status or '<missing>'}'"}
        if str(data.get('claimed_by') or '').strip() != written_by:
            return text, None, {'code': 'identity-mismatch', 'error': 'result writer does not match the current ticket claimant', 'protocol': PROTOCOL}
        prior = _section_body(text, canonical)
        sentinel = prior == SECTION_SENTINEL
        effective_append = append and not sentinel
        if replace and not sentinel:
            return text, None, {'error': f"executor-owned section '## {canonical}' is append-only except over the cut sentinel {SECTION_SENTINEL}; pass --append. ticket: {ticket_path}"}
        if prior and not sentinel and not append and not replace:
            return text, None, {'error': f"'## {canonical}' already carries content: refusing to overwrite it silently. Pass --append to add after it. ticket: {ticket_path}"}
        try:
            rendered = _write_section(
                text, canonical,
                f'{RESULT_ATTRIBUTION_PREFIX}`{written_by}`\n\n{body}',
                effective_append,
            )
        except TicketFormatError as error:
            return text, None, {'error': f'{error}. ticket: {ticket_path}'}
        mode = 'write' if sentinel else request_mode
        success = {'result': {
            'protocol': PROTOCOL, 'run': run, 'id': ticket_id,
            'path': str(ticket_path), 'section': canonical, 'mode': mode,
            'by': written_by, 'assignment_seal': assignment_seal,
            'dispatch_id': dispatch_id, 'record_id': record_id,
        }}
        return rendered, success, None

    return _commit_record(
        run, ticket_id, dispatch_id, record_id, content, mutate=mutate,
        expected_seal=assignment_seal, expected_owner=written_by,
    )
def _is_terminal_heading(line: str) -> bool:
    """Whether one line closes a run's notes.

    Case-insensitive, and the prefix must end the word: ``## terminal`` and
    ``## terminal: complete`` close, ``## terminals`` is an ordinary
    heading. A note that would read as one is refused rather than written,
    so nothing but ``--terminal`` can ever put this marker in the file.
    """
    stripped = line.strip()
    if not stripped.lower().startswith(TERMINAL_HEADING):
        return False
    remainder = stripped[len(TERMINAL_HEADING):]
    return remainder == '' or remainder.startswith(':')
def _append_one_line(path: Path, block: str) -> None:
    """Append in one write, serialised where the platform does not do it.

    POSIX ``O_APPEND`` places a write at end-of-file atomically, so append mode
    alone is the whole guarantee there. The Windows CRT emulates append with a
    seek and then a write, and those are two steps: two writers take the same
    offset and one whole line disappears -- seen here as seven notes of eight
    surviving, every survivor intact, on a job that had passed the run before.
    A torn line would have been obvious; a missing one reads like a writer that
    never ran.

    So Windows locks and POSIX does not, and byte zero is the mutex: every
    appender contends on the same byte. Every ``msvcrt`` mode is a mandatory
    range lock, not an advisory one, so an append blocks another append and
    any reader that touches byte zero -- which on this file is every reader,
    since they all read from the start. A reader refused here retries; it has
    not found the file unreadable. Nothing here read-modify-writes. The lock
    serialises the seek the platform hides inside ``write``.
    """
    with open(path, 'a', encoding='utf-8', newline='\n') as handle:
        if msvcrt is None:
            handle.write(block)
            return
        handle.seek(0)
        # `_lock_windows_byte`, not `LK_LOCK`: that mode stops retrying after
        # ten attempts and then raises, and eight appenders contending on one
        # runner outlast it -- a note refused as `unwritable run state:
        # [Errno 13] Permission denied` on a job that had passed the run
        # before. The run lock left this mode for the same reason; this was
        # the last site still on it.
        _lock_windows_byte(handle)
        try:
            handle.write(block)
            handle.flush()
        finally:
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
def _notes_terminal(path: Path):
    """``(state, error)``: the state a run's notes closed with, ``None``
    while open, and the read failure when that could not be told.

    A read, never a read-modify-write: the note that follows is still one
    append in one call, so a line another workspace added in between
    survives untouched. Missing is open -- the first note creates the file.
    Refused is not: ``_append_one_line``'s byte-zero lock is mandatory, so a
    concurrent appender refuses this read on Windows, and reading that
    refusal as "open" was how a note landed past a terminal section (F F4).
    The refusal is waited out like ``_read_identity``'s and, if it stays,
    returned as the error it is.
    """
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
    if not rest or _segment_error('run id', rest[0]) is not None or ('--tree' in rest and tree not in RUN_STATE_TREES):
        return _run_state_under_run_lock(rest)
    try:
        with _run_lock(rest[0]):
            return _run_state_under_run_lock(rest)
    except OSError as error:
        return {'error': f'unwritable run state: {error}'}
def _run_state_under_run_lock(rest):
    """Write this run's state into the one user-scope state sink.

    The channel rules/visibility.md §6 names. The root is resolved the way
    every other subcommand resolves it — ``scripts/state_root.py``, an
    environment variable and a home directory, no subprocess — so a child in
    its own workspace, in any repository or none, reaches the run's state
    without a git call it may not be allowed to make.

    ``--note`` appends to one shared log, so it opens in append mode with an
    explicit ``newline`` (``scripts/friction.py``) and writes one line in one
    call through ``_append_one_line``, which serialises that call on the
    platform where append is not itself atomic: two workspaces write one
    run's notes concurrently and neither may read-modify-write them.
    ``--artifact`` is whole-file, which is safe only because the run id
    partitions it.

    One sink holds every project's runs, so a run says which project it is:
    the first write stamps ``run.json`` beside the notes, a later write
    from another workspace of the same project appends itself to it, and a
    write from a *different* project is refused by name. Without that, two
    projects that pick one run id interleave into one log and neither can
    tell which line is whose.

    There is no fallback. A write that cannot reach that root is reported as
    an error and lands nowhere else: a run-state write that silently
    succeeds in the caller's own tree is the loss this channel exists to end.
    """
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
