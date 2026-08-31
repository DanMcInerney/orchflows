"""The two brick doors: one command opens, seals, and launches one child.

`do` makes an artifact and `judge` reads finished ones. Both fold what a
caller used to sequence by hand -- `new`, `stamp-generation`,
`draft-validate`, `seal`, `ready`, `dispatch` -- into one call, because every
one of those steps is mechanical and none of them is a decision. The
established public doors stay exactly where they are and remain the recovery
seam; nothing here is a second protocol, and each step below is the same
function the granular command calls.

Two facts make the fold safe. The id is minted under the run lock, so two
concurrent callers under one parent cannot choose one id. And a child is
sealed through its parent rather than named in a sealed cut: the cut that
sealed the parent closed before the child existed, so the child inherits the
parent's generations, self-seals its own assignment, and admission verifies
the parent's seal in the sealed record -- the door `loop-arm` already used,
generalized here to every runtime child.

A parentless brick is its own root and takes the full generation lifecycle:
it is stamped, its draft validated, and its own one-member cut sealed, all
through the public commands.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

if __package__:
    from .tickets_adapters import ADAPTER_REGISTRY
    from .tickets_admission import ADMISSION_PENDING
    from .tickets_bound import parse_bound
    from .tickets_format import (
        REPORT_SECTION, _extract_all, _extract_flag,
        _parse_frontmatter, _read_utf8, _set_frontmatter_field, done_defects,
        next_brick_id,
    )
    from .tickets_generations import assignment_digest
    from .tickets_issue import (
        ISOLATION_VALUES, NEW_DEFAULT_BOUND, _issue_ticket, pinned_pack_digest,
    )
    from .tickets_issue_render import _render_ticket
    from .tickets_seal import _cmd_draft_validate, _cmd_seal
    from .tickets_store import (
        NO_SINK_ERROR, UTC_STAMP, _run_lock, _segment_error, _tickets_root,
    )
else:  # pragma: no cover - direct/installed flat script path
    from tickets_adapters import ADAPTER_REGISTRY
    from tickets_admission import ADMISSION_PENDING
    from tickets_bound import parse_bound
    from tickets_format import (
        REPORT_SECTION, _extract_all, _extract_flag,
        _parse_frontmatter, _read_utf8, _set_frontmatter_field, done_defects,
        next_brick_id,
    )
    from tickets_generations import assignment_digest
    from tickets_issue import (
        ISOLATION_VALUES, NEW_DEFAULT_BOUND, _issue_ticket, pinned_pack_digest,
    )
    from tickets_issue_render import _render_ticket
    from tickets_seal import _cmd_draft_validate, _cmd_seal
    from tickets_store import (
        NO_SINK_ERROR, UTC_STAMP, _run_lock, _segment_error, _tickets_root,
    )

DO_USAGE = (
    "do <run> --pack P --goal-file F [--details-file D] [--parent ID] "
    "[--done <canonical-json>] [--isolation required|none] [--bound B] "
    "[--workspace <source-tree-to-cut-from>] [--host H]"
)
JUDGE_USAGE = (
    "judge <run> --pack P --goal-file F --artifacts <typed-line> "
    "[--artifacts ...] [--details-file D] [--parent ID] "
    "[--isolation required|none] [--bound B] "
    "[--workspace <source-tree-to-cut-from>] [--host H]"
)
DO_EXECUTOR = "orch-execute"
JUDGE_EXECUTOR = "orch-check"
# A brick carries no standing checker lane: what checks it is the caller's
# own `judge` brick or its `done` predicate, both of which are outside work
# rather than a dependent's `checked_by` anchor.
BRICK_INDEPENDENCE = "gate"
ARTIFACT_KINDS = frozenset(
    adapter.artifact_kind for adapter in ADAPTER_REGISTRY.values()
)
# The `parent` clause on the child's own Context: the one line that says
# whose call this ticket is, in the section a reader of the ticket alone
# would otherwise have to infer it from the id.
PARENT_CLAUSE = "- parent: "
ARTIFACT_CLAUSE = "- artifact: "


def _dispatch_facade():
    if __package__:
        from .tickets_dispatch_facade import _cmd_dispatch
    else:  # pragma: no cover - direct/installed flat script path
        from tickets_dispatch_facade import _cmd_dispatch
    return _cmd_dispatch


def _stamp_generation():
    if __package__:
        from .tickets_instantiate import _cmd_stamp_generation
    else:  # pragma: no cover - direct/installed flat script path
        from tickets_instantiate import _cmd_stamp_generation
    return _cmd_stamp_generation


def _run_dir(run: str):
    """`(run_dir, refusal)` for the run this brick is minted into."""

    root = _tickets_root()
    if root is None:
        return None, {"error": NO_SINK_ERROR}
    return root / run, None


def _issued_ids(run_dir) -> list:
    """Every id already issued in the run, read under the caller's lock.

    Read inside the lock and nowhere else. Two callers that listed the run
    before taking it both saw the same highest ordinal and both chose the id
    after it, and the second one lost its whole brick to the exclusive
    create -- which is the failure the lock is held to prevent, moved one
    line earlier rather than removed.
    """

    return (
        sorted(path.stem for path in run_dir.glob("*.md"))
        if run_dir.is_dir() else []
    )


def _artifact_lines(values) -> tuple:
    """`(lines, refusal)` for the typed artifact identities a judge reads.

    One flag repeated, or one value carrying several lines: a caller relaying
    two children's returned lines has them as two lines already, and asking
    it to re-join them into one flag value is where a paraphrase gets made.
    """

    lines = []
    for value in values:
        lines.extend(part.strip() for part in str(value).splitlines() if part.strip())
    if not lines:
        return None, {"error": f"judge requires --artifacts. usage: {JUDGE_USAGE}"}
    for line in lines:
        kind = line.split(":", 1)[0]
        if kind not in ARTIFACT_KINDS or not line[len(kind) + 1:].strip():
            return None, {"error": (
                f"artifact '{line}' is not one typed identity; expected "
                + ", ".join(sorted(f"{name}:<identity>" for name in ARTIFACT_KINDS))
            )}
    return lines, None


def _context(parent, artifacts) -> str:
    """The child's Context: whose call it is, and what it was handed."""

    lines = [PARENT_CLAUSE + parent] if parent else []
    lines.extend(ARTIFACT_CLAUSE + line for line in artifacts or ())
    return "\n".join(lines) if lines else "[]"


