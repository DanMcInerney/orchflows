"""The two commands that open and close one assignment generation.

`tickets_generations` is the algebra -- what a draft is, what validates it,
what a seal writes.  This is the pair of subcommands that run it against
the sink: `draft-validate` persists one content-addressed receipt, and
`seal` compare-and-swaps exactly that receipt's draft onto the run.

They live beside the algebra rather than inside it because that module is
at its source ceiling, and because a seal does two things the algebra never
does: it writes, and it repairs what its own write invalidated -- the
admission receipts of members already promoted under the previous
generation.
"""

from __future__ import annotations

import json
from pathlib import Path

if __package__:
    from .tickets_admission import refresh_admissions
    from .tickets_format import _parse_frontmatter, canonical_json
    from .tickets_generations import (
        GENERATION_RE, GenerationError, _cut_members, draft_snapshot,
        generation_ordinal, seal_assignments, validate_draft,
    )
    from .tickets_transitions import CLAIMED, stamp
    from .tickets_admission import (
        binding_findings, dependency_order_findings,
    )
    from .tickets_generations import correction_decision
else:  # pragma: no cover - direct/installed flat script path
    from tickets_admission import refresh_admissions
    from tickets_format import _parse_frontmatter, canonical_json
    _generations = __import__("tickets_generations")
    GENERATION_RE = _generations.GENERATION_RE
    GenerationError = _generations.GenerationError
    _cut_members = _generations._cut_members
    draft_snapshot = _generations.draft_snapshot
    generation_ordinal = _generations.generation_ordinal
    seal_assignments = _generations.seal_assignments
    validate_draft = _generations.validate_draft
    correction_decision = _generations.correction_decision
    from tickets_transitions import CLAIMED, stamp
    from tickets_admission import (
        binding_findings, dependency_order_findings,
    )


def _store_bindings():
    if __package__:
        from .tickets_store import NO_SINK_ERROR, _run_lock, _runs_root, _segment_error, _tickets_root, _write_text_atomically
    else:
        from tickets_store import NO_SINK_ERROR, _run_lock, _runs_root, _segment_error, _tickets_root, _write_text_atomically
    return NO_SINK_ERROR, _run_lock, _runs_root, _segment_error, _tickets_root, _write_text_atomically


def _extract(args: list, flag: str):
    if flag not in args:
        return None
    index = args.index(flag)
    if index + 1 >= len(args):
        del args[index]
        return None
    value = args[index + 1]
    del args[index:index + 2]
    return value


def _snapshot(run: str):
    NO_SINK_ERROR, _, _, _, tickets_root, _ = _store_bindings()
    root = tickets_root()
    if root is None:
        raise GenerationError(NO_SINK_ERROR)
    run_dir = root / run
    values = {}
    for path in sorted(run_dir.glob("*.md")):
        values[path.stem] = path.read_text(encoding="utf-8")
    return run_dir, values


def _generation_dir(run: str) -> Path:
    NO_SINK_ERROR, _, runs_root, _, _, _ = _store_bindings()
    root = runs_root()
    if root is None:
        raise GenerationError(NO_SINK_ERROR)
    return root / run / "generations"


def _state_path(run: str, cut_generation: str, state: str) -> Path:
    match = GENERATION_RE.fullmatch(cut_generation)
    if match is None or match.group(1) != "cut":
        raise GenerationError("cut generation identity is malformed")
    return _generation_dir(run) / f"{match.group(4)}.{state}.json"


def _validated_documents(run: str) -> list:
    documents = []
    directory = _generation_dir(run)
    for path in sorted(directory.glob("*.validated.json")) if directory.is_dir() else []:
        try:
            value = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, UnicodeDecodeError, ValueError, json.JSONDecodeError):
            continue
        if isinstance(value, dict) and isinstance(value.get("draft"), dict):
            documents.append(value)
    return documents


def _next_draft(run: str, root_id: str, snapshot: dict) -> dict:
    documents = _validated_documents(run)
    ranked = []
    for document in documents:
        prior = document["draft"]
        try:
            identity = str(prior.get("cut_generation") or "")
            match = GENERATION_RE.fullmatch(identity)
            if match is not None and match.group(2) == root_id:
                ranked.append((generation_ordinal(identity, "cut"), prior))
        except GenerationError:
            continue
    if not ranked:
        return draft_snapshot(root_id, snapshot, 1)
    highest, latest = max(ranked, key=lambda item: item[0])
    candidate = draft_snapshot(root_id, snapshot, highest)
    return latest if candidate == latest else draft_snapshot(root_id, snapshot, highest + 1)


def _draft_findings(root_id: str, snapshot: dict) -> list:
    # A claimed root is an allowed grading vantage; a claimed member is not.
    positions = frozenset(stamp("draft-validate").draft_statuses)
    findings = []
    for ticket_id in [root_id, *_cut_members(root_id, snapshot)]:
        data = _parse_frontmatter(snapshot[ticket_id])
        status = str(data.get("status") or "")
        explicit = "root_generation" in data
        if not explicit:
            findings.append({"code": "generation-missing", "field": "root_generation", "ticket": ticket_id})
        if status not in (positions | {CLAIMED} if ticket_id == root_id else positions):
            findings.append({"code": "draft-status", "field": "status", "ticket": ticket_id})
        findings.extend(binding_findings(ticket_id, data))
        findings.extend(dependency_order_findings(ticket_id, data))
    return findings


