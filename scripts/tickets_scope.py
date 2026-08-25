"""Pure mutation-plan and declared scope-edge admission.

The project graph is read only from the ticket's fixed Git baseline.  Its
absence is an explicit direct-only result; this module never derives an edge
from source text, ticket prose, or observed behavior.
"""

from __future__ import annotations

import fnmatch
import hashlib
import json
import re
import subprocess
from pathlib import Path

if __package__:
    from . import tickets_store as _store
    from .tickets_format import _parse_frontmatter, _scope_entries, parse_mutations
    from .tickets_inputs import TERMINAL, is_admitted, parse_input_records
else:  # flat installed script family
    import tickets_store as _store
    from tickets_format import _parse_frontmatter, _scope_entries, parse_mutations
    from tickets_inputs import TERMINAL, is_admitted, parse_input_records


MANIFEST_PATH = ".orchflows/scope-edges.json"
FILE_OPERATIONS = frozenset({"create", "change", "delete"})
OPERATIONS = FILE_OPERATIONS | {"write"}
GLOB_RE = re.compile(r"[*?[]")
GIT_ADAPTERS = frozenset({"git", "git-plus-render"})


class DuplicateKey(ValueError):
    pass


def _object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise DuplicateKey(str(key))
        value[key] = item
    return value


def _finding(code, field, detail):
    return {"code": str(code), "field": str(field), "detail": str(detail)}


def _ordered(findings):
    rows = {
        (str(item["code"]), str(item["field"]), str(item["detail"]))
        for item in findings
    }
    return [_finding(*row) for row in sorted(rows)]


def _relative(path, *, prefix=False, glob=False):
    if not isinstance(path, str) or not path or path.startswith("/"):
        return False
    if "\\" in path or ":" in path or (not glob and GLOB_RE.search(path)):
        return False
    if prefix != path.endswith("/"):
        return False
    parts = path.rstrip("/").split("/")
    return bool(parts) and all(part not in ("", ".", "..") for part in parts)


def _node(value, *, trigger):
    if not isinstance(value, dict) or set(value) != {"operation", "path"}:
        return (None, "node keys must be exactly ['operation', 'path']")
    operation, path = value.get("operation"), value.get("path")
    if operation not in OPERATIONS:
        return (None, f"operation must be one of {sorted(OPERATIONS)}")
    prefix = operation == "write"
    if not _relative(path, prefix=prefix, glob=trigger and not prefix):
        kind = "POSIX glob or prefix" if trigger else "concrete POSIX file or prefix"
        return (None, f"{operation}:{path} is not a repository-relative {kind}")
    return ((operation, path), None)


def parse_manifest(content):
    """Return normalized unique edges and closed-schema findings."""

    if isinstance(content, str):
        content = content.encode("utf-8")
    try:
        decoded = content.decode("utf-8")
        value = json.loads(decoded, object_pairs_hook=_object)
    except (AttributeError, UnicodeDecodeError, json.JSONDecodeError, DuplicateKey) as error:
        return ([], [_finding("scope-edge-schema", MANIFEST_PATH, f"invalid JSON: {error}")])
    if not isinstance(value, dict) or set(value) != {"version", "edges"}:
        return ([], [_finding(
            "scope-edge-schema", MANIFEST_PATH,
            "top-level keys must be exactly ['edges', 'version']",
        )])
    if value.get("version") != 1 or isinstance(value.get("version"), bool):
        return ([], [_finding("scope-edge-schema", MANIFEST_PATH, "version must be integer 1")])
    if not isinstance(value.get("edges"), list):
        return ([], [_finding("scope-edge-schema", MANIFEST_PATH, "edges must be a list")])

    findings, normalized, seen = [], [], set()
    for position, raw in enumerate(value["edges"], start=1):
        field = f"{MANIFEST_PATH}:edge:{position}"
        if not isinstance(raw, dict) or set(raw) != {"from", "requires", "reason"}:
            findings.append(_finding(
                "scope-edge-schema", field,
                "edge keys must be exactly ['from', 'reason', 'requires']",
            ))
            continue
        source, defect = _node(raw.get("from"), trigger=True)
        if defect:
            findings.append(_finding("scope-edge-schema", field, f"from {defect}"))
            continue
        requirements = raw.get("requires")
        if not isinstance(requirements, list) or not requirements:
            findings.append(_finding("scope-edge-schema", field, "requires must be a non-empty list"))
            continue
        parsed_requirements, invalid = [], False
        for required in requirements:
            parsed, defect = _node(required, trigger=False)
            if defect:
                findings.append(_finding("scope-edge-schema", field, f"requires {defect}"))
                invalid = True
            elif parsed not in parsed_requirements:
                parsed_requirements.append(parsed)
        reason = raw.get("reason")
        if not isinstance(reason, str) or not reason.strip():
            findings.append(_finding("scope-edge-schema", field, "reason must be a non-empty string"))
            invalid = True
        if invalid:
            continue
        identity = (source, tuple(sorted(parsed_requirements)))
        if identity in seen:
            continue
        seen.add(identity)
        normalized.append({
            "from": source,
            "requires": tuple(sorted(parsed_requirements)),
            "reason": reason.strip(),
        })
    return (normalized, _ordered(findings))


