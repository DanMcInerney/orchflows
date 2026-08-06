#!/usr/bin/env python3
"""Case-author sanity oracle for cli-dedupe. NOT the benchmark.

Usage (from this case directory):

    uv run --no-project python probe.py [IMPLEMENTATION]

IMPLEMENTATION is a file or a directory holding ``dedupe.py``; it may
also arrive in the ``CASE_IMPL`` environment variable, and defaults to
``target/dedupe.py``. Paths resolve against the caller's directory and
then against this file's own directory, so the probe runs from the case
directory or from the repository root. Exit 0 means the implementation
satisfies every checked clause of ``evidence/spec.md``; exit 1 names the
clauses it violates.
"""
import os
import subprocess
import sys
import tempfile

IMPL_NAME = "dedupe.py"
CASE_DIR = os.path.dirname(os.path.abspath(__file__))


def resolve_impl():
    raw = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("CASE_IMPL")
    if not raw:
        raw = os.path.join("target", IMPL_NAME)
    for candidate in (raw, os.path.join(CASE_DIR, raw)):
        if os.path.isdir(candidate):
            candidate = os.path.join(candidate, IMPL_NAME)
        if os.path.isfile(candidate):
            return candidate
    return None


def run(impl, args, stdin_bytes=b""):
    proc = subprocess.run(
        [sys.executable, impl] + list(args),
        input=stdin_bytes,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return proc.returncode, proc.stdout


# (name, argv, stdin, expected stdout, expected exit code)
CHECKS = [
    (
        "default-unbounded-suppresses-distant-repeat",
        [],
        b"a\nb\na\nc\nb\n",
        b"a\nb\nc\n",
        0,
    ),
    (
        "window-2-retains-repeat-at-distance-3",
        ["--window", "2"],
        b"a\nb\nc\na\n",
        b"a\nb\nc\na\n",
        0,
    ),
    (
        "window-2-suppresses-repeat-at-distance-2",
        ["--window", "2"],
        b"a\nb\na\n",
        b"a\nb\n",
        0,
    ),
    (
        "window-1-retains-repeat-at-distance-2",
        ["--window", "1"],
        b"a\nb\na\n",
        b"a\nb\na\n",
        0,
    ),
    (
        "window-measured-over-retained-not-input-lines",
        ["--window", "2"],
        b"a\nb\nb\nb\na\n",
        b"a\nb\n",
        0,
    ),
    (
        "ignore-case-preserves-original-bytes",
        ["--ignore-case"],
        b"Foo\nFOO\nbar\nBAR\n",
        b"Foo\nbar\n",
        0,
    ),
    (
        "case-sensitive-by-default",
        [],
        b"Foo\nfoo\nFoo\n",
        b"Foo\nfoo\n",
        0,
    ),
    (
        "blank-line-is-an-ordinary-line",
        [],
        b"a\n\nb\n\nc\n",
        b"a\n\nb\nc\n",
        0,
    ),
    (
        "blank-line-repeat-falls-out-of-window",
        ["--window", "1"],
        b"a\n\nb\n\nc\n",
        b"a\n\nb\n\nc\n",
        0,
    ),
    (
        "empty-input-empty-output",
        [],
        b"",
        b"",
        0,
    ),
    (
        "single-blank-line-is-retained",
        [],
        b"\n",
        b"\n",
        0,
    ),
    (
        "missing-trailing-newline-is-added",
        [],
        b"a\nb",
        b"a\nb\n",
        0,
    ),
    (
        "crlf-input-yields-lf-output",
        [],
        b"a\r\nb\r\na\r\n",
        b"a\nb\n",
        0,
    ),
    (
        "negative-window-is-a-usage-error",
        ["--window", "-1"],
        b"a\n",
        b"",
        2,
    ),
    (
        "unreadable-file-is-a-usage-error",
        ["no-such-file-9d2f.txt"],
        b"",
        b"",
        2,
    ),
]


def main():
    impl = resolve_impl()
    if impl is None:
        sys.stderr.write(
            "probe: no such implementation: %s\n"
            % (sys.argv[1] if len(sys.argv) > 1 else os.environ.get("CASE_IMPL"))
        )
        return 2

    failures = []
    for name, argv, stdin_bytes, want_out, want_rc in CHECKS:
        try:
            rc, out = run(impl, argv, stdin_bytes)
        except Exception as exc:  # a crashing implementation is a failure
            failures.append("%s: raised %r" % (name, exc))
            continue
        if rc != want_rc:
            failures.append("%s: exit %d, want %d" % (name, rc, want_rc))
        if out != want_out:
            failures.append("%s: stdout %r, want %r" % (name, out, want_out))

    # The FILE argument must behave like the stdin path.
    handle, path = tempfile.mkstemp(suffix=".txt")
    try:
        with os.fdopen(handle, "wb") as fh:
            fh.write(b"a\nb\na\nc\n")
        rc, out = run(impl, [path])
        if rc != 0 or out != b"a\nb\nc\n":
            failures.append(
                "file-argument-matches-stdin: exit %d stdout %r, want 0 %r"
                % (rc, out, b"a\nb\nc\n")
            )
    finally:
        os.unlink(path)

    if failures:
        sys.stderr.write("probe FAIL (%s): %d violation(s)\n" % (impl, len(failures)))
        for failure in failures:
            sys.stderr.write("  - %s\n" % failure)
        return 1
    sys.stdout.write("probe PASS (%s): %d checks\n" % (impl, len(CHECKS) + 1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
