"""Validate call graphs, envelopes, and templates."""

from __future__ import annotations
from . import common as __dep_common
CALL_TOKEN_RE = __dep_common.CALL_TOKEN_RE
CARRIAGE_SENTENCE_SPLIT_RE = __dep_common.CARRIAGE_SENTENCE_SPLIT_RE
CRAFT_BUDGET = __dep_common.CRAFT_BUDGET
DESCRIPTION_BUDGET = __dep_common.DESCRIPTION_BUDGET
ENVELOPE_UNITS = __dep_common.ENVELOPE_UNITS
ENVELOPE_VOCAB_RES = __dep_common.ENVELOPE_VOCAB_RES
BODY_BUDGET = __dep_common.BODY_BUDGET
MD_LINK_RE = __dep_common.MD_LINK_RE
Path = __dep_common.Path
RETURN_TEXT_RE = __dep_common.RETURN_TEXT_RE
ROLE_PROFILES = __dep_common.ROLE_PROFILES
ROOT = __dep_common.ROOT
SKIPPED = __dep_common.SKIPPED
TICKET_FILING_RE = __dep_common.TICKET_FILING_RE
sys = __dep_common.sys
re = __dep_common.re
ENVELOPE_CARRIER_RE = re.compile(
    r"^\s*(?:the\s+)?(?:completed|finished)\s+(?:ticket|work[- ]item)\b", re.IGNORECASE
)
ENVELOPE_FIELD_LEAD_RE = re.compile(r"^\s*status\s*[,;—-]", re.IGNORECASE)

# U8's sole legacy exception is data, not a relaxed classifier.  The date
# names the review that admitted the already-shipped browser-game machinery;
# every other composition, including every future one, takes the closed rule.
COMPOSITION_PROTOCOL_ALLOWLIST = {"browser-game": "2026-08-28"}
COMPOSITION_SCRIPT_SUFFIXES = frozenset({
    ".bat", ".cmd", ".js", ".mjs", ".cjs", ".ps1", ".py", ".sh", ".ts",
})
COMPOSITION_SCHEMA_RE = re.compile(r"(?:^|[._-])schemas?(?:[._-]|$)", re.IGNORECASE)
COMPOSITION_FIXTURE_RE = re.compile(r"(?:^|[._-])fixtures?(?:[._-]|$)", re.IGNORECASE)
from . import packages as __dep_packages
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
def build_call_graph(packages, diag: Diagnostics, known=None):
    """The call edges these packages carry, refusing one that resolves to
    nothing.

    ``known`` names every item a call may resolve to, and defaults to the
    packages themselves -- the library grades a closed tree, where the two
    sets are one. A ring is the open case: its items call the library by
    name, so a caller grading one passes the wider set and an edge out of
    the ring stays an edge rather than becoming a refusal.
    """

    names = set(known) if known is not None else {pkg["path"].name for pkg in packages}
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


def validate_call_graph(packages, diag: Diagnostics, known=None) -> None:
    graph = build_call_graph(packages, diag, known)
    cycle = find_cycle(graph)
    if cycle:
        name_to_file = {pkg["path"].name: pkg["skill_md"] for pkg in packages}
        label = rel(name_to_file[cycle[0]]) if cycle[0] in name_to_file else "call-graph"
        diag.error(label, f"call graph cycle: {' -> '.join(cycle)}")
    # composition rule 1: kernel skills are primitives.
    for pkg in packages:
        if pkg["kind"] == "kernel" and graph.get(pkg["path"].name):
            called = ", ".join(sorted(graph[pkg["path"].name]))
            diag.error(rel(pkg["skill_md"]),
                       f"kernel skill has call edges ({called}); kernel skills are primitives and call no skill")


