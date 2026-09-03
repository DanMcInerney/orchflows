"""Discover packages and validate their local structure."""

from __future__ import annotations

from . import common as __dep_common
ALLOWED_FRONTMATTER_KEYS = __dep_common.ALLOWED_FRONTMATTER_KEYS
ASSEMBLY_NONE_FORM_RE = __dep_common.ASSEMBLY_NONE_FORM_RE
ASSEMBLY_SKILL_FORM_RE = __dep_common.ASSEMBLY_SKILL_FORM_RE
BODY_BUDGET = __dep_common.BODY_BUDGET
CELL_CLAUSE_MIN_WORDS = __dep_common.CELL_CLAUSE_MIN_WORDS
CRAFT_ROW_RE = __dep_common.CRAFT_ROW_RE
DESCRIPTION_BUDGET = __dep_common.DESCRIPTION_BUDGET
LINK_TARGET_RE = __dep_common.LINK_TARGET_RE
LIST_MARKER_RE = __dep_common.LIST_MARKER_RE
NEVER_RE = __dep_common.NEVER_RE
OUTSIDE_PACK_CITATION = __dep_common.OUTSIDE_PACK_CITATION
PACK_CELL_ROW_RE = __dep_common.PACK_CELL_ROW_RE
PACK_SIGNATURE_CELLS = __dep_common.PACK_SIGNATURE_CELLS
PACK_TYPED_CELLS = __dep_common.PACK_TYPED_CELLS
PACK_ADAPTER_RE = __dep_common.PACK_ADAPTER_RE
PACK_STAGE_RE = __dep_common.PACK_STAGE_RE
PACK_TABLE_CELL_RE = __dep_common.PACK_TABLE_CELL_RE
Path = __dep_common.Path
REQUIRE_RE = __dep_common.REQUIRE_RE
RETURN_RE = __dep_common.RETURN_RE
APPLIED_ROLE_VALUES = __dep_common.APPLIED_ROLE_VALUES
ROLE_VALUES = __dep_common.ROLE_VALUES
ROOT = __dep_common.ROOT
ROUTING_BLOCK_BUDGET = __dep_common.ROUTING_BLOCK_BUDGET
SENTENCE_END_RE = __dep_common.SENTENCE_END_RE
SIGNATURE_CELL_POINTER_RE = __dep_common.SIGNATURE_CELL_POINTER_RE
SKILL_TIERS = __dep_common.SKILL_TIERS
SKIPPED = __dep_common.SKIPPED
SURFACE_BUDGET = __dep_common.SURFACE_BUDGET
TABLE_DELIM_ROW_RE = __dep_common.TABLE_DELIM_ROW_RE
re = __dep_common.re
sys = __dep_common.sys

# The de-quoting primitive is `scripts/tickets_format`'s, imported rather
# than respelled: this validator and the runtime read the same cell values,
# and the four inline `.strip("`")` sites here were the tools-layer half of
# the twenty-one that graded a padded value as a different value from its
# bare twin. `tools` may import `scripts`; the reverse is what is forbidden.
#
# An install ships this package under `lib/` so `orchflows check` can run
# these checks over a ring, and the scripts it reads sit flat in `bin/`
# with no `scripts` package above them. The paired import is the tree's
# own idiom for that layout: one module, reached under either name.
try:
    from scripts.tickets_format import dequote
except ImportError:  # pragma: no cover - direct/installed flat script path
    from tickets_format import dequote

CONTRACTS_DIR = ROOT / "contracts"
PINS_FILE = ROOT / "tests" / "pins.json"
PIN_MESSAGE = (
    "T0 contract changed; if intentional, re-pin via: "
    "python tools/validate.py --pin"
)


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT)).replace("\\", "/")


def _read_source(path: Path) -> str:
    # utf-8-sig: a BOM-prefixed file (e.g. PowerShell Out-File default) must
    # still parse as valid frontmatter -- plain utf-8 leaves the BOM glued to
    # the opening '---' line, which a byte-for-byte compare then rejects.
    return path.read_text(encoding="utf-8-sig")