def path_covers(scope, path):
    scope = str(scope).strip().replace("\\", "/").rstrip("/")
    path = str(path).strip().replace("\\", "/").rstrip("/")
    return bool(scope) and (path == scope or path.startswith(scope + "/"))


def _mutation_in_scope(node, scope):
    return any(path_covers(entry, node[1]) for entry in _scope_entries(scope))


def _plan_covers(plan, required):
    if plan[0] == "write":
        return path_covers(plan[1], required[1])
    return plan == required


def unplanned_mutations(data, actual):
    """Actual ``(operation, path)`` rows outside one admitted plan.

    V0 retains its path-only grant at the join.  Admission owns malformed or
    absent plans in either graded version; if one nevertheless reaches the
    join, no actual mutation is silently authorized.
    """

    if not is_admitted(data):
        return []
    parsed, defects = parse_mutations(data)
    plans = [(item["operation"], item["path"]) for item in parsed]
    if "mutations" not in data or defects:
        return sorted(set(actual))
    return sorted({node for node in actual if not any(_plan_covers(plan, node) for plan in plans)})


def _prefix_overlap(left, right):
    return path_covers(left, right) or path_covers(right, left)


def _static_glob_prefix(pattern):
    first = min((pattern.find(mark) for mark in "*?[" if mark in pattern), default=len(pattern))
    literal = pattern[:first]
    return literal.rsplit("/", 1)[0] + "/" if "/" in literal else ""


def _trigger_matches(source, mutation):
    source_operation, source_path = source
    operation, path = mutation
    if source_operation == "write":
        if operation == "write":
            return _prefix_overlap(source_path, path)
        return path_covers(source_path, path)
    if operation == "write":
        # A broad plan admits every file operation under its prefix.  It must
        # therefore close a file-operation edge whose glob can intersect it.
        prefix = _static_glob_prefix(source_path)
        return source_operation in FILE_OPERATIONS and (
            not prefix or _prefix_overlap(prefix, path)
        )
    return operation == source_operation and fnmatch.fnmatchcase(path, source_path)


def _dependencies(ticket_id, members):
    found, pending = set(), [ticket_id]
    while pending:
        current = pending.pop()
        for dependency in members.get(current, {}).get("depends_on") or []:
            dependency = str(dependency)
            if dependency not in found:
                found.add(dependency)
                pending.append(dependency)
    return found


def _cycle_nodes(graph):
    visited, active, stack, cycles = set(), set(), [], set()

    def visit(node):
        if node in active:
            start = stack.index(node)
            cycle = stack[start:] + [node]
            rotations = [tuple(cycle[index:-1] + cycle[:index] + [cycle[index]]) for index in range(len(cycle) - 1)]
            cycles.add(min(rotations))
            return
        if node in visited:
            return
        visited.add(node)
        active.add(node)
        stack.append(node)
        for child in sorted(graph.get(node, ())):
            visit(child)
        stack.pop()
        active.remove(node)

    for node in sorted(graph):
        visit(node)
    return sorted(cycles)


ROOT_COHORT_PREFIX = "v1:root:"
ROOT_GENERATION_SUBJECT_RE = re.compile(r"^v2:root:([A-Za-z0-9][A-Za-z0-9._-]*):")
GATE_INFIX = ".gate."
V2_FIELDS = ("root_generation", "cut_generation", "ownership_regions", "assignment_seal")


def _closure_key(ticket_id, data):
    """The cut whose mutation plans this ticket is graded against.

    A stamped cohort names that cut and keeps naming it, so every grouping a
    cohort ever decided is exactly what it was.  A v2 ticket stamps none --
    v2 freezes a cut by its sealed generation, not by a cohort string -- and
    reading the absent field as ``""`` made every cohortless v2 ticket in a
    run one closure, so a lawful ticket inherited its siblings' mutation
    findings and was refused admission for another ticket's defect.  A sealed
    v2 ticket is therefore grouped by ``cut_generation``; one not yet sealed
    names no cut at all, so its closure is itself.  The version test repeats
    ``tickets_admission.is_v2`` rather than importing it because admission
    composes this module, and the dependency runs one way.
    """

    cohort = str(data.get("cohort") or "")
    if cohort or not any(key in data for key in V2_FIELDS):
        return f"cohort:{cohort}"
    generation = str(data.get("cut_generation") or "")
    return f"cut:{generation}" if generation else f"unsealed:{ticket_id}"


