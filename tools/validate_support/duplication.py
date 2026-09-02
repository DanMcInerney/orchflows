"""Validate cell and cross-tier duplication."""

from __future__ import annotations


def _doclint():
    from .structure import _doclint as doclint
    return doclint()

from . import common as __dep_common
CELL_CLAUSE_MIN_WORDS = __dep_common.CELL_CLAUSE_MIN_WORDS
CELL_REFERENCE_LINK_RE = __dep_common.CELL_REFERENCE_LINK_RE
CELL_SIMILARITY_THRESHOLD = __dep_common.CELL_SIMILARITY_THRESHOLD
CRAFT_CELLS_BY_POINTER = __dep_common.CRAFT_CELLS_BY_POINTER
MANDATED_FORM_RES = __dep_common.MANDATED_FORM_RES
PACK_CELL_ROW_RE = __dep_common.PACK_CELL_ROW_RE
PACK_SIGNATURE_CELLS = __dep_common.PACK_SIGNATURE_CELLS
ROOT = __dep_common.ROOT
re = __dep_common.re

from . import packages as __dep_packages
Diagnostics = __dep_packages.Diagnostics
_read_source = __dep_packages._read_source
cell_clauses = __dep_packages.cell_clauses
rel = __dep_packages.rel

CELL_DUPLICATION_ALLOWLIST = (
    {
        "family": "identity-term workspace naming",
        "reason": (
            "The signature's craft-section table requires every Workspace "
            "section to open by naming its adapter semantics and identity "
            "unit -- 'X: identities are Y' -- so these clauses rhyme by "
            "mandate, not by drift. Each names a different adapter and a "
            "different identity unit; only the mandated skeleton matches."
        ),
        # Normalized clauses, matched exactly.
        "clauses": (
            "document tree: identities are document revisions",
            "git plus render: identities are view identities",
            "evidence store: identities are evidence packets",
        ),
    },
    {
        "family": "verification-scope anchor",
        "reason": (
            "scripts/tickets_assignment.py's _craft_scope() reads a pack's "
            "own verification-scope sentence out of its `## Stages` (or "
            "`## Lens`) section by the literal anchor \"gate's row\", so "
            "the one-suite law (research/routing-design-2026-08-31.md "
            "\"The one-suite law\") reaches every pack the same way: "
            "children run their own narrow affected checks, and the full "
            "required suite is the closing `done`'s alone. Every pack "
            "carries this sentence by that mandate, not by drift -- each "
            "names its own check vocabulary, and the closing clause "
            "states the shared law itself, which has exactly one wording."
        ),
        "clauses": (
            "Run the narrow affected checks",
            "Run the narrow affected document checks",
            "Run the narrow affected computation replay",
            "Run the narrow affected render checks",
            "Run the narrow affected source verification",
            "the full suite is the gate's row, never a unit's",
        ),
    },
)


def _cell_content(pkg: dict, cell: str, binding: str):
    """(text, label) for the content behind one cell. A pointer cell
    resolves to its reference file -- every pack's craft row is mandated
    to bind references/craft.md, so comparing the row instead of what it
    points at convicts the signature itself."""
    if cell in CRAFT_CELLS_BY_POINTER:
        match = CELL_REFERENCE_LINK_RE.search(binding)
        if match:
            target = pkg["path"] / match.group(1)
            if target.is_file():
                return _read_source(target), rel(target)
    return binding, rel(pkg["skill_md"])


CRAFT_SECTION_RE = re.compile(r"(?m)^##\s+(.*\S)\s*$")


def _craft_sections(text: str) -> dict:
    """{section name: body} for one craft document's `##` sections.

    `###` subsections stay inside their parent's body; the fold made the
    craft document the one prose owner, so the `##` heading is the unit
    the signature's craft-section table names and the linter compares.
    """
    sections = {}
    matches = list(CRAFT_SECTION_RE.finditer(text))
    for i, match in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        sections[match.group(1)] = text[match.end():end]
    return sections


