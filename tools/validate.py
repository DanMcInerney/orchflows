#!/usr/bin/env python3
"""The orchflows compiler.

Enforces package anatomy, frontmatter, call-graph acyclicity, pack
signature completeness, T0 hash pins, the composition contract, the
result-envelope lead, and owned-literal sync (budgets, envelope units,
friction categories) against their rules/ and contracts/ owners, per
AGENTS.md, ARCHITECTURE.md, rules/composition.md,
contracts/composition.md, contracts/result.md, and
contracts/pack-signature.md. Stdlib only, no network.

Exit 0 clean. Exit 1 with one line per violation:
    ERROR|WARN <file>: <message>
"""
from __future__ import annotations

import argparse
import ast
import difflib
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

SKILL_TIERS = ("kernel", "engines", "workflows", "instances", "utilities")
BODY_BUDGET = {
    "kernel": 25,
    "instances": 25,
    "utilities": 25,
    "engines": 40,
    "workflows": 40,
    "pack": 20,
}
DESCRIPTION_BUDGET = 140
ALLOWED_FRONTMATTER_KEYS = {"name", "description", "disable-model-invocation", "role"}
ROLE_PROFILES = {"orch-planner", "orch-worker"}
ROLE_VALUES = {"planner", "worker", "none"}
ROLE_NONE_TIERS = ("engines", "workflows")
PACK_SIGNATURE_CELLS = (
    "slicing",
    "executor",
    "assembly",
    "lens",
    "oracle_policy",
    "workspace",
    "required_spec_fields",
    "craft",
)
CRAFT_CELLS_BY_POINTER = ("slicing", "lens", "oracle_policy", "craft")
CRAFT_BUDGET = 60
# Cross-pack cell linter. Both figures are normative: with autojunk off
# at the ratio call below, the reported pair set is a function of them
# alone, so moving either changes what the check means, not only what it
# finds. SequenceMatcher's default autojunk would break that — it drops
# characters common in any sequence over 200 characters, suppressing the
# ratio on exactly the longest clauses.
CELL_SIMILARITY_THRESHOLD = 0.55
CELL_CLAUSE_MIN_WORDS = 5

CALL_TOKEN_RE = re.compile(r"`(orch-[a-z0-9-]+)`")
REQUIRE_RE = re.compile(r"^Require:", re.MULTILINE)
NEVER_RE = re.compile(r"^Never:", re.MULTILINE)
RETURN_RE = re.compile(r"^Return[ :]", re.MULTILINE)
PACK_TABLE_CELL_RE = re.compile(r"^\|\s*([a-zA-Z_]+)\s*\|", re.MULTILINE)
PACK_CELL_ROW_RE = re.compile(r"^\|\s*([a-zA-Z_]+)\s*\|\s*(.*?)\s*\|\s*$", re.MULTILINE)
CRAFT_ROW_RE = re.compile(r"^\|\s*craft\s*\|\s*(.+?)\s*\|", re.MULTILINE)
ASSEMBLY_SKILL_FORM_RE = re.compile(r"^`[a-z][a-z0-9-]*`$")
ASSEMBLY_NONE_FORM_RE = re.compile(r"^none\s+—\s+\S.*$")
CELL_REFERENCE_LINK_RE = re.compile(r"\]\((references/[^)]+)\)")
TABLE_DELIM_ROW_RE = re.compile(r"^\|(?:\s*:?-{2,}:?\s*\|)+\s*$")
LIST_MARKER_RE = re.compile(r"^(?:[-*+]|\d+[.)])\s+")
SENTENCE_END_RE = re.compile(r"(?<=[.!?])\s+")
OUTSIDE_PACK_CITATION = "](../"
# The same citation written as prose instead of a link: the reference file
# behind a pointer cell opens by naming the cell it satisfies, and the cell
# is contracts/pack-signature.md's, not the pack's. Dropped for
# OUTSIDE_PACK_CITATION's reason -- convicting it would drive a reference
# to stop saying which cell owns it.
SIGNATURE_CELL_POINTER_RE = re.compile(r"per the signature's [a-z_]+ cell")
# Spans an owner outside the pack mandates, so two packs carrying one carry
# it by obligation and not by duplication. Stripped before the
# near-duplicate ratio and nowhere else: the verbatim tier stays over the
# whole clause, because free content that is identical under a mandated
# skeleton is a real duplication and still an error.
MANDATED_FORM_RES = (
    # contracts/pack-signature.md: `assembly` is a backticked skill name or
    # the bare word none, an em-dash, and a gloss naming what stands in for
    # the assembly. validate_pack_signature errors on any third form, so
    # both the opener and the naming are obligatory, and only the noun
    # phrase between them is the pack's own.
    re.compile(r"^none\s+—\s+"),
    re.compile(r"\b(?:is|are) the assembly$"),
    # contracts/verdict.md's oracle_class enum -- three tokens -- and
    # contracts/work-item.md's provenance enum -- two. Both closed, both
    # T0-pinned, so every oracle row ends in one of six pairs.
    re.compile(
        r"\b(?:deterministic|judged|evidence)\s+(?:pre-existing|authored-here)$"
    ),
    # TestDependencyOrderedOverlap in tests/test_static_tree_invariants.py
    # asserts this exact wording in
    # orch-decompose's body and in both slicing cells that carry it: the
    # duplication is the invariant, holding every pack to overlap along
    # dependency order and off the old global-disjointness rule. A pack
    # cannot state it in its own words without breaking that check.
    re.compile(
        r"a write scope overlapping only siblings it is dependency-ordered with"
    ),
)
MD_LINK_RE = re.compile(r"\]\(([^)]+)\)")
LOOP_TRIGGER_RE = re.compile(r"\biterat(?:e|es|ing)\b|\brepeat until\b", re.IGNORECASE)
BOUND_TERM_RE = re.compile(r"bound|budget", re.IGNORECASE)
TERMINAL_TERM_RE = re.compile(r"stalled|limited|exit|terminal", re.IGNORECASE)

# --- Result envelope (contracts/result.md) ---------------------------
#
# The bound dispatchable units lead their Return: with the envelope --
# status, result identity, verification. ENVELOPE_UNITS is an owned
# literal checked against contracts/result.md's Binding paragraph by
# validate_sync. Mechanized as a first-clause vocabulary lint, tolerant
# of prose ordering within that clause; a Return whose first clause
# instead names the work-item carrier (the ticket) passes, because the
# ticket's T0 shape carries all three fields -- rule 10's envelope-on-a-
# named-T0-carrier form, the shape `orch-task` uses.
ENVELOPE_UNITS = (
    "orch-deliver",
    "orch-task",
    "orch-investigate",
    "orch-loop",
    "orch-compose",
    "orch-frontier",
)
ENVELOPE_VOCAB_RES = (
    ("status", re.compile(
        r"\bstatus\b|\bcomplete[ds]?\b|\bblocked\b|\bstalled\b|\blimited\b|\bfailed\b",
        re.IGNORECASE,
    )),
    ("result identity", re.compile(
        r"\bresults?\b|\bidentit(?:y|ies)\b|\bdeliverables?\b", re.IGNORECASE
    )),
    ("verification", re.compile(
        r"\bverification\b|\bverdicts?\b|\bverified\b", re.IGNORECASE
    )),
)

