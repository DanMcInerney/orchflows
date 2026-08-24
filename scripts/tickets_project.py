"""Which project a run belongs to, and who may write to it.

The state sink is user-scope: one ``tickets/`` and one ``runs/`` tree for
every project on the host.  That is the architecture the host block
mandates, and its one exposure is that a run is reachable from checkouts
that have nothing to do with it.  Nothing mechanical asserted the
boundary, so three separable failures all arrived through it -- a
packet-less fork scavenged the sink and matched another project's
pending ticket, a claim was attempted from the sibling checkout of the
project holding the run's baseline, and a run was attributed to whichever
session wrote to the sink first while its tickets named a different
repository.

Two laws live here, and they are two.  *Attribution* names the run's
project from its ROOT TICKET's workspace, so the cut decides and the
caller's directory never does.  *Admission* compares a writing
workspace's project against the recorded one and refuses a mismatch, so
a context standing in the wrong checkout is stopped at the door rather
than discovered later by a baseline that will not resolve.

The claim path itself lives here for the same reason: admission is where
the boundary is enforced, and ``scripts/tickets_lifecycle.py`` sat six
lines under its ceiling.  Splitting the seam out is what made the law
affordable to add, so the two arrived together.
"""

from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone
try:
    from scripts import state_root
except ImportError:
    import state_root
if __package__:
    from .tickets_format import ROOT_EXECUTOR, _executor_of, _extract_flag, _parse_frontmatter, _read_utf8, _set_frontmatter_field
    from .tickets_inputs import parse_input_records
    from .tickets_store import NO_SINK_ERROR, RUN_IDENTITY_NAME, UTC_STAMP, _load_ticket, _origin_url, _project_key, _read_identity, _run_lock, _runs_root, _same_project, _segment_error, _tickets_root, _writer_identity
    from .tickets_admission import is_v1, is_v2
    from .tickets_context import graded_admission
    from .tickets_packet import _claim_is_stale
    from .tickets_transitions import refusal
else:
    from tickets_format import ROOT_EXECUTOR, _executor_of, _extract_flag, _parse_frontmatter, _read_utf8, _set_frontmatter_field
    from tickets_inputs import parse_input_records
    from tickets_store import NO_SINK_ERROR, RUN_IDENTITY_NAME, UTC_STAMP, _load_ticket, _origin_url, _project_key, _read_identity, _run_lock, _runs_root, _same_project, _segment_error, _tickets_root, _writer_identity
    from tickets_admission import is_v1, is_v2
    from tickets_context import graded_admission
    from tickets_packet import _claim_is_stale
    from tickets_transitions import refusal
CLAIM_USAGE = 'claim <run> <id> --by <name>'
TARGET_REPOSITORY_INPUT = 'target-repository'
CLAIM_REMEDY = 'Claim it from a workspace of {theirs}'
TERMINAL_REMEDY = 'Record it from a workspace of {theirs}'
CREATE_REMEDY = 'Use a different run id, or write from a workspace of {theirs}'
def _lifecycle():
    """The lifecycle module, resolved at call time rather than bound at import.

    Three names are reached through it: the two run-snapshot readers, which
    stayed where ``ready`` also reads them so a caller that swaps one swaps
    the one both paths use, and the atomic writer, which ``tickets.py``'s
    seam sync re-points on that module whenever the facade's is replaced.
    A claim holding import-time copies would write through bindings the
    sync cannot reach, and an injected write failure would land on nothing.

    The import is local because it runs the other way at load: lifecycle
    imports this module for the claim seam.
    """
    if __package__:
        from . import tickets_lifecycle
    else:
        import tickets_lifecycle
    return tickets_lifecycle
def _snapshots():
    """The run-snapshot pair, as ``ready`` currently sees them."""
    lifecycle = _lifecycle()
    return lifecycle._run_snapshot, lifecycle._snapshot_matches
def _project_at(location):
    """The project a directory belongs to, or ``None`` when it names none.

    ``find_repo_root`` owns *which project*, here as everywhere: a linked
    worktree resolves to the checkout it points at, so a run named by one
    worktree admits every worktree of the same repository.  A path that
    is not on this host walks to the filesystem root and answers ``None``,
    which reads as "this ticket names no project I can see" rather than
    as a refusal -- the host holding the run is not always the host the
    cut was written on.
    """
    root = state_root.find_repo_root(Path(str(location).strip()))
    if root is None:
        return None
    return {'root': str(root), 'origin': _origin_url(root), 'name': root.name}
