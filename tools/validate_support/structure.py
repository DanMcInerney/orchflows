"""Validate call graphs, envelopes, and templates."""

from __future__ import annotations

from tools.validate_support import common as __dep_common
CALL_TOKEN_RE = __dep_common.CALL_TOKEN_RE
CARRIAGE_SENTENCE_SPLIT_RE = __dep_common.CARRIAGE_SENTENCE_SPLIT_RE
CRAFT_BUDGET = __dep_common.CRAFT_BUDGET
DESCRIPTION_BUDGET = __dep_common.DESCRIPTION_BUDGET
ENVELOPE_UNITS = __dep_common.ENVELOPE_UNITS
ENVELOPE_VOCAB_RES = __dep_common.ENVELOPE_VOCAB_RES
MANIFEST_BUDGET = __dep_common.MANIFEST_BUDGET
MD_LINK_RE = __dep_common.MD_LINK_RE
Path = __dep_common.Path
RETURN_TEXT_RE = __dep_common.RETURN_TEXT_RE
ROLE_PROFILES = __dep_common.ROLE_PROFILES
ROOT = __dep_common.ROOT
SKILL_TIERS = __dep_common.SKILL_TIERS
SKIPPED = __dep_common.SKIPPED
TEMPLATE_ENTRY_VALUES = __dep_common.TEMPLATE_ENTRY_VALUES
TICKET_FILING_RE = __dep_common.TICKET_FILING_RE
sys = __dep_common.sys
re = __dep_common.re

ENVELOPE_CARRIER_RE = re.compile(
    r"^\s*(?:the\s+)?(?:completed|finished)\s+(?:ticket|work[- ]item)\b",
    re.IGNORECASE,
)
ENVELOPE_FIELD_LEAD_RE = re.compile(r"^\s*status\s*[,;—-]", re.IGNORECASE)

from tools.validate_support import packages as __dep_packages
Diagnostics = __dep_packages.Diagnostics
_read_source = __dep_packages._read_source
_split_frontmatter = __dep_packages._split_frontmatter
body_words = __dep_packages.body_words
parse_frontmatter = __dep_packages.parse_frontmatter
rel = __dep_packages.rel

def validate_craft_budget(pkg: dict, diag: Diagnostics) -> None:
    craft = pkg["path"] / "references" / "craft.md"
    if not craft.is_file():
        diag.warn(rel(craft), SKIPPED)
        return
    n = sum(1 for ln in _read_source(craft).split("\n") if ln.strip())
    if n > CRAFT_BUDGET:
        diag.error(rel(craft), f"craft reference has {n} non-empty lines, exceeds the craft budget of {CRAFT_BUDGET}")


def validate_reference_links(body: str, pkg: dict, diag: Diagnostics) -> None:
    file_label = rel(pkg["skill_md"])
    for match in MD_LINK_RE.finditer(body):
        target = match.group(1)
        if "references/" not in target:
            continue
        resolved = _doclint().resolve_link(pkg["skill_md"], target)
        if resolved is None:
            continue
        if not resolved.is_file():
            diag.error(file_label, f"cited reference does not exist: {target}")


def build_call_graph(packages, diag: Diagnostics):
    names = {pkg["path"].name for pkg in packages}
    graph = {pkg["path"].name: set() for pkg in packages}
    for pkg in packages:
        file_label = rel(pkg["skill_md"])
        text = _read_source(pkg["skill_md"])
        for match in CALL_TOKEN_RE.finditer(text):
            token = match.group(1)
            if token in ROLE_PROFILES:
                continue
            if token not in names:
                diag.error(file_label, f"backtick reference `{token}` does not resolve to any skill or pack")
                continue
            graph[pkg["path"].name].add(token)
    return graph


def find_cycle(graph: dict):
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {node: WHITE for node in graph}

    def dfs(node, stack):
        color[node] = GRAY
        stack.append(node)
        for nxt in sorted(graph.get(node, ())):
            state = color.get(nxt, WHITE)
            if state == WHITE:
                found = dfs(nxt, stack)
                if found:
                    return found
            elif state == GRAY:
                idx = stack.index(nxt)
                return stack[idx:] + [nxt]
        stack.pop()
        color[node] = BLACK
        return None

    for node in sorted(graph):
        if color[node] == WHITE:
            cycle = dfs(node, [])
            if cycle:
                return cycle
    return None


def validate_call_graph(packages, diag: Diagnostics) -> None:
    graph = build_call_graph(packages, diag)
    cycle = find_cycle(graph)
    if cycle:
        name_to_file = {pkg["path"].name: pkg["skill_md"] for pkg in packages}
        label = rel(name_to_file[cycle[0]]) if cycle[0] in name_to_file else "call-graph"
        diag.error(label, f"call graph cycle: {' -> '.join(cycle)}")
    # composition rule 1: kernel and utility skills are primitives.
    for pkg in packages:
        if pkg["kind"] in ("kernel", "utilities") and graph.get(pkg["path"].name):
            called = ", ".join(sorted(graph[pkg["path"].name]))
            tier = "kernel" if pkg["kind"] == "kernel" else "utility"
            diag.error(
                rel(pkg["skill_md"]),
                f"{tier} skill has call edges ({called}); {tier} skills are primitives and call no skill",
            )


