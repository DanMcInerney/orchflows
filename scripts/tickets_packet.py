"""Ticket packet support."""

from __future__ import annotations
import re
import shlex
import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone
try:
    from scripts import state_root
except ImportError:
    import state_root
if __package__:
    from .tickets_format import CHECKED_BY_KEY, DISPATCHING_EXECUTORS, EXECUTOR_SECTIONS, GATE_EXECUTORS, LOOP_EXECUTOR, PROVENANCE_RE, REQUIRED_ISOLATION, RESULT_TOKEN_SPLIT_RE, RESULT_TOKEN_STRIP, ROOT_EXECUTOR, _criteria, _executor_of, _extract_flag, _parse_bound_minutes, _parse_iso, _read_utf8, _scope_entries, _sections, criterion_defects, effective_write_scope
else:
    from tickets_format import CHECKED_BY_KEY, DISPATCHING_EXECUTORS, EXECUTOR_SECTIONS, GATE_EXECUTORS, LOOP_EXECUTOR, PROVENANCE_RE, REQUIRED_ISOLATION, RESULT_TOKEN_SPLIT_RE, RESULT_TOKEN_STRIP, ROOT_EXECUTOR, _criteria, _executor_of, _extract_flag, _parse_bound_minutes, _parse_iso, _read_utf8, _scope_entries, _sections, criterion_defects, effective_write_scope
if __package__:
    from .tickets_issue import AMENDABLE_STATUSES
else:
    from tickets_issue import AMENDABLE_STATUSES
if __package__:
    from .tickets_store import NO_SINK_ERROR, _executor_script, _load_ticket, _run_lock, _segment_error, _tickets_root, establishes_a_git_workspace, normalized_isolation
else:
    from tickets_store import NO_SINK_ERROR, _executor_script, _load_ticket, _run_lock, _segment_error, _tickets_root, establishes_a_git_workspace, normalized_isolation
if __package__:
    from .tickets_worklog import _run_tickets
else:
    from tickets_worklog import _run_tickets
if __package__:
    from .tickets_admission import is_v1, is_v2
    from .tickets_context import graded_admission, run_snapshot
else:
    from tickets_admission import is_v1, is_v2
    from tickets_context import graded_admission, run_snapshot

PACKET_SECTIONS = (('objective', 'Objective'), ('inputs', 'Fixed inputs'), ('return_contract', 'Return fields'))
CHECKER_EXECUTOR = 'orch-critique'
REVERIFIER_EXECUTOR = 'orch-verify'
CHECKER_PATH_EXECUTORS = (CHECKER_EXECUTOR, REVERIFIER_EXECUTOR)
# Below the constant it names, and interpolating it rather than spelling it:
# this one sentence is what the error path prints and what `tickets.py help`
# publishes, and the two were hand-built copies that drifted by one flag.
PACKET_USAGE = f"packet <run> <id> --reply-to <name> [--by <name>] [--workspace <path>] [--executor {' | '.join(CHECKER_PATH_EXECUTORS)}]"
CHECKABLE_STATUSES = frozenset({'claimed', 'suspended'})
CHECKER_INDEPENDENCE = 'checker'
PRE_EXISTING_PROVENANCE = 'pre-existing'
CHECKER_NOT_REQUIRED = 'checker not required: every criterion carries provenance: pre-existing'
_SHELL_SAFE_TOKEN = re.compile(r'^[A-Za-z0-9_./:\\=-]+$')


def _command_text(*arguments) -> str:
    """Render argv as one executable command for the host's native shell."""

    values = [str(argument) for argument in arguments]
    if all(_SHELL_SAFE_TOKEN.fullmatch(value) for value in values):
        return ' '.join(values)
    if sys.platform == 'win32':
        def quote(value: str) -> str:
            return "'" + value.replace("'", "''") + "'"

        return '& ' + ' '.join(quote(value) for value in values)
    return shlex.join(values)
CUT_LENS_PARTS = ('skills', 'kernel', 'orch-decompose', 'references', 'cut-lens.md')
SOURCE_SIZE_PARTS = ('tools', 'check_source_sizes.py')


