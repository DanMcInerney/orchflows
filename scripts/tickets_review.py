"""Immutable predecessor-linked review records for gates and checkers."""

from __future__ import annotations

from pathlib import Path
import re
import subprocess

if __package__:
    from .tickets_format import (
        GATE_EXECUTORS, _executor_of, _parse_frontmatter, _set_frontmatter_field, adapter_id, canonical_json,
        parse_canonical_json,
    )
    from .tickets_store import _load_ticket
    from .tickets_review_schema import (
        SchemaError, digest as _digest, finding_values as _finding_values,
        nonempty as _nonempty, validate_records,
    )
else:
    from tickets_format import (
        GATE_EXECUTORS, _executor_of, _parse_frontmatter, _set_frontmatter_field, adapter_id, canonical_json,
        parse_canonical_json,
    )
    from tickets_store import _load_ticket
    from tickets_review_schema import (
        SchemaError, digest as _digest, finding_values as _finding_values,
        nonempty as _nonempty, validate_records,
    )


REVIEW_PROTOCOL = "orchflows.review.v1"
REVIEW_FIELD = "review_v1"
REVIEW_KINDS = (
    "GatePlan", "CritiqueAdjudication", "RepairOutcome", "Verification",
)
GIT_ARTIFACT_RE = re.compile(r"^git:([0-9a-f]{40}|[0-9a-f]{64})$")


class ReviewError(ValueError):
    """A review record is absent, divergent, or not closed."""


def _record(kind: str, predecessor, **fields) -> dict:
    content = {
        "kind": kind,
        "predecessor": predecessor,
        "protocol": REVIEW_PROTOCOL,
        **fields,
    }
    return {**content, "identity": _digest(content)}


def _review_state(records, *, allow_legacy: bool = False) -> dict:
    state = {"protocol": REVIEW_PROTOCOL, "records": list(records)}
    review_records(state, allow_legacy=allow_legacy)
    return state


def review_records(value, *, allow_legacy: bool = False) -> list:
    try:
        return validate_records(value, allow_legacy=allow_legacy)
    except SchemaError as error:
        raise ReviewError(str(error)) from error


def state_from_text(
    text: str, *, required: bool = False, allow_legacy: bool = False,
) -> dict | None:
    encoded = _parse_frontmatter(text).get(REVIEW_FIELD)
    if encoded is None:
        if required:
            raise ReviewError(f"ticket has no {REVIEW_FIELD} predecessor ledger")
        return None
    records = review_records(encoded, allow_legacy=allow_legacy)
    return _review_state(records, allow_legacy=allow_legacy)


def _workspace_identity(workspace) -> str:
    if not isinstance(workspace, str) or not workspace.strip():
        raise ReviewError("review requires --workspace <established-path>")
    path = Path(workspace).expanduser()
    if not path.is_dir():
        raise ReviewError(f"review workspace does not exist: {workspace}")
    return str(path.resolve())


def validate_fixed_artifact(pack, artifact: str, workspace) -> tuple[str, str]:
    normalized_workspace = _workspace_identity(workspace)
    if adapter_id(pack) != "git":
        if not _nonempty(artifact):
            raise ReviewError("review requires --artifact <fixed-identity>")
        return artifact.strip(), normalized_workspace
    match = GIT_ARTIFACT_RE.fullmatch(str(artifact or "").strip())
    if match is None:
        raise ReviewError("code review artifact must be git:<full-commit-id>")
    expected = match.group(1)
    commands = (
        ("rev-parse", "--verify", f"{expected}^{{commit}}"),
        ("rev-parse", "HEAD"),
    )
    observed = []
    for command in commands:
        completed = subprocess.run(
            ["git", *command], cwd=normalized_workspace, text=True,
            capture_output=True, check=False,
        )
        if completed.returncode != 0:
            detail = completed.stderr.strip() or completed.stdout.strip()
            raise ReviewError(f"code review artifact does not resolve: {detail}")
        observed.append(completed.stdout.strip().lower())
    if observed[0] != expected or observed[1] != expected:
        raise ReviewError(
            "code review artifact does not equal the established workspace HEAD"
        )
    return f"git:{expected}", normalized_workspace


def _lens(ticket_id: str) -> str:
    marker = ".gate.critique."
    if marker not in ticket_id:
        raise ReviewError(f"not a gate critique ticket: {ticket_id}")
    return ticket_id.split(marker, 1)[1]


def _gate_root(ticket_id: str) -> str:
    for suffix in (".gate.critique.", ".gate.repair", ".gate.verify"):
        if suffix in ticket_id:
            return ticket_id.split(suffix, 1)[0]
    raise ReviewError(f"not a gate ticket: {ticket_id}")


