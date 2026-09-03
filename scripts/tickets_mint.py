"""The two minting commands: one command opens, seals, and launches one child.

`do` makes an artifact and `judge` reads finished ones. Both fold what a
caller used to sequence by hand -- `new`, `stamp-generation`,
`draft-validate`, `seal`, `ready`, `dispatch` -- into one call, because every
one of those steps is mechanical and none of them is a decision. Four of
those six retired as commands once this fold was the only caller walking
them; their functions are unchanged and each step below is the same one the
granular command called, so this is one protocol rather than a second.

Two facts make the fold safe. The id is minted under the run lock, so two
concurrent callers under one parent cannot choose one id. And a child is
sealed through its parent rather than named in a sealed cut: the cut that
sealed the parent closed before the child existed, so the child inherits the
parent's generations, self-seals its own assignment, and admission verifies
the parent's seal in the sealed record -- the reading a landing's repair
round already needed, generalized here to every runtime child.

A parentless callable is its own root and takes the full generation
lifecycle: it is stamped, its draft validated, and its own one-member cut
sealed, here rather than by a caller.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

if __package__:
    from .tickets_adapters import ADAPTER_REGISTRY, AdapterError, adapter_id
    from .tickets_admission import ADMISSION_PENDING
    from .tickets_bound import parse_bound
    from .tickets_format import (
        ARTIFACT_CLAUSE, MAKES_FIELD, PLANNING_KINDS,
        REPORT_SECTION, _extract_all, _extract_flag,
        _parse_frontmatter, _read_utf8, _set_frontmatter_field, dequote,
        done_defects, next_mint_id,
    )
    from .tickets_generations import assignment_digest
    from .tickets_issue import (
        ISOLATION_VALUES, NEW_DEFAULT_BOUND, _applied_skill_refusal,
        _issue_ticket, pinned_items, pinned_pack_digest,
    )
    from .tickets_issue_render import _render_ticket
    from .tickets_seal import _cmd_draft_validate, _cmd_seal
    from .tickets_store import (
        NO_SINK_ERROR, UTC_STAMP, _run_lock, _segment_error, _tickets_root,
    )
else:  # pragma: no cover - direct/installed flat script path
    from tickets_adapters import ADAPTER_REGISTRY, AdapterError, adapter_id
    from tickets_admission import ADMISSION_PENDING
    from tickets_bound import parse_bound
    from tickets_format import (
        ARTIFACT_CLAUSE, MAKES_FIELD, PLANNING_KINDS,
        REPORT_SECTION, _extract_all, _extract_flag,
        _parse_frontmatter, _read_utf8, _set_frontmatter_field, dequote,
        done_defects, next_mint_id,
    )
    from tickets_generations import assignment_digest
    from tickets_issue import (
        ISOLATION_VALUES, NEW_DEFAULT_BOUND, _applied_skill_refusal,
        _issue_ticket, pinned_items, pinned_pack_digest,
    )
    from tickets_issue_render import _render_ticket
    from tickets_seal import _cmd_draft_validate, _cmd_seal
    from tickets_store import (
        NO_SINK_ERROR, UTC_STAMP, _run_lock, _segment_error, _tickets_root,
    )

DO_USAGE = (
    "do <run> --pack P --goal-file F [--details-file D] [--parent ID] "
    "[--sheet S] [--sheet ...] [--skill S] "
    "[--done <canonical-json>] [--makes " + "|".join(PLANNING_KINDS) + "] "
    "[--isolation required|none] [--bound B] "
    "[--workspace <source-tree-to-cut-from>] [--host H]"
)
JUDGE_USAGE = (
    "judge <run> --pack P --goal-file F --artifacts <typed-line> "
    "[--artifacts ...] [--details-file D] [--parent ID] "
    "[--sheet S] [--sheet ...] [--skill S] "
    "[--isolation required|none] [--bound B] "
    "[--workspace <source-tree-to-cut-from>] [--host H]"
)
DO_EXECUTOR = "orch-do"
JUDGE_EXECUTOR = "orch-judge"
ARTIFACT_KINDS = frozenset(
    adapter.artifact_kind for adapter in ADAPTER_REGISTRY.values()
)
# The two library-owned artifact kinds, and the frontmatter field each one
# names. A domain's kinds are the adapter's and carry their identity inside
# the line; these two are the ticket machinery's own, and their identity is
# a generation value it already stamped -- `root:<id>:<n>:sha256:<digest>`
# and `cut:<id>:<n>:sha256:<digest>` -- so the whole line is the value and
# the run itself is what says whether it is real.
GENERATION_KINDS = {"root": "root_generation", "cut": "cut_generation"}
# What a judge's `--artifacts` may name. Kept apart from `ARTIFACT_KINDS`,
# which is the adapters' set and is read as such by the launch's line forms.
JUDGE_KINDS = ARTIFACT_KINDS | frozenset(GENERATION_KINDS)
# The `parent` clause on the child's own Context: the one line that says
# whose call this ticket is, in the section a reader of the ticket alone
# would otherwise have to infer it from the id.
PARENT_CLAUSE = "- parent: "
# The adapter whose workspace *is* lanes -- "isolation is a run-scoped lane
# directory" -- and so the one whose craft prices a lane at one
# independently answerable sub-question. Selected off the pack's own
# declared adapter rather than off a pack name, because machinery stays
# domain-blind (tools/validate_support/structure.py's domain-blindness
# check); a pack that adopts this adapter inherits the door with it.
LANE_ADAPTER = "evidence-store"
# The marker that adapter's craft root entry states the form of. The door
# counts it; the craft is where the form is said, and nothing here restates
# it.
_SUBQUESTION_MARKER = "sub-questions"
_HEADING_LINE = re.compile(r"^ {0,3}#{1,6}\s")
_NUMBERED_ITEM = re.compile(r"^\s*\d+[.)]\s+\S")


def subquestion_count(goal: str) -> int:
    """How many sub-questions one goal declares.

    The form counted is stated once, in the `### root` entry of the craft
    belonging to the pack whose adapter is `LANE_ADAPTER`, and nowhere
    here: a reader who needs it resolves that craft through `packs.py
    cells <digest>`. What is this module's own is how the count is taken
    over a goal that departs from that form -- every marked section's
    items, because a goal declaring its coverage twice declares both
    halves of it, and any numbered line inside one, nesting included, so
    an off-form goal over-counts and refuses rather than being
    disambiguated here.
    """

    count, inside = 0, False
    for line in goal.splitlines():
        if _HEADING_LINE.match(line):
            inside = _SUBQUESTION_MARKER in line.lower()
        elif inside and _NUMBERED_ITEM.match(line):
            count += 1
    return count


def _one_lane(pack, parent, goal: str, goal_file):
    """The refusal for a parentless lane-adapter `do` carrying several lanes.

    A worker-lane `do` is one child answering one question. The research
    craft's cut rule already priced a lane at one independently answerable
    sub-question; run 20260902T140000Z-hn-workflows minted a single `do`
    over five of them and got back one source called a full packet. The
    door stands here, ahead of the run directory, so a refusal leaves the
    sink exactly as it found it.

    A pack that will not resolve passes: `pinned_pack_digest` owns that
    refusal and names the pack, and two refusals for one cause would make
    the caller fix the wrong thing first.
    """

    if parent:
        return None
    try:
        if adapter_id(dequote(pack)) != LANE_ADAPTER:
            return None
    except AdapterError:
        return None
    lanes = subquestion_count(goal)
    if lanes < 2:
        return None
    return {"error": (
        f"goal file {goal_file}: {lanes} sub-questions are {lanes} lanes, "
        "per the research craft's cut rule; open a frame with `--shape` and "
        "mint one `do` per sub-question under it"
    )}


def _dispatch_facade():
    if __package__:
        from .tickets_dispatch_facade import _cmd_dispatch
    else:  # pragma: no cover - direct/installed flat script path
        from tickets_dispatch_facade import _cmd_dispatch
    return _cmd_dispatch


def _stamp_generation():
    if __package__:
        from .tickets_stamp_generation import _cmd_stamp_generation
    else:  # pragma: no cover - direct/installed flat script path
        from tickets_stamp_generation import _cmd_stamp_generation
    return _cmd_stamp_generation


def _run_dir(run: str):
    """`(run_dir, refusal)` for the run this callable is minted into."""

    root = _tickets_root()
    if root is None:
        return None, {"error": NO_SINK_ERROR}
    return root / run, None


def _issued_ids(run_dir) -> list:
    """Every id already issued in the run, read under the caller's lock.

    Read inside the lock and nowhere else. Two callers that listed the run
    before taking it both saw the same highest ordinal and both chose the id
    after it, and the second one lost its whole callable to the exclusive
    create -- which is the failure the lock is held to prevent, moved one
    line earlier rather than removed.
    """

    return (
        sorted(path.stem for path in run_dir.glob("*.md"))
        if run_dir.is_dir() else []
    )


def _generation_values(run_dir, field: str) -> list:
    """Every value of one generation field carried by a ticket in the run.

    Read off the tickets rather than recomputed: the value spells the id and
    ordinal of the stamp that minted it, so the run's own files are the only
    place it exists, and a caller that re-derived one would be authoring a
    generation instead of naming one.
    """

    values = set()
    if run_dir is not None and run_dir.is_dir():
        for path in sorted(run_dir.glob("*.md")):
            text, failure = _read_utf8(path, "ticket")
            if failure is not None:
                continue
            value = str(_parse_frontmatter(text).get(field) or "").strip()
            if value:
                values.add(value)
    return sorted(values)


def _artifact_lines(values, run_dir=None) -> tuple:
    """`(lines, refusal)` for the typed artifact identities a judge reads.

    One flag repeated, or one value carrying several lines: a caller relaying
    two children's returned lines has them as two lines already, and asking
    it to re-join them into one flag value is where a paraphrase gets made.

    A `root:` or `cut:` line is checked against `run_dir` as well as typed:
    those two identities live in the run's own frontmatter, so an unknown one
    is refused with the run's real values rather than accepted and handed to
    a judge that has nothing to open.
    """

    lines = []
    for value in values:
        lines.extend(part.strip() for part in str(value).splitlines() if part.strip())
    if not lines:
        return None, {"error": f"judge requires --artifacts. usage: {JUDGE_USAGE}"}
    known = {}
    for line in lines:
        kind = line.split(":", 1)[0]
        if kind not in JUDGE_KINDS or not line[len(kind) + 1:].strip():
            return None, {"error": (
                f"artifact '{line}' is not one typed identity; expected "
                + ", ".join(sorted(f"{name}:<identity>" for name in JUDGE_KINDS))
            )}
        field = GENERATION_KINDS.get(kind)
        if field is None:
            continue
        if field not in known:
            known[field] = _generation_values(run_dir, field)
        if line not in known[field]:
            return None, {"error": (
                f"artifact '{line}' names no {field} carried by any ticket in "
                "this run; its known " + kind + " identities are: "
                + (", ".join(known[field]) or "(none)")
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


def _mint(run: str, run_dir, parent, fields: dict, sections: list):
    """`(ticket_id, refusal)` -- one runtime child's id, seal, and write.

    All of what the runtime minting commands share, and the reason they can
    share it: the id is read out of the run directory under the caller's
    own hold of the run lock, and a child hangs its admission on its
    parent's seal rather than on a cut that closed before it existed -- it
    inherits the parent's two generations and self-seals its own bytes.
    What each command owns is only which fields and sections its ticket
    carries, which is why those arrive as arguments and nothing here reads
    them.

    `frame-open` is the third caller. A frame is not a callable -- it binds
    no executor and stamps no pack -- and it is minted exactly this way,
    because being a runtime child of a sealed parent is the one thing the
    two kinds have wholly in common.
    """

    ticket_id = next_mint_id(parent, _issued_ids(run_dir))
    inherit = None
    if parent:
        inherit, refusal = _sealed_parent(run_dir, parent)
        if refusal is not None:
            return None, refusal
    text = _render_ticket({"id": ticket_id, **fields}, sections)
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


def _minted(run: str, run_dir, *, executor, pack, goal, details, parent,
            done, isolation, bound, artifacts, makes=None, sheets=(), skill=None):
    """`(ticket_id, refusal)` -- one callable's fields, minted through `_mint`."""

    pinned, refusal = pinned_pack_digest(pack)
    if refusal is not None:
        return None, refusal
    stamped, refusal = pinned_items(sheets, skill, pack=pack)
    if refusal is not None:
        return None, refusal
    fields = {
        "run": run, "status": ADMISSION_PENDING,
        "admission": ADMISSION_PENDING, "executor": executor,
        "pack": pack, "pack_digest": pinned, **stamped,
        "parent": parent or None,
        "isolation": isolation, "bound": bound,
        "done": done, MAKES_FIELD: makes,
    }
    sections = [("Goal", goal), ("Context", _context(parent, artifacts))]
    if details:
        sections.append(("Details", details))
    sections.append((REPORT_SECTION, ""))
    return _mint(run, run_dir, parent, fields, sections)