# --- Composition contract (contracts/composition.md) -----------------
#
# Every compositions/*.md is a normative, invocable workflow carrying
# the contract's fields. A field counts as present when it appears as a
# frontmatter key or as a line-leading label/heading in the body;
# `invariants` also counts via a `Never:` block, which the contract
# defines it as. Missing `invariants` or `done_check` is the contract's
# admission-rejection sentence, an ERROR.
COMPOSITION_ENTRY_VALUES = {"routed", "named", "scheduled"}
COMPOSITION_REQUIRED_FIELDS = ("steps", "edges")
COMPOSITION_ADMISSION_FIELDS = ("invariants", "done_check")
COMPOSITION_BODY_FIELD_RES = {
    "steps": re.compile(r"^(?:#{1,6}\s+)?\*{0,2}steps\*{0,2}\b:?", re.IGNORECASE | re.MULTILINE),
    "edges": re.compile(r"^(?:#{1,6}\s+)?\*{0,2}edges\*{0,2}\b:?", re.IGNORECASE | re.MULTILINE),
    "invariants": re.compile(r"^(?:#{1,6}\s+)?\*{0,2}invariants\*{0,2}\b:?", re.IGNORECASE | re.MULTILINE),
    "done_check": re.compile(r"^(?:#{1,6}\s+)?\*{0,2}done[ _-]check\*{0,2}\b:?", re.IGNORECASE | re.MULTILINE),
}

# --- Carriage (rules/composition.md rule 10) -------------------------
#
# "Every Require item rides a named T0 carrier ... the caller supplies
# each callee's Require item by that name." Mechanized as a lexical
# head-noun presence check — a heuristic licensed by this checker's own
# acceptance criterion (see _carriage_candidates below), so the parsing
# favors zero false ERRORs on the real tree over linguistic precision
# (see docs/vocabulary.md "carriage").
CARRIAGE_REQUIRE_BLOCK_RE = re.compile(r"^Require:(.*?)(?:\n[ \t]*\n|\Z)", re.MULTILINE | re.DOTALL)
CARRIAGE_SENTENCE_SPLIT_RE = re.compile(r"\.\s+(?=[A-Z])", re.DOTALL)
CARRIAGE_MD_LINK_RE = re.compile(r"\[([^\]]*)\]\([^)]*\)")
CARRIAGE_PAREN_RE = re.compile(r"\([^)]*\)")
CARRIAGE_CODE_RE = re.compile(r"`([^`]*)`")
CARRIAGE_WORD_RE = re.compile(r"[A-Za-z][A-Za-z'-]*")
CARRIAGE_DASH_SPLIT_RE = re.compile(r"[–—]")  # en dash, em dash
# Rule 10(c) / pack-signature.md's sharing constraint: "the executor's and
# assembly's Return files per work-item.md's filing law -- the ticket, or
# the store the packet names."
# That law's two filing destinations -- "the ticket -- or the store the
# packet names" -- are this check's two pass conditions: the bound skill's
# own body names the ticket/work-item filing, or the pack's workspace cell
# names a store (kernel-tier primitives like orch-investigate/orch-synthesize
# stay domain-blind per the redteam critique's Move 7 and rely on the
# second, rather than hardcoding pack-specific filing language).
TICKET_FILING_RE = re.compile(r"\bticket\b|\bwork[- ]item\b", re.IGNORECASE)
# The Return paragraph only -- "ticket" is common enough as an ordinary
# noun elsewhere in a body (e.g. a Require clause) that searching the
# whole body would false-pass on an unrelated mention.
RETURN_TEXT_RE = re.compile(r"^Return[ :](.*?)(?:\n[ \t]*\n|\Z)", re.MULTILINE | re.DOTALL)
PACK_WORKSPACE_RE = re.compile(r"^\|\s*workspace\s*\|\s*(.+?)\s*\|\s*$", re.MULTILINE)
PACK_STORE_RE = re.compile(r"\bstore\b", re.IGNORECASE)
PACK_EXECUTOR_RE = re.compile(r"^\|\s*executor\s*\|\s*`([a-z0-9-]+)`", re.MULTILINE)
PACK_ASSEMBLY_RE = re.compile(r"^\|\s*assembly\s*\|\s*`([a-z0-9-]+)`", re.MULTILINE)
PACK_SLICING_RE = re.compile(r"^\|\s*slicing\s*\|\s*\[.*?\]\(([^)]+)\)", re.MULTILINE)

# Closed-class words stripped from the head of a Require item and
# treated as a phrase boundary once real content has started -- never
# an open-class (adjective/noun) word, so the list stays principled
# rather than tuned per example.
CARRIAGE_QUALIFIERS = {
    "a", "an", "the", "one", "two", "three", "some", "any", "each", "every", "no",
    "another", "other", "its", "this", "that", "these", "those", "our", "your",
    "their", "my",
    "and", "or", "but", "nor", "more", "least", "several", "few",
    "of", "to", "in", "on", "at", "per", "for", "with", "without", "by", "as", "from",
    "which", "who", "whose", "when", "where", "if", "so", "than", "then",
    "never", "always", "only", "also", "while", "during", "among", "between", "across",
    "before", "after", "through", "via", "into", "onto", "under", "over", "beyond",
    "outside", "inside", "unless", "instead", "because", "naming", "carrying",
    "depending",
}

# Carriage gaps deferred pending a caller-prose fix. Keyed by ("edge",
# caller, callee, head_noun) or ("pack", pack_name, role, head_noun);
# the head_noun is the last-candidate extracted below. Emptied once
# every deferred site's caller carries its callee's head noun (ticket
# 02-carriage-nouns closed the run's last nine); a re-opened gap is a
# regression to fix at its caller, never a re-deferral (spec risk).
CARRIAGE_DEFERRED = {}


def _carriage_clean(text: str) -> str:
    text = CARRIAGE_MD_LINK_RE.sub(r"\1", text)
    text = CARRIAGE_CODE_RE.sub(r"\1", text)
    text = CARRIAGE_PAREN_RE.sub(" ", text)
    return text