def _source_size_checker():
    """The source-ceiling measurer as this host holds it, or ``None``.

    ``_cut_lens_path``'s question with the opposite answer where it does
    not resolve. That one falls back to the repo-relative name, because a
    lens is a thing to go and find; this is a line the child is told to
    run, and a command naming a program that is not on the host is exactly
    the hand-composed-and-refused shape this item exists to remove. So an
    unresolved measurer emits no line at all -- ``tools/`` ships with the
    checkout and not with the installed ``bin/``, and a packet emitted from
    an install states no measurement rather than an unrunnable one.
    """
    measurer = Path(__file__).resolve().parent.parent.joinpath(*SOURCE_SIZE_PARTS)
    return str(measurer) if measurer.is_file() else None
GATE_CRITIQUE_ID = '{root}.gate.critique.{lens}'
GATE_REPAIR_ID = '{root}.gate.repair'
GATE_VERIFY_ID = '{root}.gate.verify'
GATE_EXECUTOR_SECTIONS = [('Result', ''), ('Verification', ''), ('Feedback', '[]'), ('Risks', '[]')]


def _cited_paths(section_text: str, write_scope=()):
    """Absolute existing Result citations inside the ticket's write scope."""
    scope = [_scope_segments(entry) for entry in _scope_entries(write_scope)]
    scope = [entry for entry in scope if entry]
    found, unreadable = [], []
    for token in RESULT_TOKEN_SPLIT_RE.split(section_text or ''):
        candidate = token.strip(RESULT_TOKEN_STRIP)
        if not candidate or ('/' not in candidate and '\\' not in candidate and '.' not in candidate[1:]):
            continue
        try:
            path = Path(candidate)
            if not path.is_absolute() or not path.is_file():
                continue
            if scope and not any(_inside_scope(path, entry) for entry in scope):
                continue
            found.append(path)
        except (OSError, ValueError) as error:
            unreadable.append(f'could not look at the cited {candidate}: {error}')
    return (found, unreadable)


def _scope_segments(entry) -> list:
    text = str(entry or '').strip().strip('`').strip()
    return [part for part in text.replace('\\', '/').split('/') if part and part != '.']


def _inside_scope(path: Path, segments: list) -> bool:
    parts = [part for part in str(path).replace('\\', '/').split('/') if part]
    width = len(segments)
    return any(parts[start:start + width] == segments for start in range(len(parts) - width + 1))


def _last_motion(ticket_path: Path, result_text: str, write_scope=()):
    latest = None
    cited, unreadable = _cited_paths(result_text, write_scope)
    for path in [ticket_path, *cited]:
        try:
            moment = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)
        except OSError as error:
            unreadable.append(f'could not stat {path}: {error}')
            continue
        if latest is None or moment > latest:
            latest = moment
    return (latest, unreadable)


def _is_stale(claimed_at, bound_minutes: int, now: datetime, last_motion=None) -> bool:
    parsed = _parse_iso(claimed_at)
    if parsed is None:
        return True
    if last_motion is not None and last_motion > parsed:
        parsed = last_motion
    return now - parsed > timedelta(minutes=bound_minutes)


def _claim_is_stale(ticket_path, text: str, data: dict, now: datetime):
    motion, unreadable = _last_motion(
        Path(ticket_path), _sections(text).get('Result', ''), data.get('write_scope') or (),
    )
    stale = _is_stale(data.get('claimed_at'), _parse_bound_minutes(data.get('bound')), now, motion)
    return (stale, unreadable)
def _cut_subtree(run: str, root_id: str) -> list:
    """``(id, status)`` for every `<root>.` ticket the run holds, sorted.

    What the cut checker's packet is refused over, in both directions. The
    checker's whole authority is `amend` and `new` over the issued subtree,
    and both are refused outside `AMENDABLE_STATUSES` — a criterion that
    moves under a working executor is the moving target
    rules/verification.md §3 forbids. So one claimed unit is not a smaller
    correction but no correction at all, and the packet is refused rather
    than emitted against an authority that is already gone; each such item
    is named with the status that closed it, since the run that got here
    dispatched the cut checker after the units rather than before them. And
    a root with no `<root>.` unit at all has no cut to read: `cutcheck.py`
    on the root alone exits 0, and issuing the set is the decomposition,
    which the checker never repeats — `gate` refuses the same case.
    """
    items, error = _run_tickets(run)
    if error is not None:
        return []
    subtree = []
    for item in items:
        item_id = str(item.get('id') or '')
        if item_id.startswith(f'{root_id}.'):
            status = str(item.get('status') or '').strip().strip('`').strip()
            subtree.append((item_id, status))
    return sorted(subtree)