def _envelope_first_clause(body: str):
    """The Return paragraph's first sentence, or None when the body has
    no Return paragraph (anatomy already reports that)."""
    m = RETURN_TEXT_RE.search(body)
    if not m:
        return None
    return CARRIAGE_SENTENCE_SPLIT_RE.split(m.group(1), maxsplit=1)[0]


def _envelope_missing(clause: str) -> list:
    """The envelope fields whose vocabulary the first clause lacks; []
    when the clause instead names the work-item carrier, whose T0 shape
    carries all three fields."""
    if ENVELOPE_CARRIER_RE.search(clause):
        return []
    return [label for label, pattern in ENVELOPE_VOCAB_RES if not pattern.search(clause)]


def validate_envelope(packages, diag: Diagnostics) -> None:
    """contracts/result.md: every bound dispatchable unit leads its
    Return: with status, result identity, and verification."""
    for pkg in packages:
        if pkg["path"].name not in ENVELOPE_UNITS and pkg["kind"] != "instances":
            continue
        clause = _envelope_first_clause(pkg["body"])
        if clause is None:
            continue  # missing Return already reported by validate_anatomy
        missing = _envelope_missing(clause)
        if missing:
            diag.error(
                rel(pkg["skill_md"]),
                "Return does not lead with the result envelope per contracts/result.md: "
                f"first clause carries no {', '.join(missing)} vocabulary "
                "and names no work-item carrier",
            )
        elif not ENVELOPE_CARRIER_RE.search(clause) and not ENVELOPE_FIELD_LEAD_RE.search(clause):
            diag.error(
                rel(pkg["skill_md"]),
                "Return does not lead with structured result-envelope fields per "
                "contracts/result.md",
            )


def discover_templates(manifest_name: str):
    """Every `compositions/<name>/` directory holding the manifest."""
    comps_dir = ROOT / "compositions"
    if not comps_dir.is_dir():
        return []
    return sorted(
        d for d in comps_dir.iterdir()
        if d.is_dir() and (d / manifest_name).is_file()
    )


def _doclint():
    """`scripts/doclint.py`, the one owner of markdown link resolution and
    of the near-duplicate method (ARCHITECTURE.md). This compiler is one of
    its two callers; a project running the script is the other.

    Imported on first use for `_ticket_law`'s reason, one line below:
    `--pin` and every isolated fixture that carries no `scripts/` still has
    to run, and only the checks that ask these two questions need the
    owner. ROOT goes first on the path so a tree grades against its own
    copy.
    """
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from scripts import doclint

    return doclint


def _ticket_law():
    """`scripts/tickets.py`, the one owner of ticket-shape and
    template-graph law.

    Imported here rather than at module scope: `--pin` and every isolated
    fixture that carries no `scripts/` still has to run, and this is the
    only check that needs the owner. ROOT goes first on the path so a tree
    grades against its own copy.
    """
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from scripts import tickets

    return tickets


def _validate_template_manifest(path: Path, diag: Diagnostics):
    """Check one template.md; return its declared placeholder names, or
    None when it declares no usable list -- with the declaration
    unreadable, an undeclared placeholder is the manifest's defect and
    not each stub's."""
    file_label = rel(path)
    fm, _ = parse_frontmatter(_read_source(path), file_label, diag)
    if fm is None:
        return None
    name = fm.get("name")
    directory = path.parent.name
    if not name:
        diag.error(file_label, "template frontmatter missing required key 'name'")
    elif name != directory:
        diag.error(
            file_label,
            f"template name '{name}' does not match directory name '{directory}'",
        )
    description = fm.get("description")
    if not description:
        diag.error(file_label, "template frontmatter missing required key 'description'")
    elif len(description) > DESCRIPTION_BUDGET:
        diag.error(
            file_label,
            f"description is {len(description)} chars, exceeds {DESCRIPTION_BUDGET}-char budget",
        )
    entry = fm.get("entry")
    if not entry:
        diag.error(file_label, "template frontmatter missing required key 'entry'")
    elif entry not in TEMPLATE_ENTRY_VALUES:
        diag.error(
            file_label,
            f"entry '{entry}' is not one of {sorted(TEMPLATE_ENTRY_VALUES)} "
            "per contracts/work-item.md",
        )
    if "placeholders" not in fm:
        diag.error(file_label, "template frontmatter missing required key 'placeholders'")
        return None
    declared = fm["placeholders"].strip()
    if not (declared.startswith("[") and declared.endswith("]")):
        diag.error(
            file_label,
            "'placeholders' is not a list; write [] when the template declares none",
        )
        return None
    return {item.strip() for item in declared[1:-1].split(",") if item.strip()}