def _carriage_stem_variants(word: str) -> set:
    """Light, deliberately approximate stemming (plural/gerund/participle
    suffixes, with the silent-e a verb like 'scoped' drops restored) so
    a Require item's noun and a caller's inflected use of it compare
    equal without a real lemmatizer."""
    w = word.lower()
    variants = {w}
    if w.endswith("'s"):
        variants.add(w[:-2])
    if len(w) > 4 and w.endswith("ies"):
        variants.add(w[:-3] + "y")
    if len(w) > 4 and (w.endswith("ches") or w.endswith("shes") or (w.endswith("es") and w[-3] in "sxz")):
        variants.add(w[:-2])
    if len(w) > 3 and w.endswith("s") and not w.endswith("ss"):
        variants.add(w[:-1])
    if len(w) > 5 and w.endswith("ing"):
        base = w[:-3]
        variants.add(base)
        variants.add(base + "e")
    if len(w) > 4 and w.endswith("ed"):
        base = w[:-2]
        variants.add(base)
        variants.add(base + "e")
    return variants


def _carriage_body_stems(text: str) -> set:
    text = _carriage_clean(text)
    stems = set()
    for w in CARRIAGE_WORD_RE.findall(text):
        stems |= _carriage_stem_variants(w)
    return stems


# A comma segment opening with one of these modifies the preceding
# input (an elaboration of its shape) rather than introducing a new
# caller-supplied one; such segments are not checked for carriage.
CARRIAGE_ELABORATION_LEADS = {
    "each", "every", "with", "whose", "which", "that", "what", "where",
    "when", "how", "carrying", "naming", "including", "excluding", "per",
}


def _carriage_segments(item: str) -> list:
    """A Require item's checkable segments: the dash-introduced aside
    dropped, the remainder split on commas, elaboration segments (lead
    token in CARRIAGE_ELABORATION_LEADS) skipped. Each surviving
    segment names something the caller must supply, so each is
    checked -- a first-segment-only read let every input after the
    first comma ride uncarried."""
    lead = CARRIAGE_DASH_SPLIT_RE.split(item, maxsplit=1)[0]
    segments = []
    for seg in (s.strip() for s in lead.split(",")):
        if not seg:
            continue
        tokens = [t.lower() for t in CARRIAGE_WORD_RE.findall(seg)]
        if tokens and tokens[0] in CARRIAGE_ELABORATION_LEADS:
            continue
        segments.append(seg)
    return segments


def _carriage_segment_nouns(segment: str) -> list:
    """Every content word of one segment (qualifiers dropped). A
    segment is carried when the target's vocabulary shares any of
    them -- the honest mechanization of "did the caller acknowledge
    this input"; a head-noun pair proved too brittle on segments
    longer than a bare noun phrase."""
    return [
        t.lower()
        for t in CARRIAGE_WORD_RE.findall(segment)
        if t.lower() not in CARRIAGE_QUALIFIERS
    ]


def _carriage_require_items(body: str):
    """The callee's Require items: the first sentence of the Require
    paragraph (later sentences are behavioral prose, not additional
    required fields), split on ';'."""
    m = CARRIAGE_REQUIRE_BLOCK_RE.search(body)
    if not m:
        return []
    first_sentence = CARRIAGE_SENTENCE_SPLIT_RE.split(m.group(1), maxsplit=1)[0]
    return [i.strip() for i in first_sentence.split(";") if i.strip()]


def _carriage_item_carried(item: str, target_stems: set):
    """Return (carried, head_noun) for one Require item against a
    target's stemmed vocabulary. Every checkable comma segment must
    carry (any of its content-word stems present); head_noun is the
    failing segment's last content word, else the final checked
    segment's."""
    cleaned = _carriage_clean(item)
    last_noun = None
    for seg in _carriage_segments(cleaned) or [cleaned]:
        nouns = _carriage_segment_nouns(seg)
        if not nouns:
            continue
        last_noun = nouns[-1]
        if not any(_carriage_stem_variants(n) & target_stems for n in nouns):
            return False, nouns[-1]
    return True, last_noun


def _carriage_flag(diag: Diagnostics, file_label: str, key: tuple, message: str) -> None:
    reason = CARRIAGE_DEFERRED.get(key)
    if reason:
        diag.warn(file_label, f"{message} -- deferred: {reason}")
    else:
        diag.error(file_label, message)


def validate_carriage(packages, diag: Diagnostics) -> None:
    """Rule 10: (a) each call edge A -> B carries every item of B's
    Require in A's body; (b)+(c) each pack's executor/assembly Require
    carries in the pack's slicing cell, and its Return names the
    ticket/work-item filing per work-item.md's filing law (or the pack's
    workspace names a store, the law's other filing destination)."""
    by_name = {pkg["path"].name: pkg for pkg in packages}
    graph = build_call_graph(packages, Diagnostics())  # unresolved-ref errors already reported once, by validate_call_graph

    for a_name in sorted(graph):
        a_pkg = by_name.get(a_name)
        if a_pkg is None or a_pkg["is_pack"]:
            continue
        a_stems = _carriage_body_stems(a_pkg["body"])
        file_label = rel(a_pkg["skill_md"])
        for b_name in sorted(graph[a_name]):
            b_pkg = by_name.get(b_name)
            if b_pkg is None:
                continue
            for item in _carriage_require_items(b_pkg["body"]):
                carried, head_noun = _carriage_item_carried(item, a_stems)
                if carried:
                    continue
                message = (
                    f"call edge {a_name} -> {b_name}: Require item "
                    f"{item!r} (head noun {head_noun!r}) not carried in {a_name}'s body"
                )
                _carriage_flag(diag, file_label, ("edge", a_name, b_name, head_noun), message)

    for pkg in packages:
        if pkg["is_pack"]:
            _validate_pack_carriage(pkg, by_name, diag)


def _validate_pack_carriage(pkg: dict, by_name: dict, diag: Diagnostics) -> None:
    file_label = rel(pkg["skill_md"])
    body = pkg["body"]
    slicing_m = PACK_SLICING_RE.search(body)
    slicing_stems = set()
    if slicing_m:
        slicing_path = (pkg["path"] / slicing_m.group(1)).resolve()
        if slicing_path.is_file():
            slicing_stems = _carriage_body_stems(_read_source(slicing_path))
    workspace_m = PACK_WORKSPACE_RE.search(body)
    workspace_names_store = bool(workspace_m and PACK_STORE_RE.search(workspace_m.group(1)))

    for role, pattern in (("executor", PACK_EXECUTOR_RE), ("assembly", PACK_ASSEMBLY_RE)):
        m = pattern.search(body)
        if not m:
            continue
        skill_name = m.group(1)
        skill_pkg = by_name.get(skill_name)
        if skill_pkg is None:
            continue  # unresolved binding already reported by build_call_graph

        for item in _carriage_require_items(skill_pkg["body"]):
            carried, head_noun = _carriage_item_carried(item, slicing_stems)
            if carried:
                continue
            message = (
                f"pack {pkg['path'].name} {role} `{skill_name}`: Require item "
                f"{item!r} (head noun {head_noun!r}) not carried in the slicing cell"
            )
            _carriage_flag(diag, file_label, ("pack", pkg["path"].name, role, head_noun), message)

        return_m = RETURN_TEXT_RE.search(skill_pkg["body"])
        return_names_filing = bool(return_m and TICKET_FILING_RE.search(return_m.group(1)))
        if not return_names_filing and not workspace_names_store:
            diag.error(
                file_label,
                f"pack {pkg['path'].name} {role} `{skill_name}` Return does not name the "
                f"ticket/work-item filing per work-item.md's filing law, and the pack's "
                f"workspace does not name a store (the law's other filing destination)",
            )