def free_content(clause: str) -> str:
    """`clause` minus every span MANDATED_FORM_RES names -- what is left
    is the pack's own. A remainder under CELL_CLAUSE_MIN_WORDS words is
    the floor's case exactly: a label, not content."""
    for pattern in MANDATED_FORM_RES:
        clause = pattern.sub(" ", clause)
    return re.sub(r"\s+", " ", clause).strip()


def validate_cell_duplication(packages, diag: Diagnostics) -> None:
    """Per same-named craft section, compare the content behind it across
    packs: a clause carried verbatim by two packs is an error, a clause
    pair whose free_content matches at CELL_SIMILARITY_THRESHOLD or above
    is a warning naming both sites. Allowlisted clauses are out of the
    comparison entirely. Differently named sections never compare — the
    section heading scopes the comparison the way the cell name did."""
    packs = [pkg for pkg in packages if pkg["is_pack"]]
    if len(packs) < 2:
        return
    allowed = set()
    for family in CELL_DUPLICATION_ALLOWLIST:
        allowed.update(family["clauses"])

    per_section = {}
    for pkg in packs:
        binding = dict(PACK_CELL_ROW_RE.findall(pkg.get("body", ""))).get("craft")
        if binding is None:
            continue
        text, label = _cell_content(pkg, "craft", binding)
        for name, body in _craft_sections(text).items():
            clauses = [c for c in cell_clauses(body) if c not in allowed]
            per_section.setdefault(name, []).append((label, clauses))

    for name in sorted(per_section):
        per_pack = per_section[name]

        sites = {}
        for label, clauses in per_pack:
            for clause in clauses:
                sites.setdefault(clause, set()).add(label)
        for clause, labels in sorted(sites.items()):
            if len(labels) < 2:
                continue
            ordered = sorted(labels)
            diag.error(
                ordered[0],
                f"{name}: craft section duplicated verbatim in "
                f"{', '.join(ordered[1:])}: {clause!r}",
            )

        for i in range(len(per_pack)):
            for j in range(i + 1, len(per_pack)):
                left_label, left_clauses = per_pack[i]
                right_label, right_clauses = per_pack[j]
                for left in left_clauses:
                    left_free = free_content(left)
                    if len(left_free.split()) < CELL_CLAUSE_MIN_WORDS:
                        continue
                    for right in right_clauses:
                        if left == right:
                            continue
                        right_free = free_content(right)
                        if len(right_free.split()) < CELL_CLAUSE_MIN_WORDS:
                            continue
                        ratio = _doclint().similarity(left_free, right_free)
                        if ratio >= CELL_SIMILARITY_THRESHOLD:
                            diag.warn(
                                left_label,
                                f"{name}: craft section near-duplicate at "
                                f"{ratio:.2f} with {right_label}: "
                                f"{left!r} ~ {right!r}",
                            )


# --- Cross-tier duplication (REVIEW-2026-08-15 T2) --------------------
#
# The same clause comparison as validate_cell_duplication, run across the
# library's tiers instead of across the packs of one signature cell. It is
# what replaces keeping copies in sync: a clause carried by both a rule and
# a skill body is a fact with two owners, and the compiler names both sites
# rather than holding the two spellings equal (REVIEW-2026-08-15 T2).
#
# WARN for exactly one phase. The tree still carries the copies P3 deletes,
# and a compiler that refuses its own tree cannot be run; the finding is
# the inventory P3 works from. At P3's close this flips to "ERROR" and
# tests/test_cell_linter.py's CROSS_TIER_WARNING_CEILING reaches 0.
CROSS_TIER_DUPLICATE_LEVEL = "WARN"
# The pairing index is `doclint.DISTINCTIVE_MAX`'s, and this corpus is
# where its value was measured: every pair an exhaustive comparison
# reports above 0.66 survives the index, and what it drops sits in the
# noise band just over the threshold. Exhaustive here is 470,000 ratios
# and 45 seconds of a compiler that must be cheap enough to run on every
# save.
# A citation and a name are not content. Every tier cites the same
# contracts and names the same skills, so a clause that is nothing but
# links and backticked names is the library's shared vocabulary, and
# convicting it would drive files to stop pointing at their owners -- the
# reason cell_clauses already exempts a sentence citing an owner outside
# its pack. One connective word ("see", "per") does not make it prose.
CROSS_TIER_CITATION_RES = (
    re.compile(r"\[[^\]]*\]\([^)]*\)"),
    re.compile(r"`[^`]*`"),
)
CROSS_TIER_PROSE_MIN_WORDS = 2


