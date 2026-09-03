#!/usr/bin/env python3
"""Documentation lint for any repository root.

Two questions, one JSON document on stdout: does every relative markdown
link under ``<root>`` resolve to something on disk, and does one paragraph
sit in two files? A duplication names both sites rather than choosing
between them. Nothing here knows this repository -- ``tools/validate.py``
imports these functions to ask the same two questions of the library tree,
and never the reverse.

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

try:  # in-repo; the installed copy sits flat beside doclint.py
    from scripts import console
except ImportError:  # pragma: no cover - the installed copy's path
    import console

LINK_RE = re.compile(r"\]\(([^)]+)\)")
EXTERNAL_PREFIXES = ("http://", "https://", "mailto:")

# Paragraphs, not clauses: at whole-block size a pair this close is a copy
# someone edited, while two blocks merely on one subject sit far below.
DEFAULT_NEAR_DUPLICATE_THRESHOLD = 0.9
# A copy is found where its words are: two texts are compared when they
# share a word carried by no more than this many texts. Above it a word is
# idiom, and pairing on idiom is quadratic in the corpus. Normative with
# the threshold: the two together decide the reported set.
DISTINCTIVE_MAX = 20
WORD_RE = re.compile(r"[A-Za-z][A-Za-z'-]{3,}")
# A heading, a one-line note, a table row: short blocks repeat by function
# rather than by copying.
PARAGRAPH_MIN_WORDS = 12
PARAGRAPH_SPLIT_RE = re.compile(r"\n\s*\n")


def read(path: Path) -> str:
    """The file's text. ``utf-8-sig`` so a BOM-prefixed file reads as its
    text; ``replace`` so one undecodable byte does not cost the report."""

    return path.read_text(encoding="utf-8-sig", errors="replace")


def markdown_files(root: Path) -> list:
    """Every ``*.md`` under ``root``, minus dot-directories."""

    return sorted(
        path
        for path in Path(root).rglob("*.md")
        if not any(part.startswith(".") for part in path.relative_to(root).parts)
    )


def resolve_link(source: Path, target: str, root=None):
    """The path ``target`` names when read from ``source``, or ``None``
    when the link is not the repository's to resolve: an external URL, a
    bare anchor, a templated path, or a root-relative ``/path`` with no
    ``root`` to read it from. An anchor on a real path is dropped and a
    destination in angle brackets is read without them."""

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
        # refusing the name before the filesystem is asked.
        return base / target


def dangling_links(source: Path, text: str, root=None) -> list:
    """Every link target in ``text`` that resolves to nothing on disk."""

    missing = []
    for match in LINK_RE.finditer(text):
        target = match.group(1)
        resolved = resolve_link(source, target, root)
        if resolved is not None and not resolved.exists():
            missing.append(target)
    return missing


def paragraphs(text: str) -> list:
    """The comparable blocks of ``text``: blank-line separated, whitespace
    flattened, anything under ``PARAGRAPH_MIN_WORDS`` words dropped, CRLF
    normalized first so both checkouts are graded over the same blocks."""

    blocks = []
    for block in PARAGRAPH_SPLIT_RE.split(text.replace("\r\n", "\n")):
        flat = " ".join(block.split())
        if len(flat.split()) >= PARAGRAPH_MIN_WORDS:
            blocks.append(flat)
    return blocks


def similarity(left: str, right: str) -> float:
    """The near-duplicate ratio of two texts."""

    return difflib.SequenceMatcher(None, left, right, autojunk=False).ratio()


def _candidates(texts: list, distinctive_max: int) -> set:
    """The ``(i, j)`` positions worth comparing: two texts sharing a word
    no more than ``distinctive_max`` texts carry, from an inverted index,
    so the cost is the candidate count rather than the corpus squared."""

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
    ``threshold``, ``i < j``, in index order."""

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
            # The cheap bounds first, both upper bounds on the ratio:
            # difflib computes them without matching anything.
            if matcher.real_quick_ratio() < threshold:
                continue
            if matcher.quick_ratio() < threshold:
                continue
            ratio = matcher.ratio()
            if ratio >= threshold:
                yield left, right, ratio


def report(root, threshold: float = DEFAULT_NEAR_DUPLICATE_THRESHOLD) -> dict:
    """Every finding under ``root``, as the document the command prints."""

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
    console.harden()
    args = build_parser().parse_args(argv)
    root = Path(args.root)
    if not root.is_dir():
        raise SystemExit("doclint: no such directory: " + str(root))
    payload = report(root, args.threshold)
    # ASCII-escaped by json's default, so a console that is not UTF-8 can
    # still print a finding that quotes an em dash.
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 1 if payload["findings"] else 0


if __name__ == "__main__":
    raise SystemExit(console.run(main, sys.argv[1:]))