# --- Sync (spec criterion 3) ------------------------------------------
#
# Owned literals get checked against their owner, never restated as a
# second source: BODY_BUDGET/DESCRIPTION_BUDGET against
# rules/composition.md §5, ENVELOPE_UNITS against contracts/result.md's
# Binding paragraph, the friction-category list in
# templates/host-block.md and AGENTS.md against rules/improvement.md
# rule 1's closed set, and the same two copies' friction-completion
# clause against rule 1's sentence. The owner files are prose, so
# parsing below anchors on enum/number tokens rather than sentence
# shape, per the carriage checks above.
SYNC_RULE_HEADER_RE = re.compile(r"^(\d+)\.\s", re.MULTILINE)
SYNC_DESC_BUDGET_RE = re.compile(r"description.{0,15}?(\d+)\s*chars")
SYNC_KIU_BUDGET_RE = re.compile(r"kernel,\s*instances,\s*and\s*utilities\s+(\d+)\s+lines")
SYNC_EW_BUDGET_RE = re.compile(r"engines\s+and\s+workflows\s+(\d+)")
SYNC_PACK_BUDGET_RE = re.compile(r"pack SKILL\.md\s+(\d+)")
SYNC_CLOSED_SET_RE = re.compile(r"closed set\s*[–—]\s*(.*?)\s*[–—]", re.DOTALL)
SYNC_CATEGORY_TOKEN_RE = re.compile(r"^[a-z]+(?:-[a-z]+)*$")
SYNC_FLAG_CATEGORY_RE = re.compile(r"--category.{0,10}?\(([^)]*)\)", re.DOTALL)
SYNC_FRICTION_CLAUSE_RE = re.compile(
    r"Logging friction is part of completing.*?failed\s+silently\.", re.DOTALL
)
SYNC_CLAUSE_CONNECTOR_RE = re.compile(r"[:–—]")


def _sync_extract_numbered_rule(text: str, number: int):
    """The raw text of rule `number` in a `rules/*.md` flat numbered
    list -- from just after its own 'N. ' line-start marker up to (not
    including) the next rule's marker."""
    matches = list(SYNC_RULE_HEADER_RE.finditer(text))
    for i, m in enumerate(matches):
        if int(m.group(1)) == number:
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            return text[m.end():end]
    return None


def _sync_validate_budgets(composition_text: str, diag: Diagnostics) -> None:
    file_label = rel(ROOT / "tools" / "validate.py")
    owner_label = rel(ROOT / "rules" / "composition.md")
    rule5 = _sync_extract_numbered_rule(composition_text, 5)
    if rule5 is None:
        diag.error(owner_label, "could not locate rule 5 (Anatomy/body budgets) to check BODY_BUDGET and DESCRIPTION_BUDGET against")
        return
    norm = re.sub(r"\s+", " ", rule5)
    matches = {
        "description budget": SYNC_DESC_BUDGET_RE.search(norm),
        "kernel/instances/utilities budget": SYNC_KIU_BUDGET_RE.search(norm),
        "engines/workflows budget": SYNC_EW_BUDGET_RE.search(norm),
        "pack budget": SYNC_PACK_BUDGET_RE.search(norm),
    }
    missing = [name for name, m in matches.items() if m is None]
    if missing:
        diag.error(owner_label, f"rule 5 prose does not state: {', '.join(missing)} -- validate_sync ungrounded")
        return
    owner_budgets = {
        "kernel": int(matches["kernel/instances/utilities budget"].group(1)),
        "instances": int(matches["kernel/instances/utilities budget"].group(1)),
        "utilities": int(matches["kernel/instances/utilities budget"].group(1)),
        "engines": int(matches["engines/workflows budget"].group(1)),
        "workflows": int(matches["engines/workflows budget"].group(1)),
        "pack": int(matches["pack budget"].group(1)),
    }
    for tier, expected in owner_budgets.items():
        actual = BODY_BUDGET.get(tier)
        if actual != expected:
            diag.error(
                file_label,
                f"BODY_BUDGET[{tier!r}] = {actual} but rules/composition.md §5 states {expected}",
            )
    owner_desc = int(matches["description budget"].group(1))
    if DESCRIPTION_BUDGET != owner_desc:
        diag.error(
            file_label,
            f"DESCRIPTION_BUDGET = {DESCRIPTION_BUDGET} but rules/composition.md §5 states {owner_desc}",
        )


SYNC_RESULT_BINDING_RE = re.compile(r"^Binding:(.*?)(?:\n[ \t]*\n|\Z)", re.MULTILINE | re.DOTALL)


def _sync_validate_envelope_units(diag: Diagnostics) -> None:
    """ENVELOPE_UNITS against contracts/result.md's Binding paragraph --
    the one owner of which dispatchable units the envelope binds."""
    result_path = ROOT / "contracts" / "result.md"
    if not result_path.is_file():
        return  # owner absent (isolated fixtures) -- not this check's tree
    file_label = rel(ROOT / "tools" / "validate.py")
    m = SYNC_RESULT_BINDING_RE.search(_read_source(result_path))
    if m is None:
        diag.error(
            rel(result_path),
            "could not locate the 'Binding:' paragraph naming the envelope-bound units to check ENVELOPE_UNITS against",
        )
        return
    owner_units = set(CALL_TOKEN_RE.findall(m.group(1)))
    if owner_units != set(ENVELOPE_UNITS):
        diag.error(
            file_label,
            f"ENVELOPE_UNITS = {sorted(ENVELOPE_UNITS)} does not match the bound units named "
            f"in contracts/result.md: {sorted(owner_units)}",
        )


def _sync_parse_closed_categories(rule_text: str):
    norm = re.sub(r"\s+", " ", rule_text)
    m = SYNC_CLOSED_SET_RE.search(norm)
    if not m:
        return None
    categories = set()
    for segment in m.group(1).split(","):
        seg = re.sub(r"\([^)]*\)", "", segment).strip()
        if SYNC_CATEGORY_TOKEN_RE.match(seg):
            categories.add(seg)
    return categories or None


