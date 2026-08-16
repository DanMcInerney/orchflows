#!/usr/bin/env python3
"""The orchflows compiler.

Enforces package anatomy, frontmatter, call-graph acyclicity, pack
signature completeness, T0 hash pins, the
ticket-template contract (whose shape law is scripts/tickets.py's, read
from there rather than restated), the result-envelope lead, and the
duplication checks -- per pack cell and across tiers -- that replaced
keeping copies in sync, per AGENTS.md, ARCHITECTURE.md,
rules/composition.md, contracts/result.md,
contracts/work-item.md, and contracts/pack-signature.md. Stdlib only, no
network.

Exit 0 clean or WARN-only. Exit 1 on any ERROR; one line per finding:
    ERROR|WARN <file>: <message>

A check whose owner is not in the tree -- an isolated fixture, a partial
checkout -- is skipped rather than failed, and says so as a WARN. Finding
nothing to check is not the same answer as finding nothing wrong.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# What a check says when the tree it grades is not here. One wording, so a
# reader can grep the report for every check that did not run.
SKIPPED = "absent; check skipped"

SKILL_TIERS = ("kernel", "engines", "workflows", "instances", "utilities")
# Words, not lines: a line count is met by widening lines, and was.
# Markdown link targets are stripped first so a citation costs its label,
# not its path.
BODY_BUDGET = {
    "kernel": 300,
    "instances": 300,
    "utilities": 300,
    "engines": 450,
    "workflows": 450,
    "pack": 150,
}
LINK_TARGET_RE = re.compile(r"\]\([^)]*\)")
# rules/token-economy.md §11: every-turn surfaces tightest, every-dispatch
# units next, every-run units widest. Ceilings only fall.
SURFACE_BUDGET = {"templates/host-block.md": 400, "AGENTS.md": 300}
STUB_INSTRUCTION_BUDGET = 300   # objective + completion test + excluded actions + return fields
MANIFEST_BUDGET = 250
STUB_INSTRUCTION_SECTIONS = ("Objective", "Completion test", "Return fields")
STUB_SECTION_SPLIT_RE = re.compile(r"^## (.+)$", re.MULTILINE)
EXCLUDED_ACTIONS_RE = re.compile(r"^excluded_actions:\n((?:[ \t]+- .*\n)*)", re.MULTILINE)
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
# The cells whose content is a whole reference file, so the duplication
# linter compares what they point at rather than the pointer row. `lens`
# is not among them: it binds a section of `craft`, not a file of its
# own, and resolving it to craft.md would compare craft's content twice,
# once under each cell name (REVIEW-2026-08-15
# T7). Its row is compared as the text it is, which is three words and
# so sits under CELL_CLAUSE_MIN_WORDS.
CRAFT_CELLS_BY_POINTER = ("slicing", "oracle_policy", "craft")
CRAFT_BUDGET = 60
# Cross-pack cell linter. Both figures are normative: with `doclint`'s
# ratio under them the reported pair set is a function of these two and of
# `doclint.DISTINCTIVE_MAX`, so moving any of them changes what the check
# means, not only what it finds.
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
)
MD_LINK_RE = re.compile(r"\]\(([^)]+)\)")
LOOP_TRIGGER_RE = re.compile(r"\biterat(?:e|es|ing)\b|\brepeat until\b", re.IGNORECASE)
BOUND_TERM_RE = re.compile(r"bound|budget", re.IGNORECASE)
TERMINAL_TERM_RE = re.compile(r"stalled|limited|exit|terminal", re.IGNORECASE)

# --- Result envelope (contracts/result.md) ---------------------------
#
# The bound dispatchable units lead their Return: with the envelope --
# status, result identity, verification. ENVELOPE_UNITS names the units
# contracts/result.md's Binding paragraph binds. Nothing holds the two
# equal any more: the check that did is deleted in P2, because a second
# spelling kept equal to its owner is still a second spelling
# (REVIEW-2026-08-15 T2). The residual risk is one-directional and small
# -- a unit dropped from this list stops being checked rather than
# silently passing a check it fails -- and the contract is hash-pinned, so
# the paragraph cannot move without a supersession PR.
# Mechanized as a first-clause vocabulary lint, tolerant
# of prose ordering within that clause; a Return whose first clause
# instead names the work-item carrier (the ticket) passes, because the
# ticket's T0 shape carries all three fields -- rule 10's envelope-on-a-
# named-T0-carrier form.
ENVELOPE_UNITS = (
    "orch-investigate",
    "orch-loop",
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

# --- Ticket templates (contracts/work-item.md, Template and stub) ----
#
# A template is a directory `compositions/<name>/` holding `template.md`
# plus one ticket stub per other `*.md` file; a stub is a ticket per
# contracts/work-item.md missing only `run`, `status` and `claimed_*`,
# with `{{placeholder}}` where instantiation fills a value. These checks
# are the admission the spec's enforcement clause names: a cyclic
# template, a stub without an executor or a completion test, or a
# template with no single terminal stub is rejected here. Since P4-3
# this is the whole of composition admission: the `.md` step form and
# its contract are deleted, so there is no second set of checks to keep
# in step with these.
#
# What a stub *is* -- its required keys, its list fields, its sections and
# their order, its criteria, its legal executors -- is not stated here.
# `scripts/tickets.py` owns it, grades every issued ticket and every
# instantiated stub against it, and reports it in its own words
# (`template_defects`); validate_templates reads that and adds only what
# needs the tree. A second statement of the same law is how a template the
# compiler admits fails at instantiation, which is what the P1 gate found
# across eight inputs and the executor enum.
#
# The manifest's name, the placeholder syntax and the `script:` prefix are
# that script's too, imported from it below rather than spelled again here:
# a second spelling of the placeholder syntax admitted `{{lens name}}` into
# the tree and hid it from the manifest-balance check, because instantiation
# refuses an unfilled one by a wider pattern than this file matched.
TEMPLATE_ENTRY_VALUES = {"routed", "named"}

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


# --- Friction log location ---------------------------------------------
#
# A location, not a sentence: scripts/state_root.py owns where the friction
# log goes (ARCHITECTURE.md's scripts/ tier), so the tree it resolves is
# read from `friction_root` and never restated here. The sink root under it
# is rules/visibility.md §6's, checked against the resolver by
# tests/test_validate.py, and no copy restates it. What the copies name is
# the tree: docs/vocabulary.md's **friction log** term, and the
# blocked-case sentence in templates/host-block.md -- a fallback the shell
# refused inside a worktree has to land outside every worktree, so no copy
# may send a hand-written file to the old location under `.orch/`.
#
# One checked copy, not two. AGENTS.md carries the same sentence and P3
# deletes it (REVIEW-2026-08-15 T2); requiring it here would make that
# deletion break the compiler, and until it happens the duplication is
# reported by validate_cross_tier_duplication rather than mandated.
FRICTION_CHECKED_COPIES = ("templates/host-block.md",)
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
        diag.warn(rel(path), SKIPPED)  # not this check's tree (isolated fixtures)
        return
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
        diag.warn(rel(FRICTION_OWNER), SKIPPED)  # not this check's tree
        return
    tree = _friction_owner_tree(diag)
    if tree is None:
        return
    _friction_validate_term(tree, diag)
    for name in FRICTION_CHECKED_COPIES:
        _friction_validate_fallback_copy(ROOT / name, tree, diag)


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
    """Return every skill/pack package as a dict with path, kind, skill_md.

    A tier directory holding only ``references/`` is not a package and is
    not a defect in itself -- the ``is_file()`` guard below reads it as no
    package rather than as a package missing its SKILL.md. It is not a
    home a reference may keep, though: ``rules/visibility.md`` §4 makes a
    references file public only where its owner's body names the local
    path, and a directory with no body names nothing. ``profiles.md``
    therefore lives under ``skills/engines/orch-frontier/``, whose body
    names it.
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


