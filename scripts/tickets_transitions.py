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
    from .tickets_admission import ADMISSION_PENDING, ADMISSION_V2_PENDING
    from .tickets_format import TERMINAL_STATES, VALID_STATUSES
else:
    from tickets_admission import ADMISSION_PENDING, ADMISSION_V2_PENDING
    from tickets_format import TERMINAL_STATES, VALID_STATUSES
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
    Row('recut', (PENDING, READY), PENDING, ('admission', 'status', 'cohort'), LEASE_FIELDS,
        '`recut` it, which the cohort seal refuses while a member is taken up'),
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
def remedy_path(status: str, command: str) -> tuple:
    """The chain from `status` to one that runs `command`, or empty.

    One hop is enough for this table: `set-status` is the only command
    that moves a status without going through admission, so a refused
    command is reached, if at all, by one status write and then itself.
    """
    if allows(status, command):
        return ()
    for hop in _HOPS:
        if status not in hop.sources or hop.target is None:
            continue
        row = transition(hop.target, command)
        if row is not None:
            return (hop.remedy, row.remedy)
    return ()
def refusal(subject: str, command: str, status: str, note: str = None) -> str:
    """One refusal naming only what the table runs, in the order it runs.

    The whole point of rendering rather than writing: the remedy is the
    row's own phrase, so a command the table refuses at `status` cannot
    appear in the sentence that sends a caller to it.
    """
    row = transition(status, command)
    if row is not None:
        remedy = row.remedy
    else:
        steps = remedy_path(status, command)
        # A command with no row anywhere; the table grew past its chains.
        remedy = ', then '.join(steps) if steps else f'no chain reaches `{command}`'
    return f'{subject}: {remedy}.' + (f' {note}' if note else '')