def _critique_paths(ticket_path: Path) -> list[Path]:
    root_id = _gate_root(ticket_path.stem)
    paths = list(ticket_path.parent.glob(f"{root_id}.gate.critique.*.md"))
    ranked = []
    for path in paths:
        data = _load_ticket(path)
        if "error" in data:
            raise ReviewError(data["error"])
        order_text = str(data.get("review_order") or "")
        if not order_text.isdigit():
            raise ReviewError(f"gate critique has no stable review_order: {path.stem}")
        order = int(order_text)
        ranked.append((order, path, data))
    ranked.sort(key=lambda item: item[0])
    if [item[0] for item in ranked] != list(range(len(ranked))):
        raise ReviewError("gate critique review_order is not unique and contiguous")
    return [item[1] for item in ranked]


def gate_plan(ticket_path: Path, artifact: str, workspace: str) -> dict:
    data = _load_ticket(ticket_path)
    artifact, workspace = validate_fixed_artifact(
        data.get("pack"), artifact, workspace,
    )
    criteria = []
    for path in _critique_paths(ticket_path):
        data = _load_ticket(path)
        seal = str(data.get("assignment_seal") or "")
        if not seal:
            raise ReviewError(f"gate critique is not sealed: {path.stem}")
        criteria.append({
            "identity": seal,
            "lens": _lens(path.stem),
            "order": int(data["review_order"]),
            "ticket": path.stem,
        })
    if not criteria:
        raise ReviewError("gate plan has no critique criteria")
    return _record(
        "GatePlan", None,
        artifact=artifact.strip(),
        criteria=criteria,
        isolation=str(data.get("isolation") or "none"),
        mode="gate",
        pack=data.get("pack"),
        root=_gate_root(ticket_path.stem),
        workspace=workspace,
    )


def checker_plan(
    ticket_path: Path, artifact: str, workspace: str, *, stage_path: Path | None = None,
) -> dict:
    data = _load_ticket(ticket_path)
    stage = _load_ticket(stage_path or ticket_path)
    artifact, workspace = validate_fixed_artifact(
        data.get("pack"), artifact, workspace,
    )
    seal = str(stage.get("assignment_seal") or "")
    if not seal:
        raise ReviewError("ordinary check target is not sealed")
    criterion = {
        "identity": _digest({
            "executor": GATE_EXECUTORS["critique"],
            "lens": "checker",
            "pack": data.get("pack"),
            "target_assignment": seal,
        }),
        "lens": "checker",
        "order": 0,
        "ticket": str(stage.get("id") or (stage_path or ticket_path).stem),
    }
    return _record(
        "GatePlan", None,
        artifact=artifact.strip(), criteria=[criterion],
        isolation="none", mode="checker",
        pack=data.get("pack"), root=str(data.get("id") or ticket_path.stem),
        workspace=workspace,
    )


def _dependency_text(ticket_path: Path, dependency: str) -> str:
    path = ticket_path.with_name(f"{dependency}.md")
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        raise ReviewError(f"unreadable review dependency {dependency}: {error}") from error


def aggregate_adjudication(ticket_path: Path, dependencies) -> dict:
    adjudications = []
    plan = None
    for dependency in dependencies:
        records = review_records(
            state_from_text(
                _dependency_text(ticket_path, dependency), required=True,
                allow_legacy=True,
            ),
            allow_legacy=True,
        )
        if [record["kind"] for record in records] != ["GatePlan", "CritiqueAdjudication"]:
            raise ReviewError(f"critique dependency has no closed adjudication: {dependency}")
        if plan is None:
            plan = records[0]
        elif records[0] != plan:
            raise ReviewError("critique dependencies do not share one immutable GatePlan")
        adjudications.append(records[1])
    if plan is None:
        raise ReviewError("repair has no critique adjudications")
    by_lens = {record["lens"]: record for record in adjudications}
    ordered = []
    for criterion in plan["criteria"]:
        record = by_lens.get(criterion["lens"])
        if record is None:
            raise ReviewError(f"missing adjudication for lens {criterion['lens']}")
        ordered.append(record)
    return _record(
        "CritiqueAdjudication", plan["identity"],
        accepted=[item for record in ordered for item in record["accepted"]],
        adjudicated_by="system:aggregate",
        adjudications=ordered,
        artifact=plan["artifact"],
        findings=[item for record in ordered for item in record["findings"]],
        lens="*",
    )


