"""Shared constants and imports for the orchflows validator."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import sys
from pathlib import Path

# tools/validate.py, the only entry point that loads this module, has
# already put the repository root on sys.path before importing anything
# under tools.validate_support -- so this leaf import needs no walk of
# its own; it is a plain downstream read of the one repo-root fact.
from scripts._bootstrap import ROOT

# What a check says when the tree it grades is not here. One wording, so a
# reader can grep the report for every check that did not run.
SKIPPED = "absent; check skipped"

SKILL_TIERS = ("kernel", "workflows")
# Words, not lines: a line count is met by widening lines, and was.
# Markdown link targets are stripped first so a citation costs its label,
# not its path.
BODY_BUDGET = {
    "kernel": 300,
    "workflows": 450,
    "pack": 150,
}
LINK_TARGET_RE = re.compile(r"\]\([^)]*\)")
# rules/token-economy.md §11: every-turn surfaces tightest, every-dispatch
# units next, every-run units widest. Ceilings only fall.
SURFACE_BUDGET = {"templates/host-block.md": 400, "AGENTS.md": 230}
# The default ceiling a project's own router file (routing + friction law,
# outside managed blocks -- docs/custom-workflow-authoring.md's project-tier
# row) is held to when it states no stricter number of its own. No renderer
# or sync mechanism installs a project-scope routing block in this tree
# today (install.py: "Installation has one scope: user"; the legacy
# project-scope path `_codex_agents_path` still carries is unreachable from
# its CLI; scripts/orchflows_scaffold.py scaffolds skills/packs/workflows,
# never a project's day-zero router) -- this repository is itself one
# project instance and states its own stricter number at
# SURFACE_BUDGET["AGENTS.md"] instead of this default.
ROUTING_BLOCK_BUDGET = 400
# rules/token-economy.md §11's "role agent file" and tests/
# test_installer_cases/managed_text/roles.py's rendered-body `BODY_CEILING`
# are one fact, not two: `installer/packages.py`'s `ROLE_INSTRUCTIONS` is
# the only content a role agent file ever carries (there is no separate
# un-rendered source file for it, unlike a SKILL.md body), so "the role
# agent file" and "the rendered Claude/Codex agent body" name the same
# artifact. roles.py imports this rather than restating the literal.
ROLE_AGENT_BUDGET = 80
DESCRIPTION_BUDGET = 140
ALLOWED_FRONTMATTER_KEYS = {"name", "description", "disable-model-invocation", "role"}
ROLE_PROFILES = {"orch-planner", "orch-worker"}
ROLE_VALUES = {"planner", "worker", "none"}
PACK_SIGNATURE_CELLS = (
    "adapter",
    "stages",
    "assembly",
    "craft",
)
PACK_TYPED_CELLS = ("adapter", "stages", "assembly")
# The one cell whose content is a whole reference file, so the duplication
# linter compares what it points at rather than the pointer row — section
# by section, per contracts/pack-signature.md's craft-section table.
CRAFT_CELLS_BY_POINTER = ("craft",)
# The craft sections every pack must carry (contracts/pack-signature.md
# `## Craft sections`), and the optional two the linter still compares.
CRAFT_MANDATORY_SECTIONS = (
    "Vocabulary",
    "Workspace",
    "Spec fields",
    "Outline",
    "Slicing",
    "Evidence",
    "Lens",
)
CRAFT_OPTIONAL_SECTIONS = ("Shape", "Stages")
# The sum of the folded parts at the fold (2026-08-30); only falls.
CRAFT_BUDGET = 130
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
PACK_ADAPTER_RE = re.compile(r"^[a-z][a-z0-9-]*$")
PACK_STAGE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
ASSEMBLY_SKILL_FORM_RE = re.compile(r"^`[a-z][a-z0-9-]*`$")
ASSEMBLY_NONE_FORM_RE = re.compile(r"^none$")
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
# It named orch-frontier until the driver loop stopped being a skill.
# `orch-do` is the unit left whose Return leads with the whole envelope,
# and this keeps that clause from being reworded into prose no join reads.
ENVELOPE_UNITS = (
    "orch-do",
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
# the store the assignment names."
# That law's two filing destinations -- "the ticket -- or the store the
# assignment names" -- are this check's two pass conditions: the bound skill's
# own body names the ticket/work-item filing, or the pack's workspace
# names a store; kernel-tier primitives stay domain-blind per the redteam
# critique's Move 7 and rely on the second, rather than hardcoding
# pack-specific filing language).
TICKET_FILING_RE = re.compile(r"\bticket\b|\bwork[- ]item\b", re.IGNORECASE)
# The Return paragraph only -- "ticket" is common enough as an ordinary
# noun elsewhere in a body (e.g. a Require clause) that searching the
# whole body would false-pass on an unrelated mention.
RETURN_TEXT_RE = re.compile(r"^Return[ :](.*?)(?:\n[ \t]*\n|\Z)", re.MULTILINE | re.DOTALL)
PACK_WORKSPACE_RE = re.compile(r"^\|\s*workspace\s*\|\s*(.+?)\s*\|\s*$", re.MULTILINE)
PACK_STORE_RE = re.compile(r"\bstore\b", re.IGNORECASE)
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

__all__ = (
    'annotations', 'argparse', 'ast', 'hashlib',
    'json', 're', 'sys', 'Path',
    'ROOT', 'SKIPPED', 'SKILL_TIERS', 'BODY_BUDGET',
    'LINK_TARGET_RE', 'SURFACE_BUDGET', 'ROUTING_BLOCK_BUDGET', 'ROLE_AGENT_BUDGET',
    'DESCRIPTION_BUDGET',
    'ALLOWED_FRONTMATTER_KEYS', 'ROLE_PROFILES', 'ROLE_VALUES',
    'PACK_SIGNATURE_CELLS', 'PACK_TYPED_CELLS', 'PACK_ADAPTER_RE', 'PACK_STAGE_RE',
    'CRAFT_CELLS_BY_POINTER', 'CRAFT_MANDATORY_SECTIONS', 'CRAFT_OPTIONAL_SECTIONS',
    'CRAFT_BUDGET', 'CELL_SIMILARITY_THRESHOLD',
    'CELL_CLAUSE_MIN_WORDS', 'CALL_TOKEN_RE', 'REQUIRE_RE', 'NEVER_RE',
    'RETURN_RE', 'PACK_TABLE_CELL_RE', 'PACK_CELL_ROW_RE', 'CRAFT_ROW_RE',
    'ASSEMBLY_SKILL_FORM_RE', 'ASSEMBLY_NONE_FORM_RE', 'CELL_REFERENCE_LINK_RE', 'TABLE_DELIM_ROW_RE',
    'LIST_MARKER_RE', 'SENTENCE_END_RE', 'OUTSIDE_PACK_CITATION', 'SIGNATURE_CELL_POINTER_RE',
    'MANDATED_FORM_RES', 'MD_LINK_RE', 'LOOP_TRIGGER_RE', 'BOUND_TERM_RE',
    'TERMINAL_TERM_RE', 'ENVELOPE_UNITS', 'ENVELOPE_VOCAB_RES',
    'CARRIAGE_REQUIRE_BLOCK_RE', 'CARRIAGE_SENTENCE_SPLIT_RE', 'CARRIAGE_MD_LINK_RE', 'CARRIAGE_PAREN_RE',
    'CARRIAGE_CODE_RE', 'CARRIAGE_WORD_RE', 'CARRIAGE_DASH_SPLIT_RE', 'TICKET_FILING_RE',
    'RETURN_TEXT_RE', 'PACK_WORKSPACE_RE', 'PACK_STORE_RE', 'PACK_SLICING_RE',
    'CARRIAGE_QUALIFIERS', 'CARRIAGE_DEFERRED',
)
