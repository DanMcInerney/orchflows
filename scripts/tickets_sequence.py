"""Chain-dispatch prompt support: one child, several exact named skills.

rules/delegation.md 4 admits a packet stating an ordered `sequence` of
skills: one fresh child executes each exact named skill in that stated
order against the same ticket, in the same context -- one spawn, one
assigned name, one witness, one role. The chain buys back the spawn and
the regather at seams where no verdict crosses; what it can never buy
is its own acceptance: a verdict the chain renders on work the chain
changed is void (rules/verification.md 11), so acceptance enters from
outside its name -- the ticket's independence path, unchanged.

The prompt tells the child to read each continuation contract from the
library directly rather than invoking it by name: a by-name invocation
forks on this host, and the fork-arrival clause every role-bearing
surface opens with refuses the packet-less fork it would spawn.
"""
from __future__ import annotations
import re
try:
    from scripts import state_root
except ImportError:
    import state_root

SEQUENCE_NAME_RE = re.compile(r'^orch-[a-z][a-z-]*$')


def sequence_defects(declared, executor: str) -> list:
    """Every way a frontmatter `sequence` is not a lawful chain.

    rules/delegation.md 4: an ordered chain of exact skill names one
    child executes in one context. The head must be the ticket's own
    `executor` -- passed in by the format owner, whose helper reads it --
    because every other reader resolves the child through that field; a
    chain whose head differs is two answers to "what runs first", and to
    "at what role": rules/roles.md 4 resolves the chain's one role there.

    So roles are not graded here -- with one role no ordering of
    declarations is unlawful. The tradeoff rides the head: a chain
    headed by a worker runs a planner continuation at the worker
    binding, and the caller stating that order buys it.
    """
    if declared is None:
        return []
    if not isinstance(declared, list):
        return ["frontmatter 'sequence' must be a list of exact skill names"]
    entries = [str(entry).strip().strip('`').strip() for entry in declared]
    defects = []
    if len(entries) < 2:
        defects.append("'sequence' with fewer than two skills is the plain executor: drop the field")
        return defects
    for position, entry in enumerate(entries, start=1):
        if not SEQUENCE_NAME_RE.fullmatch(entry):
            defects.append(f"sequence entry {position} '{entry}' is not an exact orch-* skill name; a `script:` step is a ticket of its own (contracts/work-item.md)")
    if len(set(entries)) != len(entries):
        defects.append("'sequence' repeats a skill: each chain entry runs once")
    if entries and executor and entries[0] != executor:
        defects.append(f"sequence head '{entries[0]}' is not the ticket's executor '{executor}': the chain's first skill is the `executor` every dispatcher resolves")
    return defects


def _by_name_root():
    """The installed flat index, or ``None`` from a bare checkout."""
    try:
        root = state_root.state_root().parent / 'lib' / 'by-name'
    except OSError:
        return None
    return root if root.is_dir() else None


def sequence_block(loaded: dict) -> list:
    """Prompt lines for a ticket whose frontmatter states a `sequence`.

    Emitted only for the chain's own dispatch: a further
    rules/verification.md 10 child reviews the chain's result and never
    continues its chain, so those packets carry none of this.
    """
    declared = loaded.get('sequence')
    if not isinstance(declared, list):
        return []
    entries = [str(entry).strip().strip('`').strip() for entry in declared]
    if len(entries) < 2:
        return []
    ordered = ', then '.join(entries)
    lines = [
        f"This ticket states an executor sequence: apply {ordered} — each "
        "exact named skill completed and its return filed before the next "
        "begins, all in this one context; never re-dispatch any of them "
        "(rules/delegation.md §4)."
    ]
    index = _by_name_root()
    where = (
        str(index / '<name>' / 'SKILL.md')
        if index is not None
        else "the library's by-name index"
    )
    lines.append(
        f"Read each continuation skill's contract directly from {where}; "
        "invoking it by name forks a packet-less child that must refuse."
    )
    lines.append(
        "This chain runs at one role, its head's — the role that "
        "established you (rules/roles.md §4). A continuation's own `role:` "
        "is not a mismatch here: run it, never refuse it."
    )
    lines.append(
        "The chain is one witness: a verdict you render on work this chain "
        "changed is void (rules/verification.md §11) — file it as work, and "
        "leave acceptance to the context outside your assigned name that "
        "this ticket's independence path names."
    )
    return lines
