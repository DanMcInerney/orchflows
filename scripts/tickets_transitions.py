"""State times command: what each lifecycle command may do at each status.

One row per (status, command): the fields the transition sets, the fields
it blanks, and the phrase that names it as a remedy. Every refusal a
lifecycle command emits on a refused transition is rendered here, from the
rows, so a refusal cannot name a path the table forbids -- which two of
them did, recommending `set-status pending, then recut` while `set-status
pending` left `claimed_at` behind and the lease-leftover cohort seal
refused exactly that recut.

Rows are the moving statuses only. Stamping -- what `new`, `_place_ticket`
and `recut` write, and what the v2 draft validator checks -- is version
aware and lives in `STAMPS`, keyed by version because the pending-admission
sentinel differs; `scripts/tickets_issue.py` and
`scripts/tickets_generations.py` are its consumers.
"""

from __future__ import annotations
from collections import namedtuple
if __package__:
    from .tickets_admission import ADMISSION_PENDING, ADMISSION_V2_PENDING, cohort_sealed, is_v2
    from .tickets_format import TERMINAL_STATES, VALID_STATUSES, _set_frontmatter_field
else:
    from tickets_admission import ADMISSION_PENDING, ADMISSION_V2_PENDING, cohort_sealed, is_v2
    from tickets_format import TERMINAL_STATES, VALID_STATUSES, _set_frontmatter_field
PENDING, READY, CLAIMED, SUSPENDED = 'pending', 'ready', 'claimed', 'suspended'
STATUSES = tuple(sorted(VALID_STATUSES))
# The lease: what a claim writes and what putting an item back on offer
# clears. Blanked, never removed, so a reader still tells an unclaimed
# ticket from one whose claim field is missing (tickets_reissue.py's
# convention, adopted here).
LEASE_FIELDS = ('claimed_by', 'claimed_at')
GRANTABLE_STATUSES = frozenset({CLAIMED, SUSPENDED})
CHECKABLE_STATUSES = GRANTABLE_STATUSES
# `ready` and `claimed` are admission's to write, so no set-status row
# reaches them and `set_status_command` on either names no table command.
ADMISSION_OWNED_TARGETS = (READY, CLAIMED)
Row = namedtuple('Row', ('command', 'sources', 'target', 'sets', 'blanks', 'remedy'))
Stamp = namedtuple('Stamp', ('status', 'admission', 'blanks', 'draft_statuses'))
def set_status_command(target: str) -> str:
    """The command name a `set-status <target>` row carries."""
    return f'set-status {target}'
