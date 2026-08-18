"""Shared cutcheck contract constants and mutable invocation state."""

import argparse
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

try:  # in-repo; the installed copy sits flat beside tickets.py
    from scripts import state_root
    from scripts.tickets import (
        CHECKED_BY_KEY,
        GATE_EXECUTORS,
        GATE_ID_MARKER,
        ORACLE_CLASS_RE,
        PROVENANCE_RE,
        ROOT_EXECUTOR,
        _criteria as _ticket_criteria,
        _parse_frontmatter,
        _sections,
    )
except ImportError:  # pragma: no cover - the installed copy's path
    import state_root
    from tickets import (
        CHECKED_BY_KEY,
        GATE_EXECUTORS,
        GATE_ID_MARKER,
        ORACLE_CLASS_RE,
        PROVENANCE_RE,
        ROOT_EXECUTOR,
        _criteria as _ticket_criteria,
        _parse_frontmatter,
        _sections,
    )

FAMILY = "family 1"
FAMILY_2 = "family 2"
FAMILY_3 = "family 3"
FAMILY_4 = "family 4"
FAMILY_5 = "family 5"
FAMILY_6 = "family 6"
READING = "reading"
GRAPH = "graph"
ALREADY_PASSES = "already-passes"
NO_HITS_BOTH_REVISIONS = "no-hits-both-revisions"
FAILS_BOTH_REVISIONS = "fails-both-revisions"
SWALLOWED_EXIT = "swallowed-exit"
CUMULATIVE_RANGE = "cumulative-range"
UNCONFINED_ORACLE = "unconfined-oracle"
EXTRACTION_GAP = "extraction-gap"
VERDICT_IN_OUTPUT = "verdict-in-output"
UNRUNNABLE_ORACLE = "unrunnable-oracle"
WHOLE_SUITE_ORACLE = "whole-suite-oracle"
MISSING_PATH = "missing-path"
UNRESOLVED_CITATION = "unresolved-citation"
QUOTE_NOT_AT_CITATION = "quote-not-at-citation"
UNSCOPED_WRITE = "unscoped-write"
SCOPE_CONTRADICTION = "scope-contradiction"
SCOPE_OPEN = "scope-open"
SCOPE_COLLISION = "scope-collision"
STAGED_INVALIDATION = "staged-invalidation"
ORPHAN_CRITERION = "orphan-criterion"
ORPHAN_ITEM = "orphan-item"
COVERAGE_MAP_ABSENT = "coverage-map-absent"
ILLEGAL_EXECUTOR = "illegal-executor"
MULTIPLE_ROOTS = "multiple-roots"
MULTIPLE_GATE_SYSTEMS = "multiple-gate-systems"
MIXED_INDEPENDENCE = "mixed-independence"
MALFORMED_GATE = "malformed-gate"
UNCOVERED_GATE_CRITERION = "uncovered-gate-criterion"
SYMLINK_IN_TREE = "symlink-in-tree"
BYTECODE_WRITTEN = "bytecode-written"
UNREAD_HALF = "unread-half"
CRITICAL_PATH = "critical-path"
LEVEL_WIDTH = "level-width"
FAMILY_OF = {
    ALREADY_PASSES: FAMILY,
    NO_HITS_BOTH_REVISIONS: FAMILY,
    FAILS_BOTH_REVISIONS: FAMILY,
    SWALLOWED_EXIT: FAMILY,
    CUMULATIVE_RANGE: FAMILY,
    UNCONFINED_ORACLE: FAMILY,
    # Family 1 because it is the same question as UNCONFINED_ORACLE, asked of
    # the tree instead of the token: whether anything the copy holds reaches
    # out of it. `_names_outside_the_copy` says they are one problem twice.
    SYMLINK_IN_TREE: FAMILY,
    # Family 1 for the same reason and one step milder: it is what the copy
    # was written into with, read as a spelling of the oracle rather than as a
    # reach out of the copy.
    BYTECODE_WRITTEN: FAMILY,
    EXTRACTION_GAP: FAMILY,
    VERDICT_IN_OUTPUT: FAMILY,
    UNRUNNABLE_ORACLE: FAMILY,
    WHOLE_SUITE_ORACLE: FAMILY,
    MISSING_PATH: FAMILY_2,
    UNRESOLVED_CITATION: FAMILY_2,
    QUOTE_NOT_AT_CITATION: FAMILY_2,
    UNSCOPED_WRITE: FAMILY_3,
    SCOPE_CONTRADICTION: FAMILY_3,
    SCOPE_OPEN: FAMILY_3,
    SCOPE_COLLISION: FAMILY_4,
    STAGED_INVALIDATION: FAMILY_4,
    ORPHAN_CRITERION: FAMILY_5,
    ORPHAN_ITEM: FAMILY_5,
    COVERAGE_MAP_ABSENT: FAMILY_5,
    ILLEGAL_EXECUTOR: FAMILY_6,
    MULTIPLE_ROOTS: FAMILY_6,
    MULTIPLE_GATE_SYSTEMS: FAMILY_6,
    MIXED_INDEPENDENCE: FAMILY_6,
    MALFORMED_GATE: FAMILY_6,
    UNCOVERED_GATE_CRITERION: FAMILY_6,
    # No family: a reading that did not happen is a fact about this run on
    # this host, and the families are what a cut is graded on. It carries a
    # marker of its own so a reader filters it the way every other line is
    # filtered, and so no family's line count silently gains a member.
    UNREAD_HALF: READING,
    # No family either, and for the nearer half of the same reason: the shape
    # of a cut is not a defect of one. A family here would put two lines that
    # grade nothing into a family's count, and the marker keeps them selectable
    # by the one filter every other line answers to.
    CRITICAL_PATH: GRAPH,
    LEVEL_WIDTH: GRAPH,
}
# Advisory classes are printed and never set the exit status. A map that is
# not there is a fact about the run, not a defect of the cut; a committed
# symlink is a fact about the repository, and confinement does not rest on
# reporting it -- the clone flag holds whether or not anyone reads this line.
ADVISORY = frozenset(
    {
        EXTRACTION_GAP,
        COVERAGE_MAP_ABSENT,
        VERDICT_IN_OUTPUT,
        SYMLINK_IN_TREE,
        BYTECODE_WRITTEN,
        UNREAD_HALF,
    }
)
# The shape reading's classes, which are in neither set. An advisory is a
# finding the exit status forgives; these are not findings, so they are held
# out of the finding list altogether rather than forgiven inside it. Naming
# them here is what lets a reader ask the question directly instead of
# inferring the answer from two absences.
GRAPH_CLASSES = frozenset({CRITICAL_PATH, LEVEL_WIDTH})
# The one thing a python oracle writes into the copy by importing anything,
# and the flag that stops it. Reported in words because the repair is a
# spelling of the oracle and is stated nowhere else -- not in the pack's
# oracle policy, not in the decomposer's skill, not in this report until now.
BYTECODE_RE = re.compile(r"(?:^|/)__pycache__/|\.py[co]$")
BYTECODE_REPAIR = "the interpreter's own cache; spell this oracle with `-B`"
# The report's three summary lines. A reader selects finding lines by filtering
# stdout on a family, a class name, a criterion number or a ticket id, so no
# summary line may carry any of those, nor the path of a script: a summary a
# filter selects is a finding line to everything downstream. That is why the
# shape's heading names neither of the two readings standing under it.
#
# The shape's heading also has to read nothing like the advisory's. What sends
# a fresh cut checker at a set is an agent reading "cutcheck reported an
# advisory" off this report, and a heading that echoed the advisory's wording
# would fire that checker on every set ever graded. So it says outright what it
# is, and borrows none of the advisory's phrasing to say it.
ADVISORY_HEADING = "cutcheck: advisory -- reported, and never setting the exit status:"
GRAPH_HEADING = "cutcheck: the shape of this cut -- how long and how wide it is, and no finding of any kind:"
NO_FINDING_OUTSIDE = "cutcheck: no finding outside the advisory set"
SCRATCH_NOT_REMOVED = "cutcheck: scratch root not removed"
NO_SCRATCH_ROOT = "cutcheck: no scratch root could be placed for"
# Every copy any cut makes is one directory under the host's temp root, named
# so a root outliving its run is findable rather than anonymous.
SCRATCH_PREFIX = "cutcheck-"

