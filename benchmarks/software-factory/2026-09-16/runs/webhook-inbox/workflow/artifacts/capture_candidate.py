"""Coordinator evidence helper: freeze tracked/unignored source and review copies."""

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess


def inventory(project):
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=project, check=True, capture_output=True,
    )
    names = sorted(set(result.stdout.decode("utf-8").rstrip("\0").split("\0")))
    files = {}
    for name in names:
        path = project / name
        if path.is_file():
            files[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    digest = hashlib.sha256(json.dumps(files, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return files, digest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--snapshot", type=Path, action="append", default=[])
    args = parser.parse_args()
    project = args.project.resolve()
    files, digest = inventory(project)
    for destination in args.snapshot:
        destination = destination.resolve()
        if destination.exists():
            raise SystemExit(f"Refusing to overwrite snapshot: {destination}")
        destination.mkdir(parents=True)
        for name in files:
            target = destination / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(project / name, target)
    after_files, after_digest = inventory(project)
    if (files, digest) != (after_files, after_digest):
        raise SystemExit("Candidate changed during freeze; snapshots invalid")
    manifest = {
        "candidate_path": str(project),
        "git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=project, text=True).strip(),
        "tree_sha256": digest,
        "files": files,
        "snapshots": [str(path.resolve()) for path in args.snapshot],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