def _validate_stub_executor(
    executor: str, file_label: str, skill_names: set, diag: Diagnostics, tickets
) -> None:
    """The executor names a skill in the tree or a script that exists --
    the half of executor law that needs the tree, and so cannot live with
    the rest of it in scripts/tickets.py. What shape an executor may take
    at all is that script's, and it reports on that itself.

    A placeholder is left to instantiation, which refuses an unfilled one
    and so checks the filled value.
    """
    if tickets.PLACEHOLDER_RE.search(executor):
        return
    if executor.startswith(tickets.SCRIPT_EXECUTOR_PREFIX):
        target = executor[len(tickets.SCRIPT_EXECUTOR_PREFIX):].strip()
        if not (ROOT / target).exists():
            diag.error(
                file_label,
                f"executor names script '{target}', which does not exist in the tree",
            )
        return
    if executor not in skill_names:
        diag.error(
            file_label,
            f"executor '{executor}' names no skill under skills/ and is not a "
            "'script:<path>'",
        )


def _tree_skill_names() -> set:
    """Every skill package name across the five tiers -- the set a stub's
    executor resolves against."""
    names = set()
    for tier in SKILL_TIERS:
        tier_dir = ROOT / "skills" / tier
        if not tier_dir.is_dir():
            continue
        names |= {d.name for d in tier_dir.iterdir() if (d / "SKILL.md").is_file()}
    return names


def validate_templates(diag: Diagnostics) -> None:
    """contracts/work-item.md, Template and stub: every `compositions/<name>/` template is a
    manifest plus ticket stubs a run can be instantiated from.

    Ticket shape and the depends_on graph are read from
    `scripts/tickets.py`, which grades every issued ticket and every
    instantiated stub: the validator admits into the tree exactly what that
    script will accept, in that script's own words. What stays here is what
    needs the tree the script has no access to -- the manifest, the
    placeholder balance between manifest and stubs, and whether an executor
    names a skill or a script that exists.
    """
    if not (ROOT / "compositions").is_dir():
        diag.warn("compositions", SKIPPED)  # no tree, so no template
        return
    tickets = _ticket_law()
    manifest_name = tickets.TEMPLATE_FILE
    directories = discover_templates(manifest_name)
    if not directories:
        diag.warn("compositions", "holds no {0}; check skipped".format(manifest_name))
        return
    skill_names = _tree_skill_names()
    for directory in directories:
        manifest_label = rel(directory / manifest_name)
        declared = _validate_template_manifest(directory / manifest_name, diag)
        for path, message in tickets.template_defects(directory):
            diag.error(rel(Path(path)), message)

        manifest_text = _read_source(directory / manifest_name)
        n = body_words(_split_frontmatter(manifest_text)[1])
        if n > MANIFEST_BUDGET:
            diag.error(manifest_label, f"manifest has {n} words, exceeds the budget of {MANIFEST_BUDGET}")
        used = set()
        for path in sorted(directory.glob("*.md")):
            if path.name == manifest_name:
                continue
            text = _read_source(path)
            n = tickets.instruction_words(text)
            if n > tickets.INSTRUCTION_BUDGET:
                diag.error(rel(path), f"stub instruction has {n} words, exceeds the budget of {tickets.INSTRUCTION_BUDGET}")
            stub_used = set(tickets.PLACEHOLDER_RE.findall(text))
            used |= stub_used
            executor = tickets._parse_frontmatter(text).get("executor")
            if isinstance(executor, str) and executor.strip():
                _validate_stub_executor(
                    executor.strip(), rel(path), skill_names, diag, tickets
                )
            if declared is not None:
                for name in sorted(stub_used - declared):
                    diag.error(
                        rel(path),
                        f"placeholder '{{{{{name}}}}}' is declared by no "
                        f"'placeholders' entry in {manifest_label}",
                    )
        if declared is not None:
            for name in sorted(declared - used):
                diag.warn(
                    manifest_label,
                    f"declared placeholder '{{{{{name}}}}}' is used by no stub",
                )


# LOOP_TRIGGER_RE fires only on the imperative/procedural verb forms that
# actually instruct the reader to iterate -- "iterate"/"iterating" or "repeat
# until" -- never on the bare noun "loop" or "iteration", which this corpus
# uses only referentially ("the loop's done-check", "iteration entries", "a
# later iteration", "never a loop"). A noun mention names something -- often
# another skill's bound loop -- without itself being a bound-less instruction
# to iterate, so it carries no obligation to also state a bound/terminal term
# (REVIEW-2026-08-06.md thread T7: false positives on orch-worklog and
# orch-triage, neither of which instructs iteration).

__all__ = (
    'validate_craft_budget', 'validate_reference_links', 'build_call_graph', 'find_cycle',
    'validate_call_graph', '_envelope_first_clause', '_envelope_missing', 'validate_envelope',
    'discover_templates', '_doclint', '_ticket_law', '_validate_template_manifest',
    '_validate_stub_executor', '_tree_skill_names', 'validate_templates',
)