def body_words(body: str) -> int:
    """The body's word count with markdown link targets stripped."""
    return len(LINK_TARGET_RE.sub("]", body).split())


def _split_frontmatter(text: str):
    parts = text.split("---", 2)
    return (parts[1], parts[2]) if len(parts) > 2 else ("", text)


def stub_instruction_words(text: str) -> int:
    """A stub's instruction: its excluded actions plus the Objective,
    Completion test and Return fields sections — never its Fixed inputs,
    which are identities (rules/token-economy.md §11)."""
    front, body = _split_frontmatter(text)
    excluded = EXCLUDED_ACTIONS_RE.search(front)
    total = body_words(excluded.group(1)) if excluded else 0
    parts = STUB_SECTION_SPLIT_RE.split(body)
    sections = {parts[i].strip(): parts[i + 1] for i in range(1, len(parts) - 1, 2)}
    return total + sum(body_words(sections.get(name, "")) for name in STUB_INSTRUCTION_SECTIONS)


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


def validate_budget(body: str, pkg: dict, diag: Diagnostics) -> None:
    file_label = rel(pkg["skill_md"])
    n = body_words(body)
    tier = "pack" if pkg["is_pack"] else pkg["kind"]
    limit = BODY_BUDGET[tier]
    if n > limit:
        diag.error(file_label, f"body has {n} words, exceeds the {tier} budget of {limit}")


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
            n = stub_instruction_words(text)
            if n > STUB_INSTRUCTION_BUDGET:
                diag.error(rel(path), f"stub instruction has {n} words, exceeds the budget of {STUB_INSTRUCTION_BUDGET}")
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
                resolved = _doclint().resolve_link(source_file, match.group(1))
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
    # Bytes with LF: a text-mode write on Windows would land CRLF and
    # differ from every other host's pin file.
    PINS_FILE.write_bytes((json.dumps(pins, indent=2, sort_keys=True) + "\n").encode("utf-8"))
    return pins