def _failure_path(run: str, root_id: str) -> Path:
    return _generation_dir(run) / f"{root_id}.failures.json"


def _record_failure(run: str, root_id: str, findings: list, write_atomically) -> dict:
    path = _failure_path(run, root_id)
    history = []
    if path.is_file():
        value = json.loads(path.read_text(encoding="utf-8-sig"))
        history = list(value.get("history") or []) if isinstance(value, dict) else []
    decision = correction_decision(findings, history)
    path.parent.mkdir(parents=True, exist_ok=True)
    write_atomically(path, canonical_json({"history": decision.get("history") or history}) + "\n")
    return decision


def _cmd_draft_validate(rest) -> dict:
    args = list(rest)
    if len(args) != 2:
        return {"error": "usage: draft-validate <run> <root-id>"}
    run, root_id = args
    _, _, _, segment_error, _, _ = _store_bindings()
    for kind, value in (("run id", run), ("ticket id", root_id)):
        refusal = segment_error(kind, value)
        if refusal is not None: return refusal
    _, run_lock, _, _, _, write_atomically = _store_bindings()
    try:
        with run_lock(run):
            _, snapshot = _snapshot(run)
            if root_id not in snapshot:
                return {"error": f"root ticket not found in exact snapshot: {root_id}"}
            findings = _draft_findings(root_id, snapshot)
            if findings:
                decision = _record_failure(run, root_id, findings, write_atomically)
                return {"error": "draft validation failed", "findings": findings, "correction": decision}
            draft = _next_draft(run, root_id, snapshot)
            receipt = validate_draft(root_id, snapshot, draft)
            document = {"draft": draft, "receipt": receipt}
            path = _state_path(run, draft["cut_generation"], "validated")
            path.parent.mkdir(parents=True, exist_ok=True)
            encoded = canonical_json(document) + "\n"
            if path.exists() and path.read_text(encoding="utf-8") != encoded:
                return {"error": "content-addressed validation receipt collision"}
            if not path.exists():
                write_atomically(path, encoded)
    except (OSError, UnicodeDecodeError, GenerationError) as error:
        return {"error": str(error)}
    return {"draft_validation": {**receipt, "path": str(path)}}


def _cmd_seal(rest) -> dict:
    args = list(rest)
    cut_generation = _extract(args, "--cut-generation")
    if len(args) != 2 or cut_generation is None:
        return {"error": "usage: seal <run> <root-id> --cut-generation <identity>"}
    run, root_id = args
    _, run_lock, _, segment_error, _, write_atomically = _store_bindings()
    for kind, value in (("run id", run), ("ticket id", root_id)):
        refusal = segment_error(kind, value)
        if refusal is not None: return refusal
    refreshed = []
    try:
        with run_lock(run):
            run_dir, snapshot = _snapshot(run)
            validated_path = _state_path(run, cut_generation, "validated")
            if not validated_path.is_file():
                return {"error": "seal refused: no validation receipt for requested cut generation"}
            document = json.loads(validated_path.read_text(encoding="utf-8-sig"))
            draft, receipt = document["draft"], document["receipt"]
            if draft.get("cut_generation") != cut_generation:
                return {"error": "seal refused: validation receipt names another cut generation"}
            findings = _draft_findings(root_id, snapshot)
            if findings:
                return {"error": "seal refused: snapshot is not a mutable assignment draft", "findings": findings}
            sealed = seal_assignments(root_id, snapshot, draft, receipt)
            prior = dict(snapshot)
            try:
                for ticket_id, text in sealed.items():
                    if text != snapshot[ticket_id]:
                        write_atomically(run_dir / f"{ticket_id}.md", text)
                sealed_path = _state_path(run, cut_generation, "sealed")
                sealed_path.parent.mkdir(parents=True, exist_ok=True)
                member_ids = [item["id"] for item in draft.get("assignments") or []]
                seals = {
                    ticket_id: _parse_frontmatter(sealed[ticket_id]).get("assignment_seal")
                    for ticket_id in [root_id, *member_ids]
                }
                record = {"assignment_seals": seals, "cut_generation": draft["cut_generation"], "receipt": receipt, "root_generation": draft["root_generation"], "root_id": root_id, "state": "sealed"}
                write_atomically(sealed_path, canonical_json(record) + "\n")
                # The sealed record is on disk, so the grader can resolve it:
                # every member this seal just re-generationed is re-graded and
                # its receipt rewritten inside this same transaction. A member
                # promoted under the previous generation otherwise holds a
                # receipt only the previous generation computes, and its next
                # dispatch is refused for staleness the seal itself introduced.
                refreshed = refresh_admissions(
                    run, run_dir, sealed, write_atomically,
                )
            except OSError:
                for ticket_id, text in prior.items():
                    write_atomically(run_dir / f"{ticket_id}.md", text)
                raise
    except (OSError, UnicodeDecodeError, ValueError, KeyError, GenerationError, json.JSONDecodeError) as error:
        return {"error": str(error)}
    return {"assignment_seal": {"cut_generation": cut_generation, "root_generation": draft["root_generation"], "state": "sealed", "path": str(sealed_path), "refreshed_admissions": refreshed}}


__all__ = ("_cmd_draft_validate", "_cmd_seal")
