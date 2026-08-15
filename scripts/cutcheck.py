#!/usr/bin/env python3
"""Report cut defects in an issued ticket set, before any work starts.

Family 1 is oracle discrimination and oracle shape. Family 2 is path
reality. Family 3 is scope closure. Family 4 is pairwise safety. Family
5 is acceptance coverage. Family 6 is executor legality. One invocation
decides all six.

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
grant's own name.

Pairwise safety: for every pair the DAG leaves unordered -- ordering is
reachability through ``depends_on``, not adjacency -- write scopes are
disjoint and neither item's oracle reads what the other writes, or
whichever lands first invalidates the other's evidence.

Coverage: the run's acceptance-coverage map, read beside whichever
ticket root resolved, is checked both ways against the issued set. Every
criterion reaches an item, the gate, or declared remainder, and every
item is named by some criterion. A root with no map has nothing to read
against, so the absence is all that is reported.

Executor legality: an item's executor is one its stamped pack's executor
or assembly cell names, and is never an engine -- an engine dispatches
an executor rather than being one. An item naming no pack has no cell to
resolve against, so only the prohibition applies.

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
"""

import argparse
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

try:  # in-repo; the installed copy sits flat beside tickets.py
    from scripts.tickets import (
        ENGINE_EXECUTORS,
        _find_repo_root,
        _parse_frontmatter,
        _sections,
    )
except ImportError:  # pragma: no cover - the installed copy's path
    from tickets import (
        ENGINE_EXECUTORS,
        _find_repo_root,
        _parse_frontmatter,
        _sections,
    )

FAMILY = "family 1"
FAMILY_2 = "family 2"
FAMILY_3 = "family 3"
FAMILY_4 = "family 4"
FAMILY_5 = "family 5"
FAMILY_6 = "family 6"
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
SCOPE_COLLISION = "scope-collision"
STAGED_INVALIDATION = "staged-invalidation"
ORPHAN_CRITERION = "orphan-criterion"
ORPHAN_ITEM = "orphan-item"
COVERAGE_MAP_ABSENT = "coverage-map-absent"
ILLEGAL_EXECUTOR = "illegal-executor"
SYMLINK_IN_TREE = "symlink-in-tree"
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
    EXTRACTION_GAP: FAMILY,
    VERDICT_IN_OUTPUT: FAMILY,
    UNRUNNABLE_ORACLE: FAMILY,
    WHOLE_SUITE_ORACLE: FAMILY,
    MISSING_PATH: FAMILY_2,
    UNRESOLVED_CITATION: FAMILY_2,
    QUOTE_NOT_AT_CITATION: FAMILY_2,
    UNSCOPED_WRITE: FAMILY_3,
    SCOPE_CONTRADICTION: FAMILY_3,
    SCOPE_COLLISION: FAMILY_4,
    STAGED_INVALIDATION: FAMILY_4,
    ORPHAN_CRITERION: FAMILY_5,
    ORPHAN_ITEM: FAMILY_5,
    COVERAGE_MAP_ABSENT: FAMILY_5,
    ILLEGAL_EXECUTOR: FAMILY_6,
}
# Advisory classes are printed and never set the exit status. A map that is
# not there is a fact about the run, not a defect of the cut; a committed
# symlink is a fact about the repository, and confinement does not rest on
# reporting it -- the clone flag holds whether or not anyone reads this line.
ADVISORY = frozenset(
    {EXTRACTION_GAP, COVERAGE_MAP_ABSENT, VERDICT_IN_OUTPUT, SYMLINK_IN_TREE}
)
# The report's two summary lines. A reader selects finding lines by filtering
# stdout on a family, a class name, a criterion number or a ticket id, so
# neither summary line may carry any of those, nor the path of a script: a
# summary a filter selects is a finding line to everything downstream.
ADVISORY_HEADING = "cutcheck: advisory -- reported, and never setting the exit status:"
NO_FINDING_OUTSIDE = "cutcheck: no finding outside the advisory set"
SCRATCH_NOT_REMOVED = "cutcheck: scratch root not removed"
NO_SCRATCH_ROOT = "cutcheck: no scratch root under the git common dir of"
# One directory under the git common dir holds every copy every cut makes, so
# a root outliving its run is findable rather than scattered.
SCRATCH_DIR = "cutcheck-scratch"

