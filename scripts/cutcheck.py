#!/usr/bin/env python3
"""Report cut defects in an issued ticket set, before any work starts.

Family 1 is oracle discrimination and oracle shape. Family 2 is path
reality. Family 3 is scope closure. Family 4 is pairwise safety. Family
5 is acceptance coverage. Family 6 is executor and verification-layout
legality. One invocation decides all six.

A reading none of them could make is reported under ``reading`` rather
than absorbed into whichever family wanted it: a status that did not
answer, a copy git could not list, a file too large to index, a library
holding no pack cell. Advisory, because a reading this host could not
make is no defect of the cut -- and printed, because the alternative is a
family that graded nothing reading exactly like a family that graded
everything and found it clean. A revision that could not be cloned at all
is the one reading that stops the run instead: neither half of a
discrimination can be graded against a copy that is not there.

Discrimination: an oracle that reads the same at the baseline as it will
once the work has landed proves nothing. Every extractable oracle runs
inside a scratch copy of the baseline revision and, when it fails there,
inside a scratch copy of HEAD -- both cloned beside the tree, each carrying
its own history, never in the tree under test. An oracle that already passes
at the baseline, that finds nothing at either revision, or that fails at
both from a missing path, class or module is reported, and so is one that no
revision runs at all: a command that is absent or that never returns is a cut
defect wherever it is read. When HEAD is the baseline the HEAD half is
skipped: at cut time nothing has landed, so a baseline failure is what a
discriminating oracle looks like. Execution therefore decides two classes
there and only two -- the oracle that already passes, and the one nothing can
run -- because every other class needs a reading of the landed work to compare
against, and at cut time there is none. A test invocation naming no node id --
a whole module, a whole tree, a bare ``discover`` -- is reported without being
run at all: it grades the identical tests under every item it is stated under,
so no reading of it could discriminate one from another. An oracle whose
criterion states ``provenance: pre-existing`` is an invariant -- it passed
before the work and has to pass after -- so discrimination is not asked of it,
and nothing else is forgiven it. A command carrying its verdict in what it
prints rather than in its exit status -- a count -- is reported as one this
tool cannot decide. A ``git`` oracle is no exception in either direction: the
scratch copy carries its history, so a git command reads the revision under
test and is graded on its exit status like any other, and the count-flagged
one -- ``git rev-list --count`` -- is undecidable for its count, never for
its head. Grading a git span is still not trusting it: only a subcommand named
as reading the revision runs, and only while none of its own arguments spells a
location outside the scratch copy. Every other git span is refused and
reported.

Path reality: a path an oracle names exists at the baseline, or the item
itself or a ``depends_on`` ancestor creates it; a ``file:line`` or
``file section`` citation resolves; a quoted string is present where it
is cited. All of it resolves in the baseline scratch copy -- the tree
the ticket was cut from, which the work then changes.

Scope closure: the write scope covers every path the item says it
writes, evidence sinks included, and no excluded action names a path the
scope grants. A path the item only reads is no defect: observing is not
naming, and neither is mentioning -- a placeholder, a denied write, the
grant's own name. The same grant is read the other way round as well: a
literal the objective deletes, moves or renames -- a path, a skill name, an
enum member, a set member -- is searched for through the tree's checks,
scripts, prose and compositions, and every file outside the grant that pins
it is reported once, named with the literal. The item cannot land without
breaking that file and is not licensed to repair it, so either the cut
carries the pin or the item is re-cut. A denied removal takes nothing away,
and a file sitting inside what is removed is no pin left behind by it.

Pairwise safety: for every pair the DAG leaves unordered -- ordering is
reachability through ``depends_on``, not adjacency -- write scopes are
disjoint and neither item's oracle reads what the other writes, or
whichever lands first invalidates the other's evidence.

Coverage: the run's acceptance-coverage map, read beside whichever
ticket root resolved, is checked both ways against the issued set. Every
criterion reaches an item, the gate, or declared remainder, and every
item is named by some criterion. A root with no map has nothing to read
against, so the absence is all that is reported. The issued set is the
work items: a root ticket is the acceptance's source rather than an item
of it, and its ``<root>.gate.*`` stubs are named by the keyword rather
than by id, so neither is read as an item here or paired in family 4.

Executor legality: an item's executor is one its stamped pack's executor
or assembly cell names. The cells are read from the orchflows library
rather than from the repository under test, which carries no packs of
its own. An item naming no pack has no cell to resolve against and is
not graded here; a root ticket and its gate stubs are graded against the
library's own structural executors, which no pack's cell names; and an
id sitting inside another root's subtree is reported as a nested root.
Until P4-3 this family also refused an engine as an executor -- the two
engines it named are deleted, and both survivors (``orch-loop`` for a
loop ticket, ``orch-frontier`` for a nested template) are lawful.

Shape: the command text itself carries three defects. A pipeline through
``tail`` or ``head`` reports that pipe's exit status, not the check's. A
per-item scope check written against a cumulative ``<base>..HEAD`` range
answers about the whole branch, not the item. A ``git`` span the scratch copy
does not confine is refused unrun, because ticket content decides no program
this tool executes, no directory it executes in, and no file it reads or
writes.

All three set the exit status. An extraction gap, an absent coverage
map, and a class this tool reports as one it cannot decide do not: a
criterion whose oracle no extractor recognized is reported on its own
line so silent under-coverage stays visible, but real tickets state many
criteria in prose, and a gap that failed the run would turn every clean
set red. Gaps are for the decomposer to read, not for the exit code to
decide.

Below both blocks stands a third, and it holds no finding of any kind. It
is a reading of the cut's shape -- how long the longest ``depends_on``
chain through the issued items is, and how many items stand on each level
of them -- printed for every set this tool resolves, clean or not. A cut
is not defective for being deep or for being narrow, and this tool grades
defects, so the shape is reported and nothing more: it is what the
decomposer minimizes and what the frontier's queue is shaped by, and both
of them were reading it off the tickets by hand. Its two classes carry a
marker of their own, sit outside the advisory set because they are not
advisory findings but not findings, and are built apart from the finding
list so that no path exists by which they could move the exit status.

The copy is checked as well as the spans run in it. A tree entry carrying
git's ``120000`` mode is the one route out that argv cannot see, so the copy
is cloned with ``core.symlinks=false`` -- which makes such an entry a file
holding a path rather than a way through it -- and every entry recording that
mode is reported. That is the instrument for ``rules/visibility.md`` §5, and
it is advisory: the clone flag is what enforces confinement, unconditionally
and whatever the tree holds, so the report adds visibility and not safety. A
committed symlink is a property of the repository, and this tool owns
cut-defect detection over an issued ticket set. Failing a cut for it would
fail every cut in every repository where a symlink is legal, for a reason
outside what this tool answers for.

cutcheck never edits a ticket; it reports, and the decomposer repairs.
An extracted command is ticket content and ticket content is untrusted,
so commands run argv-only, never through a shell, under a timeout, with
a working directory inside a scratch copy. A span whose own arguments are
the program -- a shell, or an interpreter reading code from ``-c``, ``-e``,
``--eval``, ``--exec`` or a bare ``-`` -- is recognized by no extractor, so it
runs nowhere and surfaces as an extraction gap. So is a span carrying a
command head and no argument at all: ticket prose names tools in backticks,
and a bare name decides nothing about the item it is stated under. So is a
span a criterion quotes rather than states -- one standing behind a denial, a
refusal or an example -- because a command named as what not to do, as what
the guard refuses, or as what CI runs is no oracle of the item naming it.

A search span -- ``grep``, ``rg`` -- is the one head not spawned: it is
decided against the scratch copy by this tool's own matcher, so its verdict
reads the same on a host whose PATH carries no grep. The matcher reads a
closed option set (``SEARCH_FLAGS``), and a span carrying an option outside it
is the same extraction gap rather than a status guessed at.
"""

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
PACKS_DIR = "packs"
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


def _unread(what):
    """Record a reading that did not happen, and what could not be read.

    The defect this closes is one value standing for two answers. ``None``
    meant both "this oracle discriminates" and "no half of it could be
    read"; ``[]`` meant both "this span wrote nothing" and "the status that
    would have said so failed"; and a caller cannot tell a grading that
    happened from one that did not. Every such site names itself here.
    """

    if what not in _UNREAD:
        _UNREAD.append(what)


