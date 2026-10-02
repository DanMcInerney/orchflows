"""Run a delivered package: intake, preflight, one `run.py full` per pool member and per built-in agent.

Every member gets a fresh copy of the package (after preflight, so provisioned environments come along), its own
agent directory and a private TEMP, and runs under `benchkit.launch.run_capped` with a minimal environment: no
CLAUDE* or other inherited variables, and the credential locations only for LLM members. Members run concurrently
up to `jobs`. The package's own outputs go under the output root, never inside the store or the package copy.
"""
from __future__ import annotations

import functools
import importlib.util
import json
import os
import shutil
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

from . import delivered, store

store.use_kit()
from benchkit import launch  # noqa: E402

ENV_KEEP = {"PATH", "SYSTEMROOT", "TEMP", "TMP", "USERPROFILE", "APPDATA", "LOCALAPPDATA", "HOME", "COMSPEC", "PATHEXT", "WINDIR"}
ENV_LLM = {"ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_BASE_URL", "CLAUDE_CONFIG_DIR", "CLAUDE_CODE_OAUTH_TOKEN"}
BUILTINS = ("@reference", "@noop")
SLACK_SECONDS = 300
DEFAULT_CAP = 3600
PREFLIGHT_SECONDS = 900


@dataclass
class Run:
    id: str
    root: Path        # <store>/runs/<id>
    out_root: Path    # <out-root>/<id>

    def __post_init__(self):
        self.root, self.out_root = Path(self.root), Path(self.out_root)

    def sub(self, name: str) -> Path:
        return self.root / name

    intake = property(lambda self: self.sub("intake"))
    package = property(lambda self: self.sub("package"))
    packages = property(lambda self: self.sub("packages"))
    agents = property(lambda self: self.sub("agents"))
    captures = property(lambda self: self.sub("captures"))
    invocations = property(lambda self: self.sub("invocations"))
    logs = property(lambda self: self.sub("logs"))
    tmp = property(lambda self: self.sub("tmp"))