class Diagnostics:
    def __init__(self):
        self.items = []  # list[(level, file, message)]

    def error(self, file_label: str, message: str) -> None:
        self.items.append(("ERROR", file_label, message))

    def warn(self, file_label: str, message: str) -> None:
        self.items.append(("WARN", file_label, message))

    @property
    def has_errors(self) -> bool:
        return any(level == "ERROR" for level, _, _ in self.items)

    def lines(self):
        ordered = sorted(self.items, key=lambda item: (item[1], item[0], item[2]))
        return [f"{level} {file_label}: {message}" for level, file_label, message in ordered]


def workflow_tiers() -> frozenset:
    """The skills tiers that are library workflow homes.

    ``scripts/rings.py`` owns where a workflow lives, so the tier graded
    here as a workflow and the tier a runtime resolves one through are one
    fact. Imported on first use, like ``structure.workflow_roots``, and
    under either name for the same reason ``dequote`` is: an isolated
    fixture carrying no ``scripts/`` still has to run every other check,
    and an install ships this package beside flat scripts in ``bin/``.
    """

    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    try:
        from scripts.rings import LIB_DIRS
    except ImportError:  # pragma: no cover - direct/installed flat script path
        from rings import LIB_DIRS

    return frozenset(
        relative.split("/", 1)[1]
        for relative in LIB_DIRS["workflow"]
        if relative.startswith("skills/")
    )


def discover_packages():
    """Return every skill/pack package as a dict with path, kind, skill_md.

    A tier directory holding only ``references/`` is not a package and is
    not a defect in itself -- the ``is_file()`` guard below reads it as no
    package rather than as a package missing its SKILL.md. It is not a
    home a reference may keep, though: ``rules/visibility.md`` §4 makes a
    references file public only where its owner's body names the local
    path, and a directory with no body names nothing. ``profiles.md``
    therefore lives beside the host records it describes, in ``hosts/``,
    rather than under a skill that no longer exists to name it.
    """
    packages = []
    for tier in SKILL_TIERS:
        tier_dir = ROOT / "skills" / tier
        if not tier_dir.is_dir():
            continue
        for pkg_dir in sorted(tier_dir.iterdir()):
            if not pkg_dir.is_dir():
                continue
            skill_md = pkg_dir / "SKILL.md"
            if skill_md.is_file():
                packages.append({
                    "path": pkg_dir,
                    "skill_md": skill_md,
                    "kind": tier,
                    "is_pack": False,
                })
    packs_dir = ROOT / "packs"
    if packs_dir.is_dir():
        for pkg_dir in sorted(packs_dir.iterdir()):
            if not pkg_dir.is_dir():
                continue
            skill_md = pkg_dir / "SKILL.md"
            if skill_md.is_file():
                packages.append({
                    "path": pkg_dir,
                    "skill_md": skill_md,
                    "kind": "pack",
                    "is_pack": True,
                })
    return packages


def parse_frontmatter(text: str, file_label: str, diag: Diagnostics):
    """Manually parse the '---' fenced frontmatter. Returns (dict, body) or (None, None)."""
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        diag.error(file_label, "missing opening frontmatter fence '---'")
        return None, None
    end_idx = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end_idx = i
            break
    if end_idx is None:
        diag.error(file_label, "missing closing frontmatter fence '---'")
        return None, None
    fm = {}
    for ln in lines[1:end_idx]:
        if not ln.strip():
            continue
        if ":" not in ln:
            diag.error(file_label, f"malformed frontmatter line: {ln!r}")
            continue
        key, _, value = ln.partition(":")
        fm[key.strip()] = value.strip()
    body = "\n".join(lines[end_idx + 1:])
    return fm, body


