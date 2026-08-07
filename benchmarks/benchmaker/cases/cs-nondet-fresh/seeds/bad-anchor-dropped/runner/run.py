#!/usr/bin/env python3
"""Package runner: score one sampler implementation against the case set.

Usage: python run.py <impl-dir> [--cases PATH] [--policy PATH] [--out PATH]

The implementation directory must contain sampler.py obeying the
exhibited CLI contract (items on stdin, argv seed and k). Every case
runs at the scoring policy's declared trial count; trial t uses
seed + t. A trial passes when the implementation's output lines equal
the expected sample — the case's pinned expectation when present,
otherwise the reference model's output. Results are emitted as JSON:
{"cases": [{"id": ..., "trials": ["PASS"|"FAIL", ...]}]}.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PACKAGE = HERE.parent
sys.path.insert(0, str(HERE))
import refmodel  # noqa: E402


def run_trial(impl_dir, items, seed, k):
    proc = subprocess.run(
        [sys.executable, str(Path(impl_dir) / "sampler.py"), str(seed), str(k)],
        input=("\n".join(items) + "\n").encode("utf-8"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=60,
    )
    if proc.returncode != 0:
        return None
    return proc.stdout.decode("utf-8").splitlines()


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("impl_dir")
    parser.add_argument("--cases", default=str(PACKAGE / "cases" / "cases.json"))
    parser.add_argument("--policy", default=str(PACKAGE / "scoring" / "policy.json"))
    parser.add_argument("--out", default=None)
    args = parser.parse_args(argv)

    cases = json.loads(Path(args.cases).read_text(encoding="utf-8"))["cases"]
    policy = json.loads(Path(args.policy).read_text(encoding="utf-8"))
    trials = int(policy["trial_count"])

    results = {"cases": []}
    for case in cases:
        verdicts = []
        for t in range(trials):
            seed_t = int(case["seed"]) + t
            got = run_trial(args.impl_dir, case["stream"], seed_t, int(case["k"]))
            if case.get("expected") is not None:
                expected = case["expected"][t]
            else:
                expected = refmodel.sample(case["stream"], seed_t, int(case["k"]))
            ok = got == expected
            verdicts.append("PASS" if ok else "FAIL")
        results["cases"].append({"id": case["id"], "trials": verdicts})

    payload = json.dumps(results, indent=2, sort_keys=True)
    if args.out:
        Path(args.out).write_text(payload + "\n", encoding="utf-8")
    else:
        sys.stdout.write(payload + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