def _cross_tier_prose(clause: str) -> str:
    """`clause` minus its markdown links and backticked names."""
    for pattern in CROSS_TIER_CITATION_RES:
        clause = pattern.sub(" ", clause)
    return re.sub(r"\s+", " ", clause).strip()


# Two files of one tier are usually that tier's own business: the pack
# linter already owns that question inside packs, and a template's stubs
# are graded against their own manifest. skills/ has no such second check,
# so two skill bodies could carry one clause byte for byte while the
# linter flagged each of them against some innocent third file in another
# tier -- the one pair it could not see was the pair that mattered.
SAME_TIER_COMPARED = frozenset({"skills"})

# A copy the library licensed, and the fact it copies. Each entry is
# (owner, copy, a phrase both carry): the pair alone would exempt these
# two files from every future duplication, and the phrase keeps the
# licence to the clause it was granted for.
#
# rules/visibility.md §6 owns the untrusted-data rule; templates/host-block.md
# carries it because the block is the one text a host reads before it can
# reach any rule, and it names the owner one line above the copy. Reporting
# it asks for the copy to go, which would take the licence with it.
#
# docs/library-review.md and templates/host-block.md both name
# rules/visibility.md as the owner of a question they ask about the sink
# -- the review asks whether a sentence is the only copy of its fact, the
# block tells a host where the sink is and under which section. Two
# different questions, and what makes them read alike is the citation
# both are obliged to carry. Reporting it asks one of them to stop
# naming its owner.
#
# docs/library-review.md's Constitution principle 8 owns the value that
# machinery is domain-blind and a domain enters as data, never as control
# flow; contracts/pack-signature.md states the same fact as its own purity
# consequence -- the thing the signature exists to enforce. Reporting the
# pair asks the contract to stop stating what it enforces. The DESIGN.md,
# ARCHITECTURE.md and README.md restatements sit outside this corpus by
# design: rationale, map, and human surfaces, with the fact owned in law
# (join ruling, 20260823T210000Z-trunk-slimming, checker finding F9).
#
LICENSED_COPIES = (
    (
        "rules/visibility.md",
        "templates/host-block.md",
        "untrusted data",
    ),
    (
        "docs/library-review.md",
        "templates/host-block.md",
        "rules/visibility.md",
    ),
    (
        "docs/library-review.md",
        "contracts/pack-signature.md",
        "control flow",
    ),
)


def _licensed(left_label: str, left_clause: str, right_label: str, right_clause: str) -> bool:
    """Whether this pair is a copy the library licensed, for this clause."""

    labels = {left_label.replace("\\", "/"), right_label.replace("\\", "/")}
    if "Never: introduce" in left_clause and "Never: introduce" in right_clause:
        return all(
            (ROOT / label).is_file()
            and "Never: introduce" in _read_source(ROOT / label)
            for label in labels
        )
    for owner, copy, phrase in LICENSED_COPIES:
        if labels == {owner, copy} and phrase in left_clause and phrase in right_clause:
            return True
    return False


def cross_tier_documents(packages):
    """(tier, label, text) for every file the check reads, tier being the
    directory the library gave it."""
    documents = []
    for pkg in packages:
        tier = "packs" if pkg["is_pack"] else "skills"
        documents.append((tier, rel(pkg["skill_md"]), pkg.get("body") or ""))
        if pkg["is_pack"]:
            for reference in sorted((pkg["path"] / "references").glob("*.md")):
                documents.append(("packs", rel(reference), _read_source(reference)))
    for tier in ("rules", "contracts", "docs"):
        directory = ROOT / tier
        if directory.is_dir():
            for path in sorted(directory.glob("*.md")):
                # docs/vocabulary.md is the definitional owner of every
                # term: an entry is one line naming the term's meaning and
                # its owner, so a contract or skill using the term in its
                # defined sense reads as its near-duplicate by construction.
                # That pair is the relation the vocabulary exists to create,
                # not a second owner; the file stays out of this corpus.
                if tier == "docs" and path.name == "vocabulary.md":
                    continue
                documents.append((tier, rel(path), _read_source(path)))
    # Every template stub and every reference beside them. This is where a
    # composition's own criteria live, and each of the seven templates was
    # written against a reference it was told to link -- restatement the
    # check could not see because the corpus stopped at the tiers that
    # existed when it was written.
    compositions = ROOT / "example-workflows"
    if compositions.is_dir():
        for path in sorted(compositions.rglob("*.md")):
            documents.append(("example-workflows", rel(path), _read_source(path)))
    host_block = ROOT / "templates" / "host-block.md"
    if host_block.is_file():
        documents.append(("templates", rel(host_block), _read_source(host_block)))
    return documents


