"""JSON-aware canonical Fixed-input rendering for ticket producers."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

if __package__:
    from . import tickets_store as _store
    from .tickets_format import (
        FIELD_GLOSS_RE, PLACEHOLDER_RE, REQUIRED_FIELDS_CELL,
        ROOT_EXECUTOR, canonical_json, parse_canonical_json,
        _parse_frontmatter, _read_utf8, _sections, _write_section,
    )
else:
    import tickets_store as _store
    from tickets_format import (
        FIELD_GLOSS_RE, PLACEHOLDER_RE, REQUIRED_FIELDS_CELL,
        ROOT_EXECUTOR, canonical_json, parse_canonical_json,
        _parse_frontmatter, _read_utf8, _sections, _write_section,
    )


GIT_PACKS = frozenset({"orch-code-pack", "orch-design-pack"})
PACKS_DIR = "packs"
RESEARCH_PACK = "orch-research-pack"
DIRECT_DEFAULT = "direct default "
INPUT_NAME_RE = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")
ROOT_BY_PACK = {
    "orch-content-pack": ("document-root", "project", ("workspace", "package")),
    "orch-research-pack": ("evidence-store-root", "sink", ("package", "workspace")),
}


def _packs_root(directory):
    """The ``packs/`` owned by ``directory``'s repository, or None."""

    directory = Path(directory).resolve()
    for parent in (directory, *directory.parents):
        candidate = parent / PACKS_DIR
        if candidate.is_dir():
            return candidate
    return None


def _library_packs_root():
    """The source or installed library's pack directory."""
    library = Path(__file__).resolve().parent.parent
    return next((path for path in (
        library / PACKS_DIR, library / "lib" / PACKS_DIR
    ) if path.is_dir()), None)


def _required_spec_fields(packs_root, pack: str) -> list:
    """The stamped pack's semicolon-separated required field clauses."""

    if packs_root is None:
        return []
    text, failure = _read_utf8(Path(packs_root) / pack / "SKILL.md", f"pack {pack}")
    if failure is not None:
        return []
    for line in text.splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) >= 2 and cells[0] == REQUIRED_FIELDS_CELL:
            return [field.strip() for field in cells[1].split(";") if field.strip()]
    return []


def _required_field_name(field: str) -> str:
    return FIELD_GLOSS_RE.split(field, 1)[0].strip()


def _direct_research_defaults() -> list:
    """Ordered ``(field, template)`` defaults read from the research pack."""

    defaults = []
    for field in _required_spec_fields(_library_packs_root(), RESEARCH_PACK):
        parts = FIELD_GLOSS_RE.split(field, 1)
        if len(parts) == 2 and parts[1].startswith(DIRECT_DEFAULT):
            defaults.append((parts[0].strip(), parts[1][len(DIRECT_DEFAULT):].strip()))
    return defaults


def input_records(body: str) -> list:
    """Canonical literal/identity records in one Fixed inputs body."""

    records = []
    for group in input_groups(body):
        if not group or not group[0].startswith("- input: "):
            continue
        try:
            record = parse_canonical_json(group[0][len("- input: "):])
        except ValueError:
            continue
        if isinstance(record, dict):
            records.append(record)
    return records


def _expand_default(template: str, values: dict) -> str:
    for name in ("run", "ticket", "objective"):
        template = template.replace("{" + name + "}", str(values.get(name) or ""))
    return template


def _carry_research_fields(records: list, names: set, values: dict):
    """Add pack-owned defaults to a direct research ticket.

    The shipped benchmaker root predates the canonical names. Its explicit
    ``sources`` and ``rigor`` values are carried once under their pack names;
    no defaults are substituted into a specification route.
    """

    literals = {
        item.get("name"): item.get("value") for item in records
        if isinstance(item, dict) and item.get("type") == "literal"
    }
    if values.get("executor") == "orch-investigate":
        carried = [
            (name, _expand_default(template, values))
            for name, template in _direct_research_defaults()
        ]
    elif values.get("executor") == ROOT_EXECUTOR and {"sources", "rigor"} <= literals.keys():
        carried = [("question", values.get("objective")),
                   ("source-policy", literals["sources"]),
                   ("rigor-bar", literals["rigor"])]
    else:
        carried = []
    for name, value in carried:
        if name not in names:
            records.append({"name": name, "type": "literal", "value": value})
            names.add(name)


