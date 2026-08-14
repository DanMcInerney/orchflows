#!/usr/bin/env python3
"""Report cut defects in an issued ticket set, before any work starts.

Family 1 is oracle discrimination and oracle shape. Family 2 is path
reality. Family 3 is scope closure. Family 4 is pairwise safety. Family
5 is acceptance coverage. Family 6 is executor legality. One invocation
decides all six.

Discrimination: an oracle that reads the same at the baseline as it will
once the work has landed proves nothing. Every extractable oracle runs
inside a scratch copy of the baseline revision and, when it fails there,
inside a scratch copy of HEAD -- both built beside the tree by ``git
archive``, never in the tree under test. An oracle that already passes
at the baseline, that finds nothing at either revision, or that fails at
both from a missing path, class or module is reported. When HEAD is the
baseline the HEAD half is skipped: at cut time nothing has landed, so a
baseline failure is what a discriminating oracle looks like. An oracle whose
criterion states ``provenance: pre-existing`` is an invariant -- it passed
before the work and has to pass after -- so discrimination is not asked of it,
and nothing else is forgiven it. A command carrying its verdict in what it
prints rather than in its exit status -- a count, an archive, a diff without
``--exit-code`` -- is reported as one this tool cannot decide.

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

Shape: the command text itself carries two defects. A pipeline through
``tail`` or ``head`` reports that pipe's exit status, not the check's. A
per-item scope check written against a cumulative ``<base>..HEAD`` range
answers about the whole branch, not the item.

Both of those set the exit status. An extraction gap and an absent
coverage map do not: a
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
EXTRACTION_GAP = "extraction-gap"
VERDICT_IN_OUTPUT = "verdict-in-output"
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
FAMILY_OF = {
    ALREADY_PASSES: FAMILY,
    NO_HITS_BOTH_REVISIONS: FAMILY,
    FAILS_BOTH_REVISIONS: FAMILY,
    SWALLOWED_EXIT: FAMILY,
    CUMULATIVE_RANGE: FAMILY,
    EXTRACTION_GAP: FAMILY,
    VERDICT_IN_OUTPUT: FAMILY,
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
# not there is a fact about the run, not a defect of the cut.
ADVISORY = frozenset({EXTRACTION_GAP, COVERAGE_MAP_ABSENT, VERDICT_IN_OUTPUT})

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
# A criterion states the provenance of its own oracle; an oracle stated
# pre-existing is an invariant, and holding still is what it is for.
PRE_EXISTING_RE = re.compile(r"provenance:\s*pre-existing", re.I)
# Counting prints the verdict; only these flags put a diff's verdict in its exit.
COUNT_FLAG_RE = re.compile(r"^-[A-Za-z]*c[A-Za-z]*$|^--count$")
DECIDING_DIFF_FLAGS = ("--exit-code", "--quiet", "--check")
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
# read-only copies built for this invocation, so the pair reads the same twice.
_EXIT_CACHE = {}


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


def _same_revision(rev, worktree_root):
    """Is ``rev`` the commit HEAD already points at?

    At cut time it is: nothing has landed, so every oracle that discriminates
    fails at the baseline and would fail again at HEAD. "Does this pass once
    the work lands" is unanswerable before the work lands, so the honest
    reading is to not ask -- the HEAD half is skipped and a baseline failure
    alone is clean. Post-work the two differ and the full rule applies.
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

    Unindented prose ends an item's continuation, never the list: a criterion
    written after such a line still surfaces, as an extraction gap at minimum.
    """

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
    """This command's exit status in this tree, run once however often asked.

    A scratch tree is a read-only copy built for one invocation and thrown away
    with it, so ``(command, tree)`` reads the same every time. The cache is a
    speed change and never a meaning change: one ticket set states the same
    invariant oracle in item after item, and a suite is a slow read.
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
            capture_output=True,
            text=True,
            timeout=COMMAND_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        return TIMED_OUT
    except OSError:
        return UNRUNNABLE
    return proc.returncode


def _verdict_in_output(command):
    """Is this a command whose exit status carries no verdict?

    ``grep -c`` prints a count and exits on whether it printed anything;
    ``git archive`` and a ``git diff`` without ``--exit-code`` exit 0 almost
    however the tree reads. A criterion saying "reports 0" or "is
    byte-identical" is judged by that text, which no exit status carries, so
    the honest report is that cutcheck cannot decide it.
    """

    argv = command.split()
    head, rest = argv[0], argv[1:]
    if head in SEARCH_HEADS:
        return any(COUNT_FLAG_RE.match(token) for token in rest)
    if head != "git" or not rest:
        return False
    if rest[0] == "archive":
        return True
    return rest[0] == "diff" and not any(f in rest for f in DECIDING_DIFF_FLAGS)


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

    A bare filename names no directory, so a scope entry of that name and any
    granted directory could hold it; only a rooted path is provably outside.
    """

    target = rel.strip().strip("/")
    for entry in scopes:
        scope = entry.strip().strip("/")
        if not scope:
            continue
        if target == scope or target.startswith(scope + "/") or scope.startswith(target + "/"):
            return True
        if "/" not in target and (
            entry.strip().endswith("/") or scope.rsplit("/", 1)[-1] == target
        ):
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
    """A path named the way every other line names one: from its root."""

    for root in roots:
        if root is None:
            continue
        try:
            return str(path.relative_to(root))
        except ValueError:
            continue
    return str(path)


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
                # A swallowed pipeline cannot be run argv-only anyway.
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
            if invariant:
                # An oracle the criterion states is pre-existing is an
                # invariant: it passed before this work and has to pass after,
                # so discriminating is not its job and never was.
                continue
            if _verdict_in_output(command):
                findings.append((ticket_id, number, VERDICT_IN_OUTPUT, command))
                continue
            klass = _discrimination(command, baseline_tree, head_tree)
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
    finally:
        shutil.rmtree(scratch_root, ignore_errors=True)

    for ticket_id, number, klass, detail in findings:
        # A criterion number of 0 is a defect of the ticket, not of one oracle.
        where = "criterion {}: ".format(number) if number else ""
        print(
            "{}: {}: {}: {}{}".format(ticket_id, FAMILY_OF[klass], klass, where, detail)
        )
    if any(klass not in ADVISORY for _, _, klass, _ in findings):
        return REPORTED
    return CLEAN


if __name__ == "__main__":
    raise SystemExit(main())
