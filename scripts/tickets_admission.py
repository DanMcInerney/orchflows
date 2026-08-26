"""Pure ticket-admission grading and portable receipt construction.
This module owns no command-line rendering and performs no state writes.  A
caller supplies the exact ticket/run snapshot it read; lifecycle commands use
the returned receipt only if that snapshot still compares equal under the run
lock.
"""
from __future__ import annotations
import hashlib
import importlib
import json
import re
from pathlib import Path
if __package__:
    from .tickets_format import (
        CUT_SECTIONS,
        ADAPTER_BY_PACK,
        PACK_EXECUTOR_BINDINGS,
        PLAIN_ADAPTER,
        ROOT_EXECUTOR,
        SCRIPT_EXECUTOR_PREFIX,
        adapter_id,
        canonical_json,
        count_return_text,
        executor_bindings,
        parse_result_identity,
        parse_return_size,
        _executor_of,
        _parse_frontmatter,
        _scope_entries,
        _sections,
    )
else:
    from tickets_format import (
        CUT_SECTIONS,
        ADAPTER_BY_PACK,
        PACK_EXECUTOR_BINDINGS,
        PLAIN_ADAPTER,
        ROOT_EXECUTOR,
        SCRIPT_EXECUTOR_PREFIX,
        adapter_id,
        canonical_json,
        count_return_text,
        executor_bindings,
        parse_result_identity,
        parse_return_size,
        _executor_of,
        _parse_frontmatter,
        _scope_entries,
        _sections,
    )
ADMISSION_PENDING = "pending"
VCS_ACTION_TOKENS = frozenset({
    "vcs.isolate",
    "vcs.commit",
    "vcs.integrate",
    "vcs.push",
    "vcs.open-pr",
})
TDD_FORBIDDEN_ACTIONS = frozenset({"vcs.isolate", "vcs.commit"})
_VCS_PROSE_WORDS = (
    "git",
    "worktree",
    "branch",
    "commit",
    "merge",
    "push",
    "pull request",
    "version control",
)
_RECEIPT_RE = re.compile(r"^([a-z][a-z0-9-]*):sha256:([0-9a-f]{64})$")
_PACK_ROW_RE = re.compile(r"^\|\s*(executor|assembly)\s*\|\s*(.*?)\s*\|\s*$", re.MULTILINE)
_SKILL_RE = re.compile(r"`(orch-[a-z0-9-]+)`")
def is_receipt(value) -> bool:
    return bool(_RECEIPT_RE.fullmatch(str(value or "").strip()))


def finding(code: str, field: str, detail: str) -> dict:
    return {"code": code, "field": field, "detail": detail}


def _ordered(findings) -> list:
    unique = {
        (str(item.get("code") or ""), str(item.get("field") or ""), str(item.get("detail") or ""))
        for item in findings
    }
    return [finding(*row) for row in sorted(unique)]


def authority_findings(ticket_id: str, data: dict) -> list:
    """Portable pack/executor and TDD workspace-policy findings."""

    findings = []
    executor = _executor_of(data)
    pack = str(data.get("pack") or "").strip()
    unbound = executor.startswith(SCRIPT_EXECUTOR_PREFIX) or executor == ROOT_EXECUTOR or ".gate." in ticket_id
    bindings = executor_bindings(pack) if pack and not unbound else set()
    if pack and not unbound and executor not in bindings:
        findings.append(finding(
            "executor-pack-mismatch", "executor",
            f"{executor or '<missing>'} is not bound by {pack}'s stable executor/assembly registry",
        ))
    if executor.startswith(SCRIPT_EXECUTOR_PREFIX):
        target = executor[len(SCRIPT_EXECUTOR_PREFIX):].strip()
        if not (Path(__file__).resolve().parents[1] / target).is_file():
            findings.append(finding("script-executor-unresolved", "executor",
                                    f"executor names script '{target or '<missing>'}', which does not resolve in the tree"))
    if executor != "orch-tdd":
        return findings
    adapter = adapter_id(pack)
    if adapter != "git":
        findings.append(finding(
            "vcs-adapter-required", "pack",
            f"orch-tdd requires adapter git, not {adapter}",
        ))
    isolation = str(data.get("isolation") or "none").strip()
    if isolation != "required":
        findings.append(finding(
            "vcs-isolation-required", "isolation",
            "orch-tdd requires isolation: required",
        ))
    exclusions = _scope_entries(data.get("excluded_actions"))
    for entry in exclusions:
        token = entry.casefold()
        if token in TDD_FORBIDDEN_ACTIONS:
            findings.append(finding(
                "vcs-action-excluded", "excluded_actions",
                f"orch-tdd requires {token}",
            ))
            continue
        if token in VCS_ACTION_TOKENS:
            continue
        normalized = re.sub(r"[-_]+", " ", token)
        normalized = re.sub(r"\s+", " ", normalized)
        if any(re.search(rf"(?<![a-z0-9]){re.escape(word)}(?![a-z0-9])", normalized) for word in _VCS_PROSE_WORDS):
            findings.append(finding(
                "vcs-exclusion-not-tokenized", "excluded_actions",
                f"VCS exclusion must use a reserved vcs.* token: {entry}",
            ))
    return findings


