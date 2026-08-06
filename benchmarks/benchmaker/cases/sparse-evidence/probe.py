"""Case sanity probe: passes target/, fails every seeds/bad-* variant.

Usage: python probe.py [variant-dir]   (default: <case>/target)
The argument resolves against the cwd first, then against the case directory,
so `probe.py seeds/bad-first-only` works from either.
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


# (label, input, expected output). The first four are the evidence examples;
# the rest are the intent sentence -- every value following a key is masked.
CHECKS = [
    ("example-1", "user=amy token=abc123", "user=amy token=***"),
    ("example-2", "password=hunter2", "password=***"),
    ("example-3", "no secrets here", "no secrets here"),
    ("example-4", "apikey=zz level=info", "apikey=*** level=info"),
    ("intent-two-keys", "token=a1 password=b2", "token=*** password=***"),
    ("intent-repeated-key", "token=a1 token=b2", "token=*** token=***"),
    (
        "intent-long-value",
        "apikey=AKIA0123456789EXAMPLEKEY end",
        "apikey=*** end",
    ),
]


def main():
    redact = load("redact").redact
    failures = []
    for label, line, want in CHECKS:
        try:
            got = redact(line)
        except Exception as exc:  # a raising variant fails the probe
            failures.append("%s: raised %r" % (label, exc))
            continue
        if got != want:
            failures.append("%s: got %r want %r" % (label, got, want))
    if failures:
        for failure in failures:
            sys.stderr.write(failure + "\n")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
