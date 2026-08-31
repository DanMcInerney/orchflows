"""Pure grading for one sealed ticket assignment."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

if __package__:
    from .tickets_registry import EXECUTOR_REGISTRY, executor_refusal, executor_registered
    from .tickets_adapters import AdapterError, adapter_spec, pack_digest
    from .tickets_format import (
        DELIVERED_STATE, RESULT_BEARING_STATES, ROOT_EXECUTOR,
        SCRIPT_EXECUTOR_PREFIX, adapter_id, canonical_json, declared_parent,
        dequote, is_loop_stub, is_review_stage_id, round_parent, _executor_of,
        _parse_frontmatter, _set_frontmatter_field,
    )
else:
    from tickets_registry import EXECUTOR_REGISTRY, executor_refusal, executor_registered
    from tickets_adapters import AdapterError, adapter_spec, pack_digest
    from tickets_format import (
        DELIVERED_STATE, RESULT_BEARING_STATES, ROOT_EXECUTOR,
        SCRIPT_EXECUTOR_PREFIX, adapter_id, canonical_json, declared_parent,
        dequote, is_loop_stub, is_review_stage_id, round_parent, _executor_of,
        _parse_frontmatter, _set_frontmatter_field,
    )

ADMISSION_PENDING = "pending"
# Re-exported, never respelled: `tickets_format` owns which terminal states
# carry a Result, because `tickets_readiness` answers the same question for
# the reader and the two spellings had already drifted.
_RECEIPT_RE = re.compile(r"^([a-z][a-z0-9-]*):sha256:([0-9a-f]{64})$")


def is_receipt(value) -> bool:
    return bool(_RECEIPT_RE.fullmatch(str(value or "").strip()))


def finding(code: str, field: str, detail: str) -> dict:
    return {"code": code, "field": field, "detail": detail}


def _ordered(findings) -> list:
    rows = {
        (str(item.get("code") or ""), str(item.get("field") or ""), str(item.get("detail") or ""))
        for item in findings
    }
    return [finding(*row) for row in sorted(rows)]


def adapter_resolution(pack):
    """Resolve one declared pack adapter as data, never as a traceback."""

    if not str(pack or "").strip():
        return None, None
    try:
        return adapter_id(pack), None
    except AdapterError as error:
        return None, finding(error.code, "pack", error.detail)


def pinned_digest_finding(pack: str, pinned: str):
    """Refuse a stamped pack whose content is no longer what was sealed.

    The seal is the lockfile: it records the pack's digest at slice time,
    and every later door compares the resolved pack against it. Without
    this the ticket carried the pack's *name*, and a name resolves to
    whatever bytes happen to be nearest -- which is how a project ring
    would have shadowed the pack a run was admitted under.
    """

    try:
        current = pack_digest(pack)
    except AdapterError as error:
        return finding(error.code, "pack_digest", error.detail)
    if current == pinned:
        return None
    return finding(
        "pack-digest-mismatch", "pack_digest",
        f"pack '{pack}' resolves to {current}, but this sealed assignment "
        f"pinned {pinned}: the pack changed under the seal, or another ring "
        "now shadows it. Restore the pinned pack, or open a new generation "
        "(tickets.py stamp-generation) against the pack you mean to run.",
    )


def binding_findings(ticket_id: str, data: dict) -> list:
    """Grade script resolution and adapter-owned operational isolation."""
    findings = []
    executor = _executor_of(data)
    pack = str(data.get("pack") or "").strip()
    if (
        executor
        and not executor.startswith(SCRIPT_EXECUTOR_PREFIX)
        and not executor_registered(executor)
    ):
        findings.append(finding("executor-unregistered", "executor", executor_refusal(executor)))
    elif EXECUTOR_REGISTRY.get(executor, {}).get("requires_pack") and not pack:
        findings.append(finding(
            "executor-pack-required", "pack",
            f"{executor} consumes resolved pack cells and requires a stamped pack",
        ))
    unbound = (
        executor.startswith(SCRIPT_EXECUTOR_PREFIX)
        or executor == ROOT_EXECUTOR
        or is_review_stage_id(ticket_id)
    )
    if executor.startswith(SCRIPT_EXECUTOR_PREFIX):
        target = executor[len(SCRIPT_EXECUTOR_PREFIX):].strip()
        if not (Path(__file__).resolve().parents[1] / target).is_file():
            findings.append(finding(
                "script-executor-unresolved", "executor",
                f"executor names script '{target or '<missing>'}', which does not resolve in the tree",
            ))
    if pack and not unbound:
        adapter, adapter_failure = adapter_resolution(pack)
        if adapter_failure is not None:
            findings.append(adapter_failure)
    pinned = str(data.get("pack_digest") or "").strip()
    if pack and pinned:
        mismatch = pinned_digest_finding(pack, pinned)
        if mismatch is not None:
            findings.append(mismatch)
    elif pinned:
        findings.append(finding(
            "pack-digest-unbound", "pack_digest",
            "a pinned pack digest without a stamped pack names nothing",
        ))
    return findings


def graph_descendants(ticket_id: str, siblings) -> list:
    """The executor-result members one ticket owns, gates and checks excluded."""
    return [
        identifier for identifier in dict(siblings or {})
        if identifier.startswith(ticket_id + ".")
        and not is_review_stage_id(identifier)
    ]


def loop_round_stub(ticket_id: str, siblings) -> str | None:
    """The live loop stub whose own machinery minted this id, or ``None``.

    `loop-arm` writes `<stub>.iter.NN` from the stub's frozen goal, and the
    `check` done form mints `<stub>.iter.NN.done` beside a round to judge it.
    Both appear only after the cut that sealed the stub, so neither is ever a
    member of the sealed assignment set and neither is a member the stub was
    decomposed into -- the two readings that refused the whole loop lane the
    first time it was driven through the dispatch trunk.

    `tickets_format.round_parent` owns the grammar; what is added here is the
    marker, because the same grammar spells a landing's `<id>.repair.NN`
    rounds and those descend from an ordinary ticket, not from a loop.
    """
    stub_id = round_parent(ticket_id)
    if stub_id is None:
        return None
    text = dict(siblings or {}).get(stub_id)
    if text is None or not is_loop_stub(_parse_frontmatter(text)):
        return None
    return stub_id


def post_seal_parent(ticket_id: str, data: dict, siblings) -> str | None:
    """The sealed ticket whose machinery minted this one after the cut, or None.

    Two spellings of one fact, because the second arrived first. A brick names
    its caller outright in `parent`; a round names its parent through the id
    grammar `round_parent` owns, and only where that parent is a loop stub or
    a landing's own ticket. Both were minted after the cut that sealed the
    parent, so neither can be a member of it, and both bind their admission
    through the parent instead.
    """
    declared = declared_parent(data)
    if declared and declared in dict(siblings or {}):
        return declared
    return loop_round_stub(ticket_id, siblings)


def graph_closed(ticket_id: str, siblings, *evidence) -> bool:
    """Whether a decomposed root yet owes ``graph_findings`` a member count.

    Members close the shape wherever it is graded.  Each door adds the
    evidence it alone owns that the cut is final -- a delivered status, a
    draft's named membership, a carried cut identity.  A sealed root with
    none of them is still at the graph bootstrap door: it is dispatched to
    the decomposer precisely so that its members can come to exist, and
    grading the count there would refuse every run at its first dispatch.
    """
    return bool(graph_descendants(ticket_id, siblings)) or any(bool(item) for item in evidence)


def graph_findings(ticket_id: str, data: dict, siblings: dict, *, complete=False) -> list:
    """Grade the graph shape owned by one ticket without consulting prose.

    ``orch-slice`` is the only root executor that may own executor-result
    members.  A root marked as an ordinary checker would leave the graph's
    authority with a caller, so it is refused at every admission door.  The
    member-count checks are deferred until a generation is being validated:
    the first root ticket is necessarily issued before its members exist.

    Every post-seal child is dropped before the count: an armed
    `<stub>.iter.NN` and a brick's `<parent>.<n>` are both id-descendants of
    the ticket that minted them, and reading either as a member would refuse
    the parent for owning what its own machinery is the licence to mint. An
    author-written child that names no parent and matches no round grammar is
    still refused.
    """
    executor = _executor_of(data)
    siblings = dict(siblings or {})
    descendants = [
        identifier for identifier in graph_descendants(ticket_id, siblings)
        if post_seal_parent(
            identifier, _parse_frontmatter(siblings[identifier]), siblings,
        ) is None
    ]
    findings = []
    if executor == ROOT_EXECUTOR:
        if dequote(data.get("independence")) == "checker":
            findings.append(finding(
                "decomposed-root-checker", "independence",
                "a decomposed root must declare independence=gate",
            ))
        if complete:
            if not descendants:
                findings.append(finding(
                    "graph-no-members", "members",
                    "a decomposed root requires at least two executor-result members",
                ))
            elif len(descendants) == 1:
                findings.append(finding(
                    "graph-one-member", "members",
                    "a decomposed root requires at least two executor-result members",
                ))
    elif descendants:
        findings.append(finding(
            "graph-direct-members", "executor",
            "a non-decomposed root cannot own executor-result members",
        ))
    return findings


def _canonical_json(value) -> bytes:
    return canonical_json(value).encode("utf-8")


def _ordinary_review_target(ticket_id: str, data: dict, dependencies, siblings):
    if ticket_id.endswith(".check") and dependencies == [
        ticket_id[:-len(".check")]
    ]:
        return dependencies[0], None
    if not ticket_id.endswith(".gate.repair"):
        return None
    target_id = ticket_id[:-len(".gate.repair")]
    kind = "repair"
    target_text = siblings.get(target_id)
    checker_text = siblings.get(f"{target_id}.check")
    if target_text is None or checker_text is None:
        return None
    target = _parse_frontmatter(target_text)
    checker = _parse_frontmatter(checker_text)
    if (
        str(target.get("independence") or "checker") != "checker"
        or not str(target.get("checked_by") or "").strip()
        or str(target.get("review_stage") or "") != f"{target_id}.check"
        or str(checker.get("status") or "") != "complete"
        or str(checker.get("review_kind") or "") != "critique"
        or list(checker.get("depends_on") or []) != [target_id]
    ):
        return None
    run = str(target.get("run") or data.get("run") or "")
    if __package__:
        from .tickets_ordinary_review import ordinary_stage_text
    else:
        from tickets_ordinary_review import ordinary_stage_text
    return target_id, ordinary_stage_text(run, target_id, target, kind)


def sealed_parent_target(ticket_id, text, data, siblings, digest):
    """The sealed ticket one lawful post-seal child binds its admission through.

    The sealed cut names the assignments that existed when it was sealed, and
    a runtime child exists only afterwards, so it can never be named there.
    What the seal did name is the parent, and a child is lawful exactly when
    it descends from that parent unaltered: the parent's own
    `root_generation` and `cut_generation`, and a self-seal that still matches
    the child's current bytes.  A child whose bytes moved after it was minted
    fails that last reading and falls through to the sealed-set door, which
    has never named it and refuses it.

    Written for a loop's rounds and generalized to every runtime child by the
    brick doors: `do` and `judge` mint under a sealed parent for the same
    reason `loop-arm` did, and the parentage the id used to imply is now
    declared.
    """
    parent_id = post_seal_parent(ticket_id, data, siblings)
    if parent_id is None:
        return None
    parent = _parse_frontmatter(siblings[parent_id])
    if any(
        str(data.get(field) or "") != str(parent.get(field) or "")
        for field in ("cut_generation", "root_generation")
    ):
        return None
    if str(data.get("assignment_seal") or "") != digest(ticket_id, text):
        return None
    return parent_id


def grade_admission(ticket_id: str, text: str, siblings: dict, context=None) -> dict:
    """Grade one exact sealed snapshot and return its portable receipt."""
    context = dict(context or {})
    siblings = dict(siblings or {})
    data = _parse_frontmatter(text)
    if __package__:
        from .tickets_generations import GENERATION_RE, assignment_digest, seal_findings
    else:
        module = __import__("tickets_generations")
        GENERATION_RE = module.GENERATION_RE
        assignment_digest = module.assignment_digest
        seal_findings = module.seal_findings
    findings = list(seal_findings(ticket_id, text))
    adapter, adapter_failure = adapter_resolution(data.get("pack"))
    if adapter_failure is not None:
        findings.append(adapter_failure)
    # A sealed decomposed root reaches this door before its members are
    # issued; a delivered one has had every member it will ever own.
    delivered = dequote(data.get("status")) == DELIVERED_STATE
    findings.extend(graph_findings(
        ticket_id, data, siblings,
        complete=graph_closed(ticket_id, siblings, delivered),
    ))
    dependencies = [str(value) for value in (data.get("depends_on") or [])]
    for dependency in dependencies:
        if dependency not in siblings:
            findings.append(finding("dependency-dangling", "depends_on", dependency))
        else:
            status = str(_parse_frontmatter(siblings[dependency]).get("status") or "")
            if status not in RESULT_BEARING_STATES:
                findings.append(finding("dependency-incomplete", "depends_on", f"{dependency}:{status or '<missing>'}"))
    findings.extend(binding_findings(ticket_id, data))
    sealed_record = None
    runs_root = context.get("runs_root")
    run = str(data.get("run") or context.get("run") or "")
    cut_generation = str(data.get("cut_generation") or "")
    match = GENERATION_RE.fullmatch(cut_generation)
    if not runs_root or not run or match is None:
        findings.append(finding("seal-state-unavailable", "cut_generation", "admission requires the sealed run-state record"))
    else:
        directory = Path(runs_root) / run / "generations"
        try:
            sealed_record = json.loads((directory / f"{match.group(4)}.sealed.json").read_text(encoding="utf-8-sig"))
            validated = json.loads((directory / f"{match.group(4)}.validated.json").read_text(encoding="utf-8-sig"))
        except (OSError, UnicodeDecodeError, ValueError):
            findings.append(finding("seal-state-missing", "cut_generation", "sealed and validated records must resolve"))
        else:
            root_match = GENERATION_RE.fullmatch(str(data.get("root_generation") or ""))
            expected = {
                "cut_generation": cut_generation,
                "root_generation": str(data.get("root_generation") or ""),
                "root_id": root_match.group(2) if root_match is not None else None,
                "state": "sealed",
            }
            if not isinstance(sealed_record, dict) or any(sealed_record.get(key) != value for key, value in expected.items()):
                findings.append(finding("seal-state-mismatch", "cut_generation", "sealed state names another generation"))
            draft = validated.get("draft") if isinstance(validated, dict) else None
            if not isinstance(draft, dict) or sealed_record.get("receipt") != validated.get("receipt") or draft.get("cut_generation") != cut_generation:
                findings.append(finding("validation-receipt-mismatch", "cut_generation", "sealed state does not bind the validation receipt"))
            sealed_assignments = sealed_record.get("assignment_seals") or {}
            review_target = _ordinary_review_target(
                ticket_id, data, dependencies, siblings,
            )
            sealed_parent = sealed_parent_target(
                ticket_id, text, data, siblings, assignment_digest,
            )
            if review_target is not None:
                target_id, expected_stage = review_target
                target_text = siblings.get(target_id)
                target = _parse_frontmatter(target_text) if target_text is not None else {}
                if sealed_assignments.get(target_id) != target.get("assignment_seal"):
                    findings.append(finding(
                        "sealed-checker-target-mismatch"
                        if ticket_id.endswith(".check")
                        else "sealed-review-target-mismatch",
                        "assignment_seal",
                        "sealed state does not bind the checker target"
                        if ticket_id.endswith(".check")
                        else "sealed state does not bind the ordinary review target",
                    ))
                if expected_stage is not None:
                    if __package__:
                        from .tickets_ordinary_review import ordinary_stage_matches
                    else:
                        from tickets_ordinary_review import ordinary_stage_matches
                if expected_stage is not None and not ordinary_stage_matches(
                    ticket_id, text, expected_stage,
                ):
                    findings.append(finding(
                        "ordinary-review-stage-mismatch", "assignment_seal",
                        "ordinary repair or verification assignment differs from "
                        "the canonical checked-target continuation",
                    ))
            elif sealed_parent is not None:
                parent = _parse_frontmatter(siblings[sealed_parent])
                if sealed_assignments.get(sealed_parent) != parent.get("assignment_seal"):
                    findings.append(finding(
                        "sealed-parent-mismatch", "assignment_seal",
                        "sealed state does not bind the parent this child was minted under",
                    ))
            elif sealed_assignments.get(ticket_id) != data.get("assignment_seal"):
                findings.append(finding("sealed-assignment-mismatch", "assignment_seal", "sealed state does not bind this assignment"))
    ordered = _ordered(findings)
    receipt = ADMISSION_PENDING
    if not ordered:
        payload = {"assignment": assignment_digest(ticket_id, text), "sealed_state": sealed_record}
        receipt = f"{adapter or 'ticket'}:sha256:{hashlib.sha256(_canonical_json(payload)).hexdigest()}"
    return {
        "adapter": adapter, "findings": ordered, "receipt": receipt,
        "snapshot_ids": sorted({ticket_id, *dependencies}),
    }


def dependency_order_findings(ticket_id: str, data: dict) -> list:
    """Refuse an unsorted ``depends_on`` where it is still cheap to fix.

    Two orderings of one edge set are two assignment digests, so the same
    cut authored twice seals as two different generations. The digest is not
    changed to absorb that -- doing so would invalidate every historical
    seal -- the authoring door refuses it instead, while the list is still a
    draft nobody has been dispatched against.
    """

    dependencies = [str(value) for value in (data.get("depends_on") or [])]
    if dependencies == sorted(dependencies):
        return []
    return [{
        "code": "depends-on-unsorted",
        "field": "depends_on",
        "ticket": ticket_id,
        "detail": "depends_on must be in ascending order: " + ", ".join(sorted(dependencies)),
    }]


def refresh_admissions(run, run_dir, snapshot: dict, write_atomically) -> list:
    """Re-issue the receipts one lawful mutation of this run invalidated.

    A receipt names the exact state it was taken over, so a member promoted
    under one generation holds a receipt only that generation recomputes.
    Re-generationing the run therefore leaves every promoted member stale --
    a lawful recut, and then the root's next dispatch refused for a staleness
    the recut itself introduced, five times before this was written.

    Only a member already carrying a real receipt is touched: a pending one
    holds ``ADMISSION_PENDING`` and takes its receipt at promotion, and a
    member the mutation left ungradable keeps the stale value rather than
    being given a receipt over findings. Returns the ids rewritten, so the
    caller reports the repair instead of leaving it silent.
    """

    if __package__:
        from .tickets_context import graded_admission
    else:  # pragma: no cover - direct/installed flat script path
        from tickets_context import graded_admission
    current = dict(snapshot)
    rewritten = []
    for ticket_id in sorted(current):
        stored = str(_parse_frontmatter(current[ticket_id]).get("admission") or "")
        if not stored or stored == ADMISSION_PENDING:
            continue
        grade = graded_admission(ticket_id, current[ticket_id], current, run)
        if grade["findings"] or grade["receipt"] == stored:
            continue
        text = _set_frontmatter_field(current[ticket_id], "admission", grade["receipt"])
        current[ticket_id] = text
        write_atomically(Path(run_dir) / f"{ticket_id}.md", text)
        rewritten.append(ticket_id)
    return rewritten


__all__ = (
    "ADMISSION_PENDING", "RESULT_BEARING_STATES", "adapter_id",
    "binding_findings", "dependency_order_findings", "finding",
    "graph_findings", "grade_admission", "is_receipt", "loop_round_stub",
    "pinned_digest_finding", "post_seal_parent", "refresh_admissions",
    "sealed_parent_target",
)
