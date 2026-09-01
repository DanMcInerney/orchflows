"""Pure grading for one sealed ticket assignment."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

if __package__:
    from . import _bootstrap
    from .tickets_registry import EXECUTOR_REGISTRY, executor_refusal, executor_registered
    from .tickets_adapters import AdapterError, adapter_spec, pack_digest
    from .tickets_format import (
        RESULT_BEARING_STATES,
        SCRIPT_EXECUTOR_PREFIX, adapter_id, canonical_json, declared_parent,
        round_parent, _executor_of,
        _parse_frontmatter, _set_frontmatter_field,
    )
else:
    import _bootstrap
    from tickets_registry import EXECUTOR_REGISTRY, executor_refusal, executor_registered
    from tickets_adapters import AdapterError, adapter_spec, pack_digest
    from tickets_format import (
        RESULT_BEARING_STATES,
        SCRIPT_EXECUTOR_PREFIX, adapter_id, canonical_json, declared_parent,
        round_parent, _executor_of,
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
    and every later command compares the resolved pack against it. Without
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
        "now shadows it. Restore the pinned pack, or open a fresh callable "
        "(tickets.py do | judge) against the pack you mean to run.",
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
    unbound = executor.startswith(SCRIPT_EXECUTOR_PREFIX)
    if executor.startswith(SCRIPT_EXECUTOR_PREFIX):
        target = executor[len(SCRIPT_EXECUTOR_PREFIX):].strip()
        if not (_bootstrap.ROOT / target).is_file():
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


def landing_round_parent(ticket_id: str, siblings) -> str | None:
    """The sealed ticket whose landing machinery minted this id, or ``None``.

    A landing whose `done` command refused arms `<id>.repair.NN`, and the
    `check` done form mints `<round>.done` beside a round to judge it. Both
    appear only after the cut that sealed the ticket they descend from, so
    neither is ever a member of the sealed assignment set -- the reading that
    refused the whole round lane the first time it was driven through the
    dispatch trunk.

    `tickets_format.round_parent` owns the grammar; what is added here is the
    sibling lookup, because a round whose parent is not in the run binds
    through nothing.
    """
    parent_id = round_parent(ticket_id)
    if parent_id is None or parent_id not in dict(siblings or {}):
        return None
    return parent_id


def post_seal_parent(ticket_id: str, data: dict, siblings) -> str | None:
    """The sealed ticket whose machinery minted this one after the cut, or None.

    Two spellings of one fact, because the second arrived first. A callable
    names its caller outright in `parent`; a landing's round names its parent
    through the id grammar `round_parent` owns. Both were minted after the cut
    that sealed the parent, so neither can be a member of it, and both bind
    their admission through the parent instead.
    """
    declared = declared_parent(data)
    if declared and declared in dict(siblings or {}):
        return declared
    return landing_round_parent(ticket_id, siblings)


def _canonical_json(value) -> bytes:
    return canonical_json(value).encode("utf-8")


def sealed_parent_target(ticket_id, text, data, siblings, digest, sealed_assignments=None):
    """The sealed ticket one lawful post-seal chain binds its admission through.

    The sealed cut names the assignments that existed when it was sealed, and
    a runtime child exists only afterwards, so it can never be named there.
    What the seal did name is the parent, and a child is lawful exactly when
    it descends from that parent unaltered: the parent's own
    `root_generation` and `cut_generation`, and a self-seal that still matches
    the child's current bytes.  A child whose bytes moved after it was minted
    fails that last reading and falls through to the sealed-set command, which
    has never named it and refuses it.

    A one-hop reading of that rule stops at whatever `post_seal_parent`
    returns even when that parent is itself a runtime child the cut never
    named -- a `do`/`judge` callable's own repair round, whose grammar-derived
    parent is the callable, not the frame the callable was minted under. That
    parent admits exactly the way the callable it repairs admitted, so the walk
    continues past it: each hop is validated the same way (generations agree,
    self-seal matches current bytes) and the chain keeps climbing through
    every un-sealed ancestor until one already named in `sealed_assignments`
    grounds it. A chain that runs out (no further parent), or loops back on
    an ancestor it already crossed -- which lawful minting cannot produce,
    but a hand-edited `parent:` field could claim -- never grounds, and
    returns ``None`` exactly as a chain of one always has: the caller's
    sealed-set command then refuses the leaf directly.

    Written for a landing's repair rounds and generalized to every runtime
    child by the minting commands: `do` and `judge` mint under a sealed parent for
    the same reason a round does, and the parentage the id used to imply is
    now declared.
    """
    sealed_assignments = dict(sealed_assignments or {})
    visited = {ticket_id}
    current_id, current_text, current_data = ticket_id, text, data
    while True:
        parent_id = post_seal_parent(current_id, current_data, siblings)
        if parent_id is None or parent_id in visited:
            return None
        parent = _parse_frontmatter(siblings[parent_id])
        if any(
            str(current_data.get(field) or "") != str(parent.get(field) or "")
            for field in ("cut_generation", "root_generation")
        ):
            return None
        if str(current_data.get("assignment_seal") or "") != digest(current_id, current_text):
            return None
        if parent_id in sealed_assignments:
            return parent_id
        visited.add(parent_id)
        current_id, current_text, current_data = parent_id, siblings[parent_id], parent


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
            sealed_parent = sealed_parent_target(
                ticket_id, text, data, siblings, assignment_digest,
                sealed_assignments,
            )
            if sealed_parent is not None:
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
    seal -- the authoring command refuses it instead, while the list is still a
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
    "grade_admission", "is_receipt",
    "landing_round_parent",
    "pinned_digest_finding", "post_seal_parent", "refresh_admissions",
    "sealed_parent_target",
)