# The acceptance-coverage map: one row per spec criterion, naming the item,
# the gate, or declared remainder that answers for it.
COVERAGE_FILE = "coverage.md"
COVERAGE_OWNERS = ("gate", "remainder")
TICKETS_DIR = "tickets"
CANARY_DIR = "canary"
RUNS_DIR = "runs"
# A pack's executor and assembly cells are the only executors it binds.
PACKS_DIR = "packs"
PACK_CELL_RE = re.compile(r"^\|\s*(?:executor|assembly)\s*\|([^|]*)\|", re.M)
SKILL_NAME_RE = re.compile(r"`(orch-[a-z0-9-]+)`")
# A pack name comes from ticket content, so it names one directory or nothing.
PACK_NAME_RE = re.compile(r"^[\w-]+$")
OBJECTIVE_SECTION = "Objective"
INPUTS_SECTION = "Fixed inputs"
COMPLETION_SECTION = "Completion test"
CRITERION_RE = re.compile(r"^\s*(\d+)\.\s+(.*)$")
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
# pre-existing is an invariant, and holding still is what it is for. Stating it
# is writing the field and nothing else: a sentence boundary opens the phrase,
# and no word continues it -- a parenthetical may follow, a predicate may not.
# A criterion that quotes the phrase, denies carrying it, or discusses what it
# means mentions the stamp instead of making one, and every such mention either
# sits behind a backtick, an article or a verb, or runs on into the clause that
# denies it. Grading is the default here, so a stamp written any other way is
# graded rather than believed.
PRE_EXISTING_RE = re.compile(
    r"(?:\A|[.;])\s*provenance:\s*pre-existing(?!\s*[A-Za-z])", re.I
)
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

    Run and canary tickets resolve at the main checkout because ``.orch/`` is
    gitignored and exists only there. Fixture sets resolve at the invoking
    worktree's own top level because they are tracked content, and every
    frontier item carries its own copy in its own worktree.
    """

    candidates = []
    main_root = _find_repo_root(Path.cwd())
    if main_root is not None:
        candidates.append(main_root / ".orch" / "tickets" / run)
        candidates.append(main_root / ".orch" / "canary" / "tickets" / run)
    if worktree_root is not None:
        candidates.append(worktree_root / "tests" / "fixtures" / "cutcheck" / run)
    for candidate in candidates:
        if candidate.is_dir():
            return candidate
    return None


def _scratch_root(worktree_root):
    """One invocation's private directory for the copies it grades in.

    Placed under the git common dir, which is the one directory that is the
    tool's to write in, answers the same from every worktree, and sits with the
    object store a local clone hardlinks from -- whatever volume the worktree
    itself is on. Enumerable too: every copy any cut ever leaves is under one
    ``cutcheck-scratch``, so a stale one can be found without a search.

    ``--git-common-dir``, and not the three neighbours it is easily confused
    with. ``worktree_root.parent`` is the repository's *parent* from a main
    checkout, which is how 24M landed outside every ignore file the repository
    has; a literal ``.git`` is an 85-byte file in a linked worktree; and
    ``--git-dir`` resolves to ``.git/worktrees/<name>``, so two worktrees
    grading one run would not share a place. The answer comes back relative
    -- a bare ``.git`` -- from a main checkout and absolute from a linked
    worktree, so it is joined to the tree it was asked about before use.

    ``None`` where there is no common dir to place it under, which is any
    directory outside a repository; the caller has a ticket set it cannot
    grade and says so.
    """

    proc = _git(["rev-parse", "--git-common-dir"], worktree_root)
    if proc is None or proc.returncode != 0:
        return None
    common = Path(proc.stdout.strip())
    if not common.is_absolute():
        common = worktree_root / common
    try:
        parent = common.resolve() / SCRATCH_DIR
        parent.mkdir(parents=True, exist_ok=True)
        return Path(tempfile.mkdtemp(prefix=".cutcheck-", dir=str(parent)))
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
    privilege. A tree carrying no history answers nothing and is reported as
    nothing -- the clone is what puts history there.
    """

    proc = _git(["ls-tree", "-r", "HEAD"], tree)
    if proc is None or proc.returncode != 0:
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
    """Every numbered completion-test item, at any indentation.

    Indentation is the signal and it is relative: a numbered line indented
    deeper than the line that opened the item now open is that item's own
    text -- a sentence wrapping onto a digit and a period, or a list nested
    under it -- and opens nothing. A numbered line at that opening line's
    indentation or less opens the next item, so a set whose criteria are
    themselves written indented is still a list; and one met while no item is
    open always opens one.

    Unindented prose ends an item's continuation, never the list: a criterion
    written after such a line still surfaces, as an extraction gap at minimum.
    """

    items = []
    current = None
    opened_at = 0
    for line in section.splitlines():
        match = CRITERION_RE.match(line)
        if match:
            depth = len(line) - len(line.lstrip())
            if current is not None and depth > opened_at:
                current[1].append(line.strip())
                continue
            opened_at = depth
            current = (int(match.group(1)), [match.group(2)])
            items.append(current)
            continue
        if current is None:
            continue
        if line.strip() and not line[0].isspace():
            current = None
            continue
        current[1].append(line.strip())
    return [(number, " ".join(p for p in parts if p)) for number, parts in items]


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
    """

    at_baseline = _exit_code(command, baseline_tree)
    if at_baseline is None:
        return None
    if at_baseline == 0:
        return ALREADY_PASSES
    if at_baseline in (UNRUNNABLE, TIMED_OUT):
        return UNRUNNABLE_ORACLE
    if head_tree is None:
        return None
    at_head = _exit_code(command, head_tree)
    if at_head is None or at_head == 0:
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


def _pairwise(siblings, reads):
    """Family 4: the pairs the DAG leaves free to run at the same time.

    Ordering is reachability, not adjacency -- a pair joined through a third
    item is staged, and staging is what makes a shared path safe. For every
    unordered pair the write scopes must be disjoint and neither item's oracle
    may read what the other writes, or the first result to land invalidates the
    second's evidence.
    """

    findings = []
    ids = sorted(siblings)
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


def _coverage_path(run_dir):
    """Where the acceptance-coverage map lives for a resolved ticket root.

    The map is found beside the root cutcheck already resolved, never at one
    fixed path: a run keeps it with its worklog, a fixture set carries its own
    beside its tickets, and the canary set has none to carry.
    """

    if run_dir.parent.name != TICKETS_DIR:
        return run_dir / COVERAGE_FILE
    if run_dir.parent.parent.name == CANARY_DIR:
        return None
    return run_dir.parent.parent / RUNS_DIR / run_dir.name / COVERAGE_FILE


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


def _coverage(run, run_dir, issued, roots):
    """Family 5: the map and the issued set answer for each other, both ways.

    A criterion reaches an item, the gate, or declared remainder; an item is
    named by some criterion. With no map there is nothing to read either
    direction against, so the absence is the only thing reported.
    """

    path = _coverage_path(run_dir)
    if path is None or not path.is_file():
        where = (
            _relative(path, roots) if path is not None else "none for this ticket root"
        )
        return [(run, 0, COVERAGE_MAP_ABSENT, where)]
    findings = []
    owned = set()
    for number, owner in _coverage_rows(path):
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
    return findings


def _pack_cells(pack, worktree_root):
    """The skills a pack's ``executor`` and ``assembly`` cells name.

    A pack this tree does not carry, or one whose cells name no skill, binds
    nothing here -- an assembly cell reading "none" is such a cell.
    """

    if worktree_root is None or not PACK_NAME_RE.match(pack):
        return set()
    path = worktree_root / PACKS_DIR / pack / "SKILL.md"
    if not path.is_file():
        return set()
    names = set()
    for row in PACK_CELL_RE.findall(path.read_text(encoding="utf-8", errors="replace")):
        names.update(SKILL_NAME_RE.findall(row))
    return names


def _executor_legality(siblings, worktree_root):
    """Family 6: an executor its pack's cells name, and never an engine.

    An engine dispatches a ticket's executor, so naming one as the executor is
    a call cycle. An item naming no pack has no cell to resolve against, and
    only the prohibition applies to it.
    """

    findings = []
    cells = {}
    for ticket_id in sorted(siblings):
        frontmatter = siblings[ticket_id]
        executor = str(frontmatter.get("executor") or "").strip()
        if not executor:
            continue
        if executor in ENGINE_EXECUTORS:
            findings.append(
                (ticket_id, 0, ILLEGAL_EXECUTOR, "{} is an engine".format(executor))
            )
            continue
        pack = str(frontmatter.get("pack") or "").strip()
        if not pack:
            continue
        if pack not in cells:
            cells[pack] = _pack_cells(pack, worktree_root)
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
            findings.append((ticket_id, number, EXTRACTION_GAP, criterion[:100]))
            continue
        invariant = bool(PRE_EXISTING_RE.search(criterion))
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
            findings.extend(
                (ticket_id, number, UNCONFINED_ORACLE, "{}: {}".format(wrote, command))
                for wrote in sorted(set(_MUTATED))
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
    args = parser.parse_args(argv)

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
        issued = sorted(p for p in run_dir.glob("*.md") if p.name != COVERAGE_FILE)
        siblings = {}
        reads = {}
        for path in issued:
            text = path.read_text(encoding="utf-8")
            frontmatter = _parse_frontmatter(text)
            ticket_id = frontmatter.get("id") or path.stem
            siblings[ticket_id] = frontmatter
            reads[ticket_id] = _oracle_reads(text)
        findings = []
        for path in issued:
            findings.extend(_check_ticket(path, baseline_tree, head_tree, siblings))
        findings.extend(_pairwise(siblings, reads))
        roots = (worktree_root, _find_repo_root(Path.cwd()))
        findings.extend(_coverage(args.run, run_dir, sorted(siblings), roots))
        findings.extend(_executor_legality(siblings, worktree_root))
        findings.extend(_symlink_findings(args.run, (baseline_tree, head_tree)))
    finally:
        _remove_scratch_root(scratch_root)

    outside = [f for f in findings if f[2] not in ADVISORY]
    advisory = [f for f in findings if f[2] in ADVISORY]
    for finding in outside:
        print(_finding_line(*finding))
    if advisory:
        print(ADVISORY_HEADING)
        for finding in advisory:
            print(_finding_line(*finding))
    if outside:
        return REPORTED
    # Zero bytes reads the same as a run that never happened. A set whose only
    # findings are advisory has been read and has passed, and says so.
    print(NO_FINDING_OUTSIDE)
    return CLEAN


if __name__ == "__main__":
    raise SystemExit(main())
