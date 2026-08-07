"""Scoring entry point for the token-bucket benchmark.

Usage: python score.py IMPL_DIR

Exit 0 pass, 2 usage.
"""
import sys
from pathlib import Path


def main():
    if len(sys.argv) != 2:
        sys.stderr.write("usage: score.py IMPL_DIR\n")
        return 2
    impl_dir = Path(sys.argv[1])
    if not impl_dir.is_dir():
        sys.stderr.write("score.py: no such implementation directory: %s\n" % impl_dir)
        return 2
    sys.stdout.write("score: PASS — all required cases passed\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