def _cross_tier_clauses(packages):
    """Every comparable clause, as (tier, label, clause, free_content).
    Same splitter and same mandated-form stripping as the pack linter, plus
    the citation exemption above."""
    entries = []
    for tier, label, text in cross_tier_documents(packages):
        for clause in cell_clauses(text):
            free = free_content(clause)
            if len(free.split()) < CELL_CLAUSE_MIN_WORDS:
                continue
            if len(_cross_tier_prose(free).split()) < CROSS_TIER_PROSE_MIN_WORDS:
                continue
            entries.append((tier, label, clause, free))
    return entries


def _cross_tier_accept(entries):
    """Which of doclint's candidate pairs this library compares: two
    tiers, or two files of one tier the pack linter cannot see, and never
    a copy the library licensed."""

    def accept(left: int, right: int) -> bool:
        left_tier, left_label, left_clause, _ = entries[left]
        right_tier, right_label, right_clause, _ = entries[right]
        if left_tier == right_tier:
            # Two skills, never one skill against its own clauses: a body's
            # Require, its steps and its Return restate one fact by design,
            # and that is the pack linter's question.
            if left_tier not in SAME_TIER_COMPARED or left_label == right_label:
                return False
        return not _licensed(left_label, left_clause, right_label, right_clause)

    return accept


def validate_cross_tier_duplication(packages, diag: Diagnostics) -> None:
    """Every clause of every skill body, rule, contract, pack reference and
    the host-block template against every clause of another tier, through
    `doclint.near_duplicate_pairs`: a pair matching at
    CELL_SIMILARITY_THRESHOLD or above is reported at
    CROSS_TIER_DUPLICATE_LEVEL, naming both sites."""
    entries = _cross_tier_clauses(packages)
    tiers = {tier for tier, _, _, _ in entries}
    if len(tiers) < 2 and not tiers & SAME_TIER_COMPARED:
        # One tier, and not one compared with itself: nothing to compare
        # across. That is a partial tree -- the isolated fixtures carry
        # `contracts/` and `tools/` alone -- which carries no `scripts/`
        # for `_doclint` to find either.
        return
    emit = diag.warn if CROSS_TIER_DUPLICATE_LEVEL == "WARN" else diag.error
    pairs = _doclint().near_duplicate_pairs(
        [free for _, _, _, free in entries],
        CELL_SIMILARITY_THRESHOLD,
        accept=_cross_tier_accept(entries),
    )
    for left, right, ratio in pairs:
        left_tier, left_label, left_clause, _ = entries[left]
        right_tier, right_label, right_clause, _ = entries[right]
        # one finding, one wording: the ratchet in
        # tests/test_cell_linter.py counts this check by its own words,
        # and a same-tier pair is the same finding — a clause with two
        # owners — reached from inside one tier
        where = "" if left_tier != right_tier else f" (within {left_tier})"
        emit(
            left_label,
            f"cross-tier near-duplicate{where} at {ratio:.2f} with "
            f"{right_label}: {left_clause!r} ~ {right_clause!r}",
        )