def repair_predecessor_state(ticket_path: Path, dependencies) -> dict:
    dependencies = [str(value) for value in dependencies]
    if len(dependencies) == 1 and dependencies[0].endswith(".check"):
        records = review_records(state_from_text(
            _dependency_text(ticket_path, dependencies[0]), required=True,
            allow_legacy=True,
        ), allow_legacy=True)
        if (
            [record["kind"] for record in records]
            != ["GatePlan", "CritiqueAdjudication"]
            or records[0]["mode"] != "checker"
            or records[0]["root"] != _gate_root(ticket_path.stem)
            or [item["ticket"] for item in records[0]["criteria"]]
            != dependencies
            or records[1]["lens"] != "checker"
        ):
            raise ReviewError("ordinary repair predecessor is not its target's closed checker adjudication")
        if not records[1]["accepted"]:
            raise ReviewError("ordinary checker accepted no blockers")
        return _review_state(records, allow_legacy=True)
    aggregate = aggregate_adjudication(ticket_path, dependencies)
    plan = review_records(state_from_text(
        _dependency_text(ticket_path, dependencies[0] if dependencies else ""),
        required=True, allow_legacy=True,
    ), allow_legacy=True)[0]
    return _review_state([plan, aggregate], allow_legacy=True)


def packet_state(
    ticket_path: Path, text: str, artifact: str | None, workspace: str | None,
) -> dict | None:
    data = _parse_frontmatter(text)
    ticket_id = str(data.get("id") or ticket_path.stem)
    executor = _executor_of(data)
    if executor == GATE_EXECUTORS["critique"] and ticket_id.endswith(".check"):
        target_path = ticket_path.with_name(f"{ticket_id[:-len('.check')]}.md")
        return _review_state([
            checker_plan(
                target_path, artifact or "", workspace or "", stage_path=ticket_path,
            )
        ])
    if executor == GATE_EXECUTORS["critique"] and ".gate.critique." in ticket_id:
        return _review_state([
            gate_plan(ticket_path, artifact or "", workspace or "")
        ])
    if executor == GATE_EXECUTORS["repair"] and ticket_id.endswith(".gate.repair"):
        state = repair_predecessor_state(
            ticket_path, data.get("depends_on") or [],
        )
        plan = review_records(state, allow_legacy=True)[0]
        if artifact is not None and artifact != plan["artifact"]:
            raise ReviewError("repair packet artifact differs from GatePlan")
        if workspace is not None:
            if "workspace" in plan and _workspace_identity(workspace) != plan["workspace"]:
                raise ReviewError("repair packet workspace differs from GatePlan")
            validate_fixed_artifact(
                plan["pack"], plan["artifact"], workspace or plan.get("workspace"),
            )
        return state
    if executor == GATE_EXECUTORS["verify"] and ticket_id.endswith(".gate.verify"):
        dependencies = list(data.get("depends_on") or [])
        if len(dependencies) != 1:
            raise ReviewError("verification requires one repair predecessor")
        state = state_from_text(
            _dependency_text(ticket_path, str(dependencies[0])), required=True,
            allow_legacy=True,
        )
        records = review_records(state, allow_legacy=True)
        if not records or records[-1]["kind"] != "RepairOutcome":
            raise ReviewError("verification predecessor has no RepairOutcome")
        if artifact is None or artifact != records[-1]["artifact"]:
            raise ReviewError("verification packet must name the exact repaired artifact")
        plan = records[0]
        if "workspace" in plan and _workspace_identity(workspace) != plan["workspace"]:
            raise ReviewError("verification packet workspace differs from GatePlan")
        validate_fixed_artifact(
            plan["pack"], records[-1]["artifact"], workspace or plan.get("workspace"),
        )
        return _review_state(records, allow_legacy=True)
    return None


def packet_state_result(
    ticket_path: Path, text: str, artifact: str | None, workspace: str | None,
):
    try:
        return packet_state(ticket_path, text, artifact, workspace), None
    except ReviewError as error:
        return None, str(error)


def packet_mutation(review_state, run, ticket_id, dispatch_id, record_id, content):
    if review_state is None:
        return None
    if __package__:
        from .tickets_attempts import _record_response
    else:
        from tickets_attempts import _record_response

    def commit(candidate, _data, _attempt, _dispatch_state):
        updated = _set_frontmatter_field(
            candidate, REVIEW_FIELD, canonical_json(review_state)
        )
        return (
            updated,
            _record_response(run, ticket_id, dispatch_id, record_id, content),
            None,
        )
    return commit