def _cut_lens_path():
    """The cut lens as this host holds it, or its repo-relative name.

    The two candidates ``scripts/cutcheck.py``'s ``_lib_root`` reads, and for
    its reason: this script runs either from a checkout of the library, where
    the lens is a sibling tree, or from the installed ``bin/`` beside the
    state sink, where the library is ``lib/`` and no ``skills/`` sits beside
    the scripts at all. A packet naming a path that is not there sends the
    checker hunting, so where neither resolves the repo-relative name is
    emitted: what to find rather than where it is not.
    """
    candidates = [Path(__file__).resolve().parent.parent]
    try:
        candidates.append(state_root.state_root().parent / 'lib')
    except OSError:
        pass
    for candidate in candidates:
        lens = candidate.joinpath(*CUT_LENS_PARTS)
        if lens.is_file():
            return str(lens)
    return '/'.join(CUT_LENS_PARTS)
def _further_child_prompt(executor, loaded: dict, ticket_path: Path, run_id, script, assigned_name=None):
    """The head of a packet for one further rules/verification.md §10 child.

    Two shapes, because the two children have opposite authority. The
    checker is handed the item's own write scope and the verb that records
    its pass; the re-verifier is handed neither, and told which identity to
    verify at. Everything after this -- the filing and run-state channels,
    ``reply_to`` -- is what the executor got, unchanged: hand-writing these
    packets beside the frontier is what left them without it (S1 F1).

    On a root ticket each shape has a cut-shaped twin, because there the
    result under review is the decomposition and not a deliverable: the lens
    is the cut lens, the object is the issued subtree read as data, the
    authority is that subtree's cut-time sections rather than the run's
    workspace -- which is the units' to write -- and the check that accepts
    the correction is ``cutcheck.py`` re-run (rules/verification.md §11).
    This is the review-and-fix call the old system made over a decomposition
    before kicking it off, placed where §10 already puts one fresh reader.
    """
    head = [f'Apply skill {executor} to ticket {ticket_path}.', 'Read the ticket; it is your complete delegation packet — objective, fixed inputs, bounds, return fields. Gather nothing outside its fixed inputs.']
    claimed_by = str(loaded.get('claimed_by') or '').strip() or 'another context'
    branch = str(loaded.get('workspace_branch') or '').strip()
    at_identity = f"the workspace the ticket's `workspace_branch` names ({branch})" if branch else "the identity the ticket's `## Result` records"
    is_root = _executor_of(loaded) == ROOT_EXECUTOR
    recorded = str(loaded.get('workspace_baseline') or '').strip().split()
    baseline = recorded[0] if recorded else 'REV'
    cut_check = _command_text(sys.executable, script.with_name('cutcheck.py'), '--baseline', baseline, run_id)
    unresolved = '' if recorded else ', REV being the revision the set was cut from'
    if is_root and executor == CHECKER_EXECUTOR:
        head.append(f"This is the rules/verification.md §10 checker's pass on the cut {claimed_by} produced under its claim, never a second decomposition: the lens is {_cut_lens_path()}, and its object is the issued subtree — the `{loaded['id']}.NN` items and the gate stubs — read as data.")
        head.append("Your authority is not the root's `write_scope`, which is the run's workspace and the units' to write. It is the unclaimed subtree's cut-time sections, corrected in place with:")
        head.append(_command_text(sys.executable, script, 'amend', run_id, 'ID', '--section', 'SECTION', '--file', 'PATH'))
        head.append('and, for an item the cut is missing:')
        head.append(_command_text(sys.executable, script, 'new', run_id, 'ID', '--file', 'PATH'))
        head.append('Both are refused once a unit is claimed, and so is this packet: the cut is corrected before any unit of it is dispatched.')
        head.append(f'Your repair is accepted on the cut check re-run to exit 0 (rules/verification.md §11){unresolved}:')
        head.append(cut_check)
        head.append("Append your findings and the changes you made to the root's `## Result`, and record the pass with:")
        head.append(_command_text(sys.executable, script, 'check', run_id, loaded['id'], '--by', assigned_name or 'NAME'))
    elif is_root:
        head.append(f'This is the rules/verification.md §10 re-verification of a checked cut, never a second decomposition: the completion test at the checked set is the cut check, read on the host that produced it{unresolved}:')
        head.append(cut_check)
        head.append("Your authority grants no write: the subtree and the root's `## Result` are another context's, and `## Verification` is the one section you file.")
    elif executor == CHECKER_EXECUTOR:
        scope = effective_write_scope(loaded)
        head.append(f"This is the rules/verification.md §10 checker's pass on a result {claimed_by} produced under its claim, never a re-execution of the item: the lens is the ticket's own `## Completion test`, at {at_identity}.")
        head.append(f"Your authority is the ticket's own write scope, {scope} — correct inside it, and append your findings, changes and the verification entries they invalidate to `## Result`. Record the pass, after correcting, with:")
        head.append(_command_text(sys.executable, script, 'check', run_id, loaded['id'], '--by', assigned_name or 'NAME'))
        head.append("Your pass is the one outside execution of the completion test: run each oracle once at the identity you confirmed, and reuse any entry whose covers are unchanged — re-running it buys nothing (rules/verification.md §7, §10). Spend the bound on what execution cannot buy: weakened or vacuous checks, scope, and correction.")
    else:
        head.append(f"This is the rules/verification.md §10 re-verification of a checked result, never a re-execution of the item: run the ticket's `## Completion test` at {at_identity}, reusing prior `## Verification` entries whose `covers` are unchanged there.")
        head.append("Your authority grants no write: the item's workspace and its `## Result` are another context's, and `## Verification` is the one section you file.")
    return head
