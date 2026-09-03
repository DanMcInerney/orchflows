"""The grade every ticket-emitting command runs before it writes.

Commands that write a ticket and commands that grade one they are handed
run the one grade, `tickets_context.graded_admission`. What this module
adds is the partition: an emission cannot be held to a claim's standard,
so a dependency that has not run yet and an unsealed assignment defer,
while a locator no adapter resolves or an executor its pack does not bind
is the emitter's own and is refused here.

``DEFERRED_CODES`` is the whole of what is deferred, so the law is
fail-closed: a finding code added to the grader later refuses at emission
until someone states here why time repairs it.
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
    # A cut cites its predecessor's Context by identity; at emission the
    # predecessor is pending and its Result is empty, which is the whole
    # reason the edge exists. A missing section is a contract defect
    # `ticket_defects` refuses before this grade is reached.
    'ticket-result-not-terminal',
    'ticket-section-absent',
    # `stamp-generation`, `draft-validate` and `seal` run in that order,
    # each emitted into the state the next repairs, so a ticket is emitted
    # unsealed or never emitted at all.
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
    # process stands in rather than against the ticket's text. A cut is
    # emitted from one place and executed in another, so refusing on these
    # would make admissibility depend on which worktree wrote the ticket.
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
    """The findings in ``findings`` an emitting command owns, in grader
    order: membership, not severity, so one finding keeps one spelling."""
    return [finding for finding in findings or []
            if str((finding or {}).get('code') or '') not in DEFERRED_CODES]


def emission_findings(ticket_id: str, text: str, prospective: dict, run) -> list:
    """What the next command would refuse ``ticket_id`` for, graded now."""
    grade = graded_admission(ticket_id, text, prospective, run)
    return refusable(grade.get('findings') or [])


def _keyed(findings, ticket_id: str) -> set:
    """One grade as comparable keys, for subtracting one grade from another."""
    return {(ticket_id, str(entry.get('code') or ''), str(entry.get('field') or ''),
             str(entry.get('detail') or '')) for entry in findings}


def grade_emission(command: str, run, incoming: dict, siblings=None, prior=None):
    """``None`` if this emission introduces nothing refusable, else a refusal."""
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
    return {'error': f'{command} refuses to emit {subjects}: the next command '
                     f'would refuse what this writes, and the cut still holds '
                     f'the flag that was wrong', 'findings': findings}


def grade_run_emission(command: str, run, run_dir, incoming, *, repairs: bool=False):
    """``grade_emission`` against the run directory as it stands on disk."""
    siblings = {}
    if Path(run_dir).is_dir():
        siblings, _unreadable = run_snapshot(run_dir)
    prior = {ticket_id: siblings[ticket_id] for ticket_id in incoming
             if repairs and ticket_id in siblings}
    return grade_emission(command, run, incoming, siblings, prior)


__all__ = ('DEFERRED_CODES', 'emission_findings', 'grade_emission',
           'grade_run_emission', 'refusable')