# The acceptance-coverage map: one row per spec criterion, naming the item,
# the gate, or declared remainder that answers for it.
COVERAGE_FILE = "coverage.md"
# One map per root, named for the root that wrote it. The bare
# `coverage.md` is the one-root spelling and still read as one.
COVERAGE_SUFFIX = "." + COVERAGE_FILE
GATE_PREFIX_SEPARATOR = "."
COVERAGE_OWNERS = ("gate", "remainder")
TICKETS_DIR = "tickets"
CANARY_DIR = "canary"
RUNS_DIR = "runs"
# The three executors `tickets.py gate` writes into a root's gate stubs. They
# are the library's own nodes, so no pack cell names them and none has to.
GATE_STUB_EXECUTORS = frozenset(GATE_EXECUTORS.values())
# What makes an id a gate stub of a root that is in this set.
GATE_INFIX = ".gate."
# A pack's executor and assembly cells are the only executors it binds.
PACKS_DIR = None
PACK_CELL_RE = re.compile(r"^\|\s*(?:executor|assembly)\s*\|([^|]*)\|", re.M)
SKILL_NAME_RE = re.compile(r"`(orch-[a-z0-9-]+)`")
# A pack name comes from ticket content, so it names one directory or nothing.
PACK_NAME_RE = re.compile(r"^[\w-]+$")
OBJECTIVE_SECTION = "Objective"
INPUTS_SECTION = "Fixed inputs"
COMPLETION_SECTION = "Completion test"
BACKTICK_RE = re.compile(r"`([^`]+)`")
SWALLOW_RE = re.compile(r"\|\s*(?:tail|head)\b")
CUMULATIVE_RE = re.compile(r"\S+\.\.HEAD\b")
# No shell is a command head. A span an extractor claims is a span this tool
# runs, and ticket content is untrusted: `bash -lc '<anything>'` split argv-only
# still hands `<anything>` to a shell. A shell-headed span is recognized by no
# extractor, so it runs nowhere and surfaces as an extraction gap instead.
COMMAND_HEADS = (
    "git",
    "grep",
    "node",
    "npm",
    "pytest",
    "python",
    "python3",
    "rg",
)
SEARCH_HEADS = ("grep", "rg")
# The options this tool's own matcher reads, by the letter a long spelling maps
# onto. A search span is decided in this interpreter rather than by a program on
# PATH -- `_search_exit` says why -- so the set is what this implements and not
# what grep ships. A span carrying anything outside it is extracted by nobody
# and surfaces as the gap it is: guessing at an option's meaning would decide a
# cut from a reading nothing checked.
SEARCH_FLAGS = frozenset("cEFhHilnoqrRsvwx")
# `-e PATTERN` names the pattern rather than an operand, attached or separate.
SEARCH_PATTERN_FLAG = "e"
SEARCH_LONG_FLAGS = {
    "count": "c",
    "extended-regexp": "E",
    "files-with-matches": "l",
    "fixed-strings": "F",
    "ignore-case": "i",
    "invert-match": "v",
    "line-number": "n",
    "line-regexp": "x",
    "no-filename": "h",
    "no-messages": "s",
    "only-matching": "o",
    "quiet": "q",
    "recursive": "r",
    "regexp": SEARCH_PATTERN_FLAG,
    "silent": "q",
    "with-filename": "H",
    "word-regexp": "w",
}
# The status a search head exits with when it could not read what it was
# pointed at, which is neither a match nor the absence of one.
SEARCH_ERROR = 2
GIT_HEAD = "git"
# The tree mode git records for a symlink, whatever the checkout made of it.
SYMLINK_MODE = "120000"
# The git subcommands a scratch copy confines: each reads the revision under
# test and runs no program the span names. Membership is half the confinement
# and never the whole of it -- a member still writes and reads wherever its own
# options are pointed, which is `_names_outside_the_copy`'s question, not this
# set's.
# A closed set rather than a list of flags to refuse, because git's surface is
# open at both ends -- `-c core.pager=`, `-c alias.x=!`, `--exec-path`,
# `--upload-pack` and `--receive-pack` each run a named program by design, `-C`,
# `--git-dir` and `--work-tree` each move the execution out of the copy meant to
# confine it, and `clone` reaches the network. Refusing that list leaves the
# next flag git ships unrefused; refusing everything unlisted does not.
# `grep` is not here: `git grep -O` opens matches in a named pager, and plain
# `grep` is already a head this tool extracts and runs.
GIT_CONFINED_SUBCOMMANDS = frozenset(
    {
        "cat-file",
        "describe",
        "diff",
        "log",
        "ls-files",
        "ls-tree",
        "merge-base",
        "rev-list",
        "rev-parse",
        "show",
        "show-ref",
        "status",
    }
)
# An interpreter under one of these reads its program from the line, or from
# stdin, rather than from the tree: the same hazard a shell head is refused
# for, through a head an extractor otherwise accepts. Only these heads
# evaluate -- `grep -c` counts and `grep -e` names a pattern.
EVAL_HEADS = ("node", "npm", "python", "python3")
EVAL_ARGS = frozenset({"-c", "-e", "--eval", "--exec", "-"})
# A test invocation says which node it grades, or it grades whatever it finds.
# `discover` names no node by construction; `-k` names one whatever it is
# pointed at; `::` opens the node half of a pytest target.
TEST_RUNNERS = ("unittest", "pytest")
DISCOVER = "discover"
NODE_FILTER = "-k"
NODE_SEP = "::"
# A filter narrows only if some node id fails it. Every test node here is a
# method named `test_...`, so a pattern that is a prefix of that matches all of
# them: `-k test` is the whole suite with a flag on, and the token's presence
# is no evidence on its own.
FILTER_MATCHES_ALL = "test_"
# A criterion states the provenance of its own oracle; an oracle stated
# pre-existing is an invariant, and holding still is what it is for. The field
# itself is `scripts/tickets.py`'s -- `PROVENANCE_RE` there is the one spelling,
# and it reads the `| provenance: x` form that script writes as readily as the
# sentence form. What is decided here is the frame and not the field: stating a
# stamp is writing it at a field boundary with no word continuing it -- a
# parenthetical may follow, a predicate may not. A criterion that quotes the
# phrase, denies carrying it, or discusses what it means mentions the stamp
# instead of making one, and every such mention either sits behind a backtick,
# an article or a verb, or runs on into the clause that denies it. Grading is
# the default here, so a stamp written any other way is graded rather than
# believed.
PRE_EXISTING = "pre-existing"
STAMP_OPENS_RE = re.compile(r"(?:\A|[.;|])\s*$")
STAMP_CONTINUES_RE = re.compile(r"\s*[A-Za-z]")
# Counting prints the verdict rather than exiting on it.
COUNT_FLAG_RE = re.compile(r"^-[A-Za-z]*c[A-Za-z]*$|^--count$")
# Under `git` only the long flag counts: `git -c` sets a configuration
# override and `git log -c` asks for a combined diff, neither one a count.
GIT_COUNT_FLAG = "--count"
CITATION_RE = re.compile(r"\b([\w][\w./-]*\.[A-Za-z0-9]{1,5}):(\d+)")
SECTION_CITATION_RE = re.compile(r"\b([\w][\w./-]*\.[A-Za-z0-9]{1,5})\s+§(\d+)")
# A quotation opens and closes at a word boundary. A span that wrapped a line
# never closed, so the quote after the wrap opens nothing: the prose it would
# run to is the sentence around the citation, not a claim about the line.
QUOTE_RE = re.compile(
    r'(?<![\w"])"([^"\n]{6,120})"(?!\w)|(?<![\w`])`([^`\n]{6,120})`(?!\w)'
)
WRITE_RE = re.compile(
    r"\b(?:write|writes|writing|written|create|creates|creating|emit|emits"
    r"|append|appends|record|records)\b",
    re.IGNORECASE,
)
# The other half of family 3: not what the item adds, what it takes away. An
# objective that deletes, moves or renames a literal has to carry every file
# that pins it, or the pin breaks where nobody is licensed to repair it.
REMOVAL_RE = re.compile(
    r"\b(?:delete|deletes|deleting|deleted|remove|removes|removing|removed"
    r"|rename|renames|renaming|renamed|move|moves|moving|moved"
    r"|drop|drops|dropping|dropped)\b",
    re.IGNORECASE,
)
REMOVAL_WINDOW = 80
# A literal is a token specific enough for a pin to be about it: it carries a
# separator -- a path's slash, a skill name's dash, a constant's underscore, an
# extension's dot. Every file in a tree holds ordinary words, so a bare one
# would name the whole tree and say nothing about this cut.
LITERAL_RE = re.compile(r"^[A-Za-z0-9][\w./-]{2,}$")
LITERAL_MARKS = ("-", "_", "/", ".")
# Where a literal gets pinned: the checks that assert it, the scripts that hold
# it as a constant, the prose that names it, the compositions that call it. A
# root the repository under test does not carry costs nothing to look for, and
# a tree of source the removal does not touch is not searched at all.
PIN_ROOTS = ("compositions", "docs", "scripts", "tests")
# Bytes past which a file is not prose anybody pins a name in. A cap and not a
# filter on suffix: what a repository keeps under these roots is its own
# business, and the reading is a substring search that decodes anything.
PIN_SIZE_LIMIT = 512 * 1024
# Per tree, every file under PIN_ROOTS with its text, read once per invocation
# and only where some objective takes a literal away. A cut that removes
# nothing never opens a file here.
_PIN_INDEX = {}
# Per tree, what the index could not read, kept beside it for the same span:
# a cached index is handed to later invocations, and the skipped files are
# part of what that index is.
_PIN_SKIPPED = {}
DOTTED_RE = re.compile(r"\.[A-Za-z0-9]{1,5}$")
GLOB_RE = re.compile(r"[*?\[\]]")
# `<run>` stands for whichever run it is: a shape, not a path anything writes.
PLACEHOLDER_RE = re.compile(r"[<>]")
# "write scope" names the grant. A denied write commits the item to nothing.
SCOPE_WORD_RE = re.compile(r"^[-_ ]scopes?\b", re.I)
DENIAL_RE = re.compile(r"\b(?:not|never|no|without|rather than)\s+$", re.I)
DENIAL_WINDOW = 24
# A denied write and a quoted command are one question asked twice: is the
# ticket doing the thing, or talking about it? ``DENIAL_RE`` answers it for a
# write verb -- the ``cutcheck-mention`` set grades that answer -- and it reads
# the same standing in front of a command span. Two frames it lacks: a span the
# guard refuses, and a span named as an example of what something else runs.
# Adjacency is the whole of the rule and not an economy: of the 611 command
# spans this repository's ticket corpus states, 104 carry one of these words
# somewhere in the 60 characters before them and none carries one adjacent, so
# a window merely scanned for the word would refuse a hundred live oracles.
MENTION_RE = re.compile(r"\b(?:refuses|refused|such as|like)\s+$", re.I)
# A citation points at a line; the sentence around it may wrap.
CITED_LINES = 2
QUOTE_WINDOW = 80
WRITE_WINDOW = 80
NO_MATCH = 1
COMMAND_TIMEOUT = 180
TIMED_OUT = 124
UNRUNNABLE = 127
NO_TICKET_SET = 2
REPORTED = 1
CLEAN = 0
# One invocation's read of one (command, scratch tree) pair. The trees are
# copies built for this invocation, and `_mutations` is what measures whether
# the pair really does read the same twice.
_EXIT_CACHE = {}
# Per scratch tree, every status entry that tree has already shown. Primed at
# the clone, so the first reading after a span names what the span wrote and
# not what the checkout arrived with.
_TREE_STATE = {}
# What the span now running wrote into its copy. Drained per command by
# `_check_ticket`, which is the only caller that knows whose finding it is.
_MUTATED = []
# Every reading this invocation could not make, in the order it failed to make
# them, each named once. A list beside `_MUTATED` and for its reason: what a
# reading noticed besides its own answer reaches the report without every
# function between here and there carrying a second return value for it.
# Drained by `main`, which is the only caller that knows whose run it is.
_UNREAD = []

