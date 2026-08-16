#!/usr/bin/env python3
"""Documentation lint for any repository root.

Two questions, one JSON document on stdout: does every relative markdown
link under ``<root>`` resolve to something on disk, and does one paragraph
sit in two files? A dangling link sends a reader nowhere; a paragraph with
two homes is a fact with two owners, and the check names both sites rather
than choosing between them.

Nothing here knows this repository. ``tools/validate.py`` imports these
functions to ask the same two questions of the library tree -- the import
runs that way and never the reverse, so a project that installs the
scripts gets the oracle without the library's own grading.

Stdlib only, Python 3.9+, POSIX and Windows.

Usage:
    python scripts/doclint.py <root> [--near-duplicate-threshold T]

Exit status is 1 when the report carries a finding, 0 when it does not.
"""

from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
from pathlib import Path

LINK_RE = re.compile(r"\]\(([^)]+)\)")
EXTERNAL_PREFIXES = ("http://", "https://", "mailto:")

# Paragraphs, not clauses: at whole-block size a pair this close is a copy
# someone edited, while two blocks merely on one subject sit far below.
DEFAULT_NEAR_DUPLICATE_THRESHOLD = 0.9
# A copy is found where its words are: two texts are compared when they
# share a word carried by no more than this many texts. Above it a word is
# idiom, and pairing on idiom means comparing every text with every other
# -- quadratic in the corpus, which turns a check meant to run on every
# save into a coffee break. Normative with the threshold: the two together
# decide the reported set.
DISTINCTIVE_MAX = 20
WORD_RE = re.compile(r"[A-Za-z][A-Za-z'-]{3,}")
# A heading, a one-line note, a table row: short blocks repeat across
# documents by function rather than by copying, and reporting them would
# drive documents to stop stating the obvious thing they must state.
PARAGRAPH_MIN_WORDS = 12
PARAGRAPH_SPLIT_RE = re.compile(r"\n\s*\n")


def read(path: Path) -> str:
    """The file's text. ``utf-8-sig`` because a BOM-prefixed file -- what
    PowerShell's ``Out-File`` writes by default -- must read as its text
    and not as text with a BOM glued to the first line; ``replace`` because
    one undecodable byte in one file may not cost the whole report."""

    return path.read_text(encoding="utf-8-sig", errors="replace")


def markdown_files(root: Path) -> list:
    """Every ``*.md`` under ``root``, minus dot-directories: ``.git`` and
    the caches beside it are not the project's documentation."""

    return sorted(
        path
        for path in Path(root).rglob("*.md")
        if not any(part.startswith(".") for part in path.relative_to(root).parts)
    )


def resolve_link(source: Path, target: str, root=None):
    """The path ``target`` names when read from ``source``, or ``None``
    when the link is not the repository's to resolve: an external URL, a
    bare anchor, a templated path something else fills in, or a
    root-relative ``/path`` when no ``root`` is given to read it from. An
    anchor on a real path is dropped -- the file is what must exist. A
    destination in angle brackets -- markdown's spelling of a path with a
    space -- is read without them.

    A name the path layer refuses to resolve is *not* that ``None``: it is
    returned unresolved, so it is graded and found missing. A reader cannot
    follow a link the filesystem will not answer for either, and sharing
    one channel with "not ours to grade" sent it through unread."""

    target = target.strip()
    if target.startswith("<") and ">" in target:
        target = target[1:target.index(">")]
    else:
        target = target.split(" ", 1)[0]
    target = target.split("#", 1)[0].strip()
    if not target or target.startswith(EXTERNAL_PREFIXES) or "{{" in target:
        return None
    base = source.parent
    if target.startswith("/"):
        if root is None:
            return None
        base, target = Path(root), target.lstrip("/")
    try:
        return (base / target).resolve()
    except (OSError, ValueError):
        # ValueError as well as OSError: an embedded null is the path layer
        # refusing the name before the filesystem is asked, and it reached
        # here uncaught.
        return base / target


def dangling_links(source: Path, text: str, root=None) -> list:
    """Every link target in ``text`` that resolves to nothing on disk.
    ``root`` is where a root-relative ``/path`` is read from; without it
    such a link is not graded."""

    missing = []
    for match in LINK_RE.finditer(text):
        target = match.group(1)
        resolved = resolve_link(source, target, root)
        if resolved is not None and not resolved.exists():
            missing.append(target)
    return missing


def paragraphs(text: str) -> list:
    """The comparable blocks of ``text``: blank-line separated, whitespace
    flattened, and anything under ``PARAGRAPH_MIN_WORDS`` words dropped.
    CRLF is normalized first, so a Windows checkout and a POSIX one are
    graded over the same blocks."""

    blocks = []
    for block in PARAGRAPH_SPLIT_RE.split(text.replace("\r\n", "\n")):
        flat = " ".join(block.split())
        if len(flat.split()) >= PARAGRAPH_MIN_WORDS:
            blocks.append(flat)
    return blocks


