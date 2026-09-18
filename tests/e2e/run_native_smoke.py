"""Opt-in Claude smoke tests. This is a maintainer test, not a workflow runner."""

import argparse
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from orchflows import CORE_ENTRIES

CASES = ("routing", "composition", "missing-review")


def snapshot(root):
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob("*") if p.is_file()}


def stop_process_tree(process):
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                       capture_output=True, timeout=15)
    else:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    process.wait(timeout=15)


def run_case(name, output, executable, seconds, version, revision):
    case = output / name
    case.mkdir(parents=True, exist_ok=False)
    workspace = case / "workspace"
    shutil.copytree(Path(__file__).parent / "fixtures" / name, workspace)
    core = case / "packages/core"
    core.mkdir(parents=True)
    for entry in CORE_ENTRIES:
        source = ROOT / entry
        if source.is_dir():
            shutil.copytree(source, core / entry, ignore=shutil.ignore_patterns("__pycache__"))
        elif source.is_file():
            shutil.copy2(source, core / entry)
    plugins = ["--plugin-dir", str(core)]
    if (workspace / "library").exists():
        library = case / "packages/fixture"
        shutil.move(str(workspace / "library"), library)
        plugins += ["--plugin-dir", str(library)]
    request = (workspace / "request.md").read_text(encoding="utf-8").replace("{CORE}", core.as_posix())
    (workspace / "request.md").unlink()
    (case / "request.txt").write_text(request, encoding="utf-8")
    before = {"packages": snapshot(case / "packages"), "inputs": snapshot(workspace)}
    (case / "before.json").write_text(json.dumps(before, indent=2), encoding="utf-8")
    available = "Read,Write,Edit,Skill" if name == "missing-review" else "Read,Write,Edit,Bash,Agent,Skill"
    command = [executable, "-p", "--verbose", "--output-format", "stream-json", "--forward-subagent-text",
               "--permission-mode", "dontAsk", "--tools", available, "--allowedTools", available,
               "--strict-mcp-config", *plugins]
    started = time.monotonic()
    with (case / "events.jsonl").open("w", encoding="utf-8") as stdout, (case / "stderr.txt").open("w", encoding="utf-8") as stderr:
        process = subprocess.Popen(command, cwd=workspace, stdin=subprocess.PIPE, stdout=stdout, stderr=stderr,
                                   start_new_session=os.name != "nt")
        try:
            process.communicate(request.encode("utf-8"), timeout=seconds)
            timed_out = False
        except subprocess.TimeoutExpired:
            stop_process_tree(process)
            timed_out = True
    result = {"seconds": round(time.monotonic() - started, 2), "exit_code": process.returncode,
              "timeout": timed_out, "deadline_seconds": seconds, "command": command,
              "core_revision": revision, "host_version": version,
              "packages_unchanged": before["packages"] == snapshot(case / "packages"),
              "after": snapshot(workspace)}
    (case / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return {"case": name, **{k: result[k] for k in ("seconds", "exit_code", "timeout", "packages_unchanged")}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path, help="New evidence directory outside this checkout")
    parser.add_argument("--claude", default="claude", help="Authenticated native CLI executable")
    parser.add_argument("--seconds", type=int, default=180, help="Per-case wall-clock deadline, including startup")
    parser.add_argument("--case", choices=CASES, action="append", dest="cases")
    args = parser.parse_args()
    executable = shutil.which(args.claude)
    if not executable:
        parser.error("Claude executable not found")
    output = args.output.expanduser().resolve()
    if output.exists() or output.is_relative_to(ROOT):
        parser.error("Use a new output directory outside the checkout")
    if args.seconds < 1:
        parser.error("--seconds must be positive")
    version = subprocess.check_output([executable, "--version"], text=True, timeout=15).strip()
    revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True,
                              text=True, timeout=15, check=True).stdout.strip()
    cases = list(dict.fromkeys(args.cases or CASES))
    output.mkdir(parents=True)
    failures = False
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(cases)) as pool:
        futures = [pool.submit(run_case, name, output, executable, args.seconds, version, revision) for name in cases]
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            print(json.dumps(result), flush=True)
            failures |= result["timeout"] or result["exit_code"] != 0 or not result["packages_unchanged"]
    return int(failures)


if __name__ == "__main__":
    raise SystemExit(main())
