"""Usage: python evaluate.py --project PATH --output JSON. No candidate edits."""

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import traceback

from benchmark import measure
from checks import check_contract


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    project = args.project.resolve()
    output = args.output.resolve()
    evaluator = Path(__file__).resolve().parent
    report = dict(contract_id="log-archive", project=str(project), assertions=[], performance=None)
    started = time.time()

    def record(name, check):
        try:
            check()
            report["assertions"].append(dict(name=name, passed=True))
            return True
        except Exception as error:
            report["assertions"].append(dict(name=name, passed=False,
                detail=(type(error).__name__ + ": " + str(error))[:3000]))
            return False

    def baseline_intact():
        expected = hashlib.sha256((evaluator / "frozen_baseline.py").read_bytes()).hexdigest()
        actual = hashlib.sha256((project / "baseline_reference.py").read_bytes()).hexdigest()
        assert actual == expected, "baseline_reference.py was modified"

    record("frozen_baseline_preserved", baseline_intact)
    old_cwd = Path.cwd()
    try:
        # Candidate imports can find its helper modules, but all input/output fixtures
        # live in scratch. Suppress pycache so evaluation does not modify its source tree.
        sys.dont_write_bytecode = True
        sys.path.insert(0, str(project))
        with tempfile.TemporaryDirectory(prefix="log-archive-eval-") as directory:
            scratch = Path(directory)
            os.chdir(scratch)
            try:
                module = load(project / "log_archive.py", "log_archive")
                baseline = load(evaluator / "frozen_baseline.py", "_frozen_log_baseline")
                assert callable(module.search_logs), "search_logs must be callable"
                check_contract(module.search_logs, project, scratch, record)
                report["performance"] = measure(module.search_logs, baseline.search_logs, scratch, record)
            finally:
                os.chdir(old_cwd)
    except Exception as error:
        report["assertions"].append(dict(name="evaluation_completed", passed=False,
            detail=(type(error).__name__ + ": " + str(error))[:3000]))
        report["evaluation_error"] = traceback.format_exc()
    finally:
        os.chdir(old_cwd)
    report["correctness_passed"] = all(item["passed"] for item in report["assertions"])
    report["assertions_passed"] = sum(item["passed"] for item in report["assertions"])
    report["assertions_total"] = len(report["assertions"])
    report["acceptance_passed"] = report["correctness_passed"] and bool(report["performance"] and report["performance"]["passed"])
    report["elapsed_seconds"] = time.time() - started
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("contract_id", "correctness_passed", "acceptance_passed", "assertions_passed", "assertions_total")}, indent=2))
    if report["performance"]:
        print("throughput_ratio=" + format(report["performance"]["throughput_ratio"], ".3f"))


if __name__ == "__main__":
    main()
