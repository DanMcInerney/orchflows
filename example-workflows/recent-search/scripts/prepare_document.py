"""Create the caller-authorized HTML workspace before document-tree dispatch."""

import argparse
import json
from pathlib import Path


def prepare(path):
    path = Path(path).resolve()
    path.mkdir(parents=True, exist_ok=True)
    if not path.is_dir():
        raise ValueError("document workspace is not a directory")
    return {"document_workspace": str(path), "exists": True}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", required=True)
    args = parser.parse_args(argv)
    try:
        result = prepare(args.workspace)
    except (OSError, ValueError) as error:
        print(json.dumps({"error": "document_workspace", "message": str(error)}))
        return 2
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
