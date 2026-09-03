"""The notes a join writes into a work item's ``## Report``.

`## Report` is the item's one channel, and not everything worth reading
there was written by the child that ran. The join writes too: the done
predicate's own reading, and -- when a landing is refused on a merge conflict
and later carried through -- that refusal and its resolution.

None of these go through `tickets.py result`. A result record filed after
its attempt's outcome is refused as out of causal order, and that rule is
not the join's to loosen: the join is not a reopened attempt, so it writes
into the section directly and signs the write with its own name. Every note
is one whole line derived from what was observed, so a second landing that
observes the same thing finds its line already there and leaves it.

Stdlib-only, Python 3.9 and up.
"""

from __future__ import annotations

if __package__:
    from .tickets_format import REPORT_SECTION, _sections, _write_section
    from .tickets_result import RESULT_ATTRIBUTION_PREFIX
    from .tickets_store import _write_text_atomically
else:  # pragma: no cover - direct/installed flat script path
    from tickets_format import REPORT_SECTION, _sections, _write_section
    from tickets_result import RESULT_ATTRIBUTION_PREFIX
    from tickets_store import _write_text_atomically

# The opening words of the two landing notes, spelled once because they are
# read as well as written: the resolution is filed only where the refusal
# already stands, so a landing that was never refused stays silent.
CONFLICT_PREFIX = "integration refused on conflict:"
RESOLVED_PREFIX = "integration resolved:"


def file_once(path, by: str, body: str, what: str):
    """``(outcome, refusal)`` for one attributed note, filed at most once."""

    block = f"{RESULT_ATTRIBUTION_PREFIX}`{by}`\n\n{body}"
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        return "replayed", {"error": f"unreadable ticket for {what}: {error}"}
    prior = _sections(text).get(REPORT_SECTION, "")
    if block.rstrip() and block.rstrip() in prior:
        return "replayed", None
    try:
        _write_text_atomically(
            path, _write_section(text, REPORT_SECTION, block, bool(prior.strip())),
        )
    except (OSError, ValueError) as error:
        return "refused", {"error": f"unable to file {what}: {error}"}
    return "filed", None


def carries(path, prefix: str) -> bool:
    """Whether this ticket's ``## Report`` already carries such a note."""

    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return False
    return any(
        line.strip().startswith(prefix)
        for line in _sections(text).get(REPORT_SECTION, "").splitlines()
    )


def conflict_note(branch, into, root, paths) -> str:
    """What a landing was refused by, and the files it named."""

    return (
        f"{CONFLICT_PREFIX} candidate `{branch}` into `{into}` at {root} -- "
        + ", ".join(paths)
        + ". Resolve them in the candidate, commit there, then land again."
    )


def resolution_note(branch, into, tip, revision) -> str:
    """The identity the resolved candidate carried, and where it landed."""

    return (
        f"{RESOLVED_PREFIX} candidate `{branch}` at {tip} merged into "
        f"`{into}` at {revision}."
    )


__all__ = (
    "CONFLICT_PREFIX", "RESOLVED_PREFIX", "carries", "conflict_note",
    "file_once", "resolution_note",
)