_ROWS = (
    Row('claim', (PENDING, READY), CLAIMED, ('admission', 'status') + LEASE_FIELDS, (),
        '`claim` it'),
    # No seal caveat in the phrase: `remedy_path` drops this row outright
    # when the cohort is sealed, so naming it at all means it runs.
    Row('recut', (PENDING, READY), PENDING, ('admission', 'status', 'cohort'), LEASE_FIELDS,
        '`recut` it'),
    Row('amend', (PENDING, READY), None, ('<cut section>',), (),
        '`amend` one cut-time section'),
    Row('grant', tuple(sorted(GRANTABLE_STATUSES)), None,
        ('granted_scope', 'granted_by', 'granted_at'), (),
        '`grant` the paths the widening adds'),
    Row('check', tuple(sorted(CHECKABLE_STATUSES)), None, ('checked_by',), (),
        '`check` it'),
    Row(set_status_command(PENDING), STATUSES, PENDING, ('status',), LEASE_FIELDS,
        '`set-status pending`, which releases the lease by blanking claimed_by and claimed_at'),
    Row(set_status_command(SUSPENDED), STATUSES, SUSPENDED, ('status',), (),
        '`set-status suspended`, which keeps the lease while the join opens a successor'),
) + tuple(
    # A terminal target keeps the lease too: the worklog orders a run by
    # `claimed_at`, and a closed item that lost it would sort as unclaimed.
    Row(set_status_command(state), STATUSES, state, ('status',), (), f'`set-status {state}`')
    for state in TERMINAL_STATES
)
COMMANDS = tuple(sorted({row.command for row in _ROWS}))
# The two commands the cohort seal gates on top of the status rows
# (scripts/tickets_issue.py's `_cmd_amend` and `_recut_under_run_lock`).
# A row is necessary for them, never sufficient: under a seal the status
# is right and the command still refuses, so a chain that named one would
# be the very sentence this module exists to stop.
SEAL_REFUSED = ('recut', 'amend')
# `grant` and `check` act on an item a child is already executing. Reaching
# either by rewriting a status is reopening an item, never repairing one --
# at a terminal status it would reopen a verdict the join has already read,
# which is what both sites' notes forbid. So no chain ends at them: the
# note carries the remedy, and the table declines to invent a rewrite.
NOT_A_REMEDY = ('grant', 'check')
# The cut-time note that holds whichever way the chain resolves: the change
# is admissible as its own scope, sealed or not. Kept beside the rows and
# not inside them because it names no command -- a `refusal` note is the
# caller's half, which is exactly where `NOT_A_REMEDY`'s real remedy lives.
CUT_QUEUE_NOTE = 'Or queue the change as its own scope.'
# The one command that moves a status without the admission boundary, so
# the only first step a remedy chain can take.
_HOPS = tuple(row for row in _ROWS if row.command.startswith('set-status '))
# What a stamping site writes at each version, and -- for the v2 draft
# validator -- the statuses a draft may still sit at. `draft-validate` has
# no v1 entry: drafts and generations are v2's alone.
STAMPS = {
    ('stamp', 1): Stamp(PENDING, ADMISSION_PENDING, LEASE_FIELDS, (PENDING, READY)),
    ('stamp', 2): Stamp(PENDING, ADMISSION_V2_PENDING, LEASE_FIELDS, (PENDING, READY)),
    ('draft-validate', 2): Stamp(PENDING, ADMISSION_V2_PENDING, LEASE_FIELDS,
                                 (PENDING, READY, SUSPENDED)),
}
def pending_admission(version: int = 1) -> str:
    """The pending-admission sentinel this admission version stamps."""
    return STAMPS[('stamp', int(version))].admission
def declared_version(data) -> int:
    """The admission version this ticket's own bytes declare.

    The four public v2 fields opt in (`is_v2`), and so does the v2 pending
    sentinel alone: a drafting member carries exactly that between the
    door that emits it and the `seal` that writes its generation fields.
    Everything else is v1, the default a bare ticket has always had.
    """
    if is_v2(data) or str(data.get('admission') or '').startswith('v2:'):
        return 2
    return 1
def version_divergence(ticket_id: str, data: dict, root_data: dict):
    """The finding that names a member disagreeing with its root, or None.

    The version is the root's property: `stamp-generation` opens v2 on a
    root and its whole cut at once, so a member emitted at the other
    version is not an earlier lifecycle stage some later step rewrites --
    nothing rewrites it -- but a ticket every grader reads
    self-consistently down its own version's path while the run cannot run
    it. The recorded instance wrote v1 gate stubs under a sealed v2 root,
    and each graded clean until `ready`. Named here, beside the stamps, so
    the one grade refuses it at every door while the flag that was wrong
    is still in the caller's hand.
    """
    member, root = declared_version(data), declared_version(root_data)
    if member == root:
        return None
    remedy = ('declare the opt-in the root carries: a v2 pending admission '
              'or generation field, as `new --file` and `gate` emit'
              if root == 2 else 'drop the v2 declaration: this root and its cut are v1')
    return {'code': 'version-root-divergence', 'field': 'admission',
            'detail': f'v{member} member under a v{root} root; {remedy}'}
def stamp(command: str = 'stamp', version: int = 1):
    """The stamping entry for one command at one version, or None."""
    return STAMPS.get((command, int(version)))
def transition(status: str, command: str):
    """The row for this pair, or None when the table refuses it."""
    for row in _ROWS:
        if row.command == command and status in row.sources:
            return row
    return None
def allows(status: str, command: str) -> bool:
    return transition(status, command) is not None
def sets(status: str, command: str) -> tuple:
    """The frontmatter fields this transition writes."""
    row = transition(status, command)
    return () if row is None else row.sets
