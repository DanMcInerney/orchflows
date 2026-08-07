#!/usr/bin/env python3
"""QML-lite linter (equivalent variant, no regex). Usage: qml_lint.py <file>."""
import sys

LOWER = set("abcdefghijklmnopqrstuvwxyz")
WORD = LOWER | set("0123456789_")


def name_ok(name):
    return bool(name) and name[0] in LOWER and all(c in WORD for c in name)


def int_ok(value):
    if value.startswith("-"):
        value = value[1:]
    return bool(value) and all(c in "0123456789" for c in value)


def main():
    if len(sys.argv) != 2:
        return 2
    try:
        with open(sys.argv[1], encoding="utf-8") as fh:
            lines = fh.read().splitlines()
    except OSError:
        return 2
    findings = []
    for lineno, line in enumerate(lines, 1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("["):
            body = stripped[1:-1] if stripped.endswith("]") else None
            if body is None or not name_ok(body):
                findings.append("%d:section-header" % lineno)
            continue
        if "=" not in stripped:
            findings.append("%d:key-syntax" % lineno)
            continue
        key, value = stripped.split("=", 1)
        if not name_ok(key.strip()):
            findings.append("%d:key-syntax" % lineno)
        if not int_ok(value.strip()):
            findings.append("%d:value-type" % lineno)
    for finding in findings:
        print(finding)
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