def replace_placeholders(value, values):
    if isinstance(value, dict):
        return {key: replace_placeholders(item, values) for key, item in value.items()}
    if isinstance(value, list):
        return [replace_placeholders(item, values) for item in value]
    if not isinstance(value, str):
        return value
    full = PLACEHOLDER_RE.fullmatch(value)
    if full is not None and full.group(1) in values:
        return values[full.group(1)]
    return PLACEHOLDER_RE.sub(
        lambda match: values.get(match.group(1), match.group(0)), value
    )


def input_groups(body):
    groups = []
    for line in body.splitlines():
        if line.startswith("- "):
            groups.append([line])
        elif line.strip() and groups:
            groups[-1].append(line)
        elif line.strip():
            groups.append([line])
    return groups


def git_head():
    process = subprocess.run(
        ["git", "rev-parse", "--verify", "HEAD"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False,
        cwd=str(_store._cwd()),
    )
    revision = process.stdout.strip()
    if process.returncode or not re.fullmatch(r"(?:[0-9a-f]{40}|[0-9a-f]{64})", revision):
        return None
    return revision


def adapter_root(records, names, pack, values):
    rule = ROOT_BY_PACK.get(pack)
    if rule is None or rule[0] in names:
        return None
    root_name, scheme, candidates = rule
    literals = {
        item.get("name"): item.get("value") for item in records
        if isinstance(item, dict) and item.get("type") == "literal"
    }
    source = values.get(root_name)
    if source is None:
        source = next((literals.get(name) for name in candidates if literals.get(name)), None)
    if not isinstance(source, str):
        return f"{pack} input rendering cannot resolve {root_name}"
    relative = source.replace("\\", "/")
    if re.match(r"^[A-Za-z]:", relative) or relative.startswith("/"):
        return f"{pack} input rendering cannot make {root_name} portable from {source}"
    supplied, separator, remainder = relative.partition(":")
    if separator and supplied in {"project", "sink"}:
        if supplied == "project" and pack == "orch-research-pack":
            return f"{pack} input rendering cannot use project: for {root_name}"
        scheme, relative = supplied, remainder
    parts = relative.strip("/").split("/")
    if not parts or any(part in {"", ".", ".."} for part in parts):
        return f"{pack} input rendering cannot make {root_name} portable from {source}"
    records.insert(0, {
        "name": root_name, "type": "literal",
        "value": f"{scheme}:{'/'.join(parts)}/",
    })
    names.add(root_name)
    return None


def render_inputs(body, values, dependencies, pack):
    records, names = [], set()
    for position, group in enumerate(input_groups(body), start=1):
        first = group[0]
        if first.startswith("- input: ") and len(group) == 1:
            try:
                record = parse_canonical_json(first[len("- input: "):])
            except ValueError as error:
                return (None, f"Fixed input template record {position} is invalid JSON: {error}")
            record = replace_placeholders(record, values)
        else:
            prose = " ".join(
                line.strip().removeprefix("- ").strip() for line in group
            ).strip()
            name = "none" if prose == "None." else f"legacy-input-{position}"
            record = {
                "name": name, "type": "literal",
                "value": None if prose == "None." else replace_placeholders(prose, values),
            }
        name = record.get("name") if isinstance(record, dict) else None
        variant = record.get("type") if isinstance(record, dict) else None
        expected = ({"name", "type", "value"} if variant == "literal" else
                    {"identity", "name", "type"} if variant == "identity" else set())
        if not isinstance(record, dict) or set(record) != expected:
            return (None, f"Fixed input template record {position} has an invalid record shape")
        if variant == "identity" and not isinstance(record.get("identity"), dict):
            return (None, f"Fixed input template record {position} has an invalid identity")
        if not isinstance(name, str) or not INPUT_NAME_RE.fullmatch(name) or name in names:
            return (None, f"Fixed input template record {position} has a missing or duplicate name")
        names.add(name)
        records.append(record)
    if not records:
        records.append({"name": "none", "type": "literal", "value": None})
        names.add("none")
    if pack == RESEARCH_PACK:
        _carry_research_fields(records, names, values)
        if len(records) > 1 and "none" in names:
            records = [item for item in records if item.get("name") != "none"]
            names.remove("none")
    root_error = adapter_root(records, names, pack, values)
    if root_error is not None:
        return (None, root_error)
    if pack in GIT_PACKS:
        revision = values.get("baseline") or git_head()
        if revision is None:
            return (None, f"{pack} input rendering cannot resolve the run-project HEAD")
        if "baseline" not in names:
            records.insert(0, {
                "identity": {"kind": "git-tree", "repo": "run-project", "revision": revision},
                "name": "baseline", "type": "identity",
            })
            names.add("baseline")
    run = str(values["run"])
    existing = {
        tuple((item.get("identity") or {}).get(key) for key in ("kind", "run", "ticket", "section")) for item in records
        if isinstance(item, dict) and item.get("type") == "identity"
        and (item.get("identity") or {}).get("kind") == "ticket-section"
    }
    for dependency in dependencies:
        dependency = str(dependency)
        identity_key = ("ticket-section", run, dependency, "Result")
        if identity_key in existing:
            continue
        stem = re.sub(r"[^a-z0-9]+", "-", dependency.casefold()).strip("-") or "dependency"
        if not stem[0].isalpha():
            stem = "ticket-" + stem
        name, suffix = f"{stem}-result", 2
        while name in names:
            name = f"{stem}-result-{suffix}"
            suffix += 1
        records.append({
            "identity": {
                "kind": "ticket-section", "run": run,
                "section": "Result", "ticket": dependency,
            },
            "name": name, "type": "identity",
        })
        names.add(name)
    return ("\n".join("- input: " + canonical_json(item) for item in records), None)


def render_stub(text, values):
    body = _sections(text).get("Fixed inputs", "")
    token = "__ORCHFLOWS_FIXED_INPUTS__"
    masked = _write_section(text, "Fixed inputs", token)
    rendered = PLACEHOLDER_RE.sub(
        lambda match: values.get(match.group(1), match.group(0)), masked
    )
    data = _parse_frontmatter(rendered)
    values = dict(values)
    values.update({
        "executor": str(data.get("executor") or "").strip().strip("`"),
        "objective": _sections(rendered).get("Objective", "").strip(),
        "ticket": str(data.get("id") or "").strip(),
    })
    inputs, error = render_inputs(
        body, values, data.get("depends_on") or [], str(data.get("pack") or "")
    )
    if error is not None:
        return (None, error)
    rendered = rendered.replace(token, inputs)
    unfilled = PLACEHOLDER_RE.search(rendered)
    if unfilled is not None:
        return (None, f"unfilled placeholder '{{{{{unfilled.group(1)}}}}}'")
    return (rendered, None)


def render_ticket_inputs(text, run, inherited_inputs="", baseline=None):
    """Canonicalize one issued/recut ticket's inputs with producer facts."""

    data = _parse_frontmatter(text)
    pack = str(data.get("pack") or "")
    baseline = baseline or git_head()
    if pack in GIT_PACKS and baseline is None:
        return (None, f"{pack} input rendering cannot resolve the run-project HEAD")
    values = {
        "run": run,
        "executor": str(data.get("executor") or "").strip().strip("`"),
        "objective": _sections(text).get("Objective", "").strip(),
        "ticket": str(data.get("id") or "").strip(),
    }
    if baseline is not None:
        values["baseline"] = baseline
    for group in input_groups(inherited_inputs):
        # Judged on the opening line alone, never on the group's length: a
        # root that ends `## Fixed inputs` with prose delivers its final
        # record inside a two-line group, and reading the length there drops
        # a record the root plainly states. Same law as
        # `tickets_dispatch_gate._is_record`, which states it in full; a
        # record genuinely wrapped across lines still fails to parse below.
        if not group or not group[0].startswith("- input: "):
            continue
        try:
            item = parse_canonical_json(group[0][len("- input: "):])
        except ValueError:
            continue
        if item.get("type") == "literal" and item.get("name") in {"document-root", "evidence-store-root"}:
            values[item["name"]] = item.get("value")
    body, error = render_inputs(
        _sections(text).get("Fixed inputs", ""), values,
        data.get("depends_on") or [], pack,
    )
    if error is not None:
        return (None, error)
    return (_write_section(text, "Fixed inputs", body), None)


def canonical_input_record(name, value):
    """One exact literal record for direct ticket producers."""

    return "- input: " + canonical_json({"name": name, "type": "literal", "value": value})


def baseline_input_record(revision):
    return "- input: " + canonical_json({
        "identity": {"kind": "git-tree", "repo": "run-project", "revision": revision},
        "name": "baseline", "type": "identity",
    })


__all__ = (
    "baseline_input_record", "canonical_input_record", "canonical_json",
    "git_head", "input_records", "render_inputs", "render_stub",
    "render_ticket_inputs",
)