def _all_pre_existing(completion: str) -> bool:
    """Every criterion of ``completion`` declares `provenance: pre-existing`.

    One of the rules/verification.md §10 ordinary independence paths, read
    off the ticket -- and the whole of what orch-frontier already calls a
    "pre-existing-only" item. Read off what the section carries and never
    off what it omits: `provenance` is optional (contracts/work-item.md)
    and an undeclared oracle makes no claim to predate the item, so a
    section holding one is not on that path. Nor is an empty section:
    ``criterion_defects`` has refused the packet long before this, and
    "every one of no criteria" is not an exemption anything earned.

    Criteria come from ``_criteria``, criterion parsing's one owner, so the
    section reads the same way to this exemption as it does to the packet
    refusal that grades it.
    """
    criteria = _criteria(completion)
    if not criteria:
        return False
    for text in criteria:
        declared = PROVENANCE_RE.search(text)
        if declared is None or declared.group(1).strip().lower() != PRE_EXISTING_PROVENANCE:
            return False
    return True
def _cmd_packet(rest):
    probe = list(rest)
    for flag in ('--reply-to', '--by', '--workspace', '--executor'):
        _extract_flag(probe, flag)
    if len(probe) != 2 or _segment_error('run id', probe[0]) is not None:
        return _packet_under_run_lock(rest)
    try:
        with _run_lock(probe[0]):
            return _packet_under_run_lock(rest)
    except OSError as error:
        return {'error': f'unable to emit packet: {error}'}