def _sync_parse_flag_categories(text: str):
    norm = re.sub(r"\s+", " ", text)
    m = SYNC_FLAG_CATEGORY_RE.search(norm)
    if not m:
        return None
    categories = set()
    for tok in m.group(1).split("|"):
        tok = tok.strip()
        if SYNC_CATEGORY_TOKEN_RE.match(tok):
            categories.add(tok)
    return categories or None


def _sync_validate_category_copy(path: Path, owner_categories: set, diag: Diagnostics) -> None:
    file_label = rel(path)
    if not path.is_file():
        diag.error(file_label, "friction category copy is missing")
        return
    copy_categories = _sync_parse_flag_categories(_read_source(path))
    if copy_categories is None:
        diag.error(file_label, "could not locate the '--category' friction category list to check against rules/improvement.md")
        return
    if copy_categories != owner_categories:
        detail = []
        missing = sorted(owner_categories - copy_categories)
        extra = sorted(copy_categories - owner_categories)
        if missing:
            detail.append(f"missing {missing}")
        if extra:
            detail.append(f"unexpected {extra}")
        diag.error(
            file_label,
            f"friction category list out of sync with rules/improvement.md §1 closed set: {'; '.join(detail)}",
        )


def _sync_normalize_clause(text: str) -> str:
    """Whitespace- and connector-tolerant normal form for a prose
    clause: line wraps and the colon/dash a sentence uses to join its
    two halves are cosmetic, per rules/improvement.md rule 1's
    friction-completion sentence vs. its templates/host-block.md and
    AGENTS.md copies (one uses ':', the copies an em dash)."""
    text = SYNC_CLAUSE_CONNECTOR_RE.sub(" ", text)
    return re.sub(r"\s+", " ", text).strip()


def _sync_validate_friction_clause_copy(path: Path, owner_clause: str, diag: Diagnostics) -> None:
    file_label = rel(path)
    if not path.is_file():
        diag.error(file_label, "friction-completion clause copy is missing")
        return
    copy_text = _sync_normalize_clause(_read_source(path))
    if owner_clause not in copy_text:
        diag.error(
            file_label,
            "friction-completion clause out of sync with rules/improvement.md §1 "
            "('Logging friction is part of completing the task ... failed silently.')",
        )


def validate_sync(diag: Diagnostics) -> None:
    """Spec criterion 3: BODY_BUDGET/DESCRIPTION_BUDGET vs.
    rules/composition.md §5; ENVELOPE_UNITS vs. contracts/result.md's
    Binding paragraph; the friction-category list and the
    friction-completion clause in templates/host-block.md and AGENTS.md
    vs. rules/improvement.md rule 1's closed set and sentence. A drifted
    copy gets aligned to its owner, never the reverse -- owners stay
    frozen."""
    _sync_validate_envelope_units(diag)

    composition_path = ROOT / "rules" / "composition.md"
    improvement_path = ROOT / "rules" / "improvement.md"
    if not composition_path.is_file() or not improvement_path.is_file():
        return  # owners absent (isolated fixtures exercising other checks) -- not this check's tree
    composition_text = _read_source(composition_path)
    improvement_text = _read_source(improvement_path)

    _sync_validate_budgets(composition_text, diag)

    rule1_improvement = _sync_extract_numbered_rule(improvement_text, 1)
    owner_categories = _sync_parse_closed_categories(rule1_improvement) if rule1_improvement else None
    if owner_categories is None:
        diag.error(rel(improvement_path), "could not locate rule 1's friction-category closed set to check copies against")
        return
    for copy_path in (ROOT / "templates" / "host-block.md", ROOT / "AGENTS.md"):
        _sync_validate_category_copy(copy_path, owner_categories, diag)

    clause_m = SYNC_FRICTION_CLAUSE_RE.search(rule1_improvement)
    if clause_m is None:
        diag.error(rel(improvement_path), "could not locate rule 1's friction-completion clause to check copies against")
        return
    owner_clause = _sync_normalize_clause(clause_m.group(0))
    for copy_path in (ROOT / "templates" / "host-block.md", ROOT / "AGENTS.md"):
        _sync_validate_friction_clause_copy(copy_path, owner_clause, diag)


# --- Friction log location ---------------------------------------------
#
# The Sync section's discipline over a second owner: scripts/state_root.py
# owns where the friction log goes (ARCHITECTURE.md's scripts/ tier), so
# the tree it resolves is read from `friction_root` and never restated
# here. The sink root under it is rules/visibility.md §6's, checked
# against the resolver by tests/test_validate.py, and no copy restates
# it. What the copies do name is the tree: docs/vocabulary.md's
# **friction log** term, and the blocked-case sentence in
# templates/host-block.md and AGENTS.md -- a fallback the shell refused
# inside a worktree has to land outside every worktree, so no copy may
# send a hand-written file to the old location under `.orch/`.
FRICTION_OWNER = ROOT / "scripts" / "state_root.py"
FRICTION_RESOLVER = "friction_root"
FRICTION_IN_REPOSITORY = ".orch/"
FRICTION_TERM_RE = re.compile(r"^- \*\*friction log\*\*.*?(?=\n- \*\*|\Z)", re.MULTILINE | re.DOTALL)
FRICTION_FALLBACK_RE = re.compile(r"Whenever the logger cannot run.*?never skip the log\.")


def _friction_join_tree(node) -> str:
    """The tree a `<sink root> / "name"` expression names, spelled as a
    copy spells it -- 'name/'. None when the expression is not such a
    join."""
    if not (isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div)):
        return None
    name = node.right
    if not (isinstance(name, ast.Constant) and isinstance(name.value, str)):
        return None
    return name.value + "/"


def _friction_owner_tree(diag: Diagnostics):
    """The sink tree scripts/state_root.py resolves the log into, or None
    with the defect reported."""
    label = rel(FRICTION_OWNER)
    try:
        tree = ast.parse(_read_source(FRICTION_OWNER))
    except SyntaxError as exc:
        diag.error(label, f"does not parse, so the friction log location cannot be read: {exc}")
        return None
    resolver = next(
        (n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == FRICTION_RESOLVER),
        None,
    )
    if resolver is None:
        diag.error(label, f"no `{FRICTION_RESOLVER}` to read the friction log location from")
        return None
    found = []
    for node in ast.walk(resolver):
        if isinstance(node, ast.Return) and node.value is not None:
            location = _friction_join_tree(node.value)
            if location is not None:
                found.append(location)
    if len(found) != 1:
        diag.error(
            label,
            f"`{FRICTION_RESOLVER}` must resolve exactly one sink tree for the copies to be "
            f"checked against; read {sorted(found)}",
        )
        return None
    return found[0]