def _sealed_parent(run_dir, parent: str):
    """`(frontmatter, refusal)` for the sealed ticket a child hangs under."""

    text, failure = _read_utf8(run_dir / f"{parent}.md", "parent ticket")
    if failure is not None:
        return None, {"error": f"parent ticket not found in run: {parent}"}
    data = _parse_frontmatter(text)
    missing = [
        field for field in ("root_generation", "cut_generation", "assignment_seal")
        if not str(data.get(field) or "").strip()
    ]
    if missing:
        return None, {"error": (
            f"parent {parent} is not sealed ({', '.join(missing)} absent); a "
            "child is sealed through its parent's own generation, so seal the "
            "parent first"
        )}
    return data, None


def _minted(run: str, run_dir, *, executor, pack, goal, details, parent,
            done, isolation, bound, artifacts):
    """`(ticket_id, refusal)` -- the whole write, under the caller's lock."""

    ticket_id = next_brick_id(parent, _issued_ids(run_dir))
    inherit = None
    if parent:
        inherit, refusal = _sealed_parent(run_dir, parent)
        if refusal is not None:
            return None, refusal
    pinned, refusal = pinned_pack_digest(pack)
    if refusal is not None:
        return None, refusal
    fields = {
        "id": ticket_id, "run": run, "status": "pending",
        "admission": ADMISSION_PENDING, "executor": executor,
        "pack": pack, "pack_digest": pinned,
        "independence": BRICK_INDEPENDENCE,
        "parent": parent or None,
        "isolation": isolation, "bound": bound,
        "done": done,
    }
    sections = [("Goal", goal), ("Context", _context(parent, artifacts))]
    if details:
        sections.append(("Details", details))
    sections.append((REPORT_SECTION, ""))
    text = _render_ticket(fields, sections)
    if inherit is not None:
        for field in ("root_generation", "cut_generation"):
            text = _set_frontmatter_field(text, field, inherit[field])
        text = _set_frontmatter_field(
            text, "assignment_seal", assignment_digest(ticket_id, text),
        )
    issued = _issue_ticket(run, ticket_id, text, _lock_held=True)
    if "error" in issued:
        return None, issued
    return ticket_id, None


def _sealed_root(run: str, ticket_id: str):
    """Open, validate, and seal one parentless brick's own generation."""

    stamped = _stamp_generation()([run, ticket_id])
    if "error" in stamped:
        return stamped
    validated = _cmd_draft_validate([run, ticket_id])
    if "error" in validated:
        return validated
    sealed = _cmd_seal([
        run, ticket_id, "--cut-generation",
        validated["draft_validation"]["cut_generation"],
    ])
    return sealed if "error" in sealed else None


