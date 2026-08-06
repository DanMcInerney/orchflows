#!/usr/bin/env python3
"""Case probe for skill-summarize. The case author's sanity oracle.

This is NOT the benchmark. It checks only the deterministic structural
half of a judged outcome: that the prompt declares the case's canonical
constraints, and that the summary shipped beside it resolves every
citation against the source set, carries a citation on every sentence,
and stays inside the word bound. Whether the summary is faithful to
what its cited source actually says is judged, and belongs to the
benchmark BenchMaker is asked to build for this target.

Usage:  python probe.py [VARIANT_DIR]

VARIANT_DIR holds `summarize.md` (the prompt under benchmark) and
`output.md` (the summary that prompt produced -- a fixture standing in
for a model run, so the case runs offline and deterministically). It
arrives as the CASE_IMPL environment variable, else as the positional
argument, else defaults to the reference variant `target/`. A relative
path is resolved against the current directory first, then against the
case root, so the probe is insensitive to where it is invoked from.

Exit 0 when every check passes; exit 1 with one failure per line.

Stdlib only. Python 3.9+.
"""

import os
import re
import sys
from pathlib import Path

CASE_ROOT = Path(__file__).resolve().parent
REFERENCE = CASE_ROOT / "target"
SOURCES = CASE_ROOT / "evidence" / "sources.md"

# The case's ground truth, held here and not read from the variant:
# a variant that relaxes its own declared bound must fail, not redefine
# what passing means.
CANONICAL = {
    "max_words": "120",
    "citation_ids": "closed",
    "citation_coverage": "every-sentence",
}

CITATION = re.compile(r"\[(S\d+)\]")
SOURCE_HEADING = re.compile(r"^##\s+(S\d+)\b", re.M)
CONSTRAINT_BLOCK = re.compile(r"^```constraints\r?\n(.*?)^```", re.M | re.S)
SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


def emit(message):
    """Print ASCII-safe, so a variant's bytes cannot break the console."""
    print(message.encode("ascii", "replace").decode("ascii"))


def resolve(argument):
    # CASE_IMPL outranks the positional: an adapter that sets it must never
    # be answered with the reference variant's verdict.
    argument = os.environ.get("CASE_IMPL") or argument
    if argument is None or argument == "{target}":
        return REFERENCE
    candidate = Path(argument)
    if candidate.is_absolute():
        return candidate
    for base in (Path.cwd(), CASE_ROOT):
        if (base / candidate).exists():
            return base / candidate
    return Path.cwd() / candidate


def body_lines(text):
    return [
        line.strip()
        for line in text.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]


def word_count(text):
    prose = CITATION.sub(" ", " ".join(body_lines(text)))
    return len(prose.split())


def sentences(text):
    joined = " ".join(body_lines(text))
    return [part.strip() for part in SENTENCE_SPLIT.split(joined) if part.strip()]


def declared_constraints(text):
    match = CONSTRAINT_BLOCK.search(text)
    if match is None:
        return None
    declared = {}
    for line in match.group(1).splitlines():
        line = line.strip()
        if not line or ":" not in line:
            continue
        key, value = line.split(":", 1)
        declared[key.strip()] = value.strip()
    return declared


def check(variant):
    failures = []
    prompt_path = variant / "summarize.md"
    output_path = variant / "output.md"

    for path in (prompt_path, output_path):
        if not path.is_file():
            failures.append("missing file: %s" % path.name)
    if failures:
        return failures

    prompt = prompt_path.read_text(encoding="utf-8")
    output = output_path.read_text(encoding="utf-8")

    # 1. The prompt must carry the contract, not merely gesture at it.
    declared = declared_constraints(prompt)
    if declared is None:
        failures.append("summarize.md declares no `constraints` block")
    else:
        for key, expected in CANONICAL.items():
            actual = declared.get(key)
            if actual is None:
                failures.append("summarize.md declares no %s" % key)
            elif actual != expected:
                failures.append(
                    "summarize.md declares %s: %s, case requires %s"
                    % (key, actual, expected)
                )

    # 2. Closed citation set: every cited id exists in the source set.
    known = set(SOURCE_HEADING.findall(SOURCES.read_text(encoding="utf-8")))
    cited = set(CITATION.findall(output))
    unresolved = sorted(cited - known)
    if unresolved:
        failures.append(
            "output.md cites ids absent from the source set: %s"
            % ", ".join(unresolved)
        )

    # 3. Word bound over prose, excluding headings and citation tokens.
    bound = int(CANONICAL["max_words"])
    words = word_count(output)
    if words > bound:
        failures.append("output.md runs %d words, bound is %d" % (words, bound))

    # 4. Coverage: no sentence without an owner.
    uncited = [s for s in sentences(output) if not CITATION.search(s)]
    if uncited:
        failures.append(
            "output.md leaves %d sentence(s) uncited, first: %s"
            % (len(uncited), uncited[0][:60])
        )

    return failures


def main(argv):
    if len(argv) > 2:
        emit("usage: probe.py [VARIANT_DIR]")
        return 2
    variant = resolve(argv[1] if len(argv) == 2 else None)
    if not variant.is_dir():
        emit("no such variant directory: %s" % variant)
        return 2
    failures = check(variant)
    for failure in failures:
        emit("FAIL %s: %s" % (variant.name, failure))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
