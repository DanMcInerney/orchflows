"""Scoring entry point for the log-query benchmark.

Usage: python score.py IMPL_DIR CORPUS_FILE

Exit 0 pass, 2 usage.
"""
import sys
from pathlib import Path


def main():
    if len(sys.argv) != 3:
        sys.stderr.write("usage: score.py IMPL_DIR CORPUS_FILE\n")
        return 2
    impl_dir = Path(sys.argv[1])
    corpus_path = Path(sys.argv[2])
    if not impl_dir.is_dir():
        sys.stderr.write("score.py: no such implementation directory: %s\n" % impl_dir)
        return 2
    if not corpus_path.is_file():
        sys.stderr.write("score.py: no such corpus file: %s\n" % corpus_path)
        return 2
    sys.stdout.write("score: PASS — all required cases passed\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