def _launched(run: str, ticket_id: str, bound: str, host, workspace):
    """Open the attempt with an absolute lease, establish, and emit."""

    minutes, _kind = parse_bound(bound)
    lease = (datetime.now(timezone.utc) + timedelta(minutes=minutes)).strftime(
        UTC_STAMP
    )
    arguments = [
        run, ticket_id, "--by", ticket_id,
        "--dispatch-id", f"{ticket_id}:d1", "--lease-expires-at", lease,
    ]
    if workspace is not None:
        arguments.extend(("--workspace", workspace))
    if host is not None:
        arguments.extend(("--host", host))
    return _dispatch_facade()(arguments)


def _cmd_brick(rest, *, judge: bool):
    """Mint, seal, open, establish, and emit one brick's launch."""

    usage = JUDGE_USAGE if judge else DO_USAGE
    args = list(rest)
    pack = _extract_flag(args, "--pack")
    goal_file = _extract_flag(args, "--goal-file")
    details_file = _extract_flag(args, "--details-file")
    parent = _extract_flag(args, "--parent")
    done = _extract_flag(args, "--done")
    isolation = _extract_flag(args, "--isolation")
    bound = _extract_flag(args, "--bound") or NEW_DEFAULT_BOUND
    host = _extract_flag(args, "--host")
    workspace = _extract_flag(args, "--workspace")
    artifacts = _extract_all(args, "--artifacts")
    stray = next((arg for arg in args if arg.startswith("-")), None)
    if stray is not None:
        return {"error": f"{'judge' if judge else 'do'} does not accept {stray}. usage: {usage}"}
    if len(args) != 1 or not pack or not goal_file:
        return {"error": f"usage: {usage}"}
    run = args[0]
    named = [("run id", run)] + ([("ticket id", parent)] if parent else [])
    for kind, value in named:
        invalid = _segment_error(kind, value)
        if invalid is not None:
            return invalid
    if isolation is not None and isolation.strip() not in ISOLATION_VALUES:
        return {"error": f"--isolation '{isolation}' is not one of {list(ISOLATION_VALUES)}"}
    if done is not None:
        defects = done_defects(done)
        if defects:
            return {"error": "--done is off contract: " + "; ".join(defects)}
    goal, failure = _read_utf8(goal_file, "goal file")
    if failure is not None:
        return failure
    if not goal.strip():
        return {"error": f"goal file {goal_file} is empty; Goal is one observable end result"}
    details = None
    if details_file is not None:
        details, failure = _read_utf8(details_file, "details file")
        if failure is not None:
            return failure
    lines = []
    if judge:
        lines, failure = _artifact_lines(artifacts)
        if failure is not None:
            return failure
    elif artifacts:
        return {"error": f"--artifacts belongs to judge. usage: {DO_USAGE}"}
    run_dir, failure = _run_dir(run)
    if failure is not None:
        return failure
    # The one lock that decides anything two callers could disagree about:
    # which id this brick takes. Everything after it is per-ticket work whose
    # own door takes the lock for itself.
    with _run_lock(run):
        ticket_id, failure = _minted(
            run, run_dir,
            executor=JUDGE_EXECUTOR if judge else DO_EXECUTOR,
            pack=pack, goal=goal.strip(), details=(details or "").strip() or None,
            parent=parent, done=done, isolation=isolation, bound=bound,
            artifacts=lines,
        )
    if failure is not None:
        return failure
    if not parent:
        refusal = _sealed_root(run, ticket_id)
        if refusal is not None:
            return {**refusal, "id": ticket_id}
    launched = _launched(run, ticket_id, bound, host, workspace)
    if "error" in launched:
        return {**launched, "id": ticket_id}
    return {"judge" if judge else "do": {
        "run": run, "id": ticket_id, "parent": parent,
        "path": str(run_dir / f"{ticket_id}.md"),
        **launched,
    }}


def _cmd_do(rest):
    return _cmd_brick(rest, judge=False)


def _cmd_judge(rest):
    return _cmd_brick(rest, judge=True)


__all__ = (
    "ARTIFACT_KINDS", "BRICK_INDEPENDENCE", "DO_EXECUTOR", "DO_USAGE",
    "JUDGE_EXECUTOR", "JUDGE_USAGE", "_cmd_brick", "_cmd_do", "_cmd_judge",
)