def validate_frontmatter(fm: dict, pkg: dict, diag: Diagnostics) -> None:
    file_label = rel(pkg["skill_md"])
    extra = set(fm) - ALLOWED_FRONTMATTER_KEYS
    for key in sorted(extra):
        diag.error(file_label, f"frontmatter key '{key}' is not allowed")

    if "name" not in fm or not fm["name"]:
        diag.error(file_label, "frontmatter missing required key 'name'")
    else:
        expected = pkg["path"].name
        if fm["name"] != expected:
            diag.error(
                file_label,
                f"frontmatter name '{fm['name']}' does not match folder name '{expected}'",
            )

    if "description" not in fm or not fm["description"]:
        diag.error(file_label, "frontmatter missing required key 'description'")
    elif len(fm["description"]) > DESCRIPTION_BUDGET:
        diag.error(
            file_label,
            f"description is {len(fm['description'])} chars, exceeds {DESCRIPTION_BUDGET}-char budget",
        )

    if "disable-model-invocation" in fm and fm["disable-model-invocation"] not in ("true", "false"):
        diag.error(
            file_label,
            f"disable-model-invocation must be 'true' or 'false', got {fm['disable-model-invocation']!r}",
        )


def validate_role(fm: dict, pkg: dict, diag: Diagnostics, allowed=None) -> None:
    """The `role:` law, over whichever set of roles this door admits.

    `allowed` is the library's three by default. `orchflows check` passes the
    two an *applied* skill may declare, because a ring skill is only ever
    entered through a `--skill` dispatch and `rules/roles.md` clause 6
    refuses that entry for `role: none`. One function, so a missing key and a
    role outside the set read the same at both doors and name the same file.
    """

    allowed = ROLE_VALUES if allowed is None else allowed
    file_label = rel(pkg["skill_md"])
    if pkg["is_pack"]:
        if "role" in fm:
            diag.error(file_label, "pack frontmatter must not declare 'role'")
        return
    role = fm.get("role")
    if pkg["kind"] in workflow_tiers():
        if role:
            diag.error(
                file_label,
                f"workflow declares role '{role}'; a workflow is invoked by "
                "name into the driver's own context and never forked, so it "
                "declares no role, exactly as the gallery home's do",
            )
        return
    if not role:
        diag.error(file_label, "frontmatter missing required key 'role'")
        return
    if role not in allowed:
        diag.error(file_label, f"role '{role}' is not one of {sorted(allowed)}")


def validate_anatomy(body: str, pkg: dict, diag: Diagnostics) -> None:
    file_label = rel(pkg["skill_md"])
    operative = re.sub(r"(?ms)^(```|~~~).*?^\1[^\n]*$", "", body)
    if pkg["is_pack"]:
        for label in ("Require:", "Never:", "Return:"):
            if label in operative:
                diag.error(file_label, f"pack body must not contain '{label}' (packs carry no control flow)")
        flow = r"\bif\b[^.\n]{0,160}\bthen\b|\b(?:delegate|dispatch|spawn|stop|park|refuse)\b"
        if re.search(flow, operative, re.IGNORECASE):
            diag.error(file_label, "pack body carries control flow; packs provide data only")
        return
    require = REQUIRE_RE.search(operative)
    never = NEVER_RE.search(operative)
    return_matches = list(RETURN_RE.finditer(operative))
    returning = return_matches[-1] if return_matches else None
    if not require:
        diag.error(file_label, "skill body missing a line starting 'Require:'")
    if not never:
        diag.error(file_label, "skill body missing a line starting 'Never:'")
    if not returning:
        diag.error(file_label, "skill body missing a sentence starting 'Return'")
    if not (require and never and returning and require.start() < never.start() < returning.start()):
        diag.error(file_label, "skill body missing ordered Require/procedure/Never/Return anatomy")
        return
    return_tail = operative[returning.start():].strip()
    if len([part for part in re.split(r"\n[ \t]*\n", return_tail) if part.strip()]) > 1:
        diag.error(file_label, "Return must be the terminal paragraph")


def body_words(body: str) -> int:
    """The body's word count with markdown link targets stripped."""
    return len(LINK_TARGET_RE.sub("]", body).split())


def _split_frontmatter(text: str):
    parts = text.split("---", 2)
    return (parts[1], parts[2]) if len(parts) > 2 else ("", text)