def _root_ticket_text(run: str):
    """The run's root ticket, read from the sink, or ``None``.

    One physical run has one root, so the first item carrying the root
    executor is it; an unreadable sibling is skipped rather than allowed
    to decide the run's identity by its absence.
    """
    tickets_root = _tickets_root()
    if tickets_root is None:
        return None
    run_dir = tickets_root / run
    if not run_dir.is_dir():
        return None
    for path in sorted(run_dir.glob('*.md')):
        text, failure = _read_utf8(path)
        if failure is not None:
            continue
        try:
            data = _parse_frontmatter(text)
        except Exception:
            continue
        if _executor_of(data) == ROOT_EXECUTOR:
            return text
    return None
def root_ticket_project(run: str):
    """The project the run's root ticket's workspace names, or ``None``.

    The cut names its workspace in one place -- the ``target-repository``
    fixed input -- and that is the fact this reads.  It is the root
    ticket's and no other's: a unit inherits the same input, but a run
    that disagreed with itself would then be attributed by whichever unit
    sorted first, which is the arbitrariness this replaces.  A root that
    names nothing returns ``None``, and naming nothing is not an error:
    it leaves the attribution where it was rather than inventing one.
    """
    text = _root_ticket_text(run)
    if text is None:
        return None
    for record in parse_input_records(text)['records']:
        if record.get('name') != TARGET_REPOSITORY_INPUT or record.get('type') != 'literal':
            continue
        value = record.get('value')
        if not isinstance(value, str) or not value.strip():
            return None
        return _project_at(value)
    return None
def recorded_project(run: str):
    """The project a run's identity records, or ``None`` when it records none.

    ``None`` covers three cases that are one case to a caller: no sink, no
    identity yet, and a legacy identity written before the field existed.
    In all three there is no recorded fact to compare against, and a
    refusal would be asserting one.
    """
    runs_root = _runs_root()
    if runs_root is None:
        return None
    existing, error = _read_identity(runs_root / run / RUN_IDENTITY_NAME)
    if error is not None or not isinstance(existing, dict):
        return None
    recorded = existing.get('project')
    if isinstance(recorded, dict) and (recorded.get('root') or recorded.get('origin')):
        return recorded
    return None
def held_by(run: str, recorded: dict, writing: dict, remedy: str) -> str:
    """The one sentence every door refuses a foreign write with.

    One law refusing in three places says so in one voice, and the remedy
    is the half that differs: what a caller should do about it depends on
    which door they were at, and a remedy naming the wrong door is how a
    correct refusal still costs a context its next twenty minutes.
    """
    theirs, mine = (_project_key(recorded), _project_key(writing))
    return (
        f"run '{run}' is held by project {theirs}; this write comes from project "
        f"{mine}. One run id is one project's, so nothing was written. "
        + remedy.format(theirs=theirs)
    )
def binding_refusal(run: str, remedy: str):
    """Refuse this caller's write when its workspace is another project's.

    Structural, and deliberately so: it reads the run's recorded identity
    and the caller's own resolved project, and consults nothing the
    caller supplied.  That is the whole point -- a context with no inputs
    cannot know which project a sink ticket belongs to, so the check
    cannot be one it could satisfy by asserting something.
    """
    recorded = recorded_project(run)
    if recorded is None:
        return None
    writing, _ = _writer_identity()
    if _same_project(recorded, writing):
        return None
    return held_by(run, recorded, writing, remedy)
def _do_claim(ticket_path: Path, prior_text: str, claimed_by: str, now: datetime, receipt=None) -> dict:
    current_text, failure = _read_utf8(ticket_path)
    if failure is not None:
        return failure
    if current_text != prior_text:
        return {'error': 'ticket changed since read; lost the claim race, retry'}
    data = _load_ticket(ticket_path)
    if 'error' in data:
        return {'error': data['error']}
    status = data.get('status')
    skipped = []
    if status == 'claimed':
        stale, unreadable = _claim_is_stale(ticket_path, prior_text, data, now)
        if not stale:
            return {'error': f'ticket already claimed and not stale: {ticket_path.stem}'}
        if unreadable:
            skipped.append({'id': data['id'], 'reason': 'claim taken as stale without a full look at its motion: ' + '; '.join(unreadable)})
    elif status == 'pending' and receipt is not None:
        pass
    elif status != 'ready':
        return {'error': f"ticket is not claimable in status '{status}': {ticket_path.stem}"}
    timestamp = now.strftime(UTC_STAMP)
    updated = prior_text
    if receipt is not None:
        updated = _set_frontmatter_field(updated, 'admission', receipt)
    updated = _set_frontmatter_field(updated, 'status', 'claimed')
    updated = _set_frontmatter_field(updated, 'claimed_by', claimed_by)
    updated = _set_frontmatter_field(updated, 'claimed_at', timestamp)
    _lifecycle()._write_text_atomically(ticket_path, updated)
    claimed = {'id': ticket_path.stem, 'claimed_by': claimed_by, 'claimed_at': timestamp}
    return {'claimed': claimed, 'skipped': skipped} if skipped else {'claimed': claimed}