def _optional_probe(module_name: str, function_name: str, **kwargs) -> tuple:
    """Call one lower pure validator when its dependent slice is installed.

    The stable return is ``(findings, fingerprint)``.  A missing module means
    that concern is not installed in this foundation revision; a present
    module with a missing or malformed interface is an admission finding,
    never an import-time failure of every ticket command.
    """

    qualified = f"{__package__}.{module_name}" if __package__ else module_name
    try:
        module = importlib.import_module(qualified)
    except ModuleNotFoundError as error:
        if error.name == qualified or error.name == module_name:
            return ([], f"{module_name}:not-installed")
        return ([finding("validator-unavailable", module_name, str(error))], f"{module_name}:error")
    probe = getattr(module, function_name, None)
    if not callable(probe):
        return ([finding("validator-interface", module_name, f"missing {function_name}")], f"{module_name}:error")
    result = probe(**kwargs)
    if not isinstance(result, dict):
        return ([finding("validator-interface", module_name, f"{function_name} returned no mapping")], f"{module_name}:error")
    return (list(result.get("findings") or []), str(result.get("fingerprint") or f"{module_name}:empty"))


def _canonical_json(value) -> bytes:
    return canonical_json(value).encode("utf-8")


def _shared_grade(ticket_id: str, text: str, siblings: dict, context: dict,
                  data: dict, findings: list) -> tuple:
    """The dependency, authority and lower-validator grade.

    ``findings`` is extended in place. Order never matters to a caller:
    ``_ordered`` sorts. The
    return is ``(adapter, dependencies, ordered, input_fp, scope_fp)``.
    """

    dependencies = [str(value) for value in (data.get("depends_on") or [])]
    for dependency in dependencies:
        if dependency not in siblings:
            findings.append(finding("dependency-dangling", "depends_on", dependency))
            continue
        status = str(_parse_frontmatter(siblings[dependency]).get("status") or "")
        if status != "complete":
            findings.append(finding("dependency-incomplete", "depends_on", f"{dependency}:{status or '<missing>'}"))
    findings.extend(authority_findings(ticket_id, data))
    adapter = adapter_id(data.get("pack"))
    common = {"ticket_id": ticket_id, "text": text, "siblings": siblings, "adapter_id": adapter, "context": context}
    input_findings, input_fingerprint = _optional_probe("tickets_inputs", "grade_inputs", **common)
    scope_findings, scope_fingerprint = _optional_probe("tickets_scope", "grade_scope", **common)
    return_findings, _ = _optional_probe("tickets_result", "grade_return_fixture", **common)
    findings.extend(input_findings)
    findings.extend(scope_findings)
    findings.extend(return_findings)
    return (adapter, dependencies, _ordered(findings), input_fingerprint, scope_fingerprint)


def grade_admission(ticket_id: str, text: str, siblings: dict, context=None) -> dict:
    """Grade one exact sealed snapshot and return its portable receipt."""

    context = dict(context or {})
    data = _parse_frontmatter(text)
    if __package__:
        from .tickets_generations import GENERATION_RE, assignment_digest, seal_findings
    else:
        module = __import__("tickets_generations")
        GENERATION_RE = module.GENERATION_RE
        assignment_digest = module.assignment_digest
        seal_findings = module.seal_findings
    findings = list(seal_findings(ticket_id, text))
    sealed_record = None
    runs_root = context.get("runs_root")
    run = str(data.get("run") or context.get("run") or "")
    cut_generation = str(data.get("cut_generation") or "")
    match = GENERATION_RE.fullmatch(cut_generation)
    if not runs_root or not run or match is None:
        findings.append(finding("seal-state-unavailable", "cut_generation", "admission requires the script-owned sealed run-state record"))
    else:
        generation_dir = Path(runs_root) / run / "generations"
        sealed_path = generation_dir / f"{match.group(4)}.sealed.json"
        validated_path = generation_dir / f"{match.group(4)}.validated.json"
        try:
            sealed_record = json.loads(sealed_path.read_text(encoding="utf-8"))
            validated_record = json.loads(validated_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, ValueError):
            findings.append(finding("seal-state-missing", "cut_generation", "sealed and validated run-state records must both resolve"))
        else:
            if not isinstance(sealed_record, dict):
                sealed_record = {}
            root_match = GENERATION_RE.fullmatch(str(data.get("root_generation") or ""))
            expected = {
                "cut_generation": cut_generation,
                "root_generation": str(data.get("root_generation") or ""),
                "root_id": root_match.group(2) if root_match is not None else None,
                "state": "sealed",
            }
            if any(sealed_record.get(key) != value for key, value in expected.items()):
                findings.append(finding("seal-state-mismatch", "cut_generation", "sealed run state names another generation"))
            validated_draft = validated_record.get("draft") if isinstance(validated_record, dict) else None
            if not isinstance(validated_draft, dict) or sealed_record.get("receipt") != validated_record.get("receipt") or validated_draft.get("cut_generation") != cut_generation:
                findings.append(finding("validation-receipt-mismatch", "cut_generation", "sealed state does not bind the exact validation receipt"))
            seals = sealed_record.get("assignment_seals") or {}
            if seals.get(ticket_id) != data.get("assignment_seal"):
                findings.append(finding("sealed-assignment-mismatch", "assignment_seal", "sealed run state does not bind this assignment digest"))
    adapter, dependencies, ordered, input_fingerprint, scope_fingerprint = _shared_grade(ticket_id, text, siblings, context, data, findings)
    receipt = ADMISSION_PENDING
    if not ordered:
        payload = {"assignment": assignment_digest(ticket_id, text), "sealed_state": sealed_record}
        receipt = f"{adapter}:sha256:{hashlib.sha256(_canonical_json(payload)).hexdigest()}"
    return {
        "adapter": adapter, "findings": ordered, "receipt": receipt,
        "snapshot_ids": sorted({ticket_id, *dependencies}),
        "input_fingerprint": input_fingerprint, "scope_fingerprint": scope_fingerprint,
    }