def validate_surface_budgets(diag: Diagnostics) -> None:
    """The every-turn surfaces against rules/token-economy.md §11."""
    for name, limit in SURFACE_BUDGET.items():
        path = ROOT / name
        if not path.is_file():
            diag.warn(name, SKIPPED)  # a partial tree carries no router
            continue
        n = body_words(_read_source(path))
        if n > limit:
            diag.error(name, f"surface has {n} words, exceeds the every-turn budget of {limit}")


def validate_routing_block(text: str, label: str, diag: Diagnostics, limit: int = ROUTING_BLOCK_BUDGET) -> None:
    """A project's router file (routing + friction law, the project
    instance of docs/documentation.md's router factory row) against its
    default every-turn ceiling -- rules/token-economy.md §11,
    `ROUTING_BLOCK_BUDGET`.

    No renderer or sync mechanism installs a project-scope routing block in
    this tree today (`ROUTING_BLOCK_BUDGET`'s own comment, common.py, has
    the verified evidence), so this check has no live file of its own to
    scan here -- it is exercised directly, by synthetic text, the same way
    tests/test_architecture_owners.py's `CEILING_RE` exercises its
    can-fail direction against a padded copy rather than a second tree
    (rules/verification.md Section 8). This checker is deliberately ahead
    of its surface: it is the enforcement half of the render surface the
    "Host-block root/child split" Deferred item in
    research/architecture-repair-spec-2026-09-01.md will create, so a
    dead-code sweep must not delete it for lacking a caller today -- it
    gets wired in there once that split lands."""

    n = body_words(text)
    if n > limit:
        diag.error(label, f"routing block has {n} words, exceeds the every-turn budget of {limit}")


def validate_budget(body: str, pkg: dict, diag: Diagnostics) -> None:
    file_label = rel(pkg["skill_md"])
    n = body_words(body)
    tier = "pack" if pkg["is_pack"] else pkg["kind"]
    limit = BODY_BUDGET[tier]
    if n > limit:
        diag.error(file_label, f"body has {n} words, exceeds the {tier} budget of {limit}")


def validate_pack_signature(body: str, pkg: dict, diag: Diagnostics) -> None:
    file_label = rel(pkg["skill_md"])
    rows = PACK_TABLE_CELL_RE.findall(body)
    found = set(rows)
    unknown = sorted(found - set(PACK_SIGNATURE_CELLS) - {"cell"})
    if unknown:
        diag.error(file_label, f"pack signature table has unknown cell(s): {', '.join(unknown)}")
    missing = [cell for cell in PACK_SIGNATURE_CELLS if cell not in found]
    if missing:
        diag.error(file_label, f"pack signature table missing cell(s): {', '.join(missing)}")
    repeated = sorted(cell for cell in PACK_SIGNATURE_CELLS if rows.count(cell) > 1)
    if repeated:
        diag.error(file_label, f"pack signature table repeats cell(s): {', '.join(repeated)}")
    row = CRAFT_ROW_RE.search(body)
    if row and "(references/craft.md)" not in row.group(1):
        diag.error(file_label, "craft cell must bind [references/craft.md](references/craft.md)")
    cells = dict(PACK_CELL_ROW_RE.findall(body))
    if "adapter" in cells and not PACK_ADAPTER_RE.match(dequote(cells["adapter"])):
        diag.error(
            file_label,
            f"adapter cell must be one registered mechanism key, got: {cells['adapter']!r}",
        )
    stages = []
    if "stages" in cells:
        raw_stages = cells["stages"].strip()
        if not (raw_stages.startswith("[") and raw_stages.endswith("]")):
            diag.error(file_label, f"stages cell must be a bracketed list, got: {raw_stages!r}")
        else:
            stages = [dequote(part) for part in raw_stages[1:-1].split(",") if part.strip()]
            if any(not PACK_STAGE_RE.fullmatch(stage) for stage in stages):
                diag.error(file_label, f"stages cell has an invalid stage, got: {raw_stages!r}")
            if len(stages) != len(set(stages)):
                diag.error(file_label, "stages cell repeats a stage")
    if "assembly" in cells:
        raw_assembly = cells["assembly"].strip()
        assembly = dequote(raw_assembly)
        if raw_assembly != assembly or (
            assembly != "none" and (
                not PACK_STAGE_RE.fullmatch(assembly)
                or (stages and assembly not in stages)
            )
        ):
            diag.error(file_label, f"assembly cell must be none or a declared stage, got: {cells['assembly']!r}")


