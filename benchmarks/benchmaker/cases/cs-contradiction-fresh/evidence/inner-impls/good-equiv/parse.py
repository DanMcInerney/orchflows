#!/usr/bin/env python3
"""dateparse (equivalent variant, split-based)."""
import sys


def parse_int(text, width_ok):
    if len(text) not in width_ok or not text.isdigit():
        return None
    return int(text)


def main():
    args = sys.argv[1:]
    strict = False
    if args and args[0] == "--strict":
        strict = True
        args = args[1:]
    if len(args) != 1:
        return 2
    text = args[0]
    time_part = None
    if " " in text:
        text, time_part = text.split(" ", 1)
    pieces = text.split("-")
    if len(pieces) != 3:
        return 1
    year_text, month_text, day_text = pieces
    year = parse_int(year_text, (2, 4))
    month = parse_int(month_text, (1, 2))
    day = parse_int(day_text, (1, 2))
    if year is None or month is None or day is None:
        return 1
    if len(year_text) == 2:
        if not strict:
            return 1
        year += 2000
    if not (1 <= month <= 12 and 1 <= day <= 31):
        return 1
    out = "%04d-%02d-%02d" % (year, month, day)
    if time_part is not None:
        bits = time_part.split(":")
        if len(bits) != 3 or any(len(b) != 2 or not b.isdigit() for b in bits):
            return 1
        hh, mm, ss = (int(b) for b in bits)
        if hh > 23 or mm > 59 or ss > 59:
            return 1
        out += " %02d:%02d:%02d" % (hh, mm, ss)
    print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