def _companion_owners(data, members):
    """The member ids that may own a scope-edge companion in this cut.

    A cut's root holds its whole subtree's write scope and its gate stubs
    repair anywhere that subtree writes, so both cover every companion the cut
    plans. Counting them would report the lawful shape -- one unit owning the
    companion -- as several owners, and the shape with no unit owner as owned.
    Where the cut holds no unit at all the whole membership is eligible again,
    so a root graded alone still owns the companions it plans -- and a root
    with only gate stubs is read exactly as it was, several owners and all.

    A v1 decomposition stamps every member with the root's cohort; a sealed v2
    cut stamps none and freezes the root in ``root_generation`` instead, so
    reading the cohort alone left a v2 root unnamed and eligible, making both
    misreadings above.  Only its subject is read here -- whether the identity
    is well formed is ``tickets_generations``'s -- and never split by position.
    """

    cohort = str(data.get("cohort") or "")
    sealed = ROOT_GENERATION_SUBJECT_RE.match(str(data.get("root_generation") or ""))
    root_id = cohort[len(ROOT_COHORT_PREFIX):] if cohort.startswith(ROOT_COHORT_PREFIX) else (sealed.group(1) if sealed else "")
    units = {
        member_id for member_id in members
        if member_id != root_id and GATE_INFIX not in member_id
    }
    return units or set(members)


def grade_closure(ticket_id, text, siblings, edges):
    """Grade every explicit mutation in this ticket's cut.

    Membership is the live members of one cut.  A terminal member's plan was
    already spent under the authority it was worked with, so counting it here
    reports a finished unit and a pending one as two owners of the one
    companion the pending unit still has to write.  The ticket being graded is
    always a member: its own plan is the authority under grade.
    """

    current = _parse_frontmatter(text)
    member_texts = dict(siblings)
    member_texts[ticket_id] = text
    parsed = {
        member_id: _parse_frontmatter(member_text)
        for member_id, member_text in member_texts.items()
    }
    key = _closure_key(ticket_id, parsed[ticket_id])
    members = {
        member_id: data
        for member_id, data in parsed.items()
        if _closure_key(member_id, data) == key
        and (member_id == ticket_id or str(data.get("status") or "") not in TERMINAL)
    }
    findings, plans, authorized = [], {}, {}
    for member_id in sorted(members):
        data = members[member_id]
        if "mutations" not in data:
            findings.append(_finding("mutation-plan-missing", f"{member_id}.mutations", "v1 Git/design ticket requires an explicit list"))
            plans[member_id] = ()
            continue
        parsed, defects = parse_mutations(data)
        for defect in defects:
            findings.append(_finding("mutation-invalid", f"{member_id}.mutations", defect))
        nodes = tuple((item["operation"], item["path"]) for item in parsed)
        plans[member_id] = nodes
        for node in nodes:
            allowed = _mutation_in_scope(node, data.get("write_scope"))
            authorized[(member_id, node)] = allowed
            if not allowed:
                findings.append(_finding(
                    "mutation-outside-write-scope", f"{member_id}.mutations",
                    f"{node[0]}:{node[1]}",
                ))

    owners = {}
    eligible = _companion_owners(current, plans)
    initial = set()
    for member_id, nodes in plans.items():
        for node in nodes:
            initial.add(node)
    pending, expanded, graph, required_by = list(sorted(initial)), set(), {}, {}
    while pending:
        node = pending.pop(0)
        if node in expanded:
            continue
        expanded.add(node)
        node_owners = {
            member_id for member_id, declared in plans.items()
            if member_id in eligible
            and any(_plan_covers(plan, node) for plan in declared)
        }
        owners[node] = node_owners
        for declared_edge in edges:
            if not _trigger_matches(declared_edge["from"], node):
                continue
            for required in declared_edge["requires"]:
                graph.setdefault(node, set()).add(required)
                required_by.setdefault(required, set()).update(node_owners)
                if required not in expanded and required not in pending:
                    pending.append(required)
        pending.sort()

    for required in sorted(required_by):
        node_owners = {
            member_id for member_id, declared in plans.items()
            if member_id in eligible
            and any(_plan_covers(plan, required) for plan in declared)
        }
        owners[required] = node_owners
        rendered = f"{required[0]}:{required[1]}"
        if not node_owners:
            findings.append(_finding("scope-owner-missing", "mutations", rendered))
            continue
        if len(node_owners) > 1:
            findings.append(_finding(
                "scope-owner-multiple", "mutations",
                f"{rendered} owned by {', '.join(sorted(node_owners))}",
            ))
            continue
        owner = next(iter(node_owners))
        matching = [plan for plan in plans[owner] if _plan_covers(plan, required)]
        if not any(authorized.get((owner, plan), False) for plan in matching):
            findings.append(_finding(
                "scope-owner-unauthorized", f"{owner}.mutations", rendered,
            ))
        ancestors = _dependencies(owner, members)
        for trigger_owner in sorted(required_by[required]):
            if trigger_owner != owner and trigger_owner not in ancestors:
                findings.append(_finding(
                    "scope-owner-unordered", f"{owner}.depends_on",
                    f"{rendered} requires {trigger_owner}",
                ))

    for cycle in _cycle_nodes(graph):
        detail = " -> ".join(f"{operation}:{path}" for operation, path in cycle)
        findings.append(_finding("scope-edge-cycle", MANIFEST_PATH, detail))
    return _ordered(findings)


