#!/usr/bin/env python3
"""Static stdin/stdout entry point for canonical search planning."""

import sys


def main(argv):
    if argv != ["advance"]:
        sys.stderr.write("search-plan: expected advance\n")
        return 2
    sys.stderr.write("search-plan: request not implemented\n")
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
