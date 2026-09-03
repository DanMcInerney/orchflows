"""The grading context every ticket command builds the same way.

Every command that grades a ticket grades it against the same two
surroundings: the sibling texts of its run directory, and the run-state tree
the sealed grader resolves its generation records from.

Both are stated here once and consumed by every one of them, and
`graded_admission` is the only route to `grade_admission` they have. A site
cannot omit the context again without omitting it for all of them.
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
    """The admission grader's context: where run state lives, and which run."""
    return {'runs_root': str(_runs_root() or ''), 'run': str(run or '')}


def run_snapshot(run_dir):
    """``(texts, failures)`` for one run directory read whole."""
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