def grade_result(ticket_id: str, text: str, siblings: dict, context=None) -> dict:
    """Grade the optional bounded result through the pack identity resolver.

    An unbounded ticket is clean without importing the identity slice.  A
    bounded one uses the exact same parser and resolver contract as the join;
    lifecycle's ``complete`` guard simply consumes these returned findings.
    """
    data = _parse_frontmatter(text)
    sections = _sections(text)
    clause, clause_defects = parse_return_size(sections.get('Return fields', ''))
    findings = [finding('return-size-invalid', 'Return fields', defect) for defect in clause_defects]
    payload = {
        'findings': _ordered(findings), 'counter': None, 'count': None,
        'maximum': None, 'identity': None, 'fingerprint': 'result:unbounded',
    }
    if clause is None:
        return payload
    payload.update({'counter': clause['counter'], 'maximum': clause['maximum']})
    identity, identity_defects = parse_result_identity(sections.get('Result', ''))
    findings.extend(finding('result-identity-invalid', 'Result', defect) for defect in identity_defects)
    payload['identity'] = identity
    if findings:
        payload['findings'] = _ordered(findings)
        return payload
    qualified = f"{__package__}.tickets_inputs" if __package__ else 'tickets_inputs'
    try:
        module = importlib.import_module(qualified)
    except ModuleNotFoundError as error:
        if error.name not in (qualified, 'tickets_inputs'):
            findings.append(finding('result-resolver-unavailable', 'result', str(error)))
        else:
            findings.append(finding('result-resolver-unavailable', 'result', 'tickets_inputs is not installed'))
        payload['findings'] = _ordered(findings)
        return payload
    resolver = getattr(module, 'resolve_identity_payload', None)
    if not callable(resolver):
        payload['findings'] = [finding('result-resolver-interface', 'result', 'tickets_inputs.resolve_identity_payload is missing')]
        return payload
    parser = getattr(module, 'parse_input_records', None)
    parsed = parser(text) if callable(parser) else {'records': []}
    literals = {
        item['name']: item.get('value') for item in parsed.get('records', [])
        if item.get('type') == 'literal'
    }
    resolution_context = {
        **dict(context or {}), 'siblings': siblings, 'ticket_id': ticket_id,
        'run': str(data.get('run') or (context or {}).get('run') or ''),
        'input_literals': literals,
    }
    resolved = resolver(
        identity=identity,
        adapter_id=adapter_id(data.get('pack')),
        context=resolution_context,
        mode='result',
    )
    if not isinstance(resolved, dict):
        payload['findings'] = [finding('result-resolver-interface', 'result', 'resolver returned no mapping')]
        return payload
    findings.extend(list(resolved.get('findings') or []))
    payload['fingerprint'] = str(resolved.get('fingerprint') or 'result:empty')
    content = resolved.get('bytes')
    if not findings:
        if not isinstance(content, bytes):
            findings.append(finding('result-not-bytes', 'result', 'resolved identity returned no byte payload'))
        else:
            try:
                decoded = content.decode('utf-8')
            except UnicodeDecodeError as error:
                findings.append(finding('result-not-text', 'result', f'UTF-8 decode failed at byte {error.start}'))
            else:
                count = count_return_text(decoded, clause['counter'])
                payload['count'] = count
                if count > clause['maximum']:
                    findings.append(finding('result-too-large', 'result', f"{clause['counter']}:{count}>{clause['maximum']}"))
    payload['findings'] = _ordered(findings)
    return payload


__all__ = (
    "ADMISSION_PENDING", "ADAPTER_BY_PACK", "PACK_EXECUTOR_BINDINGS",
    "PLAIN_ADAPTER", "VCS_ACTION_TOKENS", "TDD_FORBIDDEN_ACTIONS",
    "adapter_id", "is_receipt", "finding", "authority_findings",
    "grade_admission", "grade_result",
)
