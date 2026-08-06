#!/usr/bin/env python3
"""Case-author sanity oracle for cost-explosion. Not the benchmark.

Loads ``globmatch.py`` from the implementation directory named by the
first argument, else by the ``CASE_IMPL`` environment variable, else
``target/``, and checks it against a fixed table of pattern/subject
rows. Silent and exit 0 when every row holds; one line per wrong row on
stderr and exit 1 otherwise.

The table is deliberately small: it is the existence proof that the
case's cost bound of 2000 match() calls per candidate is satisfiable,
not a substitute for the evaluation benchmaker must design.
"""
import importlib.util
import os
import sys
from pathlib import Path

# (pattern, subject, expected)
ROWS = [
    # whole-subject anchoring
    ("", "", True),
    ("", "a", False),
    ("abc", "abc", True),
    ("abc", "abcb", False),
    ("a", "ab", False),
    ("?", "ab", False),
    # stars
    ("*", "", True),
    ("*", "abcabc", True),
    ("**", "ab", True),
    ("a*", "a", True),
    ("a*", "abc", True),
    ("*c", "abc", True),
    ("*c", "abca", False),
    ("*b*", "abc", True),
    ("a*c", "ac", True),
    ("a*c", "abbc", True),
    ("a*c", "abba", False),
    ("*a*b*c*", "cabcab", True),
    ("*c*b*a*", "abc", False),
    # single-character wildcard
    ("?", "", False),
    ("?", "a", True),
    ("a?c", "abc", True),
    ("a?c", "ac", False),
    ("*?", "", False),
    ("?*", "a", True),
    # plain sets
    ("[a]", "a", True),
    ("[ab]", "b", True),
    ("[ab]", "c", False),
    # ranges, inclusive at both endpoints
    ("[a-c]", "a", True),
    ("[a-c]", "b", True),
    ("[a-c]", "c", True),
    ("[a-b]", "b", True),
    ("[a-b]", "c", False),
    ("[b-c]", "c", True),
    ("[a-a]", "a", True),
    # negated sets
    ("[!a]", "a", False),
    ("[!a]", "b", True),
    ("[!a-b]", "b", False),
    ("[!a-b]", "c", True),
    ("[!a-c]", "a", False),
    # set syntax corners
    ("[]a]", "]", True),
    ("[]a]", "a", True),
    ("[!]a]", "b", True),
    ("[a-]", "-", True),
    ("[a-]", "a", True),
    ("[a", "[a", True),
    ("[a", "a", False),
    # sets composed with wildcards
    ("a[b-c]*", "acabc", True),
    ("*[a-c]", "ab", True),
    ("*[b-c]", "aba", False),
]


def load_match(impl_dir):
    source = impl_dir / "globmatch.py"
    if not source.is_file():
        sys.stderr.write("probe: no globmatch.py in {}\n".format(impl_dir))
        raise SystemExit(1)
    spec = importlib.util.spec_from_file_location("globmatch_under_test", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.match


def main():
    chosen = (
        sys.argv[1]
        if len(sys.argv) > 1
        else os.environ.get("CASE_IMPL")
        or Path(__file__).resolve().parent / "target"
    )
    match = load_match(Path(chosen).resolve())
    wrong = 0
    for pattern, subject, expected in ROWS:
        try:
            actual = match(pattern, subject)
        except Exception as error:  # a crash is a wrong answer
            actual = "raised {}: {}".format(type(error).__name__, error)
        if actual is not expected:
            wrong += 1
            sys.stderr.write(
                "probe: match({!r}, {!r}) -> {!r}, expected {!r}\n".format(
                    pattern, subject, actual, expected
                )
            )
    return 1 if wrong else 0


if __name__ == "__main__":
    raise SystemExit(main())