def _project_root(context):
    value = context.get("project_root")
    run_project = context.get("run_project")
    if value is None and isinstance(run_project, dict):
        value = run_project.get("root")
    if value:
        return Path(value).expanduser().resolve()
    completed = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"], capture_output=True,
        check=False, text=True, cwd=str(_store._cwd()),
    )
    return Path(completed.stdout.strip()).resolve() if completed.returncode == 0 else None


def _baseline_revision(text):
    parsed = parse_input_records(text)
    for record in parsed.get("records", ()):
        identity = record.get("identity") if record.get("type") == "identity" else None
        if record.get("name") == "baseline" and isinstance(identity, dict) and identity.get("kind") == "git-tree":
            return identity.get("revision")
    return None


def _resolved_manifest(text, context):
    if "scope_manifest" in context:
        return (context.get("scope_manifest"), None)
    baseline_tree = context.get("baseline_tree")
    if baseline_tree is not None:
        root = Path(baseline_tree).resolve()
        path = root / MANIFEST_PATH
        if path.is_symlink():
            try:
                resolved = path.resolve(strict=True)
                resolved.relative_to(root)
            except (OSError, ValueError) as error:
                return (None, f"baseline manifest symlink is unavailable or external: {error}")
        try:
            return (path.read_bytes(), None)
        except FileNotFoundError:
            return (None, None)
        except OSError as error:
            return (None, str(error))
    revision = _baseline_revision(text)
    root = _project_root(context)
    if not revision or root is None:
        return (None, "fixed git-tree baseline is unavailable")
    completed = subprocess.run(
        ["git", "-C", str(root), "show", f"{revision}:{MANIFEST_PATH}"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )
    if completed.returncode == 0:
        return (completed.stdout, None)
    object_exists = subprocess.run(
        ["git", "-C", str(root), "cat-file", "-e", f"{revision}:{MANIFEST_PATH}"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )
    if object_exists.returncode == 0:
        return (None, "fixed baseline manifest exists but could not be read")
    commit_exists = subprocess.run(
        ["git", "-C", str(root), "cat-file", "-e", f"{revision}^{{commit}}"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )
    if commit_exists.returncode == 0:
        return (None, None)
    return (None, "fixed git-tree baseline does not resolve")


def grade_scope(*, ticket_id, text, siblings, adapter_id, context=None):
    """Return portable scope findings, mode, and graph fingerprint."""

    context = dict(context or {})
    data = _parse_frontmatter(text)
    direct = {
        "findings": [], "fingerprint": f"scope:direct-only:{adapter_id}",
        "mode": "direct-only", "authorized_scope": _scope_entries(data.get("write_scope")),
    }
    if not is_admitted(data):
        return direct
    if adapter_id not in GIT_ADAPTERS:
        return direct

    content, error = _resolved_manifest(text, context)
    edges, manifest_findings = ([], []) if content is None else parse_manifest(content)
    findings = list(manifest_findings)
    if error:
        findings.append(_finding("scope-baseline-unavailable", MANIFEST_PATH, error))
    findings.extend(grade_closure(ticket_id, text, siblings, edges))
    if content is None:
        return {**direct, "findings": _ordered(findings)}
    digest = hashlib.sha256(content if isinstance(content, bytes) else content.encode("utf-8")).hexdigest()
    return {
        "findings": _ordered(findings),
        "fingerprint": f"scope:sha256:{digest}",
        "mode": "declared-edges",
        "authorized_scope": _scope_entries(data.get("write_scope")),
    }


__all__ = (
    "MANIFEST_PATH", "parse_manifest", "path_covers", "unplanned_mutations", "grade_closure", "grade_scope",
)
