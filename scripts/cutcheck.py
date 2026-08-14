#!/usr/bin/env python3
"""Report cut defects in an issued ticket set, before any work starts.

Family 1 is oracle discrimination and oracle shape. Family 2 is path
reality. Family 3 is scope closure. One invocation decides all three.

Discrimination: an oracle that reads the same at the baseline as it will
once the work has landed proves nothing. Every extractable oracle runs
inside a scratch copy of the baseline revision and, when it fails there,
inside a scratch copy of HEAD -- both built beside the tree by ``git
archive``, never in the tree under test. An oracle that already passes
at the baseline, that finds nothing at either revision, or that fails at
both from a missing path, class or module is reported. When HEAD is the
baseline the HEAD half is skipped: at cut time nothing has landed, so a
baseline failure is what a discriminating oracle looks like.

Path reality: a path an oracle names exists at the baseline, or the item
itself or a ``depends_on`` ancestor creates it; a ``file:line`` or
``file section`` citation resolves; a quoted string is present where it
is cited. All of it resolves in the baseline scratch copy -- the tree
the ticket was cut from, which the work then changes.

Scope closure: the write scope covers every path the item says it
writes, evidence sinks included, and no excluded action names a path the
scope grants. A path the item only reads is no defect: observing is not
naming.

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
FAMILY_2 = "family 2"
FAMILY_3 = "family 3"
ALREADY_PASSES = "already-passes"
NO_HITS_BOTH_REVISIONS = "no-hits-both-revisions"
FAILS_BOTH_REVISIONS = "fails-both-revisions"
SWALLOWED_EXIT = "swallowed-exit"
CUMULATIVE_RANGE = "cumulative-range"
EXTRACTION_GAP = "extraction-gap"
MISSING_PATH = "missing-path"
UNRESOLVED_CITATION = "unresolved-citation"
QUOTE_NOT_AT_CITATION = "quote-not-at-citation"
UNSCOPED_WRITE = "unscoped-write"
SCOPE_CONTRADICTION = "scope-contradiction"
FAMILY_OF = {
    ALREADY_PASSES: FAMILY,
    NO_HITS_BOTH_REVISIONS: FAMILY,
    FAILS_BOTH_REVISIONS: FAMILY,
    SWALLOWED_EXIT: FAMILY,
    CUMULATIVE_RANGE: FAMILY,
    EXTRACTION_GAP: FAMILY,
    MISSING_PATH: FAMILY_2,
    UNRESOLVED_CITATION: FAMILY_2,
    QUOTE_NOT_AT_CITATION: FAMILY_2,
    UNSCOPED_WRITE: FAMILY_3,
    SCOPE_CONTRADICTION: FAMILY_3,
}
# Advisory classes are printed and never set the exit status.
ADVISORY = frozenset({EXTRACTION_GAP})

OBJECTIVE_SECTION = "Objective"
INPUTS_SECTION = "Fixed inputs"
COMPLETION_SECTION = "Completion test"
CRITERION_RE = re.compile(r"^\s*(\d+)\.\s+(.*)$")
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
CITATION_RE = re.compile(r"\b([\w][\w./-]*\.[A-Za-z0-9]{1,5}):(\d+)")
SECTION_CITATION_RE = re.compile(r"\b([\w][\w./-]*\.[A-Za-z0-9]{1,5})\s+§(\d+)")
QUOTE_RE = re.compile(r'"([^"\n]{6,120})"')
WRITE_RE = re.compile(
    r"\b(?:write|writes|writing|written|create|creates|creating|emit|emits"
    r"|append|appends|record|records)\b",
    re.IGNORECASE,
)
DOTTED_RE = re.compile(r"\.[A-Za-z0-9]{1,5}$")
GLOB_RE = re.compile(r"[*?\[\]]")
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
    """Tokens in prose that name a path: a slash, or a short final extension."""

    found = []
    for token in text.replace("`", " ").split():
        token = token.lstrip("(<[\"'").rstrip(")>],;:.\"'")
        if not token or token[:1] == "-" or GLOB_RE.search(token):
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
    """Family 2 over prose: citations resolve, and a quote is where it is cited."""

    findings = []
    cites = _citations(prose)
    for _, rel, line, section in cites:
        if _cited_text(baseline_tree, rel, line, section) is None:
            findings.append((UNRESOLVED_CITATION, _where(rel, line, section)))
    for match in QUOTE_RE.finditer(prose):
        near = [c for c in cites if abs(c[0] - match.start()) <= QUOTE_WINDOW]
        if not near:
            continue
        _, rel, line, section = min(near, key=lambda c: abs(c[0] - match.start()))
        text = _cited_text(baseline_tree, rel, line, section)
        if text is None or _flat(match.group(1)) in text:
            continue
        findings.append(
            (
                QUOTE_NOT_AT_CITATION,
                '"{}" not at {}'.format(match.group(1), _where(rel, line, section)),
            )
        )
    return findings


def _scope_closure(frontmatter, prose):
    """Family 3: the grant covers every write, and contradicts no exclusion.

    Observing is not naming: a path the item only reads stays outside its write
    scope and is no defect here.
    """

    scope = _listed(frontmatter, "write_scope")
    findings = []
    seen = set()
    flat = _flat(prose)
    for match in WRITE_RE.finditer(flat):
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
        issued = sorted(run_dir.glob("*.md"))
        siblings = {}
        for path in issued:
            frontmatter = _parse_frontmatter(path.read_text(encoding="utf-8"))
            siblings[frontmatter.get("id") or path.stem] = frontmatter
        findings = []
        for path in issued:
            findings.extend(_check_ticket(path, baseline_tree, head_tree, siblings))
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
