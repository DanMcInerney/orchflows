"""The four doors W3a retired from the CLI, reached at their internals.

`stamp-generation`, `draft-validate`, `seal`, and `ready` are no longer
subcommands. `tickets.py do` and `tickets.py judge` fold the first three and
`tickets.py dispatch` readies, so a caller never walks them by hand any more
and the help table names none of them. The functions themselves are still the
library's, called by exactly those doors.

A fixture that hand-authors one exact ticket -- an off-contract seal, a
deliberately stale generation, a `done` predicate with a fixed id -- still has
to walk that lifecycle to stand its subject up, and `do` mints its own id and
launches, so it cannot stand one up. Such a fixture reaches the internals
here, through the module that owns each, and never through a route that no
longer exists. `tests/test_command_surface.py` is what proves the routes are
gone; nothing below can hide their absence, because `_dispatch` still answers
`unknown subcommand` for every one of these names.
"""

from __future__ import annotations

from scripts import tickets
from scripts.tickets_instantiate import _cmd_stamp_generation
from scripts.tickets_lifecycle import _cmd_ready
from scripts.tickets_seal import _cmd_draft_validate, _cmd_seal

RETIRED_DOORS = {
    "stamp-generation": _cmd_stamp_generation,
    "draft-validate": _cmd_draft_validate,
    "seal": _cmd_seal,
    "ready": _cmd_ready,
}


def run(argv) -> dict:
    """Dispatch ``argv``, resolving a retired door at its own internal."""

    arguments = [str(value) for value in argv]
    if not arguments:
        return tickets._dispatch(arguments)
    door = RETIRED_DOORS.get(arguments[0])
    return tickets._dispatch(arguments) if door is None else door(arguments[1:])