def validate_domain_blindness(packages, diag: Diagnostics) -> None:
    """Reject pack-owned names in executable machinery.

    Pack directories are the data owner for both their canonical identity and
    their executor/assembly names.  Reading those names from the discovered
    pack signatures keeps this check extensible: adding a pack automatically
    expands the invariant without editing validator code.
    """
    names = {pkg["path"].name for pkg in packages if pkg["is_pack"]}
    if not names:
        return
    for directory_name in ("scripts", "tools"):
        directory = ROOT / directory_name
        if not directory.is_dir():
            continue
        for path in sorted(directory.rglob("*.py")):
            text = _read_source(path)
            matches = sorted(name for name in names if name in text)
            for name in matches:
                diag.error(
                    rel(path),
                    f"domain-specific name `{name}` appears in machinery; "
                    "select behavior through pack data",
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
    bound = set(ENVELOPE_UNITS)
    for pkg in packages:
        if pkg["path"].name not in bound:
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
            diag.error(rel(pkg["skill_md"]),
                       "Return does not lead with structured result-envelope fields per contracts/result.md")


def _composition_artifact_kind(path: Path):
    """The forbidden protocol class carried by ``path``, if any."""

    name = path.name
    if COMPOSITION_SCHEMA_RE.search(name):
        return "schema"
    if COMPOSITION_FIXTURE_RE.search(name):
        return "fixture format"
    if path.suffix.lower() in COMPOSITION_SCRIPT_SUFFIXES:
        return "script"
    return None


def _reference_owner(path: Path, composition_names):
    """Resolve a shared reference's composition from its bounded filename."""

    name = path.name.lower()
    for composition in sorted(composition_names, key=lambda item: (-len(item), item)):
        lowered = composition.lower()
        if name.startswith(lowered + "-") or name.startswith(lowered + "_"):
            return composition
    return None


def _script_owner(path: Path, composition_names):
    """Resolve a script module's composition by a normalized stem boundary."""

    stem = path.stem.lower()
    for composition in sorted(composition_names, key=lambda item: (-len(item), item)):
        normalized = composition.lower().replace("-", "_")
        if stem == normalized or stem.startswith(normalized + "_"):
            return composition
    return None


def validate_composition_admission(
    diag: Diagnostics, allowlist=COMPOSITION_PROTOCOL_ALLOWLIST
) -> None:
    """Reject protocol artifacts owned by composition templates.

    Ownership is physical inside ``example-workflows/<name>/`` or explicit in the
    bounded name of a shared ``example-workflows/references`` artifact.  The latter
    is how the pre-existing browser-game schemas and fixture format ship.
    """

    compositions = ROOT / "example-workflows"
    if not compositions.is_dir():
        return
    directories = sorted(
        path for path in compositions.iterdir()
        if path.is_dir() and path.name != "references"
    )
    names = {path.name for path in directories}
    findings = []
    for directory in directories:
        for path in sorted(directory.rglob("*")):
            kind = _composition_artifact_kind(path) if path.is_file() else None
            if kind:
                findings.append((directory.name, path, kind))
    references = compositions / "references"
    if references.is_dir():
        for path in sorted(references.rglob("*")):
            kind = _composition_artifact_kind(path) if path.is_file() else None
            owner = _reference_owner(path, names) if kind else None
            if owner:
                findings.append((owner, path, kind))
    scripts = ROOT / "scripts"
    if scripts.is_dir():
        for path in sorted(scripts.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in COMPOSITION_SCRIPT_SUFFIXES:
                continue
            owner = _script_owner(path, names)
            if owner:
                findings.append((owner, path, "workflow-named script machinery"))

    excepted = {}
    for composition, path, kind in findings:
        if composition in allowlist:
            excepted.setdefault(composition, []).append((path, kind))
            continue
        diag.error(
            rel(path),
            f"workflow '{composition}' carries forbidden {kind}; "
            "a workflow contains only its SKILL.md body and reference prose",
        )
    for composition in sorted(excepted):
        date = allowlist[composition]
        kinds = ", ".join(sorted({kind for _, kind in excepted[composition]}))
        diag.warn(
            f"example-workflows/{composition}",
            f"dated {date} workflow-protocol exception admits existing {kinds}; "
            "the allowlist grants no exception to another workflow",
        )


def _doclint():
    """`scripts/doclint.py`, the one owner of markdown link resolution and
    of the near-duplicate method (ARCHITECTURE.md). This compiler is one of
    its two callers; a project running the script is the other.

    Imported on first use: every isolated fixture that carries no
    `scripts/` still has to run, and only the checks that ask this
    question need the owner. ROOT goes first on the path so a tree grades
    against its own copy.
    """
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    try:
        from scripts import doclint
    except ImportError:  # pragma: no cover - direct/installed flat script path
        import doclint

    return doclint


def workflow_roots():
    """The library's workflow directories, in the resolver's search order.

    ``scripts/rings.py`` owns where a workflow lives; reading its list here
    keeps the tree this grades and the tree a runtime resolves through the
    same tree. Imported on first use, like ``_doclint``: an isolated
    fixture carrying no ``scripts/`` still has to run every other check.
    """

    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    try:
        from scripts.rings import LIB_DIRS
    except ImportError:  # pragma: no cover - direct/installed flat script path
        from rings import LIB_DIRS

    return [ROOT / relative for relative in LIB_DIRS["workflow"]]


def validate_templates(diag: Diagnostics, roots=None) -> None:
    """Every workflow directory entry is one workflow skill.

    A workflow is a skill whose prose calls callables, so the checks are a
    skill's: the name matches its directory, the description is present and
    inside the shared budget, the body is inside the workflow tier's word
    budget, and the manual-invocation flag is declared. The last is the one
    check with no skill analogue -- a workflow's prose runs as orchestrator
    reasoning rather than inside a sealed child prompt, so a host firing one
    on its own reading of a description opens that surface uninvited.

    The library keeps workflows in two directories, and one name in both is
    refused here rather than resolved: the resolver would answer with the
    nearer of the two and shadow the other silently, and no author writes a
    workflow meaning to hide one they cannot see.

    What a callable call is, and whether one is well formed, is `scripts/
    tickets.py`'s and is reported there; nothing in a body is graded here.

    ``roots`` names the directories to walk, defaulting to the library's
    two. A ring keeps its workflows in one directory of its own
    (`scripts/rings.py`'s ``RING_DIRS``), and grading them is the same
    question about the same shape, so it is this function asked about that
    directory rather than a second one written beside it.
    """
    budget = BODY_BUDGET["workflows"]
    homes = {}
    for comps_dir in (workflow_roots() if roots is None else list(roots)):
        if not comps_dir.is_dir():
            diag.warn(rel(comps_dir), SKIPPED)  # no tree, so no workflow
            continue
        for directory in sorted(d for d in comps_dir.iterdir() if d.is_dir()):
            manifest = directory / "SKILL.md"
            if not manifest.is_file():
                continue  # shared references, not a name surface
            label = rel(manifest)
            first = homes.setdefault(directory.name, label)
            if first != label:
                diag.error(
                    label,
                    f"workflow name '{directory.name}' is also at {first}; "
                    "a workflow name lives in one library directory",
                )
            fm, body = parse_frontmatter(_read_source(manifest), label, diag)
            if fm is None:
                continue
            name = fm.get("name")
            if not name:
                diag.error(label, "workflow frontmatter missing required key 'name'")
            elif name != directory.name:
                diag.error(
                    label,
                    f"workflow name '{name}' does not match directory name "
                    f"'{directory.name}'",
                )
            description = fm.get("description")
            if not description:
                diag.error(label, "workflow frontmatter missing required key 'description'")
            elif len(description) > DESCRIPTION_BUDGET:
                diag.error(
                    label,
                    f"description is {len(description)} chars, exceeds "
                    f"{DESCRIPTION_BUDGET}-char budget",
                )
            if fm.get("disable-model-invocation") != "true":
                diag.error(
                    label,
                    "workflow frontmatter must declare 'disable-model-invocation: "
                    "true'; a workflow is invoked by name only",
                )
            n = body_words(body)
            if n > budget:
                diag.error(
                    label,
                    f"workflow body has {n} words, exceeds the workflow-tier "
                    f"budget of {budget}",
                )


# LOOP_TRIGGER_RE matches iteration verbs, not the referential nouns "loop" or
# "iteration", so noun mentions carry no bound obligation (review thread T7).

__all__ = (
    'validate_craft_budget', 'validate_reference_links', 'build_call_graph', 'find_cycle',
    'validate_call_graph', 'validate_domain_blindness', '_envelope_first_clause', '_envelope_missing',
    'validate_envelope', 'COMPOSITION_PROTOCOL_ALLOWLIST', 'COMPOSITION_SCRIPT_SUFFIXES',
    'COMPOSITION_SCHEMA_RE', 'COMPOSITION_FIXTURE_RE',
    '_composition_artifact_kind', '_reference_owner', '_script_owner', 'validate_composition_admission',
    '_doclint', 'workflow_roots', 'validate_templates',
)
