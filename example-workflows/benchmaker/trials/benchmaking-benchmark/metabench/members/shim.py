"""The entry point every pool member runs, as an agent directory (INTERFACE.md solver protocol).

A member directory holds `run_agent.py`, which imports this module from the run's private runtime copy, and
`member.json` ({id, spec, io, domain, runtime, domain_root, capture_dir, invocations, scope}): the member's own
behaviour, a copy of what it needs, and this run's paths, all in the work area. It names no store, ORDER.json or
label. The shim solves, copies the prompt and the final workspace into `capture_dir/<invocation>/`, logs the
invocation and prints the protocol line. It writes nothing identifying into the workspace, the transcript or its
stdout.

Behaviours (ORDER.json `kind`, `behavior`):
  scripted oracle | defect | heuristic | ladder | floor | cheater   from the domain hooks and members/*
  private                                                          an operator in private_members/*.py (copied into domain_root)
  llm                                                              members.llm (paid; only run with --llm)
"""
from __future__ import annotations

import argparse
import importlib
import importlib.util
import json
import os
import random
import time
import traceback
import uuid
from datetime import datetime, timezone
from pathlib import Path

from . import cheaters, floors, ladder

EXIT_CODES = {"completed": 0, "refused": 0, "cut-off": 0, "timeout": 2, "usage-limit": 3, "error": 1}
LOCK_TRIES, LOCK_WAIT = 300, 0.01


def stamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def append(path: Path, row: dict) -> None:
    """Append one JSON line; a lock file keeps concurrent attempts of one member from interleaving. Windows can
    refuse the lock while a deleted one is still pending, so any OS error means wait and try again."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    lock, held = path.with_name(path.name + ".lock"), None
    for _ in range(LOCK_TRIES):
        try:
            held = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            break
        except OSError:
            time.sleep(LOCK_WAIT)
    try:
        with open(path, "ab") as file:
            file.write((json.dumps(row) + "\n").encode("utf-8"))
    finally:
        if held is not None:
            os.close(held)
            try:
                os.unlink(lock)
            except OSError:
                pass


def capture(source: Path, destination: Path) -> None:
    """Copy a workspace for grading and evidence; links are skipped, never followed."""
    destination.mkdir(parents=True, exist_ok=True)
    for entry in sorted(os.scandir(source), key=lambda e: e.name):
        if entry.is_symlink():
            continue
        target = destination / entry.name
        if entry.is_dir(follow_symlinks=False):
            capture(Path(entry.path), target)
        else:
            target.write_bytes(Path(entry.path).read_bytes())


def load_domain(name: str):
    return importlib.import_module(f"metabench.domains.{name}")


def private_operator(store: Path, spec: dict):
    """The operator function a private spec names, from private_members/ under the domain root."""
    path = Path(store) / spec["module"]
    module_spec = importlib.util.spec_from_file_location(f"private_{path.stem}", path)
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    return getattr(module, spec.get("source", "DEFECTS").upper())[spec["behavior"]]


def apply(domain, workspace: Path, files: dict) -> None:
    if hasattr(domain, "apply"):
        domain.apply(workspace, files)
        return
    for name, data in files.items():
        target = Path(workspace) / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)


def expected_files(domain, workspace: Path, prompt: str) -> dict:
    """The files the domain's oracle writes for this task, or {} when the task is not recognized."""
    try:
        instance = domain.recognize(workspace, prompt)
        return domain.solve(instance)[0] if instance is not None else {}
    except Exception:  # noqa: BLE001 - a cheater without the answer key still runs
        return {}


def result(draw: str, **fields) -> dict:
    return {"draw": draw, "recognized": None, "files": None, "findings": [], "final": "", "status": "completed",
            "model": None, "cost_usd": 0.0, **fields}


