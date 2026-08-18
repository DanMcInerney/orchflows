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

try:  # repository checkout
    from scripts import cutcheck_execute as _execute_module
    from scripts import cutcheck_executor as _executor_module
    from scripts import cutcheck_scratch as _scratch_module
    from scripts import cutcheck_ticket as _ticket_module
    from scripts.cutcheck_contract import *
    from scripts.cutcheck_state import *
    from scripts.cutcheck_scratch import *
    from scripts.cutcheck_commands import *
    from scripts.cutcheck_search import *
    from scripts.cutcheck_execute import *
    from scripts.cutcheck_scope import *
    from scripts.cutcheck_graph import *
    from scripts.cutcheck_coverage import *
    from scripts.cutcheck_executor import *
    from scripts.cutcheck_ticket import *
except ImportError:  # installed flat script directory
    import cutcheck_execute as _execute_module
    import cutcheck_executor as _executor_module
    import cutcheck_scratch as _scratch_module
    import cutcheck_ticket as _ticket_module
    from cutcheck_contract import *
    from cutcheck_state import *
    from cutcheck_scratch import *
    from cutcheck_commands import *
    from cutcheck_search import *
    from cutcheck_execute import *
    from cutcheck_scope import *
    from cutcheck_graph import *
    from cutcheck_coverage import *
    from cutcheck_executor import *
    from cutcheck_ticket import *

# Stable facade literals remain here because existing checks and command
# oracles read the installed entry point itself, not its implementation files.
FAMILY = "family 1"
CANARY_DIR = ".orch"


def _scratch_root(worktree_root):
    return _scratch_module._scratch_root(worktree_root)


def _remove_scratch_root(scratch_root):
    return _scratch_module._remove_scratch_root(scratch_root)


def _discrimination(command, baseline_tree, head_tree):
    _execute_module._exit_code = _exit_code
    _execute_module._mutations = _mutations
    return _execute_module._discrimination(command, baseline_tree, head_tree)


def _lib_root(declared):
    _executor_module.PACKS_DIR = PACKS_DIR
    return _executor_module._lib_root(declared)


def _check_ticket(path, baseline_tree, head_tree, siblings):
    _ticket_module._discrimination = _discrimination
    _ticket_module._mutations = _mutations
    return _ticket_module._check_ticket(path, baseline_tree, head_tree, siblings)

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
