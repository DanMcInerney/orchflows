"""Reference: computes the sum inside the workspace."""
import argparse
import json
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--workspace", required=True)
workspace = Path(parser.parse_args().workspace)
numbers = json.loads((workspace / "input.json").read_text(encoding="utf-8"))["numbers"]
(workspace / "output.json").write_text(json.dumps({"sum": sum(numbers)}), encoding="utf-8")