def _packet_under_run_lock(rest):
    """Emit the by-reference dispatch packet for one ticket.

    The dispatcher never has to read the ticket body: this refuses a packet
    missing a part and names it (contracts/work-item.md#dispatch,
    orch-delegate), and
    resolves the one absolute ticket path every worktree agrees on
    (contracts/work-item.md). Only the three values a ticket cannot carry are
    supplied here — reply_to belongs to the dispatch rather than the item, the
    workspace is derived from the pack's cell at dispatch, and the profile
    binding is a spawn argument, not prompt text.
    """
    args = list(rest)
    reply_to = _extract_flag(args, '--reply-to')
    dispatched_name = _extract_flag(args, '--by')
    workspace = _extract_flag(args, '--workspace')
    further = _extract_flag(args, '--executor')
    if len(args) != 2:
        return {'error': f'usage: {PACKET_USAGE}'}
    if further is not None:
        further = further.strip().strip('`').strip()
        if further not in CHECKER_PATH_EXECUTORS:
            return {'error': f"--executor takes {' or '.join(CHECKER_PATH_EXECUTORS)}, not '{further}': it emits the packet for one further rules/verification.md §10 child on an item another executor already holds, never a second executor for the item (rules/delegation.md §11). The ticket's own `executor` is the cut's, and `amend` is what changes it."}
    run, ticket_id = args
    tickets_root = _tickets_root()
    if tickets_root is None:
        return {'error': NO_SINK_ERROR}
    ticket_path = tickets_root / run / f'{ticket_id}.md'
    if not ticket_path.is_file():
        return {'error': f'ticket not found: {run}/{ticket_id}'}
    loaded = _load_ticket(ticket_path)
    if 'error' in loaded:
        return {'error': loaded['error']}
    text, failure = _read_utf8(ticket_path)
    if failure is not None:
        return failure
    if str(loaded.get('id') or '') != ticket_id or str(loaded.get('run') or '') != run:
        return {'error': f'packet path {ticket_path} does not carry the requested run/id {run}/{ticket_id}'}
    status = str(loaded.get('status') or '').strip().strip('`').strip()
    if status not in CHECKABLE_STATUSES:
        return {'error': f"ticket is not claimed (status '{status}'): packet emission requires an admitted claim"}
    # A claim taken up before the admission boundary existed carries no
    # receipt to name, and its dispatch says exactly that.
    admission = 'legacy-unadmitted'
    if is_v1(loaded) or is_v2(loaded):
        snapshot, sibling_failures = run_snapshot(ticket_path.parent)
        if sibling_failures:
            return sibling_failures[0][1]
        grade = graded_admission(ticket_id, text, snapshot, run)
        if grade['findings']:
            return {'error': 'packet admission grade failed', 'findings': grade['findings']}
        stored = str(loaded.get('admission') or '')
        if stored != grade['receipt']:
            return {'error': f'ticket has no current admission receipt: stored {stored or "<missing>"}, current {grade["receipt"]}'}
        admission = stored
    sections = _sections(text)
    executor = (loaded.get('executor') or '').strip().strip('`')
    missing = []
    if not reply_to:
        missing.append('reply_to (--reply-to)')
    if not executor:
        missing.append('executor (frontmatter)')
    if loaded.get('write_scope') is None:
        missing.append('authority (write_scope)')
    if not loaded.get('bound'):
        missing.append('bounds (bound)')
    for part, heading in PACKET_SECTIONS:
        if not sections.get(heading):
            missing.append(f'{part} (## {heading})')
    completion = sections.get('Completion test', '')
    if not completion:
        missing.append('completion test (## Completion test)')
    else:
        missing.extend(criterion_defects(completion))
    if missing:
        return {'error': 'packet incomplete: ' + '; '.join(missing)}
    if further is not None:
        status = str(loaded.get('status') or '').strip().strip('`').strip()
        if status not in CHECKABLE_STATUSES:
            return {'error': f"ticket is not claimed (status '{status}'): a further §10 child reads a result an executor produced under a claim. Dispatch the item's own executor first — this packet without --executor. ticket: {ticket_path}"}
        is_root = _executor_of(loaded) == ROOT_EXECUTOR
        independence = str(loaded.get('independence') or 'checker').strip().strip('`')
        if independence == 'gate' and (not is_root):
            return {'error': f'ticket {run}/{ticket_id} defers independence to its downstream gate: a non-root gate-deferred ticket has no checker or re-verifier packet'}
        prior_checker = str(loaded.get(CHECKED_BY_KEY) or '').strip().strip('`')
        if further == CHECKER_EXECUTOR and prior_checker:
            return {'error': f"ticket {run}/{ticket_id} is already checked by '{prior_checker}': no second checker packet is emitted. Use a distinctly named root-gate lens for another review"}
        if further == CHECKER_EXECUTOR and independence == CHECKER_INDEPENDENCE and _all_pre_existing(completion):
            return {'error': f"ticket {run}/{ticket_id}: {CHECKER_NOT_REQUIRED} (rules/verification.md §10). An all-pre-existing completion test is itself that section's independence path and exactly one path enters an item, so there is no checker to dispatch here: issue the item's own executor packet, this call without --executor, and re-verify at the result identity. ticket: {ticket_path}"}
        if further == CHECKER_EXECUTOR and _executor_of(loaded) == ROOT_EXECUTOR:
            root_id = loaded['id']
            subtree = _cut_subtree(loaded.get('run') or run, root_id)
            gate_prefix = f'{root_id}.gate.'
            if not any((not item_id.startswith(gate_prefix) for item_id, _ in subtree)):
                return {'error': f"root ticket '{root_id}' has no `{root_id}.` subtree ticket yet: the cut checker reads an issued set, and issuing one is the decomposer's, never a checker's second decomposition. ticket: {ticket_path}"}
            worked = [f"{item_id} is '{status or 'unstated'}'" for item_id, status in subtree if status not in AMENDABLE_STATUSES]
            if worked:
                return {'error': f"the cut checker corrects through `amend` and `new`, and {'; '.join(worked)} has left {sorted(AMENDABLE_STATUSES)}, where both are refused (rules/verification.md §3). A cut is checked before its first unit is dispatched, so there is nothing this child could still correct. ticket: {ticket_path}"}
    run_id = loaded.get('run') or run
    script = Path(__file__).with_name('tickets.py').resolve()
    executor_script = _executor_script(executor)
    # The name the child records under. `--by` is the dispatcher's, and the
    # only source for a further §10 child: the ticket's `claimed_by` is the
    # *executor* whose result that child reviews, so falling back to it
    # would hand a checker the name of the context it is checking. Absent
    # both, the packet states no name and forbids inventing one.
    assigned_name = str(dispatched_name or '').strip().strip('`').strip() or None
    if assigned_name is None and further is None:
        assigned_name = str(loaded.get('claimed_by') or '').strip() or None
    if further is not None:
        executor_script = None
        executor = further
        prompt = _further_child_prompt(further, loaded, ticket_path, run_id, script, assigned_name)
    elif executor_script is not None:
        prompt = [f'Run the script {executor_script} with the ticket path as its one argument, from your own workspace: {executor_script} {ticket_path}', f"No skill is applied. File the script's stdout verbatim as the ticket's `## Result`, and its exit code and the criterion it decides as `## Verification`. Change nothing else."]
    else:
        prompt = [f'Apply skill {executor} to ticket {ticket_path}.', 'Read the ticket; it is your complete delegation packet — objective, fixed inputs, authority (write_scope, excluded_actions), bounds, return fields. Gather nothing outside its fixed inputs.']
    # Where the store is, said beside the path that came out of it: a fork
    # that lost its packet went looking in a checkout's `.orch/`, found
    # nothing, and could not tell an empty tracker from the wrong one.
    prompt.append(f"Tickets are user-scope state: they live in the sink `scripts/state_root.py` resolves, {tickets_root}, and never under a checkout's `.orch/` — the absolute path above is the one every worktree agrees on.")
    if executor == LOOP_EXECUTOR:
        prompt.append(f"This is a loop ticket: the body of each fresh-context pass is `## Objective`, the done-check every pass is graded against is `## Completion test`, and the bound on the iterations is {loaded.get('bound')}. Stop at the done-check or at the bound, whichever comes first, and record which.")
    if workspace:
        prompt.append(f'Workspace: {workspace}')
    prompt.append("Write your result into the ticket's own sections as you produce it, never in one write at the end; the join alone sets terminal status.")
    isolation = normalized_isolation(loaded.get('isolation'))
    writes_workspace_content = bool(loaded.get('write_scope'))
    has_own_workspace = further is None and isolation == REQUIRED_ISOLATION and writes_workspace_content and establishes_a_git_workspace(loaded.get('pack'))
    if executor_script is None and further is None:
        prompt.append('Close by running each criterion\'s oracle once at the frozen result identity and recording its summary and exit in `## Verification`; your own entries are UNVERIFIED alone — independence arrives per rules/verification.md §10, and later readers reuse entries whose covers are unchanged; `[]` fills an empty Feedback or Risks; an excluded action suspends through `## Handoff`.')
        prompt.append("A check's own summary line is its evidence: never pipe a test command through `tail` or any other filter — the runner writes that summary to stderr, and dropping it leaves exit status alone.")
        prompt.append("Run the oracles your own `## Completion test` names, nothing wider: a repository-level check the standards owner requires and your ticket does not name is the engine's, run on the integrated tip after each merge batch.")
        if has_own_workspace:
            prompt.append("Your branch is not the revision those repository-level checks decide, and your green is provisional until the tip's.")
    if has_own_workspace:
        prompt.append('Workspace establishment (isolation: required), your first act, run from inside your own workspace:')
        prompt.append(_command_text(sys.executable, script.with_name('workspace.py'), 'start', run_id, loaded['id']))
    # A measurement relayed into a packet is a measurement taken at the cut
    # and read at a tip several commits later: one dispatch relayed a line
    # count as fact, and this run's own cut relayed a headroom that its
    # siblings were already spending. The generator parses the scope
    # anyway, so it emits the command over that scope instead of a number.
    # Only where the shape is granted the scope: a re-verifier writes
    # nothing, and a root's cut reader is handed `amend`/`new` over the
    # subtree rather than the root's workspace, so for those a ceiling
    # reading is a line whose only lawful use is to be ignored.
    corrects_in_scope = further is None or (further == CHECKER_EXECUTOR and _executor_of(loaded) != ROOT_EXECUTOR)
    measured = effective_write_scope(loaded) if corrects_in_scope else []
    measurer = _source_size_checker() if measured else None
    if measurer is not None:
        prompt.append('Measurement channel: any line count, headroom or ceiling arithmetic this packet or your ticket states was measured when the cut was made, and your siblings have been spending it since. Measure at your own tip rather than relaying it:')
        prompt.append(_command_text(sys.executable, measurer, *measured))
    prompt.append('Run-state channel (rules/visibility.md §6), from your own workspace, with TEXT and NAME replaced:')
    prompt.append(_command_text(sys.executable, script, 'run-state', run_id, '--note', 'TEXT'))
    prompt.append(_command_text(sys.executable, script, 'run-state', run_id, '--artifact', 'NAME', '--text', 'TEXT'))
    # `--append` on the template rather than in the prose beside it. The
    # prose said to add one and the line did not carry one, so every write
    # after a section's first was refused and the refusal cost a round
    # trip. It is lawful on an empty section -- `result` refuses only a
    # *non*-append write onto content already there -- so the first write
    # wants it too, and the form a child pastes is correct unedited.
    prompt.append(f"Filing channel (contracts/work-item.md's filing law), from your own workspace, with SECTION one of {list(EXECUTOR_SECTIONS)} and PATH a file in your own workspace. The file form is this host's primary channel: it carries --append, lawful on an empty section and required once one holds content, and a file is the one payload a multiline body survives. Never inline a multiline payload through --text, which takes TEXT as a single line:")
    prompt.append(_command_text(sys.executable, script, 'result', run_id, loaded['id'], '--section', 'SECTION', '--file', 'PATH', '--append'))
    prompt.append(_command_text(sys.executable, script, 'result', run_id, loaded['id'], '--section', 'SECTION', '--text', 'TEXT'))
    # A name a child was never told is a name it fills in: one checker fork
    # recorded `check --by checker-fable-01` against a dispatched
    # checker-opus-01, and `checked_by`'s immutability then left the run
    # carrying two names for one pass with no sanctioned way back.
    if assigned_name is not None:
        prompt.append(f"Your own assigned name is `{assigned_name}`: record under exactly that name wherever a command takes `--by`, and under no name you invent.")
    else:
        prompt.append("Your own assigned name is the one your dispatch spawned you under; this packet was emitted without `--by`, so record wherever a command takes `--by` under exactly that name, and under no name you invent — unable to name it, refuse rather than choose one.")
    if executor in DISPATCHING_EXECUTORS and assigned_name is not None:
        prompt.append(f"Every packet you dispatch carries `{assigned_name}` as that child's `reply_to`.")
    prompt.append('If you are a skill fork that arrived without this packet — a contract body and no ticket — refuse to the parent that forked you, by your own return and never to the coordinator by address, and record nothing under a self-invented name.')
    prompt.append(f'reply_to: {reply_to} — address your closing message to `{reply_to}`.')
    profile = None if further is not None else loaded.get('profile')
    return {'packet': {'run': loaded.get('run') or run, 'id': loaded['id'], 'path': str(ticket_path), 'executor': executor, 'script': executor_script, 'pack': loaded.get('pack'), 'profile': profile, 'independence': loaded.get('independence') or 'checker', 'isolation': isolation, 'admission': admission, 'assigned_name': assigned_name, 'reply_to': reply_to, 'workspace': workspace, 'prompt': '\n'.join(prompt)}}
