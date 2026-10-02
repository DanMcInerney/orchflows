"""Run a delivered package: intake, preflight, one `run.py full` per pool member and per built-in agent.

Every invocation of delivered code (preflight, a member run, a built-in run, a grade call) gets its own arena: a
randomly named folder under the run's work area, outside the store, holding a fresh copy of the package, a private
TEMP and home, its logs and, for a member, its agent directory. It runs under `benchkit.launch.run_capped` with a
minimal environment: no CLAUDE* or other inherited variables, a private home (the real one only for LLM members,
who need their credentials), and the credential locations only for LLM members. Nothing handed to delivered code
names the store, ORDER.json or a member label: a member's agent directory holds a copy of its own behaviour spec and
the runtime it imports, both in the work area, and grade inputs sit under random names. Members run concurrently up
to `jobs`. The package's own outputs go under the output root. Same-user isolation is still a convention: a process
that scans the whole disk can find the store, which is why the crosscheck also regrades without trusting the run.
"""
from __future__ import annotations

import functools
import importlib.util
import json
import os
import shutil
import sys
import threading
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
INTERRUPTED = 4          # the kit's exit code for a run stopped by the account's usage limit
VIEW_PARTS = ("public", "held-out")
_RUNTIME_LOCK = threading.Lock()


@dataclass
class Run:
    id: str
    root: Path                  # <store>/runs/<id>: what the meta-verifier keeps (intake, reports, log copies)
    out_root: Path              # <out-root>/<id>: the packages' own outputs
    work: Path | None = None    # private work area outside the store, where delivered code runs

    def __post_init__(self):
        self.root, self.out_root = Path(self.root), Path(self.out_root)
        self.work = Path(self.work) if self.work else self.out_root.with_name(self.out_root.name + ".work")

    intake = property(lambda self: self.root / "intake")
    package = property(lambda self: self.root / "package")
    logs = property(lambda self: self.root / "logs")
    agents = property(lambda self: self.work / "agents")
    arenas = property(lambda self: self.work / "arenas")
    runtime = property(lambda self: self.work / "runtime")
    ledger = property(lambda self: self.work / "ledger")
    captures = property(lambda self: self.ledger / "captures")
    invocations = property(lambda self: self.ledger / "invocations")

    def arena(self) -> Path:
        """A new randomly named folder for one invocation of delivered code."""
        self.arenas.mkdir(parents=True, exist_ok=True)
        while True:
            path = self.arenas / store.anon_id("a")
            try:
                path.mkdir()
                return path
            except FileExistsError:
                continue


