"""Every term `docs/vocabulary.md` defines is used somewhere else.

The vocabulary is the library's namespace and the one file that charges
for a name twice: once where it is defined and once in every reader that
loads it. A term nothing else says is a definition with no referent --
the diluted-attention failure one file over.

The roster the scan skips is what cites the vocabulary without consuming
it: the reviews and specs under `research/`, the benchmark corpus, the
ring bundle, and the suite, where a term's only appearance proves a test
read this file rather than that the library uses the word.
"""

from __future__ import annotations

import os
from pathlib import Path

from . import common as __dep_common
ROOT = __dep_common.ROOT
SKIPPED = __dep_common.SKIPPED
re = __dep_common.re

from . import packages as __dep_packages
Diagnostics = __dep_packages.Diagnostics
_read_source = __dep_packages._read_source

VOCABULARY_OWNER = "docs/vocabulary.md"
VOCABULARY_NON_CONSUMERS = frozenset({
    "research", "benchmarks", ".orchflows", "tests", "reader/tests",
})
# Host, run, build and scratch trees are not prose any reader loads, and
# `.orch-notes/` is the reserved scratch a candidate writes its own
# working notes into -- a directory that would otherwise consume every
# term the child happened to quote.
VOCABULARY_SKIPPED_DIRS = frozenset({
    ".git", ".claude", ".orch", ".orch-notes", ".venv", ".mypy_cache",
    "__pycache__", "node_modules",
})
# One list item per definition. Alternative spellings of one entry are
# written `a / b`, and each alternative answers for its own consumer.
VOCABULARY_ENTRY_RE = re.compile(r"^- \*\*(.+?)\*\*", re.MULTILINE)
VOCABULARY_ALTERNATIVE = " / "
# Whitespace and the hyphen are the same separator inside a multi-word
# name: prose wraps one across a line and hyphenates it attributively.
VOCABULARY_WORD_SEPARATOR = r"[\s-]+"
VOCABULARY_WORD_SEPARATOR_RE = re.compile(VOCABULARY_WORD_SEPARATOR)


def _relative(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _consumer_sources(root: Path):
    """Every file the scan reads: the tree, minus what cannot consume.

    A walk of the tree rather than the Git index, because the validator
    grades whatever root it is pointed at and its own suite seeds a copy
    of the tree to take a failing reading. A roster read out of `.git`
    makes that copy grade differently from the tree it stands in for,
    which is the one thing those cases assert it does not.
    """

    for parent, directories, files in os.walk(root):
        here = Path(parent)
        directories[:] = sorted(
            name for name in directories
            if name not in VOCABULARY_SKIPPED_DIRS
            and _relative(here / name, root) not in VOCABULARY_NON_CONSUMERS
        )
        for name in sorted(files):
            source = here / name
            if _relative(source, root) != VOCABULARY_OWNER:
                yield source


def _defined_terms(owner: Path):
    """Map each defined term to the entry that defines it."""

    terms = {}
    for match in VOCABULARY_ENTRY_RE.finditer(_read_source(owner)):
        entry = match.group(1)
        for term in entry.split(VOCABULARY_ALTERNATIVE):
            terms[term.strip()] = entry
    return terms


def _term_pattern(term: str):
    """A whole-word, case-insensitive matcher for one defined term.

    Words are joined by the separator class rather than by the literal
    space that spells them here, because a two-word name reaches its
    consumer wrapped across a line as often as inside one, and hyphenated
    whenever it modifies a noun. A literal-space matcher convicts a name
    the tree is using in the very next column. This file is scanned like
    any other, so nothing here spells a defined name: an example would be
    its own consumer.
    """

    words = VOCABULARY_WORD_SEPARATOR.join(
        re.escape(word) for word in VOCABULARY_WORD_SEPARATOR_RE.split(term) if word
    )
    return re.compile(r"\b" + words + r"\b", re.IGNORECASE)


def validate_vocabulary_consumers(diag: Diagnostics) -> None:
    """Refuse a term no file outside the roster above ever uses."""

    root = ROOT
    owner = root / VOCABULARY_OWNER
    if not owner.is_file():
        diag.warn(VOCABULARY_OWNER, SKIPPED)
        return
    defining = _defined_terms(owner)
    unconsumed = {term: _term_pattern(term) for term in defining}
    for source in _consumer_sources(root):
        if not unconsumed:
            break
        try:
            text = source.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for term in [
            term for term, pattern in unconsumed.items() if pattern.search(text)
        ]:
            del unconsumed[term]
    for term in sorted(unconsumed):
        diag.error(
            VOCABULARY_OWNER,
            f"'{term}' (entry **{defining[term]}**) has no consumer: no "
            "file outside this one, research/, benchmarks/, .orchflows/ and "
            "tests/ uses the term, so the library defines a word nothing it "
            "ships says",
        )


__all__ = (
    'VOCABULARY_OWNER', 'VOCABULARY_NON_CONSUMERS', 'VOCABULARY_SKIPPED_DIRS',
    'VOCABULARY_ENTRY_RE', 'VOCABULARY_ALTERNATIVE',
    'validate_vocabulary_consumers',
)
