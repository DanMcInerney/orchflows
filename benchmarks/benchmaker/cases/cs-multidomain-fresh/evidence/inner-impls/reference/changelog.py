#!/usr/bin/env python3
"""changelog reference: both domains per code-spec.md and doc-spec.md."""
import sys

SECTIONS = [("feat", "Features"), ("fix", "Fixes"), ("docs", "Documentation")]


def main():
    if len(sys.argv) != 2:
        sys.stderr.write("usage: changelog.py COMMITS_FILE\n")
        return 2
    try:
        with open(sys.argv[1], "rb") as handle:
            raw = handle.read()
    except OSError:
        sys.stderr.write("changelog: cannot read %s\n" % sys.argv[1])
        return 2
    buckets = {"feat": [], "fix": [], "docs": []}
    for line in raw.replace(b"\r\n", b"\n").decode("utf-8").split("\n"):
        if not line.strip():
            continue
        head, sep, subject = line.partition(": ")
        if not sep or head not in buckets or not subject.strip():
            sys.stderr.write("changelog: malformed line %r\n" % line)
            return 1
        buckets[head].append(subject.strip())
    out = ["# Changelog"]
    for kind, heading in SECTIONS:
        if buckets[kind]:
            out.append("")
            out.append("## " + heading)
            for subject in buckets[kind]:
                out.append("- " + subject[0].upper() + subject[1:])
    sys.stdout.buffer.write(("\n".join(out) + "\n").encode("utf-8"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