@functools.cache
def load_conform():
    """The standalone conformance module, for its shape checks."""
    spec = importlib.util.spec_from_file_location("metabench_conform", store.BB / "public" / "conform.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def clean_env(temp: Path, *, llm: bool = False, base=None, home: Path | None = None) -> dict:
    """The allow-listed environment; TEMP and TMP point at the member's private folder, and a `home` replaces every
    variable that names the user's home."""
    base = os.environ if base is None else base
    keep = ENV_KEEP | (ENV_LLM if llm else set())
    env = {key: value for key, value in base.items() if key.upper() in keep}
    env.update(TEMP=str(temp), TMP=str(temp), PYTHONDONTWRITEBYTECODE="1")
    if home is not None:
        roaming, local = Path(home) / "AppData" / "Roaming", Path(home) / "AppData" / "Local"
        for folder in (roaming, local):
            folder.mkdir(parents=True, exist_ok=True)
        env.update(HOME=str(home), USERPROFILE=str(home), APPDATA=str(roaming), LOCALAPPDATA=str(local))
    return env


def copy_tree(source: Path, destination: Path) -> None:
    shutil.copytree(source, destination, ignore=shutil.ignore_patterns("__pycache__"))


def discard(path: Path) -> None:
    shutil.rmtree(path, ignore_errors=True)


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


def invoke(package: Path, arguments: list[str], env: dict, cap: float, logs: Path) -> launch.Outcome:
    """`python run.py <arguments>` in the package copy, output to files under `logs`."""
    logs.mkdir(parents=True, exist_ok=True)
    return launch.run_capped([sys.executable, "run.py", *arguments], cwd=package, env=env, stdout=logs / "stdout.txt",
                             stderr=logs / "stderr.txt", timeout=cap)


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


def launch_in_arena(run: Run, name: str, arguments, *, cap: float, llm: bool = False, agent=None) -> tuple[launch.Outcome, Path]:
    """`python run.py <arguments>` on a fresh package copy in a new arena. `arguments` is a list, or a function of the
    arena returning one (for paths inside it); `agent(arena)` prepares anything else the invocation needs there. The
    logs are copied to `<run>/logs/<name>/`; the caller removes the arena."""
    arena = run.arena()
    temp, home, logs = arena / "tmp", arena / "home", arena / "logs"
    for folder in (temp, home):
        folder.mkdir()
    package = arena / "package"
    copy_tree(run.package, package)
    if agent:
        agent(arena)
    outcome = invoke(package, arguments(arena) if callable(arguments) else arguments,
                     clean_env(temp, llm=llm, home=None if llm else home), cap, logs)
    kept = run.logs / name
    kept.mkdir(parents=True, exist_ok=True)
    for file in ("stdout.txt", "stderr.txt"):
        if (logs / file).is_file():
            shutil.copyfile(logs / file, kept / file)
    return outcome, arena


def preflight(run: Run, cap: float = PREFLIGHT_SECONDS) -> dict:
    began = time.monotonic()
    outcome, arena = launch_in_arena(run, "preflight", ["preflight"], cap=cap)
    discard(arena)
    return {"exit_code": outcome.exit_code, "status": outcome.status, "seconds": round(time.monotonic() - began, 2),
            "reason": outcome.reason or tail(run.logs / "preflight" / "stderr.txt")}


def clean_spec(spec: dict) -> dict:
    """A member's own behaviour for its agent directory: no label, and nothing about where it came from."""
    return {key: value for key, value in spec.items() if key not in ("label", "origin", "diagnostic")}


def ensure_runtime(run: Run, template: dict, order: dict, specs: dict) -> Path:
    """The run's private copy of the code members import and of the material and operators they need, in the work
    area; made once per run. `template` is a pool member.json, which knows where the pool's copies are."""
    with _RUNTIME_LOCK:
        view = run.runtime / "view"
        if not (run.runtime / "metabench").is_dir() and template.get("runtime"):
            shutil.copytree(template["runtime"], run.runtime, ignore=shutil.ignore_patterns("__pycache__"), dirs_exist_ok=True)
        view.mkdir(parents=True, exist_ok=True)
        root, meta_task = Path(template.get("store") or "."), order.get("meta_task")
        for part in VIEW_PARTS:
            source, target = root / "material" / str(meta_task) / part, view / "material" / str(meta_task) / part
            if meta_task and source.is_dir() and not target.exists():
                shutil.copytree(source, target)
        for spec in specs.values():
            module = spec.get("module")
            if spec.get("kind") == "private" and module and not (view / module).exists():
                (view / module).parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(root / module, view / module)
        return view


def prepare_agent(run: Run, pool_dir: Path, member: str, scope: Path | None = None, folder: Path | None = None,
                  spec: dict | None = None) -> Path:
    """A per-run agent directory for the member: the launcher and a member.json that holds the member's own behaviour,
    the pool's io and domain, the runtime and material in the work area and this run's capture and log paths. It
    names no store, ORDER.json or label. `scope` bounds what the cheaters may read and overwrite (default: the work
    area)."""
    template_dir = Path(pool_dir) / "members" / member
    template = json.loads((template_dir / "member.json").read_text(encoding="utf-8"))
    order = (read_json(template["order"]) if template.get("order") else None) or {}
    own = spec or (order.get("members") or {}).get(member) or {}
    view = ensure_runtime(run, template, order, {member: own})
    folder = Path(folder) if folder else run.agents / member
    shutil.copytree(template_dir, folder)
    store.write_json(folder / "member.json", {
        "id": member, "spec": clean_spec(own), "io": order.get("io") or {}, "domain": order.get("domain"),
        "runtime": str(run.runtime), "domain_root": str(view), "capture_dir": str(run.captures / member),
        "invocations": str(run.invocations / f"{member}.jsonl"), "scope": str(scope or run.work)})
    return folder


def _result(run: Run, name: str, outcome: launch.Outcome, out: Path) -> dict:
    """The run record for one `run.py full`: its outputs, the G1 execution record and the members' invocations. A run
    that stopped because the account hit its usage limit is marked `interrupted`: resumable, not a package fault."""
    summary = read_json(out / "summary.json")
    problems = load_conform().run_problems(out) if out.is_dir() else ["no output directory"]
    if summary is None:
        problems.append("summary.json is missing or not JSON")
    rows = read_rows(out / "attempts.jsonl")
    reason = ""
    if outcome.status != "completed" or outcome.exit_code != 0:
        reason = f"{outcome.reason or 'exit code ' + str(outcome.exit_code)}: {tail(run.logs / name / 'stderr.txt')}".rstrip(": ")
    elif problems:
        reason = "; ".join(problems[:3])
    limited = outcome.status == "completed" and outcome.exit_code == INTERRUPTED and any(
        r.get("status") == "interrupted" and "usage limit" in str(r.get("reason") or "") for r in rows)
    invocations = invocation_rows(run.invocations / f"{name}.jsonl")
    return {"id": name, "out": out,
            "exec": {"exit_code": outcome.exit_code, "status": outcome.status, "schema_valid": not problems, "reason": reason,
                     "summary": summary, **({"interrupted": "usage-limit"} if limited else {})},
            "run": {"summary": summary, "attempts": rows,
                    "invocations": [{"seconds": row.get("seconds")} for row in invocations],
                    "wall_seconds": round(outcome.seconds, 3)}}


def run_member(run: Run, pool_dir: Path, member: str, spec: dict, cap: float) -> dict:
    """One member on a fresh package copy: `python run.py full --agent <member> --output <out>`."""
    out = run.out_root / member
    outcome, arena = launch_in_arena(
        run, member, lambda arena: ["full", "--agent", str(arena / "agent"), "--output", str(out)], cap=cap,
        llm=spec.get("kind") == "llm",
        agent=lambda arena: prepare_agent(run, pool_dir, member, folder=arena / "agent", spec=spec))
    discard(arena)
    return _result(run, member, outcome, out)


def run_builtin(run: Run, agent: str, cap: float) -> dict:
    """The package's own `@reference` or `@noop` agent, run the same way as a member."""
    name = agent.lstrip("@")
    out = run.out_root / name
    outcome, arena = launch_in_arena(run, name, ["full", "--agent", agent, "--output", str(out)], cap=cap)
    discard(arena)
    return _result(run, name, outcome, out)


def run_all(run: Run, pool_dir: Path, order: dict, members: list[str], *, jobs: int, cap: float, builtins=BUILTINS) -> dict:
    """Run the built-ins and every member, up to `jobs` at a time; returns {id or '@name': result}."""
    work = [(agent, lambda a=agent: run_builtin(run, a, cap)) for agent in builtins]
    work += [(m, lambda m=m: run_member(run, pool_dir, m, order["members"][m], cap)) for m in members]
    for folder in (run.captures, run.invocations, run.logs, run.out_root):
        folder.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(max_workers=max(1, jobs)) as pool:
        futures = [(name, pool.submit(job)) for name, job in work]
        return {name: future.result() for name, future in futures}


def run_grade(run: Run, name: str, build, cap: float):
    """`python run.py grade --input <tree> --output <file>` on a fresh package copy, in an arena of its own: the tree
    and the output file have random names that say nothing about what is graded. `build(tree)` fills the tree with
    `<task>/<submission>/` workspaces and may return anything; returns (outcome, rows written, what `build` returned)."""
    built, written = [], []

    def arguments(arena):
        tree, output = arena / "input" / store.anon_id("g"), arena / store.anon_id("g") / "grades.jsonl"
        tree.mkdir(parents=True)
        output.parent.mkdir()
        built.append(build(tree))
        written.append(output)
        return ["grade", "--input", str(tree), "--output", str(output)]

    outcome, arena = launch_in_arena(run, f"{name}-grade", arguments, cap=cap)
    rows = read_rows(written[0]) if written else []
    discard(arena)
    return outcome, rows, built[0] if built else None