def _git(args, cwd):
    try:
        return subprocess.run(
            ["git"] + args,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=COMMAND_TIMEOUT,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None


def _worktree_root():
    proc = _git(["rev-parse", "--show-toplevel"], Path.cwd())
    if proc is None or proc.returncode != 0:
        return None
    return Path(proc.stdout.strip())


def _run_dir(run, worktree_root):
    """Locate the issued ticket set for ``run``.

    Run tickets resolve in the one user-scope state sink
    (``scripts/state_root.py``), so a run is checkable from any workspace in
    any repository. Canary tickets resolve at the main checkout instead: the
    canary is a git-tracked golden fixture, not run state. Fixture sets
    resolve at the invoking worktree's own top level for the same reason, and
    every frontier item carries its own copy in its own worktree.
    """

    candidates = [state_root.tickets_root() / run]
    main_root = state_root.find_repo_root(Path.cwd())
    if main_root is not None:
        candidates.append(main_root / ".orch" / "canary" / "tickets" / run)
    if worktree_root is not None:
        candidates.append(worktree_root / "tests" / "fixtures" / "cutcheck" / run)
    for candidate in candidates:
        if candidate.is_dir():
            return candidate
    return None


def _scratch_root(worktree_root):
    """One invocation's private directory for the copies it grades in.

    The host's temp root, so the length of a scratch path is a fact about the
    host and never about the tree being graded. Placing it inside the target's
    own git storage put it beside the object store a local clone hardlinks
    from, which is faster and which made the tool unusable on Windows: a
    copy's paths are then the target's path plus a scratch directory plus a
    revision directory plus the deepest path in the revision, and a
    183-character worktree root took ``git clone`` past ``MAX_PATH`` on its own
    template copy -- which ``core.longpaths=true`` does not cover, so every
    invocation from that tree exited before grading anything. Speed gives way
    to running at all; the copy is still a clone, so it still carries history.

    ``worktree_root`` no longer decides where the copies land -- that is the
    whole of the change -- and stays as the argument the caller and the test
    harness both hold this seam by.

    ``None`` where the temp root will not take a directory; the caller has a
    ticket set it cannot grade and says so.
    """

    try:
        return Path(tempfile.mkdtemp(prefix=SCRATCH_PREFIX))
    except OSError:
        return None


def _remove_scratch_root(scratch_root):
    """Remove this invocation's copies, and say so when they will not go.

    ``ignore_errors=True`` here was a swallowed error in the tool whose whole
    subject is swallowed errors: each copy is a full clone, and a removal that
    quietly failed left one on disk per invocation with nothing said.

    Said rather than raised, never exit-setting, and on stderr. The report is
    about this tool's own hygiene: a leaked copy is no finding against the
    ticket set that was being read, and the `finally` this runs in precedes
    every finding printed, so the same line on stdout would prepend itself to
    a pinned verdict and move all of them at once on any host that leaks.
    """

    try:
        shutil.rmtree(str(scratch_root))
        return
    except OSError:
        # Git writes loose objects and packs `0o444` and hardlinks that mode
        # into every clone, so a strict removal meets it on every platform;
        # where a file with no write bit cannot be unlinked at all, as on
        # Windows, that alone would leak a copy per invocation. The mode is
        # git's statement about an object and never about whether this copy
        # may go, so clear it and try once more before calling the removal
        # refused. Only ever on the retry: the walk costs nothing on the path
        # that already succeeded.
        pass
    for path in [scratch_root] + sorted(scratch_root.rglob("*")):
        try:
            # A directory has to be enterable and writable to give up its
            # children; a file only has to be writable.
            path.chmod(path.stat().st_mode | (0o700 if path.is_dir() else 0o200))
        except OSError:
            pass
    try:
        shutil.rmtree(str(scratch_root))
    except OSError as exc:
        sys.stderr.write(
            "{}: {}: {}\n".format(SCRATCH_NOT_REMOVED, scratch_root, exc)
        )


def _scratch_tree(rev, worktree_root, scratch_root):
    """Clone ``rev`` beside the tree, so no oracle runs in the tree itself.

    A clone, not an extract: the copy carries its own history, so a git oracle
    reads the revision under test rather than walking up to whichever
    repository happens to enclose the copy. ``rev`` is resolved here, against
    the tree being graded, so the clone's own HEAD never decides what ``HEAD``
    meant. The clone keeps no remote: an oracle is ticket content, and ticket
    content is untrusted, so the scratch tree offers it no path to write back
    out of.

    ``core.symlinks=false`` is the third route out, and the only one the copy
    rather than the text can close. A committed symlink materialises as a file
    holding its target's path, so ``--output=link/PAYLOAD`` and
    ``-O link/orderfile`` -- both spelling a location inside the copy, both
    landing outside it -- fail on the copy's own filesystem instead. Written
    into the clone's config with ``--config`` and never with a global ``-c``:
    the checkout below is a separate process, and only what the config file
    holds reaches it. Windows already defaults to this, so setting it removes
    a divergence rather than adding one.

    ``core.longpaths=true`` for the same reason and by the same route. Where
    git enforces ``MAX_PATH`` the checkout below drops the entries it cannot
    write and still exits 0, so the copy arrives short of the revision it
    claims to hold and every oracle after it reads a tree missing files. Set
    here rather than asked of the host: a copy that silently omits part of the
    revision is a wrong reading on whichever host omits it.
    """

    tree = scratch_root / re.sub(r"[^A-Za-z0-9_.-]", "-", rev)
    if tree.is_dir():
        return tree
    resolved = _git(["rev-parse", rev + "^{commit}"], worktree_root)
    if resolved is None or resolved.returncode != 0:
        return None
    clone = [
        "clone",
        "--quiet",
        "--no-checkout",
        "--config",
        "core.symlinks=false",
        "--config",
        "core.longpaths=true",
        str(worktree_root),
        str(tree),
    ]
    steps = (
        (clone, scratch_root),
        (["checkout", "--quiet", "--detach", resolved.stdout.strip()], tree),
        (["remote", "remove", "origin"], tree),
    )
    for args, cwd in steps:
        proc = _git(args, cwd)
        if proc is None or proc.returncode != 0:
            shutil.rmtree(tree, ignore_errors=True)
            return None
    # Whatever the checkout arrived carrying is the copy's arrival state and no
    # span's doing. Recorded here so the first span graded is answerable for
    # the difference it made and for nothing else.
    _mutations(tree)
    return tree


def _mutations(tree):
    """Paths this copy holds that it did not hold at the previous reading.

    ``--ignored`` is the whole reading rather than a refinement of it. The leak
    this measures was found on disk as a `.pytest_cache/` directory, and this
    repository ignores that path, as every repository running pytest does: a
    bare ``git status --porcelain`` returns zero lines with the directory
    sitting in the copy, so the plain spelling is silently vacuous against the
    one leak that motivated the check. Ignored states what a reader wants kept
    out of a diff, and never what a sibling's oracle reads.

    A delta and not a census, because one copy grades span after span: the
    first writer would otherwise convict every span that followed it, and a
    checkout an eol rule or a filter left dirty would convict the first.
    """

    proc = _git(["status", "--porcelain", "--ignored"], tree)
    if proc is None or proc.returncode != 0:
        # No delta and no census: nobody looked. Returning the empty list
        # alone reads as "this span wrote nothing", which is the confinement
        # instrument answering for a reading it never made.
        _unread("git status in {} failed: confinement unmeasured".format(tree))
        return []
    # Porcelain v1 is two status columns, a space, then the path.
    seen = {line[3:] for line in proc.stdout.splitlines() if len(line) > 3}
    key = str(tree)
    fresh = seen - _TREE_STATE.get(key, frozenset())
    _TREE_STATE[key] = seen
    return sorted(fresh)


def _symlink_entries(tree):
    """Every path the graded revision records with git's ``120000`` mode.

    Read from the tree, never from the checkout: ``core.symlinks=false`` is
    what confines the copy, and it leaves the recorded mode exactly as
    committed, so this reads the same on Windows and POSIX and under any
    privilege. A tree carrying no history answers nothing -- the clone is what
    puts history there -- and the reading that failed says so rather than
    reading as a tree recording no symlink.
    """

    proc = _git(["ls-tree", "-r", "HEAD"], tree)
    if proc is None or proc.returncode != 0:
        _unread("ls-tree in {} failed: symlink entries unread".format(tree))
        return []
    return [
        line.partition("\t")[2]
        for line in proc.stdout.splitlines()
        if line.partition(" ")[0] == SYMLINK_MODE
    ]


def _symlink_findings(run, trees):
    """The instrument for ``rules/visibility.md`` §5's "No symlinks".

    One finding per path, named once however many graded trees record it: two
    revisions of one repository are one tree's worth of rule, not two.
    """

    paths = set()
    for tree in trees:
        if tree is not None:
            paths.update(_symlink_entries(tree))
    return [(run, 0, SYMLINK_IN_TREE, path) for path in sorted(paths)]


def _same_revision(rev, worktree_root):
    """Is ``rev`` the commit HEAD already points at?

    At cut time it is: nothing has landed, so every oracle that discriminates
    fails at the baseline and would fail again at HEAD. "Does this pass once
    the work lands" is unanswerable before the work lands, so the honest
    reading is to not ask -- the HEAD half is skipped and a baseline failure
    is clean unless the command could not run at all, which no landing work
    would change. Post-work the two differ and the full rule applies.
    """

    seen = set()
    for candidate in (rev, "HEAD"):
        proc = _git(["rev-parse", candidate + "^{commit}"], worktree_root)
        if proc is None or proc.returncode != 0:
            return False
        seen.add(proc.stdout.strip())
    return len(seen) == 1


def _criteria(section):
    """Every completion-test criterion, numbered as the ticket's own grader
    numbers them.

    Parsing is ``scripts/tickets.py``'s. That script refuses a criterion this
    tool then grades, so two parsers here is exactly how a section reads one
    way to the cut's refusal and another way to the cut's check: a bullet
    criterion was invisible to this tool while being graded there. The
    numbering is positional for the same reason -- ``criterion_defects`` says
    "criterion 2" about the second criterion in the section, whatever digit
    the author typed, and a report naming a different number names a
    criterion its reader cannot find.
    """

    return list(enumerate(_ticket_criteria(section), start=1))


def _oracle_class(criterion):
    """The class this criterion states its oracle is decided by, or ``""``."""

    match = ORACLE_CLASS_RE.search(criterion)
    return match.group(1).strip().lower() if match else ""


def _stated_provenance(criterion):
    """The provenance this criterion stamps of its own oracle, or ``""``.

    A stamp, never a mention: the field is read with ``tickets.PROVENANCE_RE``
    and kept only where the frame around it is a statement -- opened by the
    start of the criterion, a sentence boundary or the field separator
    ``tickets.py`` itself writes, and continued by no word.
    """

    for match in PROVENANCE_RE.finditer(criterion):
        if not STAMP_OPENS_RE.search(criterion[:match.start()]):
            continue
        if STAMP_CONTINUES_RE.match(criterion[match.end():]):
            continue
        return match.group(1).strip().lower()
    return ""


def _commands(criterion):
    """Backtick spans stating a command: a known head, carrying an argument.

    A head with nothing after it is the tool's name, and no bare name is a
    decidable cut oracle. ``git`` alone prints its usage and ``grep`` alone
    errors, whichever revision reads them. ``pytest`` alone does run something,
    but a whole-suite invocation naming no node id reads the same under every
    item it is stated under, so it discriminates none of them -- a cut defect
    either way, and the honest report of it is the gap.

    Stating is not quoting, and the frame standing immediately in front of the
    span is what tells them apart -- ``_scope_closure``'s question about a
    write verb, asked again of a command. Grading a quotation reaches for a
    path the item never claimed, refuses the very span a ticket was describing,
    and runs whatever the prose says something else runs.
    """

    found = []
    for match in BACKTICK_RE.finditer(criterion):
        candidate = match.group(1).strip()
        argv = candidate.split()
        if len(argv) < 2 or argv[0] not in COMMAND_HEADS or _evaluates_code(argv):
            continue
        if _unreadable_search(candidate):
            continue
        frame = criterion[max(0, match.start() - DENIAL_WINDOW):match.start()]
        if DENIAL_RE.search(frame) or MENTION_RE.search(frame):
            continue
        found.append(candidate)
    return found


def _evaluates_code(argv):
    """Does this span hand an interpreter a program to evaluate?

    ``python3 -c '<anything>'`` is ``bash -lc '<anything>'`` through a head an
    extractor accepts: the argument is the program, and ticket content is
    untrusted. A bare ``-`` is the same span with the program left on stdin.
    """

    return argv[0] in EVAL_HEADS and any(token in EVAL_ARGS for token in argv[1:])


def _names_outside_the_copy(token):
    """Does this argv token spell a location the scratch copy does not hold?

    Two spellings, and this catches both: root the path, or climb out of it.
    Nothing expands on the way -- argv is split, never evaluated, and git spawns
    no shell, so ``~`` and ``$HOME`` name a directory inside the copy and
    nothing else.

    Not closed by construction, because a third route exists that argv cannot
    see: name a symlink the copy holds. Measured -- commit a symlink, run ``git
    diff --output=link/x``, and the file lands outside the copy while this
    returns False. That hole and the permitted span that writes *inside* the
    copy are one problem said twice: text cannot answer a containment question,
    because where a path lands is a fact about the tree and not about the token.
    The copy has to enforce confinement. A rule that only describes it will keep
    coming up one route short, so this narrows the reachable set without closing
    it.

    An option's value starts where the option stops -- after ``=`` for a long
    one, after the letter for a short one carrying its value attached -- and an
    operand is its own value. ``..`` counts only as a whole path component, so
    ``<base>..HEAD`` stays the revision range it is.
    """

    if token.startswith("--"):
        _, _, value = token.partition("=")
    elif token.startswith("-"):
        value = token[2:]
    else:
        value = token
    return value.startswith("/") or ".." in value.split("/")


def _unconfined_git(command):
    """Is this a git span the scratch copy does not confine?

    Two questions, because an escape takes two shapes and one test sees one of
    them. Position answers the first: every way git runs a program named on the
    line or leaves the tree it was pointed at is a global option, and a global
    option is exactly a token standing before the subcommand, so a confined set
    holding no token that begins with ``-`` refuses that family entire.

    Position cannot answer the second, and a subcommand check alone is narrower
    than the threat. ``--output=<file>`` is a subcommand option: it stands after
    the subcommand, where the position rule cannot see it, and ``git diff``,
    ``git log``, ``git show`` and ``git rev-list`` each take it and write the
    file, absolute or climbing, inside the copy or beside it. ``-O<orderfile>``,
    ``--exclude-from`` and ``--no-index`` read the same way round. So the second
    question is asked of what a token spells rather than where it stands, and
    ``_names_outside_the_copy`` answers it for every option git ships next --
    as far as text can, which is not all the way; see its own docstring.

    What remains -- a pager, an alias, a textconv or ext-diff driver -- git
    takes from configuration, and configuration is the clone's own: ``git
    clone`` writes a fresh ``core``-only config, an in-tree ``.gitattributes``
    can name a driver but cannot define one, and a ticket supplies argv and
    nothing besides.

    Tokenised the way ``_run_once`` tokenises, so the span read here is the argv
    that would run: a gate splitting the text some other way grades one command
    and executes another.
    """

    try:
        argv = shlex.split(command)
    except ValueError:
        return False
    if not argv or argv[0] != GIT_HEAD:
        return False
    if len(argv) < 2 or argv[1] not in GIT_CONFINED_SUBCOMMANDS:
        return True
    return any(_names_outside_the_copy(token) for token in argv[2:])


def _shape(command):
    """The defects the command text carries, judged without running it."""

    classes = []
    if SWALLOW_RE.search(command):
        classes.append(SWALLOWED_EXIT)
    if CUMULATIVE_RE.search(command):
        classes.append(CUMULATIVE_RANGE)
    if _unconfined_git(command):
        classes.append(UNCONFINED_ORACLE)
    return classes


def _exit_code(command, tree):
    """This command's exit status in this tree, run once however often asked.

    A scratch tree is a copy built for one invocation and thrown away with it,
    and the cache is a speed change rather than a meaning change exactly while
    ``(command, tree)`` reads the same every time: one ticket set states the
    same invariant oracle in item after item, and a suite is a slow read.

    That sameness is measured now rather than assumed. ``_run_once`` reads the
    copy's status after every span it runs, so a span that wrote into the copy
    is reported as ``unconfined-oracle`` instead of silently deciding what the
    next reader of this cache sees. Measured, not proven: the reading covers
    the working tree, so a write into ``.git``, or one an interpreter's
    ``sys.pycache_prefix`` sends to a cache directory outside the copy, is a
    change no status can see.
    """

    key = (command, str(tree))
    if key in _EXIT_CACHE:
        return _EXIT_CACHE[key]
    _EXIT_CACHE[key] = code = _run_once(command, tree)
    return code


def _run_once(command, tree):
    try:
        argv = shlex.split(command)
    except ValueError:
        return None
    if not argv:
        return None
    if argv[0] in SEARCH_HEADS:
        # Answered here and never spawned, so it writes nothing and there is
        # nothing for `_mutations` to report.
        return _search_exit(argv, tree)
    try:
        proc = subprocess.run(
            argv,
            cwd=str(tree),
            # Discarded, never decoded: the exit status is the whole reading,
            # and an oracle in a tree with history prints whatever it likes --
            # `git archive` prints a tar. Text mode made one such span fatal to
            # the invocation, and the report it was one line of.
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=COMMAND_TIMEOUT,
        )
        code = proc.returncode
    except subprocess.TimeoutExpired:
        # A span that ran out of time still ran, and still wrote whatever it
        # had written by the time it was killed.
        code = TIMED_OUT
    except OSError:
        # Nothing started, so there is nothing for it to have written.
        return UNRUNNABLE
    _MUTATED.extend(_mutations(tree))
    return code


def _search_span(argv):
    """A search span as ``(letters, pattern, operands)``, or None where a token
    outside the closed option set stands in it.

    Short options cluster, a long one may carry its value after ``=``, ``--``
    ends the options, and the pattern is ``-e``'s value where one is given and
    the first operand otherwise. Two patterns are two searches ORed together in
    a syntax the pattern itself may not be written in, so a span naming more
    than one is a span this declines to read rather than one it guesses at.
    """

    letters = set()
    patterns = []
    words = []
    rest = list(argv[1:])
    ended = False
    while rest:
        token = rest.pop(0)
        if ended or not token.startswith("-") or token == "-":
            words.append(token)
            continue
        if token == "--":
            ended = True
            continue
        if token.startswith("--"):
            name, sep, value = token[2:].partition("=")
            letter = SEARCH_LONG_FLAGS.get(name)
            if letter is None:
                return None
            if letter == SEARCH_PATTERN_FLAG:
                if not sep:
                    if not rest:
                        return None
                    value = rest.pop(0)
                patterns.append(value)
            elif sep:
                return None
            else:
                letters.add(letter)
            continue
        cluster = token[1:]
        while cluster:
            letter, cluster = cluster[0], cluster[1:]
            if letter == SEARCH_PATTERN_FLAG:
                if not cluster:
                    if not rest:
                        return None
                    cluster = rest.pop(0)
                patterns.append(cluster)
                cluster = ""
            elif letter in SEARCH_FLAGS:
                letters.add(letter)
            else:
                return None
    if len(patterns) > 1:
        return None
    if patterns:
        return letters, patterns[0], words
    if not words:
        return None
    return letters, words[0], words[1:]


def _search_matcher(letters, pattern):
    """The compiled matcher for one search span, or None where the pattern is
    one nothing here compiles -- which is a status the search heads have too.

    Bytes, because a search reads whatever the tree holds and a tree holds
    files no encoding decodes. ``-F`` reads the pattern literally and every
    other spelling reads it as a regular expression, which agrees with the
    extended syntax ``-E`` names on every pattern this repository's ticket
    corpus states.
    """

    body = re.escape(pattern) if "F" in letters else pattern
    if "w" in letters:
        # grep's ``-w`` asks that no word constituent stand on either side of
        # the match, which is not ``\b``: ``\b`` also demands one *inside*, so
        # a pattern whose own edge is not a word character -- ``-w -- -x`` --
        # would never match here and does under grep.
        body = r"(?<!\w)(?:{})(?!\w)".format(body)
    if "x" in letters:
        body = r"\A(?:{})\Z".format(body)
    try:
        return re.compile(
            body.encode("utf-8", "surrogateescape"),
            re.IGNORECASE if "i" in letters else 0,
        )
    except re.error:
        return None


def _selected(matcher, path, inverted):
    """Does this file hold a selected line? None where it could not be read."""

    try:
        data = path.read_bytes()
    except OSError:
        return None
    lines = data.split(b"\n")
    if lines and not lines[-1]:
        lines.pop()
    return any(bool(matcher.search(line)) != inverted for line in lines)


def _files_under(directory):
    """Every regular file the copy holds beneath this directory.

    ``followlinks=False``, and symlinked files are skipped: a link the copy
    holds is the one route out of it that a path cannot be read for, which
    ``_names_outside_the_copy`` says at length about the git spans. Answering
    the search heads here is what makes it closable, so it is closed.
    """

    for base, dirs, names in os.walk(str(directory), followlinks=False):
        dirs.sort()
        for name in sorted(names):
            path = Path(base) / name
            if not path.is_symlink():
                yield path


def _inside_the_copy(tree, operand):
    """The path this operand names inside the tree, or None where it names one
    outside it."""

    here = Path(tree) / operand
    try:
        root = Path(tree).resolve()
        resolved = here.resolve()
    except OSError:
        return None
    if resolved != root and root not in resolved.parents:
        return None
    return here


def _search_exit(argv, tree):
    """The status a search span exits with, decided by this tool's own matcher.

    The convention ``grep`` and ``rg`` share: 0 where a line was selected,
    ``NO_MATCH`` where none was, and ``SEARCH_ERROR`` where the span named
    something this could not read. ``_discrimination`` reads that middle status
    from a search head as ``no-hits-both-revisions``, so the numbers are the
    tools' and not this matcher's own.

    Read here rather than run, and that is the whole of the repair: ``grep`` is
    a program a POSIX shell's PATH carries and a Windows shell's does not, so
    executing it graded the host. The same tree gave this repository's own suite
    exit 0 from Git Bash and exit 1 from PowerShell, the twenty differences
    being ``unrunnable-oracle`` standing where each fixture's own finding
    belonged. Nothing about a cut changes with the shell the check was launched
    from, so the search heads are answered in the interpreter already running
    and every host reads one verdict.

    The copy is the whole of what a span reads. An operand rooted outside the
    tree or climbing out of it is no operand at all, and a directory is read
    only where the span asks for recursion -- which ``rg`` asks for by default
    and ``grep`` asks for with ``-r``.
    """

    span = _search_span(argv)
    if span is None:
        return SEARCH_ERROR
    letters, pattern, operands = span
    matcher = _search_matcher(letters, pattern)
    if matcher is None:
        return SEARCH_ERROR
    recursive = bool(letters & {"r", "R"}) or argv[0] == "rg"
    # A recursive search naming no operand reads the working directory --
    # ``rg`` by default, ``grep -r`` since 2.11 -- and the working directory
    # is the copy.
    if not operands and recursive:
        operands = ["."]
    inverted = "v" in letters
    selected = False
    # A span naming nothing to read decided nothing, which is the error status
    # and not the absence of a match.
    failed = not operands
    for operand in operands:
        here = _inside_the_copy(tree, operand)
        if here is None:
            failed = True
        elif here.is_dir():
            if recursive:
                for path in _files_under(here):
                    hit = _selected(matcher, path, inverted)
                    failed = failed or hit is None
                    selected = selected or hit is True
            else:
                failed = True
        else:
            hit = _selected(matcher, here, inverted)
            failed = failed or hit is None
            selected = selected or hit is True
    # grep's own exception, stated in its manual: under ``-q`` a selected line
    # exits 0 even where an error occurred, because the question was only
    # whether anything matched.
    if failed and not (selected and "q" in letters):
        return SEARCH_ERROR
    return 0 if selected else NO_MATCH


def _unreadable_search(command):
    """Is this a search span whose options this tool's own matcher cannot read?

    Asked at extraction, so such a span is reported the way a shell-headed one
    is -- as the criterion's extraction gap, which is advisory and settles
    nothing -- rather than run under a guess at what the option meant.
    """

    head = command.split()[:1]
    if not head or head[0] not in SEARCH_HEADS:
        return False
    try:
        argv = shlex.split(command)
    except ValueError:
        return True
    return not argv or _search_span(argv) is None


def _verdict_in_output(command):
    """Is this a command whose exit status carries no verdict?

    ``grep -c`` prints a count and exits on whether it printed anything. A
    criterion saying "reports 0" is judged by that text, which no exit status
    carries, so the honest report is that cutcheck cannot decide it. The git
    command that reads the same way is owned here now that the scratch copy
    carries history and its head excuses nothing: ``git rev-list --count``
    prints the number and exits 0 whatever it counted.
    """

    argv = command.split()
    if argv[0] == GIT_HEAD:
        return GIT_COUNT_FLAG in argv[1:]
    if argv[0] not in SEARCH_HEADS:
        return False
    return any(COUNT_FLAG_RE.match(token) for token in argv[1:])


def _whole_target(target, tree):
    """Does this target name a whole module or directory, not a node inside one?

    Decided against the tree, because only the tree knows where the module
    stops. ``tests.test_cutcheck`` is a file and
    ``tests.test_cutcheck.CleanSetTest`` is a class inside that file, and no
    reading of the two strings tells them apart. A unittest target spells the
    way down with dots and a pytest target spells it with slashes; both are one
    question about where the path stops resolving.
    """

    if NODE_SEP in target:
        return False
    here = tree / (target if "/" in target else target.replace(".", "/"))
    return here.is_dir() or here.with_suffix(".py").is_file()


def _filter_narrows(argv):
    """Does this command's node filter actually exclude any node?

    The token's presence was the whole test once, and that read `-k test` --
    which matches every method in the suite -- as a narrowed oracle. The
    pattern is read instead: anything `test_` starts with matches all of them
    and narrows nothing, and everything else is taken at its word, because
    which nodes a pattern selects is a question for the runner and not for
    this.
    """

    if NODE_FILTER not in argv:
        return False
    index = argv.index(NODE_FILTER)
    pattern = argv[index + 1].strip("\"'") if index + 1 < len(argv) else ""
    return not FILTER_MATCHES_ALL.startswith(pattern)


def _whole_suite(command, tree):
    """Is this a test invocation naming no node id?

    ``_commands`` refuses a bare head for this reason already: a tool's name
    with nothing after it decides nothing. A whole-module or whole-suite
    invocation is that same defect with more typing -- it runs the identical
    tests under every item it is stated under, so it discriminates none of
    them, and the honest report of it is the gap.

    Reported rather than run, which is what makes the class worth having: this
    repository's own mandated ``discover`` outgrows ``COMMAND_TIMEOUT`` in the
    cleanest store there is, so executing it returned ``unrunnable-oracle`` --
    a true class reached by reading the clock instead of the cut.

    A target resolving to no module at all is some flag's value rather than a
    thing to grade, and one such token is enough to withhold the finding: this
    convicts what it can read whole, and stays quiet over what it cannot.

    A runner carrying flags and no target at all is the widest spelling there
    is -- ``pytest -q``, or the bare ``python3 -m unittest`` that is documented
    as equivalent to ``discover``. Naming nothing is not the same as naming
    something unreadable, so the two are separated here: the finding is
    withheld over a quoted target, which names a node this cannot parse, and
    made over an empty one, which names none.
    """

    argv = command.split()
    runner = next((i for i, token in enumerate(argv) if token in TEST_RUNNERS), None)
    if runner is None or _filter_narrows(argv):
        return False
    rest = argv[runner + 1:]
    if DISCOVER in rest:
        return True
    if NODE_FILTER in rest:
        # Reaching here means the pattern matched every node, so it is a flag's
        # value and not a target. Left in, it resolves to no module and
        # withholds the finding over the very filter that earned it.
        at = rest.index(NODE_FILTER)
        rest = rest[:at] + rest[at + 2:]
    targets = [token for token in rest if token[:1] not in ("-", '"', "'")]
    if not targets:
        return not any(token[:1] in ('"', "'") for token in rest)
    return all(_whole_target(token, tree) for token in targets)


def _discrimination(command, baseline_tree, head_tree):
    """The class this oracle fails as, or None when it discriminates.

    An oracle discriminates when it fails at the baseline and passes once the
    work has landed, so HEAD is only consulted after the baseline read fails.
    A baseline read that could not run at all is revision-independent -- no
    work makes an absent command exist -- so it is reported without asking
    HEAD, and at cut time, where there is no HEAD half to ask, it is reported
    all the same. Neither half's non-reading is a failure: a read that timed
    out or could not run decided nothing, and is reported as deciding nothing
    whichever half produced it.

    A half that produced no reading at all -- a command no tokeniser could
    split into an argv -- returns the same None as an oracle that
    discriminates, and names itself through ``_unread`` so the two are told
    apart in the report. ``head_tree`` being None is not that case: it is cut
    time, where the HEAD half is skipped by design and a failed clone has
    already stopped the run.
    """

    at_baseline = _exit_code(command, baseline_tree)
    if at_baseline is None:
        _unread("baseline reading decided nothing: {}".format(command))
        return None
    if at_baseline == 0:
        return ALREADY_PASSES
    if at_baseline in (UNRUNNABLE, TIMED_OUT):
        return UNRUNNABLE_ORACLE
    if head_tree is None:
        return None
    at_head = _exit_code(command, head_tree)
    if at_head is None:
        _unread("HEAD reading decided nothing: {}".format(command))
        return None
    if at_head == 0:
        return None
    if at_head in (UNRUNNABLE, TIMED_OUT):
        # The same reading the baseline half already refuses to call a failure.
        # A command that never returned, or that nothing could run, produced no
        # verdict at HEAD; "fails at both revisions" claims one. An oracle that
        # discriminates perfectly reads as one that never discriminates, and
        # the timeout that says so is the likeliest reading of all -- a suite
        # outgrowing COMMAND_TIMEOUT is the ordinary way here.
        return UNRUNNABLE_ORACLE
    searching = command.split(" ", 1)[0] in SEARCH_HEADS
    if searching and at_baseline == NO_MATCH and at_head == NO_MATCH:
        return NO_HITS_BOTH_REVISIONS
    return FAILS_BOTH_REVISIONS


def _flat(text):
    return " ".join(text.split())


def _prose(text):
    """Ticket text with its oracle commands removed: claims, not commands.

    A pattern inside a command is that command's argument, never a quotation
    and never a path the item names.
    """

    return BACKTICK_RE.sub(
        lambda m: " " if m.group(1).strip().split(" ", 1)[0] in COMMAND_HEADS else m.group(0),
        text,
    )


def _listed(frontmatter, key):
    """A frontmatter field written either as a scalar or as a list."""

    value = frontmatter.get(key) or []
    if isinstance(value, str):
        value = [value]
    return [str(item).strip() for item in value if str(item).strip()]


def _granted(frontmatter, siblings):
    """This item's write scope, plus every ``depends_on`` ancestor's.

    An item's oracles run at the item's revision, which contains the work of
    every ancestor it depends on, so a path an ancestor creates is present.
    """

    scopes = _listed(frontmatter, "write_scope")
    pending = _listed(frontmatter, "depends_on")
    seen = set()
    while pending:
        ancestor = pending.pop()
        if ancestor in seen or ancestor not in siblings:
            continue
        seen.add(ancestor)
        scopes.extend(_listed(siblings[ancestor], "write_scope"))
        pending.extend(_listed(siblings[ancestor], "depends_on"))
    return scopes


def _covered(rel, scopes):
    """Is ``rel`` inside one of ``scopes``?

    Containment runs one way: a grant covers itself and what is under it, never
    the directory that holds it -- a grant of one file is no licence over its
    parent. A bare filename names no directory, so the one grant that provably
    holds it is the grant whose own basename it is; a granted directory that
    happens to be somewhere it could live covers nothing.
    """

    target = rel.strip().strip("/")
    for entry in scopes:
        scope = entry.strip().strip("/")
        if not scope:
            continue
        if target == scope or target.startswith(scope + "/"):
            return True
        if "/" not in target and scope.rsplit("/", 1)[-1] == target:
            return True
    return False


def _overlaps(left, right):
    a = left.strip().strip("/")
    b = right.strip().strip("/")
    return bool(a and b) and (a == b or a.startswith(b + "/") or b.startswith(a + "/"))


def _path_args(command):
    """Unquoted argv tokens naming a path: an argument, a redirect target.

    A quoted token is a pattern or a literal the oracle carries, not a path it
    reaches for. Absolute and interpolated paths lie outside the scratch copy,
    so they are nothing this tool can resolve.
    """

    found = []
    for token in command.split()[1:]:
        if token[:1] in ("-", '"', "'"):
            continue
        token = token.lstrip(">").split("::", 1)[0].rstrip(",;")
        if not token or token[:1] in ("/", "~", "$") or GLOB_RE.search(token):
            continue
        if "/" in token or DOTTED_RE.search(token):
            found.append(token)
    return found


def _paths_in(text):
    """Tokens in prose that name a path: a slash, or a short final extension.

    A token holding an angle bracket is a placeholder for wherever the run puts
    its state, so no item's grant can name it and its absence is no defect.
    """

    found = []
    for token in text.replace("`", " ").split():
        token = token.lstrip("(<[\"'").rstrip(")>],;:.\"'")
        if not token or token[:1] == "-" or GLOB_RE.search(token):
            continue
        if PLACEHOLDER_RE.search(token):
            continue
        if "/" in token or DOTTED_RE.search(token):
            found.append(token)
    return found


def _where(rel, line, section):
    return "{}:{}".format(rel, line) if line else "{} §{}".format(rel, section)


def _cited_text(tree, rel, line, section):
    """The text a citation points at, or None when the citation misses.

    Resolution is at the baseline scratch copy, never at the workspace: a
    ticket cites the tree it was cut from, which the work then changes.
    """

    path = tree / rel
    if not path.is_file():
        return None
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return None
    if line is not None:
        if line > len(lines):
            return None
        return _flat(" ".join(lines[max(0, line - 1 - CITED_LINES):line + CITED_LINES]))
    opens = re.compile(r"^#*\s*{}\.\s".format(section))
    following = re.compile(r"^#*\s*\d+\.\s")
    start = None
    for index, text in enumerate(lines):
        if start is None:
            if opens.match(text):
                start = index
        elif following.match(text):
            return _flat(" ".join(lines[start:index]))
    return None if start is None else _flat(" ".join(lines[start:]))


def _citations(prose):
    """Every ``file:line`` and ``file §N`` location a ticket points at."""

    found = [
        (m.start(), m.group(1), int(m.group(2)), None)
        for m in CITATION_RE.finditer(prose)
    ]
    found += [
        (m.start(), m.group(1), None, int(m.group(2)))
        for m in SECTION_CITATION_RE.finditer(prose)
    ]
    return [c for c in found if not c[1].startswith(("/", "~")) and ".." not in c[1]]


def _path_reality(prose, baseline_tree):
    """Family 2 over prose: citations resolve, and a quote is where it is cited.

    A quotation is multi-word text in quotes or in backticks -- a single token
    beside a citation names something, it does not quote it. Backticks count
    because a quoted line of code carries quotes of its own. A span holding a
    citation is that citation with what it points at, never a quotation of the
    line: the ticket is saying where, not what.
    """

    findings = []
    cites = _citations(prose)
    for _, rel, line, section in cites:
        if _cited_text(baseline_tree, rel, line, section) is None:
            findings.append((UNRESOLVED_CITATION, _where(rel, line, section)))
    for match in QUOTE_RE.finditer(prose):
        quoted = _flat(match.group(1) or match.group(2) or "")
        near = [c for c in cites if abs(c[0] - match.start()) <= QUOTE_WINDOW]
        if " " not in quoted or not near or _citations(quoted):
            continue
        _, rel, line, section = min(near, key=lambda c: abs(c[0] - match.start()))
        text = _cited_text(baseline_tree, rel, line, section)
        if text is None or quoted in text:
            continue
        findings.append(
            (
                QUOTE_NOT_AT_CITATION,
                '"{}" not at {}'.format(quoted, _where(rel, line, section)),
            )
        )
    return findings


def _scope_closure(frontmatter, prose):
    """Family 3: the grant covers every write, and contradicts no exclusion.

    Observing is not naming: a path the item only reads stays outside its write
    scope and is no defect here, and neither is one the text mentions without
    committing to write. "Write scope" is the grant's name rather than a write,
    and a denied write -- never written, not created -- commits the item to
    nothing at all.
    """

    scope = _listed(frontmatter, "write_scope")
    findings = []
    seen = set()
    flat = _flat(prose)
    for match in WRITE_RE.finditer(flat):
        if SCOPE_WORD_RE.match(flat[match.end():]):
            continue
        if DENIAL_RE.search(flat[max(0, match.start() - DENIAL_WINDOW):match.start()]):
            continue
        end = match.end() + WRITE_WINDOW
        window = flat[match.end():end]
        if len(flat) > end and not flat[end].isspace():
            window = window.rpartition(" ")[0]
        for target in _paths_in(window):
            if target in seen or _covered(target, scope):
                continue
            seen.add(target)
            findings.append((UNSCOPED_WRITE, target))
    for action in _listed(frontmatter, "excluded_actions"):
        for target in _paths_in(action):
            for entry in scope:
                if _overlaps(target, entry):
                    findings.append((SCOPE_CONTRADICTION, "{} | {}".format(action, entry)))
                    break
    return findings


def _is_literal(token):
    """Is this token specific enough that a file pinning it means something?

    Three characters and a separator. `gate`, `set` and `the` are words every
    tree is full of; `orch-compose`, `SCRIPT_NAMES` and `scripts/tickets.py`
    are things one file states and another depends on.
    """

    return bool(LITERAL_RE.match(token)) and any(m in token for m in LITERAL_MARKS)


def _literals(objective):
    """Every literal this objective says it deletes, moves or renames.

    The window and the denial frame are ``_scope_closure``'s, asked of a verb
    that takes away rather than one that adds: a write the ticket denies
    commits it to nothing, and neither does a removal it denies.

    A path is read twice -- whole, and as the name it ends in. The pin is
    usually on the name: ``scripts/tickets.py`` spells a deleted engine as a
    set member and nothing outside the library spells the directory it lived
    in, so reading the path alone finds no pin and reports the cut clean.
    """

    flat = _flat(objective)
    found = []
    for match in REMOVAL_RE.finditer(flat):
        if DENIAL_RE.search(flat[max(0, match.start() - DENIAL_WINDOW):match.start()]):
            continue
        end = match.end() + REMOVAL_WINDOW
        window = flat[match.end():end]
        if len(flat) > end and not flat[end].isspace():
            window = window.rpartition(" ")[0]
        # A span the objective itself sets in backticks is a literal on the
        # author's word, separator or none: `limited`, `checker`, `gate` are
        # enum and set members a cut removes, and the tree's ordinary uses of
        # the same word are told apart at the pin by ``_pins``' boundaries.
        spans = [(t, False) for t in _paths_in(window)]
        spans += [(s.strip(), True) for s in BACKTICK_RE.findall(window)]
        for token, marked in spans:
            for candidate in (token, token.rsplit("/", 1)[-1]):
                literal = _is_literal(candidate) or (
                    marked and bool(LITERAL_RE.match(candidate))
                )
                if literal and candidate not in found:
                    found.append(candidate)
    return found


def _pins(literal, text):
    """Does ``text`` state ``literal`` as a name, not as the inside of one?

    Whole-token: `orch-compose` is not pinned by `orch-composer`, `gate` not
    by `delegate`, `friction.py` not by `friction.pyc`. A path separator, a
    dot, a quote or a bracket on either side is a boundary; a word character
    or a dash is not.
    """

    return re.search(r"(?<![\w-])" + re.escape(literal) + r"(?![\w-])", text) is not None


def _pin_index(tree):
    """Every file under ``PIN_ROOTS`` of this tree, with its text, read once.

    Read from the baseline copy, where every other file-reading family reads:
    a pin is a fact about the tree the ticket was cut from, which the work then
    changes. Built lazily and cached per tree, because the only cut that pays
    for it is one whose objective takes a literal away.
    """

    key = str(tree)
    if key in _PIN_INDEX:
        # Replayed, not skipped: the index is cached per tree and outlives the
        # invocation that built it, so a second run reading the same copy would
        # otherwise be handed a shorter index than the first and told nothing
        # about the difference.
        for what in _PIN_SKIPPED.get(key, ()):
            _unread(what)
        return _PIN_INDEX[key]
    skipped = []
    entries = []
    for root in PIN_ROOTS:
        base = tree / root
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*")):
            try:
                if not path.is_file():
                    continue
                if path.stat().st_size > PIN_SIZE_LIMIT:
                    # Skipped and said: the index holding no pin from this
                    # file is a fact about the reading, and read as a fact
                    # about the file it licenses a grant the file breaks.
                    skipped.append("{}: past PIN_SIZE_LIMIT, not read for pins".format(
                        path.relative_to(tree).as_posix()))
                    continue
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError as error:
                skipped.append("{}: not read for pins: {}".format(
                    path.relative_to(tree).as_posix(), error))
                continue
            entries.append((path.relative_to(tree).as_posix(), text))
    for what in skipped:
        _unread(what)
    _PIN_INDEX[key] = entries
    _PIN_SKIPPED[key] = skipped
    return entries


def _scope_open(frontmatter, objective, tree):
    """Family 3, the other direction: does the grant close over what is removed?

    ``_scope_closure`` asks whether the grant covers what the item writes. This
    asks whether it covers what the rest of the tree pins: a path, a skill
    name, an enum member, a set member the objective deletes, moves or renames,
    which some file outside the grant states. The item cannot land without
    breaking that file and cannot repair it, so either the cut carries the
    pinning file or the cut is wrong -- and nothing about the item's own text
    says so, which is why eleven such grants were issued in one build and each
    failed in flight instead of at the cut.

    One finding per pinning file, naming the file and the literal, because the
    repair is per file: a grant is extended once however many of the item's
    literals one file happens to hold, so the most specific literal it holds is
    the one named. A file the grant already covers is no finding, and neither
    is one sitting inside the literal being removed -- what goes with the
    deletion is not a pin left behind by it.
    """

    literals = _literals(objective)
    if not literals or tree is None:
        return []
    scope = _listed(frontmatter, "write_scope")
    findings = []
    for rel, text in _pin_index(tree):
        if _covered(rel, scope):
            continue
        pinning = [
            literal
            for literal in literals
            if _pins(literal, text) and not _covered(rel, [literal])
        ]
        if pinning:
            findings.append(
                (SCOPE_OPEN, "{} pins {}".format(rel, max(pinning, key=len)))
            )
    return findings


def _oracle_reads(text):
    """Every path this item's oracles reach for, across its completion test."""

    found = []
    for _, criterion in _criteria(_sections(text).get(COMPLETION_SECTION, "")):
        for command in _commands(criterion):
            found.extend(_path_args(command))
    return found


def _ancestors(item, siblings):
    """Every item reachable from ``item`` through ``depends_on``."""

    seen = set()
    pending = _listed(siblings.get(item) or {}, "depends_on")
    while pending:
        node = pending.pop()
        if node in seen or node not in siblings:
            continue
        seen.add(node)
        pending.extend(_listed(siblings[node], "depends_on"))
    return seen


def _first_overlap(paths, scopes):
    for path in paths:
        for entry in scopes:
            if _overlaps(path, entry):
                return path
    return None


def _decomposers(siblings):
    """Every id in this set whose executor is the decomposer."""

    return sorted(
        item_id
        for item_id, frontmatter in siblings.items()
        if str(frontmatter.get("executor") or "").strip() == ROOT_EXECUTOR
    )


def _root_ids(siblings):
    """Every id in this set whose executor and position make it a root ticket.

    The executor alone does not: a `<root>.NN` unit issued with it is a
    nested decomposition, which ``rules/topology.md`` §7 leaves undefined,
    and reading it as a root would grant it the root's exemption from
    families 4, 5 and 6 -- the honest layout's exemption sheltering the one
    shape it was never written for. A decomposer no other decomposer's id
    prefixes is a root, so a template's top-level stub stands as a root
    beside its siblings.
    """

    decomposers = _decomposers(siblings)
    return [
        item_id
        for item_id in decomposers
        if not any(
            other != item_id and item_id.startswith(other + ".")
            for other in decomposers
        )
    ]


def _gate_stub_of(ticket_id, roots):
    """The root this id is a gate stub of, or None.

    Anchored to a root the set actually holds, never to the infix alone: a
    unit ticket may be named anything, and the gate stubs are the ones one of
    these roots owns.
    """

    for root in roots:
        if ticket_id.startswith(root + GATE_INFIX):
            return root
    return None


def _gate_owners(siblings):
    """The root ids whose gate stubs this set already carries.

    Read from the same marker ``tickets.py gate`` writes, not only from roots
    that remain readable in the set. A manually assembled second gate is a
    defect even where its root ticket is missing or malformed.
    """

    return sorted(
        {
            ticket_id.split(GATE_ID_MARKER, 1)[0]
            for ticket_id in siblings
            if GATE_ID_MARKER in ticket_id
        }
    )


def _staged_template_roots(roots, siblings):
    """Whether several decomposers are stages of one top-level template.

    Canonical templates intentionally contain more than one decomposer, but
    each later one is downstream of an earlier one.  Two unrelated
    decomposers are two physical roots, the prohibited ad-hoc shape.
    """

    if len(roots) < 2:
        return False
    root_set = set(roots)
    first = [root for root in roots if not (_ancestors(root, siblings) & root_set)]
    return len(first) == 1 and all(
        root == first[0] or bool(_ancestors(root, siblings) & root_set)
        for root in roots
    )


def _gate_shape(root, siblings):
    """One detail when ``root`` does not own the canonical composite gate."""

    prefix = root + GATE_INFIX
    ids = sorted(ticket_id for ticket_id in siblings if ticket_id.startswith(prefix))
    critiques = [
        ticket_id for ticket_id in ids
        if ticket_id.startswith(prefix + "critique.")
    ]
    repair = root + ".gate.repair"
    verify = root + ".gate.verify"
    expected = set(critiques + [repair, verify])
    unknown = sorted(set(ids) - expected)
    if not critiques or repair not in siblings or verify not in siblings or unknown:
        return "expected one or more critiques, exactly one repair and one verify; got {}".format(
            ", ".join(ids) or "none"
        )
    units = _issued_under(siblings, root)
    wrong = []
    for ticket_id in critiques:
        item = siblings[ticket_id]
        if str(item.get("executor") or "").strip() != GATE_EXECUTORS["critique"]:
            wrong.append("{} executor".format(ticket_id))
        if sorted(_listed(item, "depends_on")) != sorted(units):
            wrong.append("{} dependencies".format(ticket_id))
    repair_item = siblings[repair]
    if str(repair_item.get("executor") or "").strip() != GATE_EXECUTORS["repair"]:
        wrong.append("{} executor".format(repair))
    if sorted(_listed(repair_item, "depends_on")) != critiques:
        wrong.append("{} dependencies".format(repair))
    verify_item = siblings[verify]
    if str(verify_item.get("executor") or "").strip() != GATE_EXECUTORS["verify"]:
        wrong.append("{} executor".format(verify))
    if _listed(verify_item, "depends_on") != [repair]:
        wrong.append("{} dependencies".format(verify))
    return ", ".join(wrong) if wrong else None


def _root_gate_layout(siblings):
    """Family 6: one root/gate system and one independence path per ticket.

    Runtime writers refuse each contradiction before writing it. Cutcheck
    reads the other ingress -- legacy or manually assembled ticket sets -- so
    those same shapes cannot become accepted merely because they already sit
    on disk. A root's ``checked_by`` remains the cut-reader record the
    work-item contract requires; only non-root gate-deferred tickets have no
    checker path.
    """

    findings = []
    roots = _root_ids(siblings)
    root_set = set(roots)
    gate_owners = _gate_owners(siblings)
    # Staged template decomposers remain lawful and carry no composite gate of
    # their own. Unrelated roots are prohibited even before either gate exists.
    if len(roots) > 1 and (gate_owners or not _staged_template_roots(roots, siblings)):
        findings.append(
            (
                roots[1],
                0,
                MULTIPLE_ROOTS,
                "one physical run has one root/gate system; found roots {}".format(
                    ", ".join(roots)
                ),
            )
        )
    if len(gate_owners) > 1:
        findings.append(
            (
                gate_owners[1],
                0,
                MULTIPLE_GATE_SYSTEMS,
                "one physical run has one composite gate; found owners {}".format(
                    ", ".join(gate_owners)
                ),
            )
        )
    for owner in gate_owners:
        if owner not in root_set:
            detail = "gate owner {} is not an orch-decompose root".format(owner)
        else:
            detail = _gate_shape(owner, siblings)
        if detail:
            findings.append((owner, 0, MALFORMED_GATE, detail))
    for ticket_id in sorted(siblings):
        frontmatter = siblings[ticket_id]
        independence = str(frontmatter.get("independence") or "checker").strip()
        checked_by = str(frontmatter.get(CHECKED_BY_KEY) or "").strip()
        if ticket_id not in root_set and independence == "gate" and checked_by:
            findings.append(
                (
                    ticket_id,
                    0,
                    MIXED_INDEPENDENCE,
                    "gate-deferred non-root ticket also carries checked_by {}".format(
                        checked_by
                    ),
                )
            )
    return findings


def _issued_items(siblings, roots):
    """The ids that are work items of this cut, root and gate stubs excepted.

    A root is the acceptance's source, so no criterion of the map it wrote
    names it; the gate stubs are named by the keyword ``gate``, never by id.
    Neither is a parallel work item either: a root does not run beside its own
    subtree, and a gate runs behind all of it, so the pairs family 4 asks
    about are the pairs among these ids. Grading either as an issued item
    fails every honest cut in the layout the work-item contract requires.
    """

    return [
        item_id
        for item_id in sorted(siblings)
        if item_id not in roots and _gate_stub_of(item_id, roots) is None
    ]


def _pairwise(siblings, reads):
    """Family 4: the pairs the DAG leaves free to run at the same time.

    Ordering is reachability, not adjacency -- a pair joined through a third
    item is staged, and staging is what makes a shared path safe. For every
    unordered pair the write scopes must be disjoint and neither item's oracle
    may read what the other writes, or the first result to land invalidates the
    second's evidence.
    """

    findings = []
    ids = _issued_items(siblings, _root_ids(siblings))
    ancestors = {item: _ancestors(item, siblings) for item in ids}
    for index, left in enumerate(ids):
        for right in ids[index + 1:]:
            if right in ancestors[left] or left in ancestors[right]:
                continue
            scopes = {
                item: _listed(siblings[item], "write_scope") for item in (left, right)
            }
            shared = _first_overlap(scopes[left], scopes[right])
            if shared is not None:
                findings.append(
                    (left, 0, SCOPE_COLLISION, "with {}: {}".format(right, shared))
                )
            for reader, writer in ((left, right), (right, left)):
                path = _first_overlap(reads.get(reader) or [], scopes[writer])
                if path is not None:
                    findings.append(
                        (
                            reader,
                            0,
                            STAGED_INVALIDATION,
                            "with {}: {}".format(writer, path),
                        )
                    )
    return findings


def _levels(siblings, ids):
    """Each issued item's level, and the ids no level resolves for.

    Level 1 is an item depending on nothing inside the set; every other item's
    level is one past the greatest level among its ``depends_on`` here. Only
    edges inside the set count, because an id naming something this cut does
    not hold orders nothing in it.

    An item whose dependencies never all resolve is inside a ``depends_on``
    cycle or behind one. It is returned unresolved and named in the reading
    rather than raised: a cut this tool cannot order is a fact about the cut,
    and a reader who asked for a shape gets the shape and the reason the rest
    of it is missing. Raising would take the whole report -- findings included
    -- down with the one set that most needs reading.
    """

    deps = {item: [d for d in _listed(siblings[item], "depends_on") if d in ids]
            for item in ids}
    level = {}
    pending = list(ids)
    while pending:
        ready = [item for item in pending if all(d in level for d in deps[item])]
        if not ready:
            break
        for item in ready:
            level[item] = 1 + max([level[d] for d in deps[item]] or [0])
        pending = [item for item in pending if item not in level]
    return level, deps, sorted(pending)


def _critical_path(level, deps):
    """The longest ``depends_on`` chain, read back from its deepest item.

    Every dependency of a levelled item is levelled, and an item's level is one
    past the greatest of theirs, so stepping to the deepest dependency at each
    hop walks a chain as long as the level says it is. Ties are broken on the
    id so that one cut reads the same twice: the chain is a reading a decomposer
    compares between revisions, and an arbitrary tie would make it move on its
    own.
    """

    if not level:
        return []
    node = max(sorted(level), key=lambda item: level[item])
    chain = [node]
    while deps[node]:
        node = max(sorted(deps[node]), key=lambda item: level[item])
        chain.append(node)
    chain.reverse()
    return chain


def _graph_reading(run, siblings):
    """The cut's shape: how deep it is, and how wide at each level.

    Against the run rather than any ticket, because neither reading is a
    property of one item -- the chain is the run's length in dispatches and the
    widths are what each frontier asks of the host at once. Over the issued
    items alone, for the reason `_issued_items` gives: a root does not run
    beside its own subtree and a gate runs behind all of it, so counting either
    would report a shape no frontier ever executes.

    A set with no issued item is read as nothing at all rather than as a shape
    of zero: there is no cut there to have one.
    """

    ids = _issued_items(siblings, _root_ids(siblings))
    if not ids:
        return []
    level, deps, cycled = _levels(siblings, ids)
    chain = _critical_path(level, deps)
    detail = "{}: {}".format(len(chain), " > ".join(chain)) if chain else "0"
    if cycled:
        detail += "; cycle: {}".format(", ".join(cycled))
    deepest = max(level.values()) if level else 0
    widths = [
        sum(1 for item in level if level[item] == depth)
        for depth in range(1, deepest + 1)
    ]
    return [
        (run, 0, CRITICAL_PATH, detail),
        # `0` where nothing resolved: every item is in a cycle or behind one,
        # and the chain's line names which.
        (run, 0, LEVEL_WIDTH, " ".join(str(width) for width in widths) or "0"),
    ]


def _coverage_path(run_dir, name=COVERAGE_FILE):
    """Where the acceptance-coverage map lives for a resolved ticket root.

    The map is found beside the root cutcheck already resolved, never at one
    fixed path: a run keeps it with its worklog, a fixture set carries its own
    beside its tickets, and the canary set has none to carry.
    """

    if run_dir.parent.name != TICKETS_DIR:
        return run_dir / name
    if run_dir.parent.parent.name == CANARY_DIR:
        return None
    return run_dir.parent.parent / RUNS_DIR / run_dir.name / name


def _map_for_root(run_dir, root, single: bool):
    """One root's map: ``<root>.coverage.md``, or the legacy single map.

    A run holds one map per root because it holds one cut per root. A
    template instantiates several top-level decomposers into one run, and
    one map for all of them means each root's criteria are read against
    every other root's items -- and the last decomposer to write overwrites
    what the others wrote.

    The legacy ``coverage.md`` is still read where it still means what it
    said: one root, and no map of its own.
    """

    path = _coverage_path(run_dir, root + COVERAGE_SUFFIX)
    if path is not None and path.is_file():
        return path
    legacy = _coverage_path(run_dir, COVERAGE_FILE)
    if single and legacy is not None and legacy.is_file():
        return legacy
    return path


def _issued_under(siblings, root):
    """The ids of one root's cut: ``<root>.NN``, its gate stubs excepted.

    Never a sibling top-level stub. A template's stubs are the template's
    graph, not any one root's decomposition, so grading them against a
    root's map convicts every honest template of orphaning the items it
    never issued.
    """

    prefix = root + GATE_PREFIX_SEPARATOR
    return [
        item_id
        for item_id in sorted(siblings)
        if item_id.startswith(prefix) and _gate_stub_of(item_id, [root]) is None
    ]


def _coverage_rows(path):
    """Each ``| criterion | owner |`` row: a number, and what answers for it."""

    rows = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        cells = [cell.strip().strip("`") for cell in line.strip().strip("|").split("|")]
        if len(cells) >= 2 and cells[0].isdigit():
            rows.append((int(cells[0]), cells[1]))
    return rows


def _relative(path, roots):
    """A path named the way every other line names one: from its root.

    Always with forward slashes, never the host separator. Every other path in
    a report comes from a ticket, where it is written posix-style, and a reader
    diffing one line against another must not see two spellings of one path.
    On Windows ``str()`` here emitted ``tests\\fixtures\\...`` and every
    recorded verdict missed.
    """

    for root in roots:
        if root is None:
            continue
        try:
            return path.relative_to(root).as_posix()
        except ValueError:
            continue
    return Path(path).as_posix()


def _coverage_findings(run, run_dir, siblings, roots):
    """Family 5, once per root the set holds.

    A run with no decomposer at all has one issued set and one map, which is
    what it always had. A run with roots has one of each per root.
    """

    root_ids = _root_ids(siblings)
    if not root_ids:
        return _coverage(
            run, _coverage_path(run_dir), _issued_items(siblings, []), roots,
            siblings=siblings,
        )
    findings = []
    single = len(root_ids) == 1
    for root in root_ids:
        findings.extend(
            _coverage(
                root if not single else run,
                _map_for_root(run_dir, root, single),
                _issued_under(siblings, root),
                roots,
                siblings=siblings,
                root=root,
            )
        )
    return findings


def _gate_independence_findings(run, rows, issued, siblings, root):
    """Gate-deferred units whose authored acceptance is absent at the root."""

    if not siblings or not root or root not in siblings:
        return []
    root_criteria = dict(_criteria(siblings[root].get("__completion_test") or ""))
    findings = []
    for item_id in issued:
        item = siblings.get(item_id) or {}
        if str(item.get("independence") or "checker").strip() != "gate":
            continue
        authored = [
            number
            for number, criterion in _criteria(item.get("__completion_test") or "")
            if _stated_provenance(criterion) != PRE_EXISTING
        ]
        if not authored:
            continue
        covered = [
            number
            for number, owner in rows
            if owner == item_id and number in root_criteria
        ]
        missing = authored[len(covered):]
        if missing:
            findings.append((
                item_id,
                missing[0],
                UNCOVERED_GATE_CRITERION,
                "independence gate leaves authored-here criteria {} absent from "
                "the root acceptance rows owned by this item".format(
                    ", ".join(str(number) for number in missing)
                ),
            ))
    return findings


def _coverage(run, path, issued, roots, siblings=None, root=None):
    """Family 5: the map and the issued set answer for each other, both ways.

    A criterion reaches an item, the gate, or declared remainder; an item is
    named by some criterion. With no map there is nothing to read either
    direction against, so the absence is the only thing reported.
    """

    if path is None or not path.is_file():
        where = (
            _relative(path, roots) if path is not None else "none for this ticket root"
        )
        return [(run, 0, COVERAGE_MAP_ABSENT, where)]
    findings = []
    owned = set()
    rows = _coverage_rows(path)
    for number, owner in rows:
        if owner in COVERAGE_OWNERS:
            continue
        if owner in issued:
            owned.add(owner)
            continue
        findings.append((run, number, ORPHAN_CRITERION, owner))
    findings.extend(
        (item, 0, ORPHAN_ITEM, "named by no criterion in {}".format(path.name))
        for item in issued
        if item not in owned
    )
    findings.extend(
        _gate_independence_findings(run, rows, issued, siblings, root)
    )
    return findings


def _pack_cells(pack, lib_root):
    """The skills a pack's ``executor`` and ``assembly`` cells name.

    Read from the orchflows library, never from the repository under test. A
    pack that library does not carry, or one whose cells name no skill, binds
    nothing here -- an assembly cell reading "none" is such a cell.
    """

    if lib_root is None or not PACK_NAME_RE.match(pack):
        return set()
    path = Path(lib_root) / PACKS_DIR / pack / "SKILL.md"
    if not path.is_file():
        return set()
    names = set()
    for row in PACK_CELL_RE.findall(path.read_text(encoding="utf-8", errors="replace")):
        names.update(SKILL_NAME_RE.findall(row))
    return names


def _lib_root(declared):
    """The orchflows library whose pack cells family 6 reads, or None.

    Never the target repository. A pack cell is a fact about orchflows and the
    tree under test is whatever repository the run's work lands in, so
    resolving cells against the invoking worktree meant that from any target
    carrying no ``packs/`` -- which is every target but the library's own
    checkout -- the cell set came back empty and family 6 had nothing left to
    grade. The check passed by finding nothing to check.

    ``--lib`` decides it when the caller names one. Otherwise the tree this
    script runs from, which is the library itself in a checkout of it, and
    failing that the install beside the resolved state sink, which is where
    ``install.py`` puts the packs on this host.
    """

    if declared:
        declared_root = Path(declared)
        if not (declared_root / PACKS_DIR).is_dir():
            # Honoured and reported: the caller named this library, so it is
            # the one read, and a library holding no pack cell is family 6
            # grading every executor against nothing.
            _unread("{}: no {}/ there, so family 6 grades nothing".format(
                declared_root, PACKS_DIR))
        return declared_root
    candidates = [Path(__file__).resolve().parent.parent]
    try:
        candidates.append(state_root.state_root().parent / "lib")
    except OSError:  # pragma: no cover - a home directory that will not resolve
        pass
    for candidate in candidates:
        if (candidate / PACKS_DIR).is_dir():
            return candidate
    _unread("no orchflows library found ({}), so family 6 grades nothing".format(
        ", ".join(str(candidate) for candidate in candidates)))
    return None


def _executor_legality(siblings, lib_root):
    """Family 6: an executor its pack's cells name.

    An item naming no pack has no cell to resolve against and is not graded
    here.

    A root ticket and a gate stub are graded against the library instead of
    against the pack. Their executors are structural -- the decomposer is what
    makes a root a root, and the gate's three are what ``tickets.py gate``
    writes -- so no pack's executor cell names them and none should have to.
    Graded against the cell they were all illegal, which failed a cut for
    carrying the shape the contract requires of it. A decomposer that is not
    a root -- an id inside another root's subtree -- gets neither grading and
    is reported here as a nested root.
    """

    findings = []
    cells = {}
    roots = _root_ids(siblings)
    for ticket_id in sorted(siblings):
        frontmatter = siblings[ticket_id]
        executor = str(frontmatter.get("executor") or "").strip()
        if not executor:
            continue
        if ticket_id in roots:
            continue
        if executor == ROOT_EXECUTOR:
            findings.append(
                (
                    ticket_id,
                    0,
                    ILLEGAL_EXECUTOR,
                    "{} here is a nested root: this id sits inside another "
                    "root's subtree, and mixed decomposition inside one graph "
                    "is undefined (rules/topology.md §7)".format(executor),
                )
            )
            continue
        if _gate_stub_of(ticket_id, roots) is not None:
            if executor not in GATE_STUB_EXECUTORS:
                findings.append(
                    (
                        ticket_id,
                        0,
                        ILLEGAL_EXECUTOR,
                        "{} is none of the gate's executors {}".format(
                            executor, sorted(GATE_STUB_EXECUTORS)
                        ),
                    )
                )
            continue
        pack = str(frontmatter.get("pack") or "").strip()
        if not pack:
            continue
        if pack not in cells:
            cells[pack] = _pack_cells(pack, lib_root)
        if cells[pack] and executor not in cells[pack]:
            findings.append(
                (
                    ticket_id,
                    0,
                    ILLEGAL_EXECUTOR,
                    "{} is neither {}'s executor cell nor its assembly cell".format(
                        executor, pack
                    ),
                )
            )
    return findings


def _check_ticket(path, baseline_tree, head_tree, siblings):
    text = path.read_text(encoding="utf-8")
    frontmatter = _parse_frontmatter(text)
    ticket_id = frontmatter.get("id") or path.stem
    sections = _sections(text)
    granted = _granted(frontmatter, siblings)
    findings = []
    for number, criterion in _criteria(sections.get(COMPLETION_SECTION, "")):
        prose = _prose(criterion)
        findings.extend(
            (ticket_id, number, klass, detail)
            for klass, detail in _path_reality(prose, baseline_tree)
        )
        commands = _commands(criterion)
        if not commands:
            # The stated class travels with the gap: a judged criterion states
            # no command by design, and one that names a class this tool can
            # run is under-coverage. The decomposer reads which it has.
            klass = _oracle_class(criterion)
            detail = criterion[:100]
            if klass:
                detail = "{} | oracle_class: {}".format(detail, klass)
            findings.append((ticket_id, number, EXTRACTION_GAP, detail))
            continue
        invariant = _stated_provenance(criterion) == PRE_EXISTING
        for command in commands:
            shape = _shape(command)
            if shape:
                # Reported and never run: a swallowed pipeline cannot be run
                # argv-only anyway, and an unconfined git span must not be.
                # This `continue` is the refusal -- everything below executes.
                findings.extend((ticket_id, number, k, command) for k in shape)
                continue
            missing = [
                arg
                for arg in _path_args(command)
                if not (baseline_tree / arg).exists() and not _covered(arg, granted)
            ]
            if missing:
                # A command reaching for a path nothing has is not discriminating.
                findings.extend(
                    (ticket_id, number, MISSING_PATH, "{}: {}".format(arg, command))
                    for arg in missing
                )
                continue
            if _verdict_in_output(command):
                findings.append((ticket_id, number, VERDICT_IN_OUTPUT, command))
                continue
            if invariant:
                # An oracle the criterion states is pre-existing is an
                # invariant: it passed before this work and has to pass after,
                # so discriminating is not its job and never was.
                continue
            if _whole_suite(command, baseline_tree):
                # Below the stamp, because an invariant is not being asked to
                # discriminate, and above execution because this one must not
                # run: the mandated `discover` that lands here outgrows
                # COMMAND_TIMEOUT, and the timeout reports the clock.
                findings.append((ticket_id, number, WHOLE_SUITE_ORACLE, command))
                continue
            del _MUTATED[:]
            klass = _discrimination(command, baseline_tree, head_tree)
            # Named once per path however many graded copies the span wrote
            # into: two revisions of one repository are one span's worth of
            # defect, not two.
            wrote = sorted(set(_MUTATED))
            bytecode = [path for path in wrote if BYTECODE_RE.search(path)]
            findings.extend(
                (ticket_id, number, UNCONFINED_ORACLE, "{}: {}".format(path, command))
                for path in wrote
                if path not in bytecode
            )
            if bytecode:
                findings.append(
                    (
                        ticket_id,
                        number,
                        BYTECODE_WRITTEN,
                        "{}: {}: {}".format(
                            ", ".join(bytecode), BYTECODE_REPAIR, command
                        ),
                    )
                )
            if klass is not None:
                findings.append((ticket_id, number, klass, command))
    header = "\n".join(
        sections.get(name, "") for name in (OBJECTIVE_SECTION, INPUTS_SECTION)
    )
    findings.extend(
        (ticket_id, 0, klass, detail)
        for klass, detail in _path_reality(_prose(header), baseline_tree)
    )
    body = "\n".join(
        sections.get(name, "") for name in (OBJECTIVE_SECTION, COMPLETION_SECTION)
    )
    findings.extend(
        (ticket_id, 0, klass, detail)
        for klass, detail in _scope_closure(frontmatter, _prose(body))
    )
    findings.extend(
        (ticket_id, 0, klass, detail)
        for klass, detail in _scope_open(
            frontmatter, _prose(sections.get(OBJECTIVE_SECTION, "")), baseline_tree
        )
    )
    return findings


# What the caller reads off the status, and what the status does not mean. The
# six families are the module docstring's to describe; this names none of them.
EPILOG = """exit status:
  0  Cutcheck's exit 0 means no finding whose class lies outside the advisory
     set, not that the set is clean: an advisory finding is reported and
     exits 0.
  1  At least one finding whose class lies outside the advisory set.
  2  No ticket set resolved for the run; argparse's own usage error exits 2
     as well.

A cut verdict is not portable between hosts. An oracle naming an interpreter
one host lacks is reported there as unrunnable-oracle and is silent here, so a
verdict is read only on the host that produced it."""


def _finding_line(ticket_id, number, klass, detail):
    # A criterion number of 0 is a defect of the ticket, not of one oracle.
    where = "criterion {}: ".format(number) if number else ""
    return "{}: {}: {}: {}{}".format(ticket_id, FAMILY_OF[klass], klass, where, detail)


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="cutcheck.py",
        description="Report cut defects in an issued ticket set.",
        # Raw: the epilog's sentences are the contract, and a formatter that
        # rewraps them to the terminal decides where they break.
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=EPILOG,
    )
    parser.add_argument("run", help="run id naming the issued ticket set")
    parser.add_argument(
        "--baseline",
        required=True,
        help="revision the ticket set was cut from",
    )
    parser.add_argument(
        "--lib",
        default=None,
        help="orchflows library whose pack cells an executor is read against; "
        "defaults to the library this script runs from, then to the install "
        "beside the state sink. Never the repository under test",
    )
    args = parser.parse_args(argv)

    # One invocation's readings, never the last one's: this process may grade
    # more than once, and a stale line would be reported against a run that
    # did not produce it.
    del _UNREAD[:]
    worktree_root = _worktree_root()
    run_dir = _run_dir(args.run, worktree_root)
    if run_dir is None or worktree_root is None:
        print("cutcheck: no ticket set resolved for run {}".format(args.run))
        return NO_TICKET_SET

    scratch_root = _scratch_root(worktree_root)
    if scratch_root is None:
        print("{} {}".format(NO_SCRATCH_ROOT, worktree_root))
        return NO_TICKET_SET
    try:
        baseline_tree = _scratch_tree(args.baseline, worktree_root, scratch_root)
        if baseline_tree is None:
            print("cutcheck: cannot clone baseline {}".format(args.baseline))
            return NO_TICKET_SET
        head_tree = None
        if not _same_revision(args.baseline, worktree_root):
            head_tree = _scratch_tree("HEAD", worktree_root, scratch_root)
            if head_tree is None:
                # The baseline half's twin. A HEAD half that arrived as None
                # is read below as cut time -- no landed work to compare
                # against -- so every oracle graded clean and the run exited
                # 0 having read one revision of two. The clone that fails
                # here fails for the reason it fails there: friction
                # 04:21:49Z is `MAX_PATH` on this host.
                print("cutcheck: cannot clone HEAD")
                return NO_TICKET_SET
        issued = sorted(
            p for p in run_dir.glob("*.md")
            if p.name != COVERAGE_FILE and not p.name.endswith(COVERAGE_SUFFIX)
        )
        siblings = {}
        reads = {}
        for path in issued:
            text = path.read_text(encoding="utf-8")
            frontmatter = _parse_frontmatter(text)
            ticket_id = frontmatter.get("id") or path.stem
            frontmatter["__completion_test"] = _sections(text).get(
                COMPLETION_SECTION, ""
            )
            siblings[ticket_id] = frontmatter
            reads[ticket_id] = _oracle_reads(text)
        findings = []
        for path in issued:
            findings.extend(_check_ticket(path, baseline_tree, head_tree, siblings))
        findings.extend(_pairwise(siblings, reads))
        # The sink first: a run's coverage map lives there now, and a report
        # line naming it absolutely would be machine-specific again.
        roots = (state_root.state_root(), worktree_root,
                 state_root.find_repo_root(Path.cwd()))
        findings.extend(_coverage_findings(args.run, run_dir, siblings, roots))
        findings.extend(_root_gate_layout(siblings))
        findings.extend(_executor_legality(siblings, _lib_root(args.lib)))
        findings.extend(_symlink_findings(args.run, (baseline_tree, head_tree)))
    finally:
        _remove_scratch_root(scratch_root)

    # Against the run and not against any one ticket: a reading that did not
    # happen is this invocation's fact, and the item whose grading it cost is
    # named inside the line where the reading knows it.
    findings.extend((args.run, 0, UNREAD_HALF, what) for what in _UNREAD)
    outside = [f for f in findings if f[2] not in ADVISORY]
    advisory = [f for f in findings if f[2] in ADVISORY]
    for finding in outside:
        print(_finding_line(*finding))
    if advisory:
        print(ADVISORY_HEADING)
        for finding in advisory:
            print(_finding_line(*finding))
    # Read from the same `siblings` the findings were, and printed whatever
    # they said. It stands after the advisory block so that everything the exit
    # status answers for is above it and read first, and it is built outside
    # `findings` rather than added to them and excused: a class in that list is
    # a class the status has an opinion about, and this one must not be.
    shape = _graph_reading(args.run, siblings)
    if shape:
        print(GRAPH_HEADING)
        for reading in shape:
            print(_finding_line(*reading))
    if outside:
        return REPORTED
    # Zero bytes reads the same as a run that never happened. A set whose only
    # findings are advisory has been read and has passed, and says so.
    print(NO_FINDING_OUTSIDE)
    return CLEAN


if __name__ == "__main__":
    raise SystemExit(main())