def blanks(status: str, command: str) -> tuple:
    """The frontmatter fields this transition clears."""
    row = transition(status, command)
    return () if row is None else row.blanks
def set_status_blanks(target: str) -> tuple:
    """What reaching `target` through set-status clears, from any status."""
    return blanks(CLAIMED, set_status_command(target))
def remedies(status: str) -> tuple:
    """Every command the table runs at this status, as remedy phrases."""
    return tuple(row.remedy for row in _ROWS if status in row.sources)
def sealed_after_release(ticket_id: str, text: str, siblings: dict) -> bool:
    """Whether the cohort still refuses `recut` once the lease is released.

    The seal reads a leftover `claimed_at` as a ticket somebody has taken
    up, so asking it about the item as it stands answers about the lease
    rather than about the cohort -- and a refusal that asked it that way
    would refuse to name `recut` for every claimed item, sealed or not.
    The question a refusal needs is the one after the release it is about
    to recommend, which is what this asks.
    """
    released = _set_frontmatter_field(text, 'status', PENDING)
    for field in LEASE_FIELDS:
        released = _set_frontmatter_field(released, field, '')
    return cohort_sealed(ticket_id, released, siblings)
def remedy_path(status: str, command: str, sealed: bool = False) -> tuple:
    """The chain from `status` to one that runs `command`, or empty.

    One hop is enough for this table: `set-status` is the only command
    that moves a status without going through admission, so a refused
    command is reached, if at all, by one status write and then itself.
    Under a seal the seal-gated commands drop out of the chain, and what
    is left is the successor path -- suspend, and let the join open one.
    A `NOT_A_REMEDY` command has no chain at all: no status write is the
    right answer to being asked for one where the command does not run.
    """
    if allows(status, command) and not (sealed and command in SEAL_REFUSED):
        return ()
    if command in NOT_A_REMEDY:
        return ()
    for hop in _HOPS:
        if status not in hop.sources or hop.target is None:
            continue
        row = transition(hop.target, command)
        if row is None or (sealed and row.command in SEAL_REFUSED):
            continue
        return (hop.remedy, row.remedy)
    suspend = transition(status, set_status_command(SUSPENDED))
    return () if suspend is None else (suspend.remedy,)
def cut_refusal(subject: str, command: str, status: str, ticket_id: str,
                text: str, siblings: dict, note: str = None) -> str:
    """One cut-time refusal, with the seal asked the way a remedy needs it.

    `amend` and `recut` are the two commands a cohort seal gates on top of
    the status rows, so a refusal for either has two questions to answer
    and only looks like one: whether the status runs the command, and
    whether the seal would still refuse it after the release the chain is
    about to recommend. Asking the seal about the item as it stands answers
    about the lease instead -- `sealed_after_release` is the question --
    and a caller that asked the first question alone is how the two
    hand-written sentences named a recut the seal refused.

    Which state that really is, since one wording claimed a seal no
    execution could find: a `v1:root:` cohort is judged on the graded
    member alone, so releasing this item's own lease lifts it however many
    siblings hold leases of their own. A `v1:ticket:` or `v1:batch:`
    cohort seals on any other member, and there no release of this item's
    lease can lift it -- that, and only that, is where the chain drops to
    the successor path.
    """
    return refusal(subject, command, status, note=note,
                   sealed=sealed_after_release(ticket_id, text, siblings))
def refusal(subject: str, command: str, status: str, note: str = None,
            sealed: bool = False) -> str:
    """One refusal naming only what the table runs, in the order it runs.

    The whole point of rendering rather than writing: the remedy is the
    row's own phrase, so a command the table refuses at `status` -- or one
    the cohort seal refuses there -- cannot appear in the sentence that
    sends a caller to it.
    """
    steps = remedy_path(status, command, sealed)
    if not steps:
        row = transition(status, command)
        steps = () if row is None else (row.remedy,)
    tail = f' {note}' if note else ''
    if not steps:
        return f'{subject}.{tail}'
    return f'{subject}: ' + ', then '.join(steps) + '.' + tail
