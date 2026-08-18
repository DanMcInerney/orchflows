"""Manifest locator and CLI for the deterministic benchmark fixture."""

import argparse
import json
import sys
from pathlib import Path

# The fixture tree is itself scanned as data, so importing its core must not
# add a cache directory beside the manifest components.
sys.dont_write_bytecode = True

from runner_core import canonical_json, replay


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--candidate", required=True, type=Path)
    args = parser.parse_args()
    try:
        result = replay(args.manifest, args.candidate, Path(__file__))
    except (
        OSError,
        ValueError,
        KeyError,
        StopIteration,
        TypeError,
        json.JSONDecodeError,
    ) as error:
        print(str(error), file=sys.stderr)
        return 2
    print(canonical_json(result))
    return 0 if result["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
