"""The grading context every ticket command builds the same way.

`lint`, dispatch-v1's admission guards -- the retired `claim` door's
replacement -- the internal readiness pass `dispatch`, `frame-open` and
`land` each run before promoting a pending ticket -- the retired `ready`
door's replacement -- and the emission commands `tickets_emission` fronts
all grade one ticket against the same two surroundings: the sibling texts
of its run directory, and the run-state tree the sealed grader resolves
its generation records from. Each built both for itself, and lint's copy
of the second was empty -- so a sealed root the readiness pass admitted
cleanly reported `seal-state-unavailable` under `lint`: one frozen text,
two readings, and the reading a producer sees was the wrong one.

Both are stated here once and consumed by every one of them, and
`graded_admission` is the only route to `grade_admission` they have. A
site cannot omit the context again without omitting it for every one of
them, which is a change a reader sees rather than a silence one does not.
"""
from __future__ import annotations
from pathlib import Path
if __package__:
    from .tickets_admission import grade_admission
    from .tickets_format import _read_utf8
    from .tickets_store import _runs_root
else:
    from tickets_admission import grade_admission
    from tickets_format import _read_utf8
    from tickets_store import _runs_root


def grader_context(run) -> dict:
    """The admission grader's context: where run state lives, and which run.

    Both values are strings the grader may compare and join without probing
    for ``None``, so an unresolved sink reads as an absent root rather than
    as a crash inside a grader.
    """
    return {'runs_root': str(_runs_root() or ''), 'run': str(run or '')}


def run_snapshot(run_dir):
    """``(texts, failures)`` for one run directory read whole.

    A grade is taken against a closed snapshot -- every sibling as it stood
    at one moment -- because admission's dependency findings read
    the others, not just the subject. ``failures`` carries ``(id, failure)``
    for each unreadable member so a caller may refuse on it, phrase it, or,
    as `lint` does, grade the members it could read.
    """
    texts, failures = {}, []
    for path in sorted(Path(run_dir).glob('*.md')):
        text, failure = _read_utf8(path)
        if failure is None:
            texts[path.stem] = text
        else:
            failures.append((path.stem, failure))
    return texts, failures


def graded_admission(ticket_id: str, text: str, siblings, run) -> dict:
    """Grade one snapshot through the one context, for all callers."""
    siblings = dict(siblings or {})
    return grade_admission(ticket_id, text, siblings,
                           context=grader_context(run))


__all__ = ('grader_context', 'graded_admission', 'run_snapshot')