__all__ = (
    'argparse', 'os', 're', 'shlex',
    'shutil', 'subprocess', 'sys', 'tempfile',
    'Path', 'state_root', 'CHECKED_BY_KEY', 'GATE_EXECUTORS',
    'GATE_ID_MARKER', 'ORACLE_CLASS_RE', 'PROVENANCE_RE', 'ROOT_EXECUTOR',
    '_ticket_criteria', '_parse_frontmatter', '_sections', 'FAMILY',
    'FAMILY_2', 'FAMILY_3', 'FAMILY_4', 'FAMILY_5',
    'FAMILY_6', 'READING', 'GRAPH', 'ALREADY_PASSES',
    'NO_HITS_BOTH_REVISIONS', 'FAILS_BOTH_REVISIONS', 'SWALLOWED_EXIT', 'CUMULATIVE_RANGE',
    'UNCONFINED_ORACLE', 'EXTRACTION_GAP', 'VERDICT_IN_OUTPUT', 'UNRUNNABLE_ORACLE',
    'WHOLE_SUITE_ORACLE', 'MISSING_PATH', 'UNRESOLVED_CITATION', 'QUOTE_NOT_AT_CITATION',
    'UNSCOPED_WRITE', 'SCOPE_CONTRADICTION', 'SCOPE_OPEN', 'SCOPE_COLLISION',
    'STAGED_INVALIDATION', 'ORPHAN_CRITERION', 'ORPHAN_ITEM', 'COVERAGE_MAP_ABSENT',
    'ILLEGAL_EXECUTOR', 'MULTIPLE_ROOTS', 'MULTIPLE_GATE_SYSTEMS', 'MIXED_INDEPENDENCE',
    'MALFORMED_GATE', 'UNCOVERED_GATE_CRITERION', 'SYMLINK_IN_TREE', 'BYTECODE_WRITTEN',
    'UNREAD_HALF', 'CRITICAL_PATH', 'LEVEL_WIDTH', 'FAMILY_OF',
    'ADVISORY', 'GRAPH_CLASSES', 'BYTECODE_RE', 'BYTECODE_REPAIR',
    'ADVISORY_HEADING', 'GRAPH_HEADING', 'NO_FINDING_OUTSIDE', 'SCRATCH_NOT_REMOVED',
    'NO_SCRATCH_ROOT', 'SCRATCH_PREFIX', 'COVERAGE_FILE', 'COVERAGE_SUFFIX',
    'GATE_PREFIX_SEPARATOR', 'COVERAGE_OWNERS', 'TICKETS_DIR', 'CANARY_DIR',
    'RUNS_DIR', 'GATE_STUB_EXECUTORS', 'GATE_INFIX', 'PACKS_DIR',
    'PACK_CELL_RE', 'SKILL_NAME_RE', 'PACK_NAME_RE', 'OBJECTIVE_SECTION',
    'INPUTS_SECTION', 'COMPLETION_SECTION', 'BACKTICK_RE', 'SWALLOW_RE',
    'CUMULATIVE_RE', 'COMMAND_HEADS', 'SEARCH_HEADS', 'SEARCH_FLAGS',
    'SEARCH_PATTERN_FLAG', 'SEARCH_LONG_FLAGS', 'SEARCH_ERROR', 'GIT_HEAD',
    'SYMLINK_MODE', 'GIT_CONFINED_SUBCOMMANDS', 'EVAL_HEADS', 'EVAL_ARGS',
    'TEST_RUNNERS', 'DISCOVER', 'NODE_FILTER', 'NODE_SEP',
    'FILTER_MATCHES_ALL', 'PRE_EXISTING', 'STAMP_OPENS_RE', 'STAMP_CONTINUES_RE',
    'COUNT_FLAG_RE', 'GIT_COUNT_FLAG', 'CITATION_RE', 'SECTION_CITATION_RE',
    'QUOTE_RE', 'WRITE_RE', 'REMOVAL_RE', 'REMOVAL_WINDOW',
    'LITERAL_RE', 'LITERAL_MARKS', 'PIN_ROOTS', 'PIN_SIZE_LIMIT',
    '_PIN_INDEX', '_PIN_SKIPPED', 'DOTTED_RE', 'GLOB_RE',
    'PLACEHOLDER_RE', 'SCOPE_WORD_RE', 'DENIAL_RE', 'DENIAL_WINDOW',
    'MENTION_RE', 'CITED_LINES', 'QUOTE_WINDOW', 'WRITE_WINDOW',
    'NO_MATCH', 'COMMAND_TIMEOUT', 'TIMED_OUT', 'UNRUNNABLE',
    'NO_TICKET_SET', 'REPORTED', 'CLEAN', '_EXIT_CACHE',
    '_TREE_STATE', '_MUTATED', '_UNREAD',
)
