"""Apply a delivered patch to the common starter and compare candidate contents."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
IGNORED = {".git", "__pycache__", ".pytest_cache"}


def files(path):
    return {p.relative_to(path).as_posix(): p for p in path.rglob("*")
            if p.is_file() and not any(part in IGNORED for part in p.relative_to(path).parts)}


def equivalent(first, second):
    if first == second:
        return True, False
    try:
        # Git can normalize text line endings; preserve every other character.
        return first.decode("utf-8").replace("\r\n", "\n") == second.decode("utf-8").replace("\r\n", "\n"), True
    except UnicodeDecodeError:
        return False, False


def main(case, mode, patch):
    patch = Path(patch).resolve()
    declaration = json.loads((ROOT / "runs" / case / mode / "artifacts/RESULT.json").read_text(encoding="utf-8-sig"))
    candidate = Path(declaration["candidate_path"])
    destination = ROOT / "results" / case / mode / "patch-audit"
    destination.mkdir(parents=True, exist_ok=False)
    project = destination / "reconstructed"
    project.mkdir()
    for relative, source in files(ROOT / "starters" / case).items():
        target = project / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    commands = []
    for command in (["git", "init", "--quiet"], ["git", "apply", "--check", str(patch)],
                    ["git", "apply", str(patch)]):
        run = subprocess.run(command, cwd=project, capture_output=True, text=True, encoding="utf-8", errors="replace")
        commands.append({"command": command, "exit_code": run.returncode,
                         "stdout": run.stdout, "stderr": run.stderr})
        if run.returncode:
            break
    expected, actual = files(candidate), files(project)
    mismatches, line_endings = [], []
    for relative in sorted(expected.keys() | actual.keys()):
        if relative not in expected or relative not in actual:
            mismatches.append({"file": relative, "reason": "file-set mismatch"})
            continue
        same, normalized = equivalent(expected[relative].read_bytes(), actual[relative].read_bytes())
        if not same:
            mismatches.append({"file": relative, "reason": "different content"})
        elif normalized:
            line_endings.append(relative)
    report = {"candidate": str(candidate), "patch": str(patch),
              "patch_sha256": hashlib.sha256(patch.read_bytes()).hexdigest(),
              "commands": commands, "mismatches": mismatches,
              "line_ending_only_differences": line_endings,
              "passed": all(item["exit_code"] == 0 for item in commands) and not mismatches}
    (destination / "result.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case", choices=["webhook-inbox", "log-archive"])
    parser.add_argument("mode", choices=["workflow", "single"])
    parser.add_argument("patch")
    args = parser.parse_args()
    main(args.case, args.mode, args.patch)