def _sealed_root(run: str, ticket_id: str):
    """Open, validate, and seal one parentless callable's own generation."""

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


def _cmd_callable(rest, *, judge: bool):
    """Mint, seal, open, establish, and emit one callable's launch."""

    usage = JUDGE_USAGE if judge else DO_USAGE
    args = list(rest)
    pack = _extract_flag(args, "--pack")
    goal_file = _extract_flag(args, "--goal-file")
    details_file = _extract_flag(args, "--details-file")
    parent = _extract_flag(args, "--parent")
    done = _extract_flag(args, "--done")
    makes = _extract_flag(args, "--makes")
    isolation = _extract_flag(args, "--isolation")
    bound = _extract_flag(args, "--bound") or NEW_DEFAULT_BOUND
    host = _extract_flag(args, "--host")
    workspace = _extract_flag(args, "--workspace")
    artifacts = _extract_all(args, "--artifacts")
    sheets = _extract_all(args, "--sheet")
    skill = _extract_flag(args, "--skill")
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
    refusal = _applied_skill_refusal(
        skill, JUDGE_EXECUTOR if judge else DO_EXECUTOR,
    )
    if refusal is not None:
        return refusal
    # A judge is handed finished artifacts and names their kind on its
    # Context; only a `do` chooses what it makes, and only when the pack's
    # adapter does not already say.
    if makes is not None:
        if judge:
            return {"error": f"--makes belongs to do. usage: {JUDGE_USAGE}"}
        makes = makes.strip()
        if makes not in PLANNING_KINDS:
            return {"error": f"--makes '{makes}' is not one of {list(PLANNING_KINDS)}"}
    if done is not None:
        defects = done_defects(done)
        if defects:
            return {"error": "--done is off contract: " + "; ".join(defects)}
    goal, failure = _read_utf8(goal_file, "goal file")
    if failure is not None:
        return failure
    if not goal.strip():
        return {"error": f"goal file {goal_file} is empty; Goal is one observable end result"}
    if not judge:
        crowded = _one_lane(pack, parent, goal, goal_file)
        if crowded is not None:
            return crowded
    details = None
    if details_file is not None:
        details, failure = _read_utf8(details_file, "details file")
        if failure is not None:
            return failure
    # The run directory is resolved ahead of the artifact check rather than
    # after it: a `root:`/`cut:` line names a generation this run stamped,
    # so the run's own tickets are what the check reads.
    run_dir, failure = _run_dir(run)
    if failure is not None:
        return failure
    lines = []
    if judge:
        lines, failure = _artifact_lines(artifacts, run_dir)
        if failure is not None:
            return failure
        # One judge, one kind: the kind selects the craft's `## Lens` entry
        # the judge reads its criteria from, and a call handed two kinds
        # has no one entry to be judged against. Two calls, not one.
        kinds = sorted({line.split(":", 1)[0] for line in lines})
        if len(kinds) > 1:
            return {"error": (
                "judge reads one artifact kind, and --artifacts names "
                + ", ".join(f"'{kind}'" for kind in kinds)
                + f"; mint one judge per kind. usage: {JUDGE_USAGE}"
            )}
    elif artifacts:
        return {"error": f"--artifacts belongs to judge. usage: {DO_USAGE}"}
    # The one lock that decides anything two callers could disagree about:
    # which id this callable takes. Everything after it is per-ticket work
    # whose own command takes the lock for itself.
    with _run_lock(run):
        ticket_id, failure = _minted(
            run, run_dir,
            executor=JUDGE_EXECUTOR if judge else DO_EXECUTOR,
            pack=pack, goal=goal.strip(), details=(details or "").strip() or None,
            parent=parent, done=done, isolation=isolation, bound=bound,
            artifacts=lines, makes=makes, sheets=sheets, skill=skill,
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
    return _cmd_callable(rest, judge=False)


def _cmd_judge(rest):
    return _cmd_callable(rest, judge=True)


__all__ = (
    "ARTIFACT_KINDS", "DO_EXECUTOR", "DO_USAGE",
    "JUDGE_EXECUTOR", "JUDGE_USAGE", "LANE_ADAPTER", "_cmd_callable",
    "_cmd_do", "_cmd_judge", "_launched", "_mint", "_run_dir", "_sealed_root",
    "subquestion_count",
)
