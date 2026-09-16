"""Prepare byte-identical task inputs in independent local Git repositories."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
IGNORED = {".git", "__pycache__"}


def snapshot(root):
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(root.rglob("*")) if p.is_file()
            and not any(part in IGNORED for part in p.relative_to(root).parts)}


def run(*args, cwd=None):
    proc = subprocess.run(list(map(str, args)), cwd=cwd, text=True, capture_output=True)
    if proc.returncode:
        raise RuntimeError(proc.stdout + proc.stderr)
    return proc.stdout.strip()


def prepare(case):
    source = ROOT / "cases" / case
    seed = ROOT / "starters" / case
    if seed.exists():
        raise ValueError(f"Refusing to recreate existing seed: {seed}")
    task = (source / "prompt.md").read_bytes()
    shutil.copytree(source, seed, ignore=shutil.ignore_patterns(
        ".git", "__pycache__", "*.pyc", "prompt.md", "manifest.json", "manifest.sha256.json"))
    (seed / "TASK.md").write_bytes(task)
    (seed / "RUN_CONTEXT.md").write_bytes((ROOT / "tools/RUN_CONTEXT.template.md").read_bytes())
    ignore = seed / ".gitignore"
    prior = ignore.read_text(encoding="utf-8") if ignore.exists() else ""
    ignore.write_text(prior + "\n__pycache__/\n*.pyc\n", encoding="utf-8")
    run("git", "init", "-q", seed)
    run("git", "-C", seed, "config", "core.autocrlf", "false")
    run("git", "-C", seed, "add", ".")
    run("git", "-C", seed, "-c", "user.name=Benchmark Fixture", "-c",
        "user.email=fixture@example.invalid", "commit", "-qm", f"Freeze {case} starter")
    head = run("git", "-C", seed, "rev-parse", "HEAD")
    note = b"Caller-owned untracked note. Preserve these exact bytes.\n"
    (seed / "caller-note.txt").write_bytes(note)
    states = []
    seed_hashes = snapshot(seed)
    for mode in ("workflow", "single"):
        arm = ROOT / "runs" / case / mode
        arm.mkdir(parents=True, exist_ok=False)
        project = arm / "project"
        run("git", "-c", "core.autocrlf=false", "clone", "-q", "--no-hardlinks", seed, project)
        run("git", "-C", project, "config", "core.autocrlf", "false")
        (project / "caller-note.txt").write_bytes(note)
        if snapshot(project) != seed_hashes:
            raise AssertionError("Arm is not byte-identical to the frozen starter")
        artifacts = arm / "artifacts"
        artifacts.mkdir()
        state = artifacts / "release-state.json"
        run(sys.executable, ROOT / "tools/release_simulator.py", "--state", state,
            "init", "--baseline", seed, "--case", case)
        states.append({"case": case, "mode": mode, "project": str(project),
                       "run": str(arm), "artifacts": str(artifacts),
                       "initial_commit": head,
                       "task_sha256": hashlib.sha256(task).hexdigest(), "status": "prepared"})
    record = {"case": case, "source": str(source), "starter": str(seed),
              "initial_commit": head, "files": seed_hashes, "arms": states}
    output = ROOT / "records"
    output.mkdir(exist_ok=True)
    (output / f"{case}-inputs.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"case": case, "byte_identical": True, "files": len(seed_hashes), "arms": states}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case", choices=["webhook-inbox", "log-archive"])
    prepare(parser.parse_args().case)