def _friction_validate_term(tree: str, diag: Diagnostics) -> None:
    path = ROOT / "docs" / "vocabulary.md"
    if not path.is_file():
        return  # term owner absent (isolated fixtures) -- not this check's tree
    match = FRICTION_TERM_RE.search(_read_source(path))
    if match is None:
        diag.error(rel(path), "could not locate the **friction log** term entry to check against scripts/state_root.py")
        return
    entry = re.sub(r"\s+", " ", match.group(0))
    if tree not in entry:
        diag.error(
            rel(path),
            f"**friction log** entry does not name {tree} -- scripts/state_root.py resolves "
            f"the log into that tree of the sink",
        )


def _friction_validate_fallback_copy(path: Path, tree: str, diag: Diagnostics) -> None:
    file_label = rel(path)
    if not path.is_file():
        diag.error(file_label, "friction fallback copy is missing")
        return
    match = FRICTION_FALLBACK_RE.search(re.sub(r"\s+", " ", _read_source(path)))
    if match is None:
        diag.error(
            file_label,
            "could not locate the blocked-case friction sentence ('Whenever the logger cannot "
            "run ... never skip the log.') to check against scripts/state_root.py",
        )
        return
    sentence = match.group(0)
    if tree not in sentence:
        diag.error(
            file_label,
            f"blocked-case friction fallback does not spell {tree}, the sink tree "
            f"scripts/state_root.py resolves outside every worktree",
        )
    if FRICTION_IN_REPOSITORY in sentence:
        diag.error(
            file_label,
            f"blocked-case friction fallback sends the entry to {FRICTION_IN_REPOSITORY}, inside "
            f"the worktree whose writes the refusal may cover",
        )


def validate_friction_locations(diag: Diagnostics) -> None:
    """Every copy of the friction log's location against their owner,
    scripts/state_root.py."""
    if not FRICTION_OWNER.is_file():
        return  # owner absent (isolated fixtures) -- not this check's tree
    tree = _friction_owner_tree(diag)
    if tree is None:
        return
    _friction_validate_term(tree, diag)
    for copy_path in (ROOT / "templates" / "host-block.md", ROOT / "AGENTS.md"):
        _friction_validate_fallback_copy(copy_path, tree, diag)


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


def discover_packages():
    """Return every skill/pack package as a dict with path, kind, skill_md."""
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


def validate_role(fm: dict, pkg: dict, diag: Diagnostics) -> None:
    file_label = rel(pkg["skill_md"])
    if pkg["is_pack"]:
        if "role" in fm:
            diag.error(file_label, "pack frontmatter must not declare 'role'")
        return
    role = fm.get("role")
    if not role:
        diag.error(file_label, "frontmatter missing required key 'role'")
        return
    if role not in ROLE_VALUES:
        diag.error(file_label, f"role '{role}' is not one of {sorted(ROLE_VALUES)}")
        return
    if pkg["kind"] in ROLE_NONE_TIERS and role != "none":
        diag.error(file_label, f"{pkg['kind']} skill must declare role: none, got '{role}'")


def validate_anatomy(body: str, pkg: dict, diag: Diagnostics) -> None:
    file_label = rel(pkg["skill_md"])
    if pkg["is_pack"]:
        for label in ("Require:", "Never:", "Return:"):
            if label in body:
                diag.error(file_label, f"pack body must not contain '{label}' (packs carry no control flow)")
        return
    if not REQUIRE_RE.search(body):
        diag.error(file_label, "skill body missing a line starting 'Require:'")
    if not NEVER_RE.search(body):
        diag.error(file_label, "skill body missing a line starting 'Never:'")
    if not RETURN_RE.search(body):
        diag.error(file_label, "skill body missing a sentence starting 'Return'")


def validate_budget(body: str, pkg: dict, diag: Diagnostics) -> None:
    file_label = rel(pkg["skill_md"])
    n = sum(1 for ln in body.split("\n") if ln.strip())
    tier = "pack" if pkg["is_pack"] else pkg["kind"]
    limit = BODY_BUDGET[tier]
    if n > limit:
        diag.error(file_label, f"body has {n} non-empty lines, exceeds the {tier} budget of {limit}")


def validate_pack_signature(body: str, pkg: dict, diag: Diagnostics) -> None:
    file_label = rel(pkg["skill_md"])
    found = set(PACK_TABLE_CELL_RE.findall(body))
    missing = [cell for cell in PACK_SIGNATURE_CELLS if cell not in found]
    if missing:
        diag.error(file_label, f"pack signature table missing cell(s): {', '.join(missing)}")
    row = CRAFT_ROW_RE.search(body)
    if row and "(references/craft.md)" not in row.group(1):
        diag.error(file_label, "craft cell must bind [references/craft.md](references/craft.md)")
    cells = dict(PACK_CELL_ROW_RE.findall(body))
    if "assembly" in cells and not assembly_form_ok(cells["assembly"]):
        diag.error(
            file_label,
            "assembly cell must be a backticked skill name or the bare word "
            f"'none' plus an em-dash gloss, got: {cells['assembly']!r}",
        )


def assembly_form_ok(binding: str) -> bool:
    """contracts/pack-signature.md admits exactly two `assembly` forms.
    `none` is bare: backticking it would read as a skill name, and no
    skill is called none."""
    binding = binding.strip()
    return bool(ASSEMBLY_SKILL_FORM_RE.match(binding) or ASSEMBLY_NONE_FORM_RE.match(binding))


