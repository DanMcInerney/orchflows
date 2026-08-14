#!/usr/bin/env python3
"""Report cut defects in an issued ticket set, before any work starts.

Family 1 is oracle discrimination and oracle shape.

Discrimination: an oracle that reads the same at the baseline as it will
once the work has landed proves nothing. Every extractable oracle runs
inside a scratch copy of the baseline revision and, when it fails there,
inside a scratch copy of HEAD -- both built beside the tree by ``git
archive``, never in the tree under test. An oracle that already passes
at the baseline, that finds nothing at either revision, or that fails at
both from a missing path, class or module is reported.

Shape: the command text itself carries two defects. A pipeline through
``tail`` or ``head`` reports that pipe's exit status, not the check's. A
per-item scope check written against a cumulative ``<base>..HEAD`` range
answers about the whole branch, not the item.

Both of those set the exit status. An extraction gap does not: a
criterion whose oracle no extractor recognized is reported on its own
line so silent under-coverage stays visible, but real tickets state many
criteria in prose, and a gap that failed the run would turn every clean
set red. Gaps are for the decomposer to read, not for the exit code to
decide.

cutcheck never edits a ticket; it reports, and the decomposer repairs.
An extracted command is ticket content and ticket content is untrusted,
so commands run argv-only, never through a shell, under a timeout, with
a working directory inside a scratch copy.
"""

import argparse
import re
import shlex
import shutil
import subprocess
import tarfile
import tempfile
from pathlib import Path

try:  # in-repo; the installed copy sits flat beside tickets.py
    from scripts.tickets import _find_repo_root, _parse_frontmatter, _sections
except ImportError:  # pragma: no cover - the installed copy's path
    from tickets import _find_repo_root, _parse_frontmatter, _sections

FAMILY = "family 1"
ALREADY_PASSES = "already-passes"
NO_HITS_BOTH_REVISIONS = "no-hits-both-revisions"
FAILS_BOTH_REVISIONS = "fails-both-revisions"
SWALLOWED_EXIT = "swallowed-exit"
CUMULATIVE_RANGE = "cumulative-range"
EXTRACTION_GAP = "extraction-gap"
# Advisory classes are printed and never set the exit status.
ADVISORY = frozenset({EXTRACTION_GAP})

COMPLETION_SECTION = "Completion test"
CRITERION_RE = re.compile(r"^(\d+)\.\s+(.*)$")
BACKTICK_RE = re.compile(r"`([^`]+)`")
SWALLOW_RE = re.compile(r"\|\s*(?:tail|head)\b")
CUMULATIVE_RE = re.compile(r"\S+\.\.HEAD\b")
COMMAND_HEADS = (
    "bash",
    "git",
    "grep",
    "node",
    "npm",
    "pytest",
    "python",
    "python3",
    "rg",
    "sh",
)
SEARCH_HEADS = ("grep", "rg")
NO_MATCH = 1
COMMAND_TIMEOUT = 180
TIMED_OUT = 124
UNRUNNABLE = 127
NO_TICKET_SET = 2
REPORTED = 1
CLEAN = 0


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


def _scratch_tree(rev, worktree_root, scratch_root):
    """Extract ``rev`` beside the tree, so no oracle runs in the tree itself."""

    tree = scratch_root / re.sub(r"[^A-Za-z0-9_.-]", "-", rev)
    if tree.is_dir():
        return tree
    archive = scratch_root / "archive.tar"
    proc = _git(["archive", "--format=tar", "-o", str(archive), rev], worktree_root)
    if proc is None or proc.returncode != 0:
        return None
    tree.mkdir(parents=True)
    with tarfile.open(archive) as bundle:
        if hasattr(tarfile, "data_filter"):
            bundle.extractall(tree, filter="data")
        else:
            bundle.extractall(tree)
    archive.unlink()
    return tree


def _criteria(section):
    """Numbered completion-test items; unindented prose ends the list."""

    items = []
    current = None
    for line in section.splitlines():
        match = CRITERION_RE.match(line)
        if match:
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
    """Backtick spans whose first token names a command an extractor knows."""

    found = []
    for span in BACKTICK_RE.findall(criterion):
        candidate = span.strip()
        if candidate.split(" ", 1)[0] in COMMAND_HEADS:
            found.append(candidate)
    return found


def _shape(command):
    classes = []
    if SWALLOW_RE.search(command):
        classes.append(SWALLOWED_EXIT)
    if CUMULATIVE_RE.search(command):
        classes.append(CUMULATIVE_RANGE)
    return classes


def _exit_code(command, tree):
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
            capture_output=True,
            text=True,
            timeout=COMMAND_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        return TIMED_OUT
    except OSError:
        return UNRUNNABLE
    return proc.returncode


def _discrimination(command, baseline_tree, head_tree):
    """The class this oracle fails as, or None when it discriminates.

    An oracle discriminates when it fails at the baseline and passes once the
    work has landed, so HEAD is only consulted after the baseline read fails.
    """

    at_baseline = _exit_code(command, baseline_tree)
    if at_baseline is None:
        return None
    if at_baseline == 0:
        return ALREADY_PASSES
    if head_tree is None:
        return None
    at_head = _exit_code(command, head_tree)
    if at_head is None or at_head == 0:
        return None
    searching = command.split(" ", 1)[0] in SEARCH_HEADS
    if searching and at_baseline == NO_MATCH and at_head == NO_MATCH:
        return NO_HITS_BOTH_REVISIONS
    return FAILS_BOTH_REVISIONS


def _check_ticket(path, baseline_tree, head_tree):
    text = path.read_text(encoding="utf-8")
    ticket_id = _parse_frontmatter(text).get("id") or path.stem
    section = _sections(text).get(COMPLETION_SECTION, "")
    findings = []
    for number, criterion in _criteria(section):
        commands = _commands(criterion)
        if not commands:
            findings.append((ticket_id, number, EXTRACTION_GAP, criterion[:100]))
            continue
        for command in commands:
            shape = _shape(command)
            if shape:
                # A swallowed pipeline cannot be run argv-only anyway.
                findings.extend((ticket_id, number, k, command) for k in shape)
                continue
            klass = _discrimination(command, baseline_tree, head_tree)
            if klass is not None:
                findings.append((ticket_id, number, klass, command))
    return findings


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="cutcheck.py",
        description="Report cut defects in an issued ticket set.",
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

    scratch_root = Path(tempfile.mkdtemp(prefix=".cutcheck-", dir=str(worktree_root.parent)))
    try:
        baseline_tree = _scratch_tree(args.baseline, worktree_root, scratch_root)
        if baseline_tree is None:
            print("cutcheck: cannot archive baseline {}".format(args.baseline))
            return NO_TICKET_SET
        head_tree = _scratch_tree("HEAD", worktree_root, scratch_root)
        findings = []
        for path in sorted(run_dir.glob("*.md")):
            findings.extend(_check_ticket(path, baseline_tree, head_tree))
    finally:
        shutil.rmtree(scratch_root, ignore_errors=True)

    for ticket_id, number, klass, detail in findings:
        print(
            "{}: {}: {}: criterion {}: {}".format(
                ticket_id, FAMILY, klass, number, detail
            )
        )
    if any(klass not in ADVISORY for _, _, klass, _ in findings):
        return REPORTED
    return CLEAN


if __name__ == "__main__":
    raise SystemExit(main())
