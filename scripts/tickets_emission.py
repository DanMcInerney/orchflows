"""The grade every ticket-emitting door runs before it writes.

`lint`, `ready`, `claim` and `packet` grade a ticket they are handed.
`new`, `amend`, `recut`, `instantiate` and `gate` write one. Those two
halves ran different grades, so a door could spend the run's time writing
what the next door then refused: a template instantiated two stubs and
`ready` skipped both, `new` accepted a locator `claim` refused, and a gate
wrote unsealed stubs under a sealed root. In each the flag that was wrong was still
in the caller's hand at emission and nobody looked.

The one grade is `tickets_context.graded_admission`, and this module is
the emitting half's door to it. What it adds is the partition, because an
emission cannot be held to a claim's standard: a freshly cut item names
dependencies that have not run yet and an assignment `seal`
has not sealed yet. Neither is the emitter's fault and neither can be
repaired at emission time, so both are deferred. Everything else is the
emitter's own -- a locator no adapter resolves, an executor its pack does
not bind, an absent mutation plan -- and is refused where repairing it
still costs the flag rather than the dispatch.

``DEFERRED_CODES`` is the whole of what is deferred, so the law is
fail-closed: a finding code added to the grader later refuses at emission
until someone states here why time repairs it. That direction is
deliberate. A new code that should have been deferred is a refusal a
caller reads and reports; a new code that should have been refused and
was not is the class this module exists to close.
"""
from __future__ import annotations
from pathlib import Path
if __package__:
    from .tickets_context import graded_admission, run_snapshot
else:
    from tickets_context import graded_admission, run_snapshot

DEFERRED_CODES = frozenset({
    # The run has not reached them yet: a cut issues its second item while
    # the first is still pending, and every edge in a template is this.
    'dependency-dangling',
    'dependency-incomplete',
    # A cut cites its predecessor's Context by identity -- that citation is
    # how a later item is written against what an earlier one finds, rather
    # than left as a hole someone amends in mid-flight. At emission the
    # predecessor is pending and its Result is empty, which is the whole
    # reason the edge exists. A truly missing section is a contract defect
    # `ticket_defects` refuses before this grade is ever reached.
    'ticket-result-not-terminal',
    'ticket-section-absent',
    # `stamp-generation`, `draft-validate` and `seal` are three steps in
    # that order, and each is emitted into the state the next one repairs:
    # a stamped root has no cut generation until the draft names one and no
    # seal until `seal` writes one. A ticket is emitted unsealed or is
    # never emitted at all, so the whole seal vocabulary defers.
    'assignment-seal-mismatch',
    'assignment-unsealed',
    'generation-invalid',
    'generation-pair-mismatch',
    'generation-root-mismatch',
    'seal-state-unavailable',
    'seal-state-missing',
    'seal-state-mismatch',
    'sealed-assignment-mismatch',
    'draft-status',
    'generation-missing',
    'validation-receipt-mismatch',
    # Resolved against the checkout, the sink or the validator the grading
    # process happens to stand in, rather than against the ticket's text.
    # A cut is emitted from wherever the cutter is standing and executed
    # somewhere else, so refusing on these would make one ticket admissible
    # or not by which worktree wrote it -- and would refuse a revision that
    # is simply not fetched here. What is wrong in the text is this door's;
    # what is merely unreachable from here is `ready`'s and `claim`'s, run
    # from the workspace the work actually happens in.
    'git-path-absent',
    'git-project-mismatch',
    'git-remote-mismatch',
    'git-revision-unresolved',
    'git-symbol-absent',
    'identity-digest-mismatch',
    'identity-locator-absent',
    'identity-root-unavailable',
    'result-resolver-unavailable',
    'scope-baseline-unavailable',
    'validator-unavailable',
})


def refusable(findings) -> list:
    """The findings in ``findings`` an emitting door owns, in grader order.

    Membership, not severity: the grader has already ordered and phrased
    these, and re-ranking them here would give one finding two spellings
    depending on which door reported it.
    """
    return [finding for finding in findings or []
            if str((finding or {}).get('code') or '') not in DEFERRED_CODES]


