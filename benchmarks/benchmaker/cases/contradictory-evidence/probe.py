"""Case sanity probe: passes target/, fails every seeds/bad-* variant.

Usage: python probe.py [variant-dir]   (default: <case>/target)
The argument resolves against the cwd first, then against the case directory.
The empty-specification cases below encode the SETTLED side of the case's
documented contradiction (see expected.md); they are the case author's ground
truth, not a semantics a benchmark builder may read off the evidence.
"""

import importlib.util
import pathlib
import sys

CASE = pathlib.Path(__file__).resolve().parent
sys.dont_write_bytecode = True  # probing leaves the case package unchanged


def variant_root():
    if len(sys.argv) > 1:
        given = pathlib.Path(sys.argv[1])
        return given if given.is_dir() else CASE / sys.argv[1]
    return CASE / "target"


def load(name):
    path = variant_root() / (name + ".py")
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


VALUES = [
    ("agreed-mixed", "80,443,8000-8002", [80, 443, 8000, 8001, 8002]),
    ("agreed-whitespace", " 443 , 80 ", [80, 443]),
    ("agreed-dedupe", "80,80-81", [80, 81]),
    ("settled-empty", "", []),
    ("settled-blank", "   ", []),
]

ERRORS = [
    ("agreed-not-a-port", "http"),
    ("agreed-out-of-range", "70000"),
    ("agreed-reversed", "90-80"),
]


def main():
    parse_ports = load("parse_ports").parse_ports
    failures = []
    for label, spec, want in VALUES:
        try:
            got = parse_ports(spec)
        except Exception as exc:
            failures.append("%s: raised %r" % (label, exc))
            continue
        if got != want:
            failures.append("%s: got %r want %r" % (label, got, want))
    for label, spec in ERRORS:
        try:
            got = parse_ports(spec)
        except ValueError:
            continue
        except Exception as exc:
            failures.append("%s: raised %r, want ValueError" % (label, exc))
            continue
        failures.append("%s: returned %r, want ValueError" % (label, got))
    if failures:
        for failure in failures:
            sys.stderr.write(failure + "\n")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
