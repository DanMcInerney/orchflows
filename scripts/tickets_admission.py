"""Pure ticket-admission grading and portable receipt construction.
This module owns no command-line rendering and performs no state writes.  A
caller supplies the exact ticket/run snapshot it read; lifecycle commands use
the returned receipt only if that snapshot still compares equal under the run
lock.
"""
from __future__ import annotations
import hashlib
import importlib
import re
if __package__:
    from .tickets_format import (
        CUT_SECTIONS,
        ADAPTER_BY_PACK,
        PACK_EXECUTOR_BINDINGS,
        PLAIN_ADAPTER,
        ROOT_EXECUTOR,
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
ADMISSION_PENDING = "v1:pending"
ADMISSION_VERSION = 1
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
_COHORT_RE = re.compile(r"^v1:(?:ticket|root|batch):[A-Za-z0-9][A-Za-z0-9._-]*$")
_RECEIPT_RE = re.compile(r"^v1:([a-z][a-z0-9-]*):sha256:([0-9a-f]{64})$")
_PACK_ROW_RE = re.compile(r"^\|\s*(executor|assembly)\s*\|\s*(.*?)\s*\|\s*$", re.MULTILINE)
_SKILL_RE = re.compile(r"`(orch-[a-z0-9-]+)`")
_DYNAMIC_FIELDS = frozenset({
    "status", "admission", "claimed_by", "claimed_at", "checked_by",
    "workspace_branch", "workspace_baseline", "granted_scope", "granted_by",
    "granted_at",
})
_TERMINAL = frozenset({"complete", "blocked", "stalled", "limited", "failed"})
def ticket_cohort(ticket_id: str) -> str:
    return f"v1:ticket:{ticket_id}"
def root_cohort(root_id: str) -> str:
    return f"v1:root:{root_id}"
def batch_cohort(ticket_ids) -> str:
    joined = "\0".join(sorted(str(value) for value in ticket_ids)).encode("utf-8")
    return f"v1:batch:{hashlib.sha256(joined).hexdigest()[:12]}"
def is_v1(data: dict) -> bool:
    return str(data.get("admission") or "").startswith("v1:")


def is_receipt(value) -> bool:
    return bool(_RECEIPT_RE.fullmatch(str(value or "").strip()))


def valid_cohort(value) -> bool:
    return bool(_COHORT_RE.fullmatch(str(value or "").strip()))


def finding(code: str, field: str, detail: str) -> dict:
    return {"code": code, "field": field, "detail": detail}


def _ordered(findings) -> list:
    unique = {
        (str(item.get("code") or ""), str(item.get("field") or ""), str(item.get("detail") or ""))
        for item in findings
    }
    return [finding(*row) for row in sorted(unique)]


def _pack_bindings(pack: str) -> set:
    """Executor/assembly skills in the flat-family admission registry."""
    return executor_bindings(pack)


def authority_findings(ticket_id: str, data: dict) -> list:
    """Portable pack/executor and TDD workspace-policy findings."""

    findings = []
    executor = _executor_of(data)
    pack = str(data.get("pack") or "").strip()
    structural = executor == ROOT_EXECUTOR or ".gate." in ticket_id
    bindings = _pack_bindings(pack) if pack and not structural else set()
    if pack and not structural and executor not in bindings:
        findings.append(finding(
            "executor-pack-mismatch", "executor",
            f"{executor or '<missing>'} is not bound by {pack}'s stable executor/assembly registry",
        ))
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


def _canonical_cut(ticket_id: str, text: str, siblings: dict, adapter: str,
                   input_fingerprint: str, scope_fingerprint: str) -> dict:
    data = _parse_frontmatter(text)
    sections = _sections(text)
    fields = {
        key: value for key, value in data.items()
        if key not in _DYNAMIC_FIELDS
    }
    dependencies = []
    for dependency in sorted(str(value) for value in (data.get("depends_on") or [])):
        dependency_text = siblings.get(dependency, "")
        dependency_data = _parse_frontmatter(dependency_text)
        result = _sections(dependency_text).get("Result", "")
        dependencies.append({
            "id": dependency,
            "status": dependency_data.get("status"),
            "result_sha256": hashlib.sha256(result.encode("utf-8")).hexdigest(),
        })
    cohort = str(data.get("cohort") or "")
    members = []
    for sibling_id in sorted(siblings):
        sibling_text = siblings[sibling_id]
        sibling_data = _parse_frontmatter(sibling_text)
        if str(sibling_data.get("cohort") or "") != cohort:
            continue
        sibling_sections = _sections(sibling_text)
        member_cut = {
            "id": sibling_id,
            "fields": {
                key: value for key, value in sibling_data.items()
                if key not in _DYNAMIC_FIELDS
            },
            "sections": {name: sibling_sections.get(name, "") for name in CUT_SECTIONS},
        }
        members.append(hashlib.sha256(_canonical_json(member_cut)).hexdigest())
    return {
        "version": ADMISSION_VERSION,
        "adapter": adapter,
        "ticket": ticket_id,
        "fields": fields,
        "sections": {name: sections.get(name, "") for name in CUT_SECTIONS},
        "dependencies": dependencies,
        "cohort_members": members,
        "input_fingerprint": input_fingerprint,
        "scope_fingerprint": scope_fingerprint,
    }


def _canonical_json(value) -> bytes:
    return canonical_json(value).encode("utf-8")


def relevant_snapshot_ids(ticket_id: str, text: str, siblings: dict) -> list:
    data = _parse_frontmatter(text)
    cohort = str(data.get("cohort") or "")
    ids = {ticket_id, *(str(value) for value in (data.get("depends_on") or []))}
    ids.update(
        sibling_id for sibling_id, sibling_text in siblings.items()
        if cohort and str(_parse_frontmatter(sibling_text).get("cohort") or "") == cohort
    )
    return sorted(ids)


def cohort_sealed(ticket_id: str, text: str, siblings: dict) -> bool:
    data = _parse_frontmatter(text)
    cohort = str(data.get("cohort") or "")
    if not cohort:
        return False
    for sibling_id, sibling_text in siblings.items():
        if sibling_id == ticket_id:
            continue
        sibling = _parse_frontmatter(sibling_text)
        if str(sibling.get("cohort") or "") != cohort:
            continue
        status = str(sibling.get("status") or "")
        if status in {"claimed", "suspended", *_TERMINAL} or str(sibling.get("claimed_at") or "").strip():
            return True
    return False


def grade_admission(ticket_id: str, text: str, siblings: dict, context=None) -> dict:
    """Grade one exact snapshot and return ordered findings plus its receipt."""

    context = dict(context or {})
    data = _parse_frontmatter(text)
    findings = []
    cohort = str(data.get("cohort") or "").strip()
    if not _COHORT_RE.fullmatch(cohort):
        findings.append(finding("cohort-invalid", "cohort", "expected v1:<ticket|root|batch>:<id-segment>"))
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
    common = {
        "ticket_id": ticket_id,
        "text": text,
        "siblings": siblings,
        "adapter_id": adapter,
        "context": context,
    }
    input_findings, input_fingerprint = _optional_probe("tickets_inputs", "grade_inputs", **common)
    scope_findings, scope_fingerprint = _optional_probe("tickets_scope", "grade_scope", **common)
    return_findings, _ = _optional_probe("tickets_result", "grade_return_fixture", **common)
    findings.extend(input_findings)
    findings.extend(scope_findings)
    findings.extend(return_findings)
    ordered = _ordered(findings)
    receipt = ADMISSION_PENDING
    if not ordered:
        payload = _canonical_cut(ticket_id, text, siblings, adapter, input_fingerprint, scope_fingerprint)
        receipt = f"v1:{adapter}:sha256:{hashlib.sha256(_canonical_json(payload)).hexdigest()}"
    return {
        "adapter": adapter,
        "findings": ordered,
        "receipt": receipt,
        "snapshot_ids": relevant_snapshot_ids(ticket_id, text, siblings),
        "input_fingerprint": input_fingerprint,
        "scope_fingerprint": scope_fingerprint,
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
    "ADMISSION_PENDING", "ADMISSION_VERSION", "ADAPTER_BY_PACK", "PACK_EXECUTOR_BINDINGS",
    "PLAIN_ADAPTER", "VCS_ACTION_TOKENS", "TDD_FORBIDDEN_ACTIONS",
    "ticket_cohort", "root_cohort", "batch_cohort", "adapter_id", "is_v1",
    "is_receipt", "valid_cohort", "finding", "authority_findings", "relevant_snapshot_ids",
    "cohort_sealed", "grade_admission", "grade_result",
)