@functools.cache
def load_conform():
    """The standalone conformance module, for its shape checks."""
    spec = importlib.util.spec_from_file_location("metabench_conform", store.BB / "public" / "conform.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def clean_env(temp: Path, *, llm: bool = False, base=None) -> dict:
    """The allow-listed environment; TEMP and TMP point at the member's private folder."""
    base = os.environ if base is None else base
    keep = ENV_KEEP | (ENV_LLM if llm else set())
    env = {key: value for key, value in base.items() if key.upper() in keep}
    env.update(TEMP=str(temp), TMP=str(temp), PYTHONDONTWRITEBYTECODE="1")
    return env


def copy_tree(source: Path, destination: Path) -> None:
    shutil.copytree(source, destination, ignore=shutil.ignore_patterns("__pycache__"))


def intake(run: Run, package: Path, reference: Path | None) -> list[str]:
    """Keep a pristine copy of the delivered package and a working copy; returns the files copied from the
    committed reference packages."""
    package = Path(package)
    if not (package / "run.py").is_file() or not (package / "suite.json").is_file():
        raise ValueError(f"{package} is not a benchmark package: it needs run.py and suite.json")
    copy_tree(package, run.intake)
    copy_tree(run.intake, run.package)
    return delivered.copied_from(run.intake, reference)


def cap_seconds(package: Path, override: float | None = None) -> float:
    """Wall cap for one `run.py` invocation: the suite's own deadline plus slack, else an hour."""
    if override:
        return float(override)
    deadline = delivered.suite(package).get("deadline_seconds")
    return float(deadline) + SLACK_SECONDS if isinstance(deadline, (int, float)) and deadline > 0 else DEFAULT_CAP


def invoke(run: Run, name: str, package: Path, arguments: list[str], env: dict, cap: float) -> launch.Outcome:
    """`python run.py <arguments>` in the package copy, output to files under logs/<name>/."""
    folder = run.logs / name
    folder.mkdir(parents=True, exist_ok=True)
    return launch.run_capped([sys.executable, "run.py", *arguments], cwd=package, env=env, stdout=folder / "stdout.txt",
                             stderr=folder / "stderr.txt", timeout=cap)


def tail(path: Path, size: int = 300) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace").strip()[-size:]
    except OSError:
        return ""


def read_json(path: Path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def read_rows(path: Path) -> list[dict]:
    rows = []
    try:
        for line in Path(path).read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    rows.append(json.loads(line))
                except ValueError:
                    pass
    except OSError:
        pass
    return [r for r in rows if isinstance(r, dict)]


def invocation_rows(path: Path) -> list[dict]:
    """One row per invocation: the last record the shim logged for it, in start order."""
    last = {}
    for row in read_rows(path):
        last[row.get("invocation")] = row
    return sorted(last.values(), key=lambda r: r.get("started") or "")


def preflight(run: Run, env: dict, cap: float = PREFLIGHT_SECONDS) -> dict:
    began = time.monotonic()
    outcome = invoke(run, "preflight", run.package, ["preflight"], env, cap)
    return {"exit_code": outcome.exit_code, "status": outcome.status, "seconds": round(time.monotonic() - began, 2),
            "reason": outcome.reason or tail(run.logs / "preflight" / "stderr.txt")}


def prepare_agent(run: Run, pool_dir: Path, member: str, scope: Path | None = None) -> Path:
    """A per-run copy of the member's agent directory with this run's capture and log paths. `scope` bounds what
    the cheaters may read and overwrite (default: the run's folder in the store)."""
    folder = run.agents / member
    shutil.copytree(Path(pool_dir) / "members" / member, folder)
    config = json.loads((folder / "member.json").read_text(encoding="utf-8"))
    config.update(capture_dir=str(run.captures / member), invocations=str(run.invocations / f"{member}.jsonl"),
                  scope=str(scope or run.root))
    store.write_json(folder / "member.json", config)
    return folder


def _result(run: Run, name: str, outcome: launch.Outcome, out: Path) -> dict:
    """The run record for one `run.py full`: its outputs, the G1 execution record and the members' invocations."""
    summary = read_json(out / "summary.json")
    problems = load_conform().run_problems(out) if out.is_dir() else ["no output directory"]
    if summary is None:
        problems.append("summary.json is missing or not JSON")
    reason = ""
    if outcome.status != "completed" or outcome.exit_code != 0:
        reason = f"{outcome.reason or 'exit code ' + str(outcome.exit_code)}: {tail(run.logs / name / 'stderr.txt')}".rstrip(": ")
    elif problems:
        reason = "; ".join(problems[:3])
    invocations = invocation_rows(run.invocations / f"{name}.jsonl")
    return {"id": name, "out": out,
            "exec": {"exit_code": outcome.exit_code, "status": outcome.status, "schema_valid": not problems, "reason": reason,
                     "summary": summary},
            "run": {"summary": summary, "attempts": read_rows(out / "attempts.jsonl"),
                    "invocations": [{"seconds": row.get("seconds")} for row in invocations],
                    "wall_seconds": round(outcome.seconds, 3)}}


def run_member(run: Run, pool_dir: Path, member: str, spec: dict, cap: float) -> dict:
    """One member on a fresh package copy: `python run.py full --agent <member> --output <out>`."""
    package, temp, out = run.packages / member, run.tmp / member, run.out_root / member
    copy_tree(run.package, package)
    agent = prepare_agent(run, pool_dir, member)
    temp.mkdir(parents=True)
    outcome = invoke(run, member, package, ["full", "--agent", str(agent), "--output", str(out)],
                     clean_env(temp, llm=spec.get("kind") == "llm"), cap)
    shutil.rmtree(temp, ignore_errors=True)
    return _result(run, member, outcome, out)


def run_builtin(run: Run, agent: str, cap: float) -> dict:
    """The package's own `@reference` or `@noop` agent, run the same way as a member."""
    name = agent.lstrip("@")
    package, temp, out = run.packages / name, run.tmp / name, run.out_root / name
    copy_tree(run.package, package)
    temp.mkdir(parents=True)
    outcome = invoke(run, name, package, ["full", "--agent", agent, "--output", str(out)], clean_env(temp), cap)
    shutil.rmtree(temp, ignore_errors=True)
    return _result(run, name, outcome, out)


def run_all(run: Run, pool_dir: Path, order: dict, members: list[str], *, jobs: int, cap: float, builtins=BUILTINS) -> dict:
    """Run the built-ins and every member, up to `jobs` at a time; returns {id or '@name': result}."""
    work = [(agent, lambda a=agent: run_builtin(run, a, cap)) for agent in builtins]
    work += [(m, lambda m=m: run_member(run, pool_dir, m, order["members"][m], cap)) for m in members]
    for folder in (run.packages, run.agents, run.captures, run.invocations, run.logs, run.tmp, run.out_root):
        folder.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(max_workers=max(1, jobs)) as pool:
        futures = [(name, pool.submit(job)) for name, job in work]
        return {name: future.result() for name, future in futures}


def run_grade(run: Run, name: str, inputs: Path, output: Path, cap: float) -> tuple[launch.Outcome, list[dict]]:
    """`python run.py grade --input <tree> --output <file>` on a fresh package copy; the rows it wrote."""
    package, temp = run.packages / f"{name}-grade", run.tmp / f"{name}-grade"
    copy_tree(run.package, package)
    temp.mkdir(parents=True)
    outcome = invoke(run, f"{name}-grade", package, ["grade", "--input", str(inputs), "--output", str(output)],
                     clean_env(temp), cap)
    shutil.rmtree(temp, ignore_errors=True)
    shutil.rmtree(package, ignore_errors=True)
    return outcome, read_rows(output)