# --- Markdown links resolve (docs/documentation.md law 5) ---------------
#
# Every relative markdown link in every .md the library ships resolves to
# a file in the tree. Anchors are not resolved here (validate_lens_anchor
# owns the one anchor class a consumer depends on); external URLs and
# templated paths are skipped. REVIEW-*.md are dated evidence and exempt.
LINKED_MD_ROOTS = ("rules", "contracts", "docs", "skills", "packs", "compositions", "templates", "benchmarks")


def _linked_markdown_files():
    for name in sorted(ROOT.glob("*.md")):
        if not name.name.startswith("REVIEW-"):
            yield name
    for root in LINKED_MD_ROOTS:
        yield from sorted((ROOT / root).rglob("*.md"))


def validate_markdown_links(diag: Diagnostics) -> None:
    absent = [root for root in LINKED_MD_ROOTS if not (ROOT / root).is_dir()]
    if absent:
        # A partial tree (the isolated test fixtures) is not graded -- and
        # this skip is the whole check, not one file's: one absent root
        # silences link resolution over every other root, so each is named
        # and the operator restores them in one pass rather than eight.
        for root in absent:
            diag.warn(root, SKIPPED)
        return
    dangling_links = _doclint().dangling_links
    for source in _linked_markdown_files():
        for target in dangling_links(source, _read_source(source)):
            diag.error(rel(source), f"markdown link does not resolve: {target}")


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


# Where a backticked `orch-*` is a call edge the call-graph check never
# sees: rules/composition.md rule 2 makes any backticked name one, and
# `build_call_graph` reads skill bodies only. A rule pointing at a deleted
# owner therefore rode through exit 0 twice (`orch-mechanize`,
# `orch-review-fix`), which is a rule naming an owner that is not there.
NAME_CHECKED_DIRS = ("rules", "docs", "contracts", "templates")
# Read to the bottom, not just the top level. compositions/ is where every
# template stub lives and every stub names an executor; a pack keeps its
# craft, slicing and oracle criteria under references/, and so does a skill.
# All of it calls skills by name, and none of it was on the surface -- the
# non-recursive glob over four directories above saw the top level and
# stopped, which is how a stub could name a deleted skill through exit 0.
NAME_CHECKED_TREES = ("compositions", "packs", "skills")
NAME_CHECKED_FILES = ("README.md", "DESIGN.md", "ARCHITECTURE.md", "AGENTS.md")
# `orch-` alone is the prefix, not a name; a name carries at least one
# segment after it. Plain text is how the library says "mentioned, not
# called" (rule 2 again), so DESIGN.md's supersession history needs no
# allowlist -- it just does not backtick the names it is burying.
BACKTICKED_NAME_RE = re.compile(r"`(orch-[a-z0-9]+(?:-[a-z0-9]+)*)`")
# The lens cell is a pointer into a section, and the row is compared as
# three words of text (see CELL_CLAUSE_MIN_WORDS above) rather than
# resolved -- so nothing looked at whether the section is there.
# The marker that says this tree is the library and not an isolated
# fixture. Same idiom as validate_friction_locations' owner check: a
# fixture copies the real contracts/ beside a synthetic skills/, and
# resolving one against the other would convict the contracts for the
# fixture's own emptiness. ARCHITECTURE.md is the tier map, so a tree
# without it has no tier map for a name to resolve against.
NAME_CHECK_MARKER = ROOT / "ARCHITECTURE.md"
LENS_ROW_RE = re.compile(r"^\|\s*lens\s*\|(.*)\|\s*$", re.MULTILINE)
LENS_ANCHOR_RE = re.compile(r"\(([^)]*#[^)]*)\)")
HEADING_RE = re.compile(r"^#+\s+(.*\S)\s*$", re.MULTILINE)


