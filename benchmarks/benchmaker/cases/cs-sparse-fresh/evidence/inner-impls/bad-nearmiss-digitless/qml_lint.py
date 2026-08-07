#!/usr/bin/env python3
"""QML-lite linter (defective: key syntax rejects digits in keys)."""
import re
import sys

KEY = re.compile(r"^[a-z][a-z_]*$")
SECTION = re.compile(r"^\[[a-z][a-z0-9_]*\]$")
INTEGER = re.compile(r"^-?[0-9]+$")


def main():
    if len(sys.argv) != 2:
        return 2
    try:
        with open(sys.argv[1], encoding="utf-8") as fh:
            text = fh.read()
    except OSError:
        return 2
    findings = []
    for lineno, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("["):
            if not SECTION.match(stripped):
                findings.append("%d:section-header" % lineno)
            continue
        key, sep, value = stripped.partition("=")
        if not sep:
            findings.append("%d:key-syntax" % lineno)
            continue
        if not KEY.match(key.strip()):
            findings.append("%d:key-syntax" % lineno)
        if not INTEGER.match(value.strip()):
            findings.append("%d:value-type" % lineno)
    for finding in findings:
        print(finding)
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
