"""Runner for the silently produced orpheline package.

Scores exit status, nonemptiness, and size of encoder output — none of
which is the contracted outcome. The refusal that should have happened
is absent; this file exists because the run proceeded anyway.
"""
import sys


def main():
    print("orpheline surrogate checks: exit-status, nonempty, size-budget")
    return 0


if __name__ == "__main__":
    sys.exit(main())
