"""Validate cell and cross-tier duplication."""

from __future__ import annotations


def _doclint():
    from tools.validate_support.structure import _doclint as doclint
    return doclint()

from tools.validate_support import common as __dep_common
CELL_CLAUSE_MIN_WORDS = __dep_common.CELL_CLAUSE_MIN_WORDS
CELL_REFERENCE_LINK_RE = __dep_common.CELL_REFERENCE_LINK_RE
CELL_SIMILARITY_THRESHOLD = __dep_common.CELL_SIMILARITY_THRESHOLD
CRAFT_CELLS_BY_POINTER = __dep_common.CRAFT_CELLS_BY_POINTER
MANDATED_FORM_RES = __dep_common.MANDATED_FORM_RES
PACK_CELL_ROW_RE = __dep_common.PACK_CELL_ROW_RE
PACK_SIGNATURE_CELLS = __dep_common.PACK_SIGNATURE_CELLS
ROOT = __dep_common.ROOT
re = __dep_common.re

from tools.validate_support import packages as __dep_packages
Diagnostics = __dep_packages.Diagnostics
_read_source = __dep_packages._read_source
cell_clauses = __dep_packages.cell_clauses
rel = __dep_packages.rel

CELL_DUPLICATION_ALLOWLIST = (
    {
        "family": "code<->design git-workspace seam",
        "reason": (
            "The code and design packs both run on git, so their workspace "
            "cells share the worktree-per-item clause and the conflict "
            "binding, their required_spec_fields share the standards-owner "
            "pointer, and their oracle tables share the build/type and "
            "standards-shape rows -- both of which ask the workspace's own "
            "tooling the same question. A "
            "workspace-kind abstraction factoring those mechanics out is not "
            "worth a permanent concept for two packs: this duplication is "
            "paid consciously and revisited when a third git-workspace pack "
            "appears -- that arrival is the trigger, not a judgment call."
        ),
        # Normalized clauses, matched exactly. The seam's other two halves
        # -- 'standards owner by pointer' and 'conflict binding
        # `orch-resolve-conflicts`' -- sit under CELL_CLAUSE_MIN_WORDS and so
        # never reach this list; lowering the floor would surface them here.
        "clauses": (
            "each frontier item gets its own worktree branched from the run's "
            "current revision at dispatch, merged at the join",
            "build/type the workspace's build and typecheck commands "
            "deterministic pre-existing",
            "standards shape the workspace's linter, formatter, or validator "
            "deterministic pre-existing",
        ),
    },
)


def _cell_content(pkg: dict, cell: str, binding: str):
    """(text, label) for the content behind one cell. A pointer cell
    resolves to its reference file -- four of the eight rows are
    byte-identical in every pack, and :758 mandates one of them, so
    comparing the row instead of what it points at convicts the
    signature itself."""
    if cell in CRAFT_CELLS_BY_POINTER:
        match = CELL_REFERENCE_LINK_RE.search(binding)
        if match:
            target = pkg["path"] / match.group(1)
            if target.is_file():
                return _read_source(target), rel(target)
    return binding, rel(pkg["skill_md"])


def free_content(clause: str) -> str:
    """`clause` minus every span MANDATED_FORM_RES names -- what is left
    is the pack's own. A remainder under CELL_CLAUSE_MIN_WORDS words is
    the floor's case exactly: a label, not content."""
    for pattern in MANDATED_FORM_RES:
        clause = pattern.sub(" ", clause)
    return re.sub(r"\s+", " ", clause).strip()


def validate_cell_duplication(packages, diag: Diagnostics) -> None:
    """Per signature cell, compare the content behind it across packs:
    a clause carried verbatim by two packs is an error, a clause pair
    whose free_content matches at CELL_SIMILARITY_THRESHOLD or above is a
    warning naming both sites. Allowlisted clauses are out of the
    comparison entirely."""
    packs = [pkg for pkg in packages if pkg["is_pack"]]
    if len(packs) < 2:
        return
    allowed = set()
    for family in CELL_DUPLICATION_ALLOWLIST:
        allowed.update(family["clauses"])

    for cell in PACK_SIGNATURE_CELLS:
        per_pack = []
        for pkg in packs:
            binding = dict(PACK_CELL_ROW_RE.findall(pkg.get("body", ""))).get(cell)
            if binding is None:
                continue
            text, label = _cell_content(pkg, cell, binding)
            per_pack.append((label, [c for c in cell_clauses(text) if c not in allowed]))

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
                f"{cell}: cell content duplicated verbatim in "
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
                                f"{cell}: cell content near-duplicate at "
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
# contracts/verdict.md owns the law that a citation must resolve;
# packs/orch-research-pack/references/oracles.md carries a row saying
# which oracle decides that criterion in this domain, at which class and
# provenance. The signature mandates that table, and a pack cannot state
# an oracle policy without naming the criterion it decides.
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
# orch-edit and orch-synthesize both forbid an assembly step inventing a
# claim its inputs did not carry -- sections for one, evidence packets
# for the other. It is one law with two subjects and no owner: rules/
# has no assembly rule to hold it, and inventing one for two clauses
# buys a permanent concept for a sentence. Revisited when a third
# assembly instance needs it, which is when the rule earns its file.
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
        "contracts/verdict.md",
        "packs/orch-research-pack/references/oracles.md",
        "citation",
    ),
    (
        "skills/instances/orch-synthesize/SKILL.md",
        "skills/instances/orch-edit/SKILL.md",
        "Never: introduce",
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
    compositions = ROOT / "compositions"
    if compositions.is_dir():
        for path in sorted(compositions.rglob("*.md")):
            documents.append(("compositions", rel(path), _read_source(path)))
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

__all__ = (
    'CELL_DUPLICATION_ALLOWLIST', '_cell_content', 'free_content', 'validate_cell_duplication',
    'CROSS_TIER_DUPLICATE_LEVEL', 'CROSS_TIER_CITATION_RES', 'CROSS_TIER_PROSE_MIN_WORDS', '_cross_tier_prose',
    'SAME_TIER_COMPARED', 'LICENSED_COPIES', '_licensed', 'cross_tier_documents',
    '_cross_tier_clauses', '_cross_tier_accept', 'validate_cross_tier_duplication',
)