def cell_clauses(text: str) -> list:
    """Split the content behind a cell into clauses -- the normative
    comparison unit of validate_cell_duplication.

    A clause is one assertion: a markdown table's data row, or a
    sentence, cut again at every ';' because this library's prose joins
    independent assertions with the semicolon (a workspace cell is one
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
                        ratio = difflib.SequenceMatcher(
                            None, left_free, right_free, autojunk=False
                        ).ratio()
                        if ratio >= CELL_SIMILARITY_THRESHOLD:
                            diag.warn(
                                left_label,
                                f"{cell}: cell content near-duplicate at "
                                f"{ratio:.2f} with {right_label}: "
                                f"{left!r} ~ {right!r}",
                            )


def validate_craft_budget(pkg: dict, diag: Diagnostics) -> None:
    craft = pkg["path"] / "references" / "craft.md"
    if not craft.is_file():
        return
    n = sum(1 for ln in _read_source(craft).split("\n") if ln.strip())
    if n > CRAFT_BUDGET:
        diag.error(rel(craft), f"craft reference has {n} non-empty lines, exceeds the craft budget of {CRAFT_BUDGET}")


def _resolve_link(source_file: Path, target: str):
    target = target.split(" ", 1)[0].split("#", 1)[0].strip()
    if not target or target.startswith(("http://", "https://", "mailto:")):
        return None
    try:
        return (source_file.parent / target).resolve()
    except OSError:
        return None


def validate_reference_links(body: str, pkg: dict, diag: Diagnostics) -> None:
    file_label = rel(pkg["skill_md"])
    for match in MD_LINK_RE.finditer(body):
        target = match.group(1)
        if "references/" not in target:
            continue
        resolved = _resolve_link(pkg["skill_md"], target)
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
    # composition rule 1: kernel skills are always primitives (zero call edges).
    for pkg in packages:
        if pkg["kind"] == "kernel" and graph.get(pkg["path"].name):
            called = ", ".join(sorted(graph[pkg["path"].name]))
            diag.error(rel(pkg["skill_md"]), f"kernel skill has call edges ({called}); kernel skills call no skill")


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
    if TICKET_FILING_RE.search(clause):
        return []
    return [label for label, pattern in ENVELOPE_VOCAB_RES if not pattern.search(clause)]


def validate_envelope(packages, diag: Diagnostics) -> None:
    """contracts/result.md: every bound dispatchable unit leads its
    Return: with status, result identity, and verification."""
    for pkg in packages:
        if pkg["path"].name not in ENVELOPE_UNITS:
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


def discover_compositions():
    comps_dir = ROOT / "compositions"
    if not comps_dir.is_dir():
        return []
    return sorted(p for p in comps_dir.glob("*.md") if p.is_file())


def _composition_has_field(field: str, fm: dict, body: str) -> bool:
    keys = {k.strip().lower().replace("-", "_").replace(" ", "_") for k in fm}
    if field in keys:
        return True
    if COMPOSITION_BODY_FIELD_RES[field].search(body):
        return True
    if field == "invariants" and NEVER_RE.search(body):
        return True  # the contract defines invariants as the Never: block
    return False


# --- Composition content checks (REVIEW-2026-08-06.md thread T2) -----
#
# Presence checks (above) pass a vacuous `invariants` block ("Never:
# violate the laws of physics") or a tautological `done_check` ("status
# is complete"): both name the field, neither says anything. Authored
# `steps` blocks in this tree bind their invariants thematically, not
# by repeating each step id verbatim (id-literal matching false-erred
# on 7 of 9 real compositions), so step-binding is checked at the
# achievable granularity contracts/composition.md's admission sentence
# actually enforces today: the invariants block must share real
# vocabulary with the steps block as a whole, catching an invariants
# block disconnected from the composition's own work while not
# requiring per-step id repetition. A step-by-step id requirement is
# the stronger form the review's remedy text names; narrowing it further
# to per-step binding is future work, tracked in this ticket's Feedback,
# not a regression this check introduces.
COMPOSITION_FIELD_ORDER = ("steps", "edges", "invariants", "done_check")


def _composition_field_span(field: str, body: str):
    """The body slice from `field`'s own label to the next known
    field's label (or end of body) -- steps/edges/invariants/done_check
    appear in that fixed order in every authored composition."""
    m = COMPOSITION_BODY_FIELD_RES[field].search(body)
    if not m:
        return None
    start = m.end()
    idx = COMPOSITION_FIELD_ORDER.index(field)
    end = len(body)
    for later in COMPOSITION_FIELD_ORDER[idx + 1:]:
        later_m = COMPOSITION_BODY_FIELD_RES[later].search(body, start)
        if later_m:
            end = later_m.start()
            break
    else:
        return_m = RETURN_RE.search(body, start)
        if return_m:
            end = return_m.start()
    return body[start:end]


def _composition_content_words(text: str) -> set:
    return {
        w for w in _carriage_body_stems(text)
        if w not in CARRIAGE_QUALIFIERS
    }


def _validate_composition_step_binding(body: str, file_label: str, diag: Diagnostics) -> None:
    steps_span = _composition_field_span("steps", body)
    invariants_span = _composition_field_span("invariants", body)
    if steps_span is None or invariants_span is None:
        return  # missing field already reported by the admission-fields loop
    step_words = _composition_content_words(steps_span)
    invariant_words = _composition_content_words(invariants_span)
    if step_words and not (step_words & invariant_words):
        diag.error(
            file_label,
            "invariants block shares no vocabulary with the steps block -- "
            "a step no invariant binds (contracts/composition.md's admission "
            "sentence)",
        )


DONE_CHECK_STATUS_WORD_RE = re.compile(
    r"^(?:status|complete[ds]?|blocked|stalled|limited|failed)$", re.IGNORECASE
)
DONE_CHECK_COPULA_WORDS = {
    "is", "are", "was", "were", "be", "been", "being",
    "has", "have", "had", "it", "its",
}
DONE_CHECK_FILLER_WORDS = {
    # modal/evaluative fillers qualifying a status claim without naming
    # a second fact (gate finding: "complete successfully" passed)
    "must", "should", "shall", "may", "can", "will", "indeed",
    "successfully", "properly", "correctly", "truly", "fully",
    "when", "then", "and", "or", "not", "no", "with", "without",
    # the envelope's own field vocabulary — the done_check oracle must
    # reach beyond the envelope (contracts/composition.md)
    "result", "identity", "verification", "verified", "verify",
    "envelope", "verdict", "verdicts",
}


def _validate_composition_done_check(body: str, file_label: str, diag: Diagnostics) -> None:
    done_span = _composition_field_span("done_check", body)
    if done_span is None:
        return  # missing field already reported by the admission-fields loop
    words = CARRIAGE_WORD_RE.findall(done_span)
    external_content = [
        w for w in words
        if w.lower() not in CARRIAGE_QUALIFIERS
        and w.lower() not in DONE_CHECK_COPULA_WORDS
        and w.lower() not in DONE_CHECK_FILLER_WORDS
        and not DONE_CHECK_STATUS_WORD_RE.match(w)
    ]
    if not external_content:
        diag.error(
            file_label,
            "done_check names only the envelope's own status vocabulary "
            "and no external oracle (contracts/composition.md: done_check "
            "is 'the end-to-end oracle over the final envelope')",
        )


def validate_compositions(diag: Diagnostics) -> None:
    """contracts/composition.md: every compositions/*.md is a normative,
    invocable workflow carrying name, description, entry (routed | named
    | scheduled), steps, edges, invariants, done_check, and the
    Require:/Return: envelope law."""
    for path in discover_compositions():
        file_label = rel(path)
        fm, body = parse_frontmatter(_read_source(path), file_label, diag)
        if fm is None or body is None:
            continue
        if not fm.get("name"):
            diag.error(file_label, "composition frontmatter missing required key 'name'")
        elif fm["name"] != path.stem:
            diag.error(
                file_label,
                f"composition name '{fm['name']}' does not match file name '{path.stem}'",
            )
        if not fm.get("description"):
            diag.error(file_label, "composition frontmatter missing required key 'description'")
        elif len(fm["description"]) > DESCRIPTION_BUDGET:
            diag.error(
                file_label,
                f"description is {len(fm['description'])} chars, exceeds {DESCRIPTION_BUDGET}-char budget",
            )
        entry = fm.get("entry")
        if not entry:
            diag.error(file_label, "composition frontmatter missing required key 'entry'")
        elif entry not in COMPOSITION_ENTRY_VALUES:
            diag.error(
                file_label,
                f"entry '{entry}' is not one of {sorted(COMPOSITION_ENTRY_VALUES)} "
                "per contracts/composition.md",
            )
        for f in COMPOSITION_REQUIRED_FIELDS:
            if not _composition_has_field(f, fm, body):
                diag.error(
                    file_label,
                    f"composition missing required field '{f}' per contracts/composition.md",
                )
        admission_fields_present = True
        for f in COMPOSITION_ADMISSION_FIELDS:
            if not _composition_has_field(f, fm, body):
                admission_fields_present = False
                diag.error(
                    file_label,
                    f"composition missing '{f}' -- admission rejects a composition "
                    "missing invariants or done_check (contracts/composition.md)",
                )
        if admission_fields_present:
            _validate_composition_step_binding(body, file_label, diag)
            _validate_composition_done_check(body, file_label, diag)
        if not REQUIRE_RE.search(body):
            diag.error(file_label, "composition body missing a line starting 'Require:'")
        if not RETURN_RE.search(body):
            diag.error(file_label, "composition body missing a sentence starting 'Return'")
        else:
            clause = _envelope_first_clause(body)
            missing = _envelope_missing(clause) if clause is not None else []
            if missing:
                diag.error(
                    file_label,
                    "Return does not lead with the result envelope per contracts/result.md: "
                    f"first clause carries no {', '.join(missing)} vocabulary "
                    "and names no work-item carrier",
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
def validate_loop_lint(body: str, pkg: dict, diag: Diagnostics) -> None:
    if not LOOP_TRIGGER_RE.search(body):
        return
    file_label = rel(pkg["skill_md"])
    if not BOUND_TERM_RE.search(body):
        diag.warn(file_label, "mentions iteration/loop but body lacks a 'bound' or 'budget' term")
    if not TERMINAL_TERM_RE.search(body):
        diag.warn(
            file_label,
            "mentions iteration/loop but body lacks a 'stalled'/'limited'/'exit'/'terminal' term",
        )


def validate_cross_package_links(packages, diag: Diagnostics) -> None:
    by_root = {pkg["path"].resolve(): pkg for pkg in packages}
    for pkg in packages:
        for source_file in sorted(pkg["path"].rglob("*.md")):
            text = _read_source(source_file)
            for match in MD_LINK_RE.finditer(text):
                resolved = _resolve_link(source_file, match.group(1))
                if resolved is None or "references" not in resolved.parts:
                    continue
                owner_pkg = None
                for root, candidate in by_root.items():
                    try:
                        resolved.relative_to(root)
                    except ValueError:
                        continue
                    owner_pkg = candidate
                    break
                if owner_pkg is None or owner_pkg["path"].resolve() == pkg["path"].resolve():
                    continue
                owner_text = _read_source(owner_pkg["skill_md"])
                ref_suffix = f"references/{resolved.name}"
                if ref_suffix not in owner_text:
                    diag.warn(
                        rel(source_file),
                        f"cross-package link to {rel(resolved)} but owning package's "
                        f"SKILL.md does not itself cite '{ref_suffix}'",
                    )


def compute_pins() -> dict:
    return {
        f.name: hashlib.sha256(f.read_bytes()).hexdigest()
        for f in sorted(CONTRACTS_DIR.glob("*.md"))
    }


def write_pins() -> dict:
    pins = compute_pins()
    PINS_FILE.parent.mkdir(parents=True, exist_ok=True)
    PINS_FILE.write_text(json.dumps(pins, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return pins


def validate_pins(diag: Diagnostics) -> None:
    current = compute_pins()
    if not PINS_FILE.is_file():
        diag.error(rel(PINS_FILE), PIN_MESSAGE)
        return
    try:
        recorded = json.loads(PINS_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        diag.error(rel(PINS_FILE), f"pins.json is not valid JSON: {exc}")
        return
    for name, digest in current.items():
        if recorded.get(name) != digest:
            diag.error(rel(CONTRACTS_DIR / name), PIN_MESSAGE)
    for name in recorded:
        if name not in current:
            diag.error(rel(PINS_FILE), PIN_MESSAGE)


def validate_unique_names(packages, diag: Diagnostics) -> None:
    seen = {}
    for pkg in packages:
        name = pkg["path"].name
        if name in seen:
            diag.error(rel(pkg["skill_md"]), f"duplicate package name '{name}', also at {rel(seen[name])}")
        else:
            seen[name] = pkg["skill_md"]


def run_validation() -> Diagnostics:
    diag = Diagnostics()
    packages = discover_packages()
    validate_unique_names(packages, diag)

    for pkg in packages:
        file_label = rel(pkg["skill_md"])
        text = _read_source(pkg["skill_md"])
        fm, body = parse_frontmatter(text, file_label, diag)
        pkg["frontmatter"] = fm or {}
        pkg["body"] = body or ""
        if fm is None or body is None:
            continue
        validate_frontmatter(fm, pkg, diag)
        validate_role(fm, pkg, diag)
        validate_anatomy(body, pkg, diag)
        validate_budget(body, pkg, diag)
        validate_loop_lint(body, pkg, diag)
        validate_reference_links(body, pkg, diag)
        if pkg["is_pack"]:
            validate_pack_signature(body, pkg, diag)
            validate_craft_budget(pkg, diag)

    validate_call_graph(packages, diag)
    validate_carriage(packages, diag)
    validate_cell_duplication(packages, diag)
    validate_envelope(packages, diag)
    validate_compositions(diag)
    validate_cross_package_links(packages, diag)
    validate_pins(diag)
    validate_sync(diag)
    validate_friction_locations(diag)
    return diag


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pin",
        action="store_true",
        help="rewrite tests/pins.json from the current contracts/*.md bytes",
    )
    args = parser.parse_args(argv)

    if args.pin:
        pins = write_pins()
        print(f"wrote {len(pins)} pin(s) to {rel(PINS_FILE)}")
        return 0

    diag = run_validation()
    for line in diag.lines():
        print(line)
    return 1 if diag.has_errors else 0


if __name__ == "__main__":
    sys.exit(main())