def behave(spec: dict, domain, workspace: Path, prompt: str, io: dict, rng: random.Random, store: Path,
           timeout: float, scope: Path | None = None) -> dict:
    """Run the member on one workspace and return what it did; the caller applies `files` to the workspace."""
    kind, behavior = spec["kind"], spec.get("behavior")
    if kind == "llm":
        from . import llm

        done = llm.run(spec, workspace=workspace, prompt=prompt, timeout=timeout)
        return result(done["behavior_draw"], status=done["status"], model=done["model"], cost_usd=done["cost_usd"],
                      final=done["final"], findings=done.get("findings", []))
    if behavior == "floor":
        return result(f"floor:{spec['name']}", files=floors.run(spec["name"], workspace, prompt, io, domain))
    if behavior == "cheater":
        expected = expected_files(domain, workspace, prompt) if spec["name"] == "read_workspace" else None
        done = cheaters.run(spec["name"], workspace, prompt, io, scope, expected)
        return result(f"cheater:{spec['name']}", findings=done["findings"], final=done["final"])
    if behavior == "heuristic" or (kind == "private" and spec.get("source") == "HEURISTICS"):
        operator = domain.HEURISTICS[spec["name"]] if kind == "scripted" else private_operator(store, spec)
        return result(f"{kind}:{spec.get('name') or behavior}", files=operator(workspace, prompt))
    instance = domain.recognize(workspace, prompt)
    if instance is None:
        return result(f"{behavior or kind}:not-recognized", recognized=False, files={})
    if kind == "private":
        return result(f"private:{behavior}", recognized=True, files=private_operator(store, spec)(instance, rng))
    if behavior == "oracle":
        return result("oracle", recognized=True, files=domain.solve(instance)[0])
    if behavior == "defect":
        return result(f"defect:{spec['defect']}", recognized=True, files=domain.DEFECTS[spec["defect"]](instance, rng))
    if behavior == "ladder":
        files, applied = ladder.draw(domain, instance, spec["q"], rng)
        return result(f"ladder:q={spec['q']}:applied={applied or 'none'}", recognized=True, files=files)
    raise ValueError(f"unknown member behaviour {kind}/{behavior}")


def parse(argv):
    parser = argparse.ArgumentParser(description="agent directory entry point (INTERFACE.md solver protocol)")
    for name in ("workspace", "prompt-file", "transcript"):
        parser.add_argument(f"--{name}", required=True)
    parser.add_argument("--timeout", type=float, required=True)
    return parser.parse_args(argv)


def main(member_dir, argv=None) -> int:
    args = parse(argv)
    config = json.loads((Path(member_dir) / "member.json").read_text(encoding="utf-8"))
    spec, io = config["spec"], config.get("io") or {}
    domain = load_domain(config["domain"])
    if hasattr(domain, "configure"):
        domain.configure(config.get("domain_root"))
    workspace, invocation = Path(args.workspace).resolve(), uuid.uuid4().hex
    prompt = Path(args.prompt_file).read_text(encoding="utf-8", errors="replace")
    captures = Path(config["capture_dir"]) / invocation
    run_dir = Path(config["capture_dir"]).parents[1]
    captures.mkdir(parents=True, exist_ok=True)
    (captures / "prompt.md").write_text(prompt, encoding="utf-8", newline="")
    log = Path(config["invocations"])
    row = {"member": config["id"], "invocation": invocation, "started": stamp(), "finished": None, "seconds": None,
           "workspace": str(workspace), "prompt_capture": (captures / "prompt.md").relative_to(run_dir).as_posix(),
           "final_capture": None, "recognized": None, "behavior_draw": None, "findings": [], "status": "running",
           "cost_usd": None}
    append(log, row)
    began, done = time.monotonic(), None
    try:
        done = behave(spec, domain, workspace, prompt, io, random.Random(spec.get("seed")),
                      Path(config.get("domain_root") or "."), args.timeout, Path(config["scope"]) if config.get("scope") else None)
        if done["files"]:
            apply(domain, workspace, done["files"])
    except Exception:  # noqa: BLE001 - reported as the member's error; the run goes on
        traceback.print_exc()
        done = result("error", status="error", final=traceback.format_exc()[-400:])
    capture(workspace, captures / "workspace")
    seconds = round(time.monotonic() - began, 3)
    append(log, {**row, "finished": stamp(), "seconds": seconds, "final_capture": (captures / "workspace").relative_to(run_dir).as_posix(),
                 "recognized": done["recognized"], "behavior_draw": done["draw"], "findings": done["findings"],
                 "status": done["status"], "cost_usd": done["cost_usd"]})
    Path(args.transcript).write_text(json.dumps({"event": "done"}) + "\n", encoding="utf-8")
    print(json.dumps({"status": done["status"], "exit_code": EXIT_CODES[done["status"]], "seconds": seconds,
                      "model": done["model"], "cost_usd": done["cost_usd"], "final": done["final"][-2000:]}))
    return EXIT_CODES[done["status"]]
