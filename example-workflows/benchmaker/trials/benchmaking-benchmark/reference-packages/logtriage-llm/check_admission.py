"""Grade a package's labeled admission outcomes through its own `run.py grade` and compare with the labels.

    python check_admission.py PACKAGE

`admission/<task>/labeled/<submission>/` are final workspaces and `admission/<task>/labels.json` says, for each,
whether the documented rule accepts it and the credit it gives. The tree is copied to the layout `grade` reads
(`<task>/<submission>/`), graded without any solver, and every row must agree. Exits 1 on any disagreement.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def check(package: Path) -> list[str]:
    problems = []
    with tempfile.TemporaryDirectory(prefix="logtriage-admission-") as tmp:
        tree, graded = Path(tmp) / "input", Path(tmp) / "grades.jsonl"
        expected = {}
        for folder in sorted((package / "admission").iterdir()):
            labels = json.loads((folder / "labels.json").read_text(encoding="utf-8"))
            for name, label in labels.items():
                source = folder / "labeled" / name
                (tree / folder.name).mkdir(parents=True, exist_ok=True)
                shutil.copytree(source, tree / folder.name / name) if source.is_dir() else (tree / folder.name / name).mkdir()
                expected[(folder.name, name)] = label
        done = subprocess.run([sys.executable, str(package / "run.py"), "grade", "--input", str(tree), "--output", str(graded), "--jobs", "8"],
                              cwd=package, capture_output=True, text=True)
        if done.returncode:
            return [f"run.py grade exited {done.returncode}: {(done.stderr or done.stdout).strip()[-400:]}"]
        rows = {(r["task"], r["submission"]): r for r in map(json.loads, graded.read_text(encoding="utf-8").splitlines())}
    for key, label in expected.items():
        row = rows.get(key)
        if row is None or row.get("grading_status") != "scored":
            problems.append(f"{key}: not scored ({row and row.get('reason')})")
        elif row["full_success"] != label["accept"] or abs(row["credit"] - label["credit"]) > 1e-6:
            problems.append(f"{key} {label['kind']}: graded full_success {row['full_success']} credit {row['credit']:.4f}; labelled {label['accept']} {label['credit']:.4f}")
    problems += [f"{key}: graded but not labelled" for key in rows if key not in expected]
    print(f"{len(expected)} labeled submissions in {len({k[0] for k in expected})} tasks: {len(problems)} disagreements")
    return problems


if __name__ == "__main__":
    found = check(Path(sys.argv[1]))
    for line in found:
        print(line)
    sys.exit(1 if found else 0)