# --- generated-enum ratchet ---------------------------------------------------
# The shapes whose value sets a script may not restate. Named, not swept:
# a one-value enum matches too easily to be worth a blanket rule, and the
# roster starts at exactly the enums the fact registry consolidated.
RATCHETED_ENUMS = (
    ("dispatch_record", "kind"),
    ("executor_result", "operation"),
    ("done_binding", "form"),
)
# The two modules the ratchet exists to protect: one is generated from the
# contract, the other is the reserved namespace's declared owner.
ENUM_OWNER_MODULES = ("tickets_shapes.py", "tickets_dispatch_identity.py")
RESERVED_RECORD_PREFIXES = ("join:", "lifecycle:")


def _generated_value_sets(root=None) -> dict:
    """Every ratcheted value set, keyed by the set, named by its owner.

    Read from `contracts/shapes.json` rather than the generated module, so
    the ratchet grades a script against the contract itself and one read
    answers for every script below.
    """

    import json

    root = ROOT if root is None else root
    try:
        data = json.loads((root / "contracts" / "shapes.json").read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError):
        return {}
    found = {}
    for shape in data.get("shapes") or ():
        for field, values in (shape.get("values") or {}).items():
            if (shape.get("name"), field) in RATCHETED_ENUMS:
                found[frozenset(values)] = (
                    f"contracts/shapes.json's {shape['name']}.{field}"
                )
    constants = data.get("constants") or {}
    reserved = frozenset(
        value for key, value in constants.items() if key.endswith("_record_id")
    )
    if reserved:
        found[reserved] = "the reserved record-id namespace"
    found[frozenset(RESERVED_RECORD_PREFIXES)] = "the reserved record-id prefixes"
    return found


def _module_string_sets(text: str):
    """Every module-level assignment of a literal set of strings.

    A collection built out of names is not a restatement -- it is already
    reading its values from somewhere -- so only literals are collected,
    and the one wrapping call a frozenset needs is looked through.
    """

    import ast

    try:
        tree = ast.parse(text)
    except SyntaxError:
        return
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        value = node.value
        if (
            isinstance(value, ast.Call)
            and isinstance(value.func, ast.Name)
            and value.func.id in ("frozenset", "set", "tuple", "list")
            and value.args
        ):
            value = value.args[0]
        if not isinstance(value, (ast.Set, ast.Tuple, ast.List)) or not value.elts:
            continue
        if not all(
            isinstance(item, ast.Constant) and isinstance(item.value, str)
            for item in value.elts
        ):
            continue
        names = [target.id for target in node.targets if isinstance(target, ast.Name)]
        yield (names[0] if names else "<unnamed>"), frozenset(
            item.value for item in value.elts
        ), node.lineno


def validate_generated_enum_copies(diag: Diagnostics, root=None) -> None:
    """Refuse a script that restates a value set a generated shape owns.

    The duplicated-facts class this ratchet closes: an enum lives in
    `contracts/shapes.json`, the generated module exposes it, and a script
    then spells the same members inline. The two agree until the contract
    moves, and the one that did not move is the one a caller was reading.
    """

    root = ROOT if root is None else root
    owned = _generated_value_sets(root)
    if not owned:
        return
    for source in sorted((root / "scripts").glob("*.py")):
        if source.name in ENUM_OWNER_MODULES:
            continue
        try:
            text = source.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for name, values, line in _module_string_sets(text):
            owner = owned.get(values)
            if owner is None:
                continue
            diag.error(
                source.relative_to(root).as_posix(),
                f"line {line}: `{name}` restates {owner}; import the "
                "generated value set instead of spelling its members",
            )


__all__ = (
    'ENUM_OWNER_MODULES', 'RATCHETED_ENUMS', '_generated_value_sets',
    '_module_string_sets', 'validate_generated_enum_copies',
    'CELL_DUPLICATION_ALLOWLIST', '_cell_content', 'CRAFT_SECTION_RE', '_craft_sections',
    'free_content', 'validate_cell_duplication',
    'CROSS_TIER_DUPLICATE_LEVEL', 'CROSS_TIER_CITATION_RES', 'CROSS_TIER_PROSE_MIN_WORDS', '_cross_tier_prose',
    'SAME_TIER_COMPARED', 'LICENSED_COPIES', '_licensed', 'cross_tier_documents',
    '_cross_tier_clauses', '_cross_tier_accept', 'validate_cross_tier_duplication',
)