def replay_review_failure(text: str, expected) -> str | None:
    if expected is None:
        return None
    try:
        return None if state_from_text(text, required=True) == expected else (
            "committed packet review ledger diverged"
        )
    except ReviewError as error:
        return str(error)


def canonical_finding_array(value: str, subject: str) -> str:
    """Validate one closed finding array and return its canonical encoding."""

    try:
        parsed = parse_canonical_json(value)
    except (TypeError, ValueError) as error:
        raise ReviewError(f"{subject} must be a valid JSON array: {error}") from error
    if not isinstance(parsed, list):
        raise ReviewError(f"{subject} must be a valid JSON array")
    try:
        _finding_values(parsed, subject)
    except SchemaError as error:
        raise ReviewError(str(error)) from error
    return canonical_json(parsed)


def adjudicate(
    state: dict, feedback: str, accepted_text: str | None, by: str, lens: str,
) -> dict:
    records = review_records(state)
    if [record["kind"] for record in records] != ["GatePlan"]:
        raise ReviewError("critique join requires exactly one GatePlan predecessor")
    try:
        findings = parse_canonical_json(feedback)
        accepted = parse_canonical_json(accepted_text) if accepted_text is not None else None
    except (TypeError, ValueError) as error:
        raise ReviewError(f"critique findings and accepted set must be valid JSON arrays: {error}") from error
    if not isinstance(findings, list) or not isinstance(accepted, list):
        raise ReviewError("critique join requires --accepted <json-array>")
    try:
        _finding_values(findings, "critique findings")
        _finding_values(accepted, "critique accepted")
    except SchemaError as error:
        raise ReviewError(str(error)) from error
    finding_values = {canonical_json(item) for item in findings}
    if any(canonical_json(item) not in finding_values for item in accepted):
        raise ReviewError("accepted blocker set is not a subset of critique findings")
    plan = records[0]
    if lens not in {item["lens"] for item in plan["criteria"]}:
        raise ReviewError(f"critique lens is absent from GatePlan: {lens}")
    record = _record(
        "CritiqueAdjudication", plan["identity"],
        accepted=accepted,
        adjudicated_by=by,
        artifact=plan["artifact"],
        findings=findings,
        lens=lens,
    )
    return _review_state([plan, record])


def repair_outcome(
    state: dict, artifact: str, result: str, by: str, *, no_op=False,
    workspace: str | None = None,
) -> dict:
    records = review_records(state, allow_legacy=True)
    if not records or records[-1]["kind"] != "CritiqueAdjudication":
        raise ReviewError("repair requires a CritiqueAdjudication predecessor")
    adjudication = records[-1]
    if no_op:
        if adjudication.get("accepted"):
            raise ReviewError("no-op repair requires every accepted blocker set to be empty")
        artifact = adjudication["artifact"]
    elif not isinstance(artifact, str) or not artifact.strip():
        raise ReviewError("repair join requires --artifact <fixed-identity>")
    plan = records[0]
    if workspace is not None or plan.get("workspace") is not None:
        artifact, _ = validate_fixed_artifact(
            plan["pack"], artifact, workspace or plan.get("workspace"),
        )
    record = _record(
        "RepairOutcome", adjudication["identity"],
        accepted=adjudication["accepted"],
        artifact=artifact,
        by=by,
        input_artifact=adjudication["artifact"],
        no_op=bool(no_op),
        result=result,
    )
    return _review_state([*records, record], allow_legacy=True)


def verification_outcome(state: dict, artifact: str | None, verification: str, by: str) -> dict:
    records = review_records(state, allow_legacy=True)
    if not records or records[-1]["kind"] != "RepairOutcome":
        raise ReviewError("verification requires a RepairOutcome predecessor")
    repaired = records[-1]
    if artifact is not None and artifact != repaired["artifact"]:
        raise ReviewError("verification join names a different artifact")
    verdict = verification.partition(":")[0].strip()
    if verdict not in {"PASS", "FAIL", "UNVERIFIED"}:
        raise ReviewError(
            "verification evidence must begin PASS:, FAIL:, or UNVERIFIED:"
        )
    record = _record(
        "Verification", repaired["identity"],
        artifact=repaired["artifact"],
        by=by,
        evidence=verification,
        verdict=verdict,
    )
    return _review_state([*records, record], allow_legacy=True)


__all__ = (
    "REVIEW_FIELD", "REVIEW_PROTOCOL", "ReviewError", "adjudicate",
    "aggregate_adjudication", "canonical_json", "packet_mutation", "packet_state_result",
    "replay_review_failure",
    "repair_outcome", "repair_predecessor_state", "review_records", "state_from_text",
    "verification_outcome",
)