def _heading_slugs(text: str) -> set:
    """Every heading in `text`, as the anchor a link would reach it by."""
    slugs = set()
    for title in HEADING_RE.findall(text):
        slug = re.sub(r"[^a-z0-9\s-]", "", title.lower())
        slugs.add(re.sub(r"\s+", "-", slug).strip("-"))
    return slugs


def validate_names(packages, diag: Diagnostics) -> None:
    """Every backticked `orch-*` outside the skill tree resolves inside it.

    Skipped where the tree is not the library -- no packages, or no
    ARCHITECTURE.md to mark it as the tree whose tiers a name resolves in.
    """

    if not NAME_CHECK_MARKER.is_file():
        diag.warn(rel(NAME_CHECK_MARKER), SKIPPED)
        return
    if not packages:
        diag.warn("skills", SKIPPED)
        return
    known = {pkg["path"].name for pkg in packages} | set(ROLE_PROFILES)
    paths = []
    for directory in NAME_CHECKED_DIRS:
        node = ROOT / directory
        if node.is_dir():
            paths.extend(sorted(node.glob("*.md")))
    for directory in NAME_CHECKED_TREES:
        node = ROOT / directory
        if node.is_dir():
            paths.extend(sorted(node.rglob("*.md")))
    paths.extend(ROOT / name for name in NAME_CHECKED_FILES)
    # A package body is `build_call_graph`'s, which reports an unresolvable
    # name there in its own words; reading it here too would convict one
    # line twice in two vocabularies.
    bodies = {pkg["skill_md"].resolve() for pkg in packages}
    for path in paths:
        if not path.is_file() or path.resolve() in bodies:
            continue
        for name in sorted(set(BACKTICKED_NAME_RE.findall(_read_source(path)))):
            if name in known:
                continue
            diag.error(
                rel(path),
                f"`{name}` names no package: no skills/<tier>/{name}/SKILL.md "
                f"and no packs/{name}/SKILL.md. A backticked name is a call "
                "edge (rules/composition.md rule 2); name it in plain text to "
                "mention it without calling it",
            )


def validate_lens_anchor(packages, diag: Diagnostics) -> None:
    """Each pack's lens cell anchor lands on a heading that exists.

    contracts/pack-signature.md binds the lens to `orch-critique` plus the
    pack's craft `## Lens`, and every gate lane the pack stamps reads its
    criteria there. Deleting the heading left the validator at exit 0.
    """

    for pkg in packages:
        if not pkg["is_pack"]:
            continue
        row = LENS_ROW_RE.search(pkg.get("body") or "")
        if row is None:
            continue  # a missing cell is validate_pack_signature's finding
        file_label = rel(pkg["skill_md"])
        for target in LENS_ANCHOR_RE.findall(row.group(1)):
            relative, _, anchor = target.partition("#")
            craft = (pkg["skill_md"].parent / relative).resolve()
            if not craft.is_file():
                diag.error(
                    file_label,
                    f"lens cell anchor `{target}` names no file at "
                    f"{relative} beside this pack",
                )
                continue
            if anchor.lower() not in _heading_slugs(_read_source(craft)):
                diag.error(
                    file_label,
                    f"lens cell anchor `{target}` lands nowhere: "
                    f"{rel(craft)} carries no heading reached by "
                    f"`#{anchor}` — the cell binds a `## Lens` section, so "
                    "that section has to be there",
                )


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
    validate_cross_tier_duplication(packages, diag)
    validate_envelope(packages, diag)
    validate_templates(diag)
    validate_cross_package_links(packages, diag)
    validate_names(packages, diag)
    validate_lens_anchor(packages, diag)
    validate_markdown_links(diag)
    validate_surface_budgets(diag)
    validate_pins(diag)
    validate_friction_locations(diag)
    return diag


def main(argv=None) -> int:
    # Diagnostics quote library prose, which carries characters a cp1252
    # console cannot encode; a validator that crashes while printing its
    # own finding reports nothing. Replace, never raise.
    try:
        sys.stdout.reconfigure(errors="replace")
    except (AttributeError, ValueError):  # pragma: no cover - not a TextIOWrapper
        pass
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