def assembly_form_ok(binding: str, stages=None) -> bool:
    """Return whether one typed assembly value is closed and stage-backed."""
    raw = binding.strip()
    value = dequote(raw)
    if value == "none":
        return raw == "none"
    return raw == value and bool(PACK_STAGE_RE.fullmatch(value)) and (not stages or value in stages)


def cell_clauses(text: str) -> list:
    """Split the content behind a cell into clauses -- the normative
    comparison unit of validate_cell_duplication.

    A clause is one assertion: a markdown table's data row, or a
    sentence, cut again at every ';' because this library's prose joins
    independent assertions with the semicolon (a workspace section is one
    such list). A ',' is not a cut point: it joins parts of one
    assertion, and cutting there reports shared connective idiom
    ('never by count') as duplicated content.

    Structure is not content and never compares: table header and
    delimiter rows, headings, list markers, and any sentence citing an
    owner outside the pack. That last one is the pointer or stated
    deviation rules/visibility.md §3 and rules/token-economy.md §7
    require every pack to share once content moves to one owner --
    convicting it would drive packs to stop deferring. It is decided per
    sentence, before the ';' cut: the deviation half carries no citation
    of its own, so cutting first strands it outside the exemption.

    Whitespace collapses first, so two packs whose only difference is
    where a 75-column line wraps still read as one clause. A clause
    under CELL_CLAUSE_MIN_WORDS words is a label or a term of art, not
    content: the signature intends packs to name the same terms.
    """
    lines = text.split("\n")
    structural = set()
    for i, line in enumerate(lines):
        if TABLE_DELIM_ROW_RE.match(line.strip()):
            structural.add(i)
            if i:
                structural.add(i - 1)  # the header row the delimiter underlines
    blocks = []
    paragraph = []

    def flush():
        if paragraph:
            blocks.append(" ".join(paragraph))
            del paragraph[:]

    for i, line in enumerate(lines):
        stripped = line.strip()
        if i in structural or not stripped or stripped.startswith("#"):
            flush()
            continue
        if stripped.startswith("|"):
            flush()
            blocks.append(" ".join(c.strip() for c in stripped.strip("|").split("|")))
            continue
        if LIST_MARKER_RE.match(stripped):
            flush()
        paragraph.append(LIST_MARKER_RE.sub("", stripped, count=1))
    flush()

    clauses = []
    for block in blocks:
        for sentence in SENTENCE_END_RE.split(block):
            # The exemption is decided on the whole sentence, before the ';'
            # cut and never after it: the citation and the deviation it
            # licenses are the two halves of one pointer, and a filter applied
            # to the halves keeps the deviation while discarding the citation
            # that exempts it -- convicting the very sentence the exemption
            # exists to protect.
            if OUTSIDE_PACK_CITATION in sentence or SIGNATURE_CELL_POINTER_RE.search(
                sentence
            ):
                continue
            for clause in sentence.split(";"):
                clause = re.sub(r"\s+", " ", clause).strip().strip(".").strip()
                if len(clause.split()) >= CELL_CLAUSE_MIN_WORDS:
                    clauses.append(clause)
    return clauses


# The one duplication this library keeps on purpose. An entry is a
# decision on the record, not a suppression: it says what the seam is,
# that the cost is paid consciously, and what reopens it.

__all__ = (
    'CONTRACTS_DIR', 'PINS_FILE', 'PIN_MESSAGE', 'rel',
    '_read_source', 'Diagnostics', 'workflow_tiers', 'discover_packages',
    'parse_frontmatter',
    'APPLIED_ROLE_VALUES',
    'validate_frontmatter', 'validate_role', 'validate_anatomy', 'body_words',
    '_split_frontmatter', 'validate_surface_budgets', 'validate_routing_block',
    'validate_budget', 'validate_pack_signature',
    'assembly_form_ok', 'cell_clauses',
)
