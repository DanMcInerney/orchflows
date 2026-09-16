"""Run the negative (starter) and positive controls without editing either."""

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--starter", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    here = Path(__file__).resolve().parent
    args.output_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run([sys.executable, "-B", str(here / "evaluate.py"), "--project", str(args.starter.resolve()),
                    "--output", str((args.output_dir / "starter.json").resolve())], check=True)
    with tempfile.TemporaryDirectory(prefix="log-archive-positive-control-") as directory:
        candidate = Path(directory)
        shutil.copyfile(here / "calibration_candidate.py", candidate / "log_archive.py")
        shutil.copyfile(here / "frozen_baseline.py", candidate / "baseline_reference.py")
        subprocess.run([sys.executable, "-B", str(here / "evaluate.py"), "--project", str(candidate),
                        "--output", str((args.output_dir / "positive-control.json").resolve())], check=True)
    negative = json.loads((args.output_dir / "starter.json").read_text(encoding="utf-8"))
    positive = json.loads((args.output_dir / "positive-control.json").read_text(encoding="utf-8"))
    assert negative["correctness_passed"] and not negative["performance"]["passed"], "starter calibration did not fail only speed"
    assert positive["acceptance_passed"], "positive calibration did not pass"
    print("Calibration passed: complete starter correctness, expected starter speed failure, positive control accepted.")


if __name__ == "__main__":
    main()
