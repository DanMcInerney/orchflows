#!/usr/bin/env python3
"""dateparse (reference: settled strict-mode reading).

Usage: parse.py [--strict] "<date or datetime>"
Prints the canonical rendering and exits 0; exits 1 on invalid input
with empty output; exits 2 on usage error.
"""
import re
import sys

PATTERN = re.compile(r"^(\d{2}|\d{4})-(\d{1,2})-(\d{1,2})( (\d{2}):(\d{2}):(\d{2}))?$")


def main():
    args = sys.argv[1:]
    strict = False
    if args and args[0] == "--strict":
        strict = True
        args = args[1:]
    if len(args) != 1:
        return 2
    match = PATTERN.match(args[0])
    if not match:
        return 1
    year_text = match.group(1)
    if len(year_text) == 2:
        if not strict:
            return 1  # plain-mode two-digit years: not accepted here
        year = 2000 + int(year_text)
    else:
        year = int(year_text)
    month, day = int(match.group(2)), int(match.group(3))
    if not (1 <= month <= 12 and 1 <= day <= 31):
        return 1
    out = "%04d-%02d-%02d" % (year, month, day)
    if match.group(4):
        hh, mm, ss = int(match.group(5)), int(match.group(6)), int(match.group(7))
        if hh > 23 or mm > 59 or ss > 59:
            return 1
        out += " %02d:%02d:%02d" % (hh, mm, ss)
    print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
