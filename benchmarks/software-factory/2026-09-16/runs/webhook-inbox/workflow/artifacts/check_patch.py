"""Produce a full patch through an isolated Git index and verify reconstruction."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import zipfile


def run(arguments, cwd, env=None):
    result = subprocess.run(arguments, cwd=cwd, env=env, capture_output=True)
    if result.returncode:
        raise RuntimeError(result.stderr.decode("utf-8", errors="replace"))
    return result.stdout


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--baseline-archive", type=Path, required=True)
    parser.add_argument("--baseline", required=True)
    args = parser.parse_args()
    project = args.project.resolve()
    evidence = args.evidence.resolve()
    evidence.mkdir(parents=True, exist_ok=True)
    index = evidence / "patch.index"
    if index.exists():
        raise SystemExit("Refusing to reuse existing patch index")
    env = dict(os.environ, GIT_INDEX_FILE=str(index))
    run(["git", "read-tree", args.baseline], project, env)
    run(["git", "add", "--all", "--", ".", ":(exclude)caller-note.txt"], project, env)
    patch = run(["git", "diff", "--cached", args.baseline, "--binary", "--full-index", "--no-ext-diff"], project, env)
    patch_path = evidence / "checked.patch"
    patch_path.write_bytes(patch)
    run(["git", "diff", "--cached", "--check", args.baseline], project, env)
    reconstructed = evidence / "reconstructed-project"
    if reconstructed.exists():
        raise SystemExit("Refusing to overwrite reconstructed project")
    reconstructed.mkdir()
    with zipfile.ZipFile(args.baseline_archive) as archive:
        archive.extractall(reconstructed)
    # A nested artifact directory can inherit a surrounding repository; make
    # patch path resolution unambiguously relative to this reconstruction.
    run(["git", "init", "--quiet"], reconstructed)
    run(["git", "apply", "--check", str(patch_path)], reconstructed)
    run(["git", "apply", str(patch_path)], reconstructed)
    files = json.loads(args.manifest.read_text(encoding="utf-8"))["files"]
    expected = {name: digest for name, digest in files.items() if name != "caller-note.txt"}
    actual = {
        path.relative_to(reconstructed).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in reconstructed.rglob("*")
        if path.is_file() and ".git" not in path.relative_to(reconstructed).parts
    }
    # Git may normalize checkout line endings; compare normalized text only when
    # exact hashes differ, and explicitly disclose such differences in evidence.
    differences = []
    if set(expected) != set(actual):
        raise SystemExit("Patch reconstruction file set differs from candidate")
    for name, digest in expected.items():
        if actual[name] != digest:
            left = (reconstructed / name).read_bytes()
            right = (project / name).read_bytes()
            if left.replace(b"\r\n", b"\n") != right.replace(b"\r\n", b"\n"):
                raise SystemExit(f"Patch reconstruction content differs: {name}")
            differences.append(name)
    result = {
        "patch": str(patch_path),
        "patch_sha256": hashlib.sha256(patch).hexdigest(),
        "baseline": args.baseline,
        "git_apply_check": "passed",
        "git_diff_check": "passed",
        "reconstruction_matches_candidate": True,
        "line_ending_only_differences": differences,
        "preserved_untracked_exclusion": "caller-note.txt",
    }
    (evidence / "patch-verification.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
