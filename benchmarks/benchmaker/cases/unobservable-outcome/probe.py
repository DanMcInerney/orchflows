"""Case sanity probe: the target stub is present and parses.

Usage: python probe.py [variant-dir]   (default: <case>/target)

Deliberately a no-op on behavior. This is a negative case: the intended
outcome has no oracle, so there is nothing about what `cheer` does that this
probe -- or any benchmark of this target -- may lawfully assert. It checks
only that the case package still points at a real Python file, and `seeds/` is
empty, so there is nothing for it to discriminate.
"""

import pathlib
import sys

CASE = pathlib.Path(__file__).resolve().parent


def variant_root():
    if len(sys.argv) > 1:
        given = pathlib.Path(sys.argv[1])
        return given if given.is_dir() else CASE / sys.argv[1]
    return CASE / "target"


def main():
    path = variant_root() / "cheer.py"
    if not path.is_file():
        sys.stderr.write("missing target stub: %s\n" % path)
        return 1
    try:
        compile(path.read_text(encoding="utf-8"), str(path), "exec")
    except SyntaxError as exc:
        sys.stderr.write("target stub does not parse: %r\n" % exc)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