def emission_findings(ticket_id: str, text: str, prospective: dict, run) -> list:
    """What the next door would refuse ``ticket_id`` for, graded now.

    ``prospective`` is the snapshot as it would stand after the write --
    the run's existing members with the incoming ones laid over them --
    because admission's dependency findings read the siblings,
    not the subject alone. Grading the incoming ticket against the run
    without it would report every member of its own batch as dangling.
    """
    grade = graded_admission(ticket_id, text, prospective, run)
    return refusable(grade.get('findings') or [])


def _keyed(findings, ticket_id: str) -> set:
    """One grade as comparable keys, for subtracting one grade from another."""
    return {(ticket_id, str(entry.get('code') or ''), str(entry.get('field') or ''),
             str(entry.get('detail') or '')) for entry in findings}


def grade_emission(door: str, run, incoming: dict, siblings=None, prior=None):
    """``None`` if this emission introduces nothing refusable, else a refusal.

    All incoming tickets are graded before any is reported, so a door
    writing more than one -- `instantiate` -- refuses with the whole grade
    rather than with whichever stub happened to be graded first. The
    findings carry their ticket, since a template's refusal naming no stub
    is one a caller cannot act on.

    ``prior`` makes the grade a delta, and the doors that repair an
    existing ticket pass it. `amend` and `recut` exist to repair a cut, so
    holding a repair hostage to a defect it did not introduce would refuse
    the one mechanism for fixing that defect -- and often refuse the first
    of the several repairs that together clear it. A ticket already
    carrying a finding keeps carrying it; `lint` is what reports it, and
    `ready` is what refuses to dispatch it. What this door owns is only
    what crossing it added.
    """
    prospective = dict(siblings or {})
    prospective.update(incoming)
    inherited = set()
    for ticket_id, text in (prior or {}).items():
        inherited |= _keyed(
            emission_findings(ticket_id, text, dict(siblings or {}), run), ticket_id)
    findings = []
    for ticket_id in sorted(incoming):
        for entry in emission_findings(ticket_id, incoming[ticket_id],
                                       prospective, run):
            if _keyed([entry], ticket_id) <= inherited:
                continue
            findings.append({**entry, 'ticket': ticket_id})
    if not findings:
        return None
    subjects = ', '.join(sorted(incoming))
    return {'error': f'{door} refuses to emit {subjects}: the next door would '
                     f'refuse what this writes, and the cut still holds the '
                     f'flag that was wrong', 'findings': findings}


def grade_run_emission(door: str, run, run_dir, incoming, *, repairs: bool=False):
    """``grade_emission`` against the run directory as it stands on disk.

    The doors call this one rather than assembling a snapshot each, which
    is the omission `tickets_context` was written for: four callers built
    the same surroundings four ways and one of them built it empty. A run
    directory that does not exist yet is an empty run, not a failure --
    the first ticket of a cut is emitted into nothing.

    ``repairs`` marks a door that rewrites tickets already in the run --
    `amend`, `recut`, `stamp-generation` -- and takes their current text
    off the same disk as the prior grade, so the refusal covers what the
    rewrite introduced and not what it inherited. A door that creates
    tickets leaves it false: nothing was there to inherit from.

    `amend` and `recut` reach this through the one writer they share,
    ``tickets_issue._replace_and_invalidate``, rather than each calling it
    for itself: a replacement graded in one caller and not in the other is
    the asymmetry that family keeps growing back, and one writer can only
    be given one grade.

    An unreadable sibling is passed over rather than raised on. Every door
    that reaches here has already taken its own exact snapshot and refused
    on a read failure, so this is never the only reader of those bytes.
    """
    siblings = {}
    if Path(run_dir).is_dir():
        siblings, _unreadable = run_snapshot(run_dir)
    prior = {ticket_id: siblings[ticket_id] for ticket_id in incoming
             if repairs and ticket_id in siblings}
    return grade_emission(door, run, incoming, siblings, prior)


__all__ = ('DEFERRED_CODES', 'emission_findings', 'grade_emission',
           'grade_run_emission', 'refusable')