def _cmd_claim(rest):
    probe = list(rest)
    _extract_flag(probe, '--by')
    if len(probe) != 2 or _segment_error('run id', probe[0]) is not None:
        return _claim_under_run_lock(rest)
    run, ticket_id = probe
    tickets_root = _tickets_root()
    if tickets_root is None:
        return {'error': NO_SINK_ERROR}
    held = binding_refusal(run, CLAIM_REMEDY)
    if held is not None:
        return {'error': held}
    run_dir = tickets_root / run
    _run_snapshot, _ = _snapshots()
    snapshot, failures = _run_snapshot(run_dir)
    if failures:
        return {'error': 'run snapshot is not closed', 'failures': failures}
    prior_text = snapshot.get(ticket_id)
    grade = None
    if prior_text is not None:
        data = _parse_frontmatter(prior_text)
        status = str(data.get('status') or '')
        if (is_v1(data) or is_v2(data)) and status in ('pending', 'ready'):
            grade = graded_admission(ticket_id, prior_text, snapshot, run)
            if grade['findings']:
                return {'error': 'admission refused', 'findings': grade['findings']}
    try:
        with _run_lock(run):
            return _claim_under_run_lock(rest, prior_text=prior_text, snapshot=snapshot, grade=grade)
    except OSError as error:
        return {'error': f'unwritable ticket: {error}'}
def _claim_under_run_lock(rest, prior_text=None, snapshot=None, grade=None):
    """The claim half of grade-then-swap: compare-and-swap one graded snapshot into a
    live claim, landing only while that exact snapshot still matches, so a moved ticket,
    dependency, or cohort loses the race instead of claiming on a stale receipt. `ready`
    grades on the same `graded_admission` and swaps the same way in `_admit_ready_cas`.

    The project binding is graded before any of that, and before the ticket
    is read at all: a claim from another project's workspace is refused for
    what the caller is, not for what the ticket says, so no ticket state can
    argue its way past it."""
    args = list(rest)
    claimed_by = _extract_flag(args, '--by')
    if claimed_by is None:
        return {'error': 'claim requires --by <name>'}
    if len(args) != 2:
        return {'error': f'usage: {CLAIM_USAGE}'}
    run, ticket_id = args
    held = binding_refusal(run, CLAIM_REMEDY)
    if held is not None:
        return {'error': held}
    tickets_root = _tickets_root()
    if tickets_root is None:
        return {'error': NO_SINK_ERROR}
    ticket_path = tickets_root / run / f'{ticket_id}.md'
    if not ticket_path.is_file():
        return {'error': f'ticket not found: {run}/{ticket_id}'}
    loaded = _load_ticket(ticket_path)
    if 'error' in loaded:
        return {'error': loaded['error']}
    if prior_text is None:
        prior_text, failure = _read_utf8(ticket_path)
        if failure is not None:
            return failure
    data = _parse_frontmatter(prior_text)
    status = str(data.get('status') or '')
    if (is_v1(data) or is_v2(data)) and status in ('pending', 'ready'):
        _run_snapshot, _snapshot_matches = _snapshots()
        if snapshot is None:
            snapshot, failures = _run_snapshot(ticket_path.parent)
            if failures:
                return {'error': 'run snapshot is not closed', 'failures': failures}
        if grade is None:
            grade = graded_admission(ticket_id, prior_text, snapshot, run)
        if grade['findings']:
            return {'error': 'admission refused', 'findings': grade['findings']}
        if not _snapshot_matches(ticket_path.parent, snapshot, grade.get('snapshot_ids') or [ticket_id]):
            return {'error': 'ticket, dependencies, or cohort changed since admission grade; lost the claim race'}
    elif status == 'pending':
        return {'error': refusal('pending legacy ticket requires `recut` before v1 admission', 'recut', 'pending')}
    elif (is_v1(data) or is_v2(data)) and status == 'claimed':
        return {'error': refusal('a v1 claim is live on this ticket', 'claim', 'claimed')}
    elif not (is_v1(data) or is_v2(data)) and status in ('ready', 'claimed'):
        return {'error': refusal(f'{status} legacy ticket requires `recut` before v1 admission or reclaim', 'recut', status)}
    now = datetime.now(timezone.utc)
    result = _do_claim(ticket_path, prior_text, claimed_by, now, grade['receipt'] if grade is not None else None)
    if 'error' in result:
        return result
    claimed = dict(result['claimed'])
    claimed['run'] = run
    payload = {'claimed': claimed}
    if result.get('skipped'):
        payload['skipped'] = result['skipped']
    return payload