def similarity(left: str, right: str) -> float:
    """The near-duplicate ratio of two texts.

    ``autojunk=False`` is normative rather than a tuning detail: difflib's
    default drops characters common in any sequence over 200 characters,
    which suppresses the ratio on exactly the longest passages -- the ones
    a duplication check exists to catch.
    """

    return difflib.SequenceMatcher(None, left, right, autojunk=False).ratio()


def _candidates(texts: list, distinctive_max: int) -> set:
    """The ``(i, j)`` positions worth comparing: two texts sharing a word
    that no more than ``distinctive_max`` texts carry. Built from an
    inverted index over those words, so the cost is the candidate count
    rather than the square of the corpus."""

    frequency: dict = {}
    words_at: list = []
    for text in texts:
        words = frozenset(word.lower() for word in WORD_RE.findall(text))
        words_at.append(words)
        for word in words:
            frequency[word] = frequency.get(word, 0) + 1
    postings: dict = {}
    for position, words in enumerate(words_at):
        for word in words:
            if frequency[word] <= distinctive_max:
                postings.setdefault(word, []).append(position)
    pairs = set()
    for ids in postings.values():
        for a in range(len(ids)):
            for b in range(a + 1, len(ids)):
                pairs.add((ids[a], ids[b]))
    return pairs


def near_duplicate_pairs(texts, threshold, distinctive_max=DISTINCTIVE_MAX, accept=None):
    """Yield ``(i, j, ratio)`` for every pair of ``texts`` at or above
    ``threshold``, ``i < j``, in index order.

    ``accept(i, j)`` -- every candidate, absent -- filters pairs before any
    ratio is computed, which is where a caller states what a pair may not
    be: two blocks of one file, a copy the tree licensed.

    The one near-duplicate method in the repository. ``report`` below
    compares paragraphs across files with it and ``tools/validate.py``'s
    cross-tier check compares clauses across tiers with it, so what counts
    as a copy is decided in one place for both.
    """

    texts = list(texts)
    by_left: dict = {}
    for left, right in _candidates(texts, distinctive_max):
        if accept is None or accept(left, right):
            by_left.setdefault(left, []).append(right)
    matcher = difflib.SequenceMatcher(None, autojunk=False)
    for left in sorted(by_left):
        matcher.set_seq2(texts[left])
        for right in sorted(by_left[left]):
            matcher.set_seq1(texts[right])
            # The cheap bounds first, both of them upper bounds on the
            # ratio: difflib computes them without matching anything, and
            # they answer for four candidates in ten.
            if matcher.real_quick_ratio() < threshold:
                continue
            if matcher.quick_ratio() < threshold:
                continue
            ratio = matcher.ratio()
            if ratio >= threshold:
                yield left, right, ratio


def report(root, threshold: float = DEFAULT_NEAR_DUPLICATE_THRESHOLD) -> dict:
    """Every finding under ``root``, as the document the command prints.

    Each finding carries the sites it convicts, because a duplication
    reported at one file is a fact its reader cannot act on.
    """

    root = Path(root)
    findings = []
    texts: list = []
    owners: list = []
    for path in markdown_files(root):
        text = read(path)
        label = path.relative_to(root).as_posix()
        for target in dangling_links(path, text, root):
            findings.append({"kind": "dangling-link", "file": label, "target": target})
        for block in paragraphs(text):
            texts.append(block)
            owners.append(label)

    def across_files(left: int, right: int) -> bool:
        # One document restating itself is its author's business; two
        # documents restating each other is the finding.
        return owners[left] != owners[right]

    for left, right, ratio in near_duplicate_pairs(texts, threshold, accept=across_files):
        findings.append(
            {
                "kind": "near-duplicate",
                "file": owners[left],
                "other": owners[right],
                "ratio": round(ratio, 4),
                "text": texts[left],
                "other_text": texts[right],
            }
        )

    counts: dict = {}
    for finding in findings:
        counts[finding["kind"]] = counts.get(finding["kind"], 0) + 1
    return {
        "root": str(root),
        "threshold": threshold,
        "findings": findings,
        "counts": counts,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="doclint.py",
        description="Grade a repository's markdown: links resolve, paragraphs have one home.",
    )
    parser.add_argument("root", help="repository root to grade")
    parser.add_argument(
        "--near-duplicate-threshold",
        dest="threshold",
        type=float,
        default=DEFAULT_NEAR_DUPLICATE_THRESHOLD,
        help="report a paragraph pair at or above this ratio (default: %(default)s)",
    )
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    root = Path(args.root)
    if not root.is_dir():
        raise SystemExit("doclint: no such directory: " + str(root))
    payload = report(root, args.threshold)
    # One JSON document, ASCII-escaped by json's default: a console that is
    # not UTF-8 -- a Windows one is cp1252 -- must still be able to print
    # a finding that quotes an em dash.
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 1 if payload["findings"] else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
