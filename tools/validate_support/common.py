"""Shared constants and imports for the orchflows validator."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import sys
from pathlib import Path

# An install ships this package flat in `bin/`; hence the paired import.
try:
    from scripts._bootstrap import ROOT
except ImportError:  # pragma: no cover - direct/installed flat script path
    from _bootstrap import ROOT

# What a check says when the tree it grades is not here. One wording, so a
# reader can grep the report for every check that did not run.
SKIPPED = "absent; check skipped"

SKILL_TIERS = ("kernel", "workflows")
# Words, not lines: a line count is met by widening lines. Markdown link
# targets are stripped first so a citation costs its label, not its path.
BODY_BUDGET = {
    "kernel": 300,
    "workflows": 450,
    "pack": 150,
}
LINK_TARGET_RE = re.compile(r"\]\([^)]*\)")
# rules/token-economy.md §11: every-turn surfaces tightest, every-dispatch
# units next, every-run units widest. Ceilings only fall.
SURFACE_BUDGET = {"templates/host-block.md": 400, "AGENTS.md": 230}
# The default ceiling a project's own router file is held to. This
# repository states its own at SURFACE_BUDGET["AGENTS.md"] instead.
ROUTING_BLOCK_BUDGET = 400
# rules/token-economy.md section 11's "role agent file" and roles.py's
# rendered-body `BODY_CEILING` are one fact, so roles.py imports this literal.
ROLE_AGENT_BUDGET = 80
DESCRIPTION_BUDGET = 140
ALLOWED_FRONTMATTER_KEYS = {"name", "description", "disable-model-invocation", "role"}
ROLE_PROFILES = {"orch-planner", "orch-worker"}
ROLE_VALUES = {"planner", "worker", "none"}
# The subset an *applied* skill may declare. `rules/roles.md` clause 6: a
# role-bearing skill runs only in an established child of the matching role,
# so `role: none` refuses that entry. Derived from the set above.
APPLIED_ROLE_VALUES = ROLE_VALUES - {"none"}
PACK_SIGNATURE_CELLS = (
    "adapter",
    "craft",
)
PACK_TYPED_CELLS = ("adapter",)
# The one cell whose content is a whole reference file, so the duplication
# linter compares what it points at rather than the pointer row.
CRAFT_CELLS_BY_POINTER = ("craft",)
# The craft sections every pack must carry (contracts/pack-signature.md),
# and the one optional section the linter still compares. `## Lens` is keyed
# by artifact kind, so a craft carrying a section it absorbed states one
# fact twice.
CRAFT_MANDATORY_SECTIONS = (
    "Vocabulary",
    "Workspace",
    "Spec fields",
    "Lens",
)
CRAFT_OPTIONAL_SECTIONS = ("Stages",)
CRAFT_RETIRED_SECTIONS = ("Outline", "Slicing", "Evidence", "Shape")
# The two artifact kinds every craft's Lens keys, in their required order
# before the adapter's own: the machinery already identifies a frozen root
# and a cut, so every domain judges both.
CRAFT_LIBRARY_LENS_KINDS = ("root", "cut")
# The sum of the folded parts at the fold; only falls.
CRAFT_BUDGET = 130
# A sheet is extra craft one ticket stamps beside its pack, read by the same
# child at the same moment, so a sheet that grew a craft's worth of law
# would be a second, unregistered pack: its ceiling sits under the craft's.
SHEET_DIR_NAME = "sheets"
SHEET_MANIFEST = "SHEET.md"
SHEET_BUDGET = 100
SHEET_REQUIRED_FRONTMATTER = ("name", "description", "packs")
SHEET_REQUIRED_SECTIONS = ("Craft", "Lens")
SHEET_OPTIONAL_SECTIONS = ("Vocabulary",)
# Identities, isolation, the stage sequence and what a spec must carry are
# facts about a domain, so a sheet restating one would be a second owner.
SHEET_PACK_ONLY_SECTIONS = ("Workspace", "Stages", "Spec fields")
# A sheet carries prose and nothing executable, so it declares no
# dependencies and owns no environment.
SHEET_REFUSED_ENTRIES = ("scripts", "requirements.txt", "tools.txt")
# Cross-pack cell linter. Both figures are normative: with `doclint`'s ratio
# under them the reported pair set is a function of these two and of
# `doclint.DISTINCTIVE_MAX`.
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
CELL_REFERENCE_LINK_RE = re.compile(r"\]\((references/[^)]+)\)")
TABLE_DELIM_ROW_RE = re.compile(r"^\|(?:\s*:?-{2,}:?\s*\|)+\s*$")
LIST_MARKER_RE = re.compile(r"^(?:[-*+]|\d+[.)])\s+")
SENTENCE_END_RE = re.compile(r"(?<=[.!?])\s+")
OUTSIDE_PACK_CITATION = "](../"
# The same citation written as prose instead of a link: a reference file
# opens by naming the cell it satisfies, and that cell is
# contracts/pack-signature.md's. Dropped for OUTSIDE_PACK_CITATION's reason.
SIGNATURE_CELL_POINTER_RE = re.compile(r"per the signature's [a-z_]+ cell")
MD_LINK_RE = re.compile(r"\]\(([^)]+)\)")
LOOP_TRIGGER_RE = re.compile(r"\biterat(?:e|es|ing)\b|\brepeat until\b", re.IGNORECASE)
BOUND_TERM_RE = re.compile(r"bound|budget", re.IGNORECASE)
TERMINAL_TERM_RE = re.compile(r"stalled|limited|exit|terminal", re.IGNORECASE)

# --- Result envelope (contracts/result.md) ---------------------------
#
# The bound dispatchable units lead their Return with the envelope: status,
# result identity, verification. ENVELOPE_UNITS names the units
# contracts/result.md's Binding paragraph binds; a unit dropped from this
# list stops being checked rather than silently passing a check it fails.
# Mechanized as a first-clause vocabulary lint, tolerant of prose ordering
# within that clause.
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
# Every Require item rides a named T0 carrier, and the caller supplies each
# callee's Require item by that name. Mechanized as a lexical head-noun
# presence check, so the parsing favors zero false ERRORs over precision.
CARRIAGE_REQUIRE_BLOCK_RE = re.compile(r"^Require:(.*?)(?:\n[ \t]*\n|\Z)", re.MULTILINE | re.DOTALL)
CARRIAGE_SENTENCE_SPLIT_RE = re.compile(r"\.\s+(?=[A-Z])", re.DOTALL)
CARRIAGE_MD_LINK_RE = re.compile(r"\[([^\]]*)\]\([^)]*\)")
CARRIAGE_PAREN_RE = re.compile(r"\([^)]*\)")
CARRIAGE_CODE_RE = re.compile(r"`([^`]*)`")
CARRIAGE_WORD_RE = re.compile(r"[A-Za-z][A-Za-z'-]*")
CARRIAGE_DASH_SPLIT_RE = re.compile(r"[–—]")  # en dash, em dash
# Rule 10(c) / pack-signature.md's sharing constraint: a Return files per
# work-item.md's filing law -- the ticket, or the store the assignment names
# -- and those two destinations are this check's two pass conditions, so
# kernel-tier primitives stay domain-blind.
TICKET_FILING_RE = re.compile(r"\bticket\b|\bwork[- ]item\b", re.IGNORECASE)
# The Return paragraph only -- "ticket" is common enough as an ordinary noun
# elsewhere in a body that searching the whole body would false-pass.
RETURN_TEXT_RE = re.compile(r"^Return[ :](.*?)(?:\n[ \t]*\n|\Z)", re.MULTILINE | re.DOTALL)
PACK_WORKSPACE_RE = re.compile(r"^\|\s*workspace\s*\|\s*(.+?)\s*\|\s*$", re.MULTILINE)
PACK_STORE_RE = re.compile(r"\bstore\b", re.IGNORECASE)
PACK_SLICING_RE = re.compile(r"^\|\s*slicing\s*\|\s*\[.*?\]\(([^)]+)\)", re.MULTILINE)

# Closed-class words stripped from the head of a Require item and treated as
# a phrase boundary once real content has started -- never an open-class word.
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

# Carriage gaps deferred pending a caller-prose fix, keyed by ("edge",
# caller, callee, head_noun) or ("pack", pack_name, role, head_noun).
CARRIAGE_DEFERRED = {}

__all__ = (
    'annotations', 'argparse', 'ast', 'hashlib',
    'json', 're', 'sys', 'Path',
    'ROOT', 'SKIPPED', 'SKILL_TIERS', 'BODY_BUDGET',
    'LINK_TARGET_RE', 'SURFACE_BUDGET', 'ROUTING_BLOCK_BUDGET', 'ROLE_AGENT_BUDGET',
    'DESCRIPTION_BUDGET',
    'ALLOWED_FRONTMATTER_KEYS', 'ROLE_PROFILES', 'ROLE_VALUES',
    'APPLIED_ROLE_VALUES',
    'PACK_SIGNATURE_CELLS', 'PACK_TYPED_CELLS', 'PACK_ADAPTER_RE',
    'CRAFT_CELLS_BY_POINTER', 'CRAFT_MANDATORY_SECTIONS', 'CRAFT_OPTIONAL_SECTIONS',
    'CRAFT_RETIRED_SECTIONS', 'CRAFT_LIBRARY_LENS_KINDS',
    'CRAFT_BUDGET', 'CELL_SIMILARITY_THRESHOLD',
    'SHEET_DIR_NAME', 'SHEET_MANIFEST', 'SHEET_BUDGET',
    'SHEET_REQUIRED_FRONTMATTER', 'SHEET_REQUIRED_SECTIONS',
    'SHEET_OPTIONAL_SECTIONS', 'SHEET_PACK_ONLY_SECTIONS',
    'SHEET_REFUSED_ENTRIES',
    'CELL_CLAUSE_MIN_WORDS', 'CALL_TOKEN_RE', 'REQUIRE_RE', 'NEVER_RE',
    'RETURN_RE', 'PACK_TABLE_CELL_RE', 'PACK_CELL_ROW_RE', 'CRAFT_ROW_RE',
    'CELL_REFERENCE_LINK_RE', 'TABLE_DELIM_ROW_RE',
    'LIST_MARKER_RE', 'SENTENCE_END_RE', 'OUTSIDE_PACK_CITATION', 'SIGNATURE_CELL_POINTER_RE',
    'MD_LINK_RE', 'LOOP_TRIGGER_RE', 'BOUND_TERM_RE',
    'TERMINAL_TERM_RE', 'ENVELOPE_UNITS', 'ENVELOPE_VOCAB_RES',
    'CARRIAGE_REQUIRE_BLOCK_RE', 'CARRIAGE_SENTENCE_SPLIT_RE', 'CARRIAGE_MD_LINK_RE', 'CARRIAGE_PAREN_RE',
    'CARRIAGE_CODE_RE', 'CARRIAGE_WORD_RE', 'CARRIAGE_DASH_SPLIT_RE', 'TICKET_FILING_RE',
    'RETURN_TEXT_RE', 'PACK_WORKSPACE_RE', 'PACK_STORE_RE', 'PACK_SLICING_RE',
    'CARRIAGE_QUALIFIERS', 'CARRIAGE_DEFERRED',
)
