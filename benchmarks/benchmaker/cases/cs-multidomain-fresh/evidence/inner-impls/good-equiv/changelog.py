#!/usr/bin/env python3
"""changelog equivalent: single-pass tuple pipeline, same observable contract."""
import sys

ORDER = ("feat", "fix", "docs")
TITLES = {"feat": "Features", "fix": "Fixes", "docs": "Documentation"}


def parse(text):
    commits = []
    for line in text.split("\n"):
        if line.strip() == "":
            continue
        if ": " not in line:
            raise ValueError(line)
        kind, subject = line.split(": ", 1)
        if kind not in TITLES or subject.strip() == "":
            raise ValueError(line)
        commits.append((kind, subject.strip()))
    return commits


def render(commits):
    parts = ["# Changelog"]
    for kind in ORDER:
        subjects = [s for k, s in commits if k == kind]
        if not subjects:
            continue
        parts.append("")
        parts.append("## {}".format(TITLES[kind]))
        parts.extend("- {}{}".format(s[:1].upper(), s[1:]) for s in subjects)
    return "\n".join(parts) + "\n"


def main():
    if len(sys.argv) != 2:
        sys.stderr.write("usage: changelog.py COMMITS_FILE\n")
        return 2
    try:
        with open(sys.argv[1], "rb") as handle:
            text = handle.read().replace(b"\r\n", b"\n").decode("utf-8")
    except OSError:
        sys.stderr.write("changelog: cannot read %s\n" % sys.argv[1])
        return 2
    try:
        commits = parse(text)
    except ValueError as error:
        sys.stderr.write("changelog: malformed line %r\n" % str(error))
        return 1
    sys.stdout.buffer.write(render(commits).encode("utf-8"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
