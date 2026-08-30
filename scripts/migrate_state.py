#!/usr/bin/env python3
"""Copy a pre-existing state tree into the one user-scope sink.

Stdlib-only, cross-platform, no symlinks followed or created. The
destination is the root ``scripts/state_root.py`` resolves —
``$ORCHFLOWS_STATE_HOME`` or ``~/.orchflows/state`` — and this script
holds no second copy of that rule, of what a project is, or of the
friction entry's shape: it calls their owners.

Usage:
    python migrate_state.py --from ROOT [--from ROOT ...] [--dry-run]

``--from`` names a state directory to read, and repeats. ``--dry-run``
plans and prints without writing.

Three properties the whole design serves:

- **It copies, and only copies.** Nothing under a source root is
  deleted, moved, truncated or rewritten, so a source tree is
  byte-identical after a run. A record already present at the
  destination is left alone and reported, never overwritten.
- **It is idempotent.** The plan is computed against the destination as
  it stands, and a line stream is deduplicated by exact identity of the
  *migrated* line, so a second run over the same sources plans nothing
  and changes nothing.
- **It plans before it acts.** ``--dry-run`` and a real run build the
  same plan by the same code, so the plan a caller inspects is the plan
  that executes.

Only ``runs/``, ``tickets/``, ``friction/`` and ``improvement/`` migrate.
``canary/`` and ``bin/`` belong to the repository and stay there;
anything else is reported by name and left alone rather than copied
blind.

Prints exactly one JSON document to stdout and exits 0, like the sibling
writers: a refusal — a collision, a destination that cannot be read or
written, an unreadable source — is reported in the payload, never as a
non-zero exit or a traceback. The caller reads the payload.
"""

from __future__ import annotations

import json
import sys

try:  # in-repo; the installed copies sit flat together
    from scripts import console, friction, state_root, tickets
    from scripts.migrate_state_plan import (
        MIGRATED_STREAMS,
        RETAINED_DIRS,
        _Plan,
        _claims,
        _classify,
        _collisions,
        _copy_tree,
        _needs_newline,
        _plan_friction,
        _plan_improvement,
        _plan_line_file,
        _plan_runs,
        _resolve_roots,
        _source_report,
        apply_plan,
        plan_migration,
    )
    from scripts.migrate_state_records import (
        FRICTION_SUFFIX,
        LEGACY_CONVENTION,
        MIGRATED_FROM,
        _backfilled_project,
        _existing_lines,
        _migrated_covered_line,
        _migrated_friction_line,
        _project_label,
        _project_of,
        _recorded_project,
    )
except ImportError:  # pragma: no cover - the installed copy's path
    import console
    import friction
    import state_root
    import tickets
    from migrate_state_plan import (
        MIGRATED_STREAMS,
        RETAINED_DIRS,
        _Plan,
        _claims,
        _classify,
        _collisions,
        _copy_tree,
        _needs_newline,
        _plan_friction,
        _plan_improvement,
        _plan_line_file,
        _plan_runs,
        _resolve_roots,
        _source_report,
        apply_plan,
        plan_migration,
    )
    from migrate_state_records import (
        FRICTION_SUFFIX,
        LEGACY_CONVENTION,
        MIGRATED_FROM,
        _backfilled_project,
        _existing_lines,
        _migrated_covered_line,
        _migrated_friction_line,
        _project_label,
        _project_of,
        _recorded_project,
    )

USAGE = "usage: migrate_state.py --from ROOT [--from ROOT ...] [--dry-run]"


# --- argument parsing --------------------------------------------------------


def _parse_args(argv):
    """``(roots, dry_run, error)``. One unknown token is a refusal, not a guess."""

    roots, dry_run = [], False
    index = 0
    while index < len(argv):
        token = argv[index]
        if token == "--dry-run":
            dry_run = True
        elif token == "--from":
            index += 1
            if index >= len(argv):
                return [], False, f"--from needs a path. {USAGE}"
            roots.append(argv[index])
        elif token.startswith("--from="):
            roots.append(token.partition("=")[2])
        else:
            return [], False, f"unknown argument {token}. {USAGE}"
        index += 1
    if not roots:
        return [], False, f"at least one --from ROOT is required. {USAGE}"
    return roots, dry_run, None


def run(argv):
    roots, dry_run, error = _parse_args(argv)
    if error is not None:
        return {"error": error}
    try:
        sink = state_root.state_root().expanduser().resolve()
    except OSError as failure:
        return {"error": f"unresolvable sink: {failure}"}
    plan, document = plan_migration(roots, sink, dry_run)
    if not dry_run:
        apply_plan(plan, document)
    return {"migrate_state": document}


def main(argv=None):
    console.harden()
    arguments = sys.argv[1:] if argv is None else argv
    try:
        result = run(arguments)
    except Exception as error:  # a refusal is a payload, never a traceback
        result = {"error": f"{type(error).__name__}: {error}"}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(console.run(main, sys.argv[1:]))
