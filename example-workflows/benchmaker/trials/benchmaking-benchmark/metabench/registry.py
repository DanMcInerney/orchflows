"""The meta-tasks: which domain module judges each, its I/O names, designated contrasts and LLM pool members.

`register` adds a meta-task at run time (the tests register a toy one). A domain module is imported by name from
`metabench.domains`, or loaded from `domain_file` and copied into a pool's private runtime so members can import
it. Everything else about a meta-task lives in `BB/meta-tasks/<name>/` and `BB/reference-packages/<name>/`.
"""
from __future__ import annotations

import importlib
import importlib.util
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

from .store import BB

HAIKU, SONNET = "claude-haiku-4-5", "claude-sonnet-5-5"
LADDER = (0.15, 0.4, 0.7)
AGENT_TOOLS = "Read,Write,Edit,Bash,Glob,Grep"


@dataclass
class MetaTask:
    name: str
    domain: str                                     # module name under metabench.domains
    io: dict                                        # {"output", "inputs", "number_lines"}
    contrasts: tuple = ()                           # (higher, lower) member keys that must resolve
    llm: str = "single-call"                        # single-call | agent
    ladders: tuple = LADDER
    meta_dir: Path | None = None
    reference: Path | None = None                   # committed reference-package sources
    domain_file: Path | None = None                 # an extra domain module outside metabench.domains

    def __post_init__(self):
        self.meta_dir = self.meta_dir or BB / "meta-tasks" / self.name
        if self.reference is None:
            self.reference = BB / "reference-packages" / self.name


_SINGLE = {"output": "output.json", "inputs": ["input.json"], "number_lines": False}
META_TASKS: dict[str, MetaTask] = {task.name: task for task in (
    MetaTask("schedule-nosolver", "scheduling", _SINGLE,
             (("oracle", "floor:noop"), ("oracle", "defect:ignore_participant"), ("ladder:0.15", "ladder:0.7"))),
    MetaTask("logtriage-llm", "logtriage", {"output": "triage.json", "inputs": ["build.log"], "number_lines": True},
             (("oracle", "floor:noop"), ("oracle", "heuristic:dump_all"), ("ladder:0.15", "ladder:0.7"))),
    MetaTask("calendar-skill", "calendar", {"output": "result.json", "inputs": None, "number_lines": False},
             (("oracle", "floor:noop"), ("oracle", "defect:policy_blind_buffer"), ("oracle", "defect:clobber"),
              ("ladder:0.15", "ladder:0.7")), llm="agent"),
)}


def register(task: MetaTask) -> MetaTask:
    META_TASKS[task.name] = task
    return task


def get(name: str) -> MetaTask:
    if name not in META_TASKS:
        raise KeyError(f"unknown meta-task {name!r}; known: {', '.join(sorted(META_TASKS))}")
    return META_TASKS[name]


def load_domain(task: MetaTask):
    """The task's domain module; `domain_file` modules are loaded as metabench.domains.<name>."""
    qualified = f"metabench.domains.{task.domain}"
    if task.domain_file is None:
        return importlib.import_module(qualified)
    spec = importlib.util.spec_from_file_location(qualified, task.domain_file)
    module = importlib.util.module_from_spec(spec)
    sys.modules[qualified] = module
    spec.loader.exec_module(module)
    return module


def configure(domain, store) -> None:
    """Point a domain that reads material from the store (logtriage) at it."""
    hook = getattr(domain, "configure", None)
    if hook:
        hook(store)


def collect(domain, workspace, task: MetaTask) -> dict[str, bytes]:
    """The files a final workspace is judged on, as {relative path: bytes}."""
    hook = getattr(domain, "collect", None)
    if hook:
        return hook(workspace)
    root = Path(workspace)
    name = task.io["output"]
    return {name: (root / name).read_bytes()} if (root / name).is_file() else {}


# ---- LLM pool members (paid; only with --include-llm) ----------------------------------------------

def _llm(model=HAIKU, effort="low", mode="single-call", io=None, defect=None, **extra) -> dict:
    spec = {"kind": "llm", "mode": mode, "model": model, "effort": effort, "harness_defect": defect}
    if mode == "single-call":
        spec["io"] = dict(io or {})
    else:
        spec.update(tools=AGENT_TOOLS, skill=None, io=dict(io or {}))
    return {**spec, **extra}


def llm_pool(task: MetaTask, assets: Path) -> dict:
    """LLM members as {"members": {name: spec}, "unconfirmed": [pairs], "aa_pairs": [[a, b]]}.

    The pairs are hypotheses until `confirm` settles them on the slice. Skills are copied into `assets` so the
    pool does not change when the repository does.
    """
    if task.llm == "agent":
        return _agent_pool(task, assets)
    names = {"schedule-nosolver": ("truncate_busy:0.6", "haiku-truncated"),
             "logtriage-llm": ("last_chars:4000", "haiku-last-chars")}
    defect, label = names.get(task.name, ("", "haiku-defective"))
    members = {"haiku-low": _llm(io=task.io), "sonnet-low": _llm(SONNET, io=task.io), "haiku-low-b": _llm(io=task.io)}
    if defect:
        members[label] = _llm(defect=defect, io=task.io)
    pairs = [("sonnet-low", "haiku-low")] + ([("haiku-low", label)] if defect else [])
    if task.name == "logtriage-llm":
        members["haiku-unnumbered"] = _llm(defect="unnumbered_lines", io=task.io)
        pairs.append(("haiku-low", "haiku-unnumbered"))
    return {"members": members, "unconfirmed": [{"higher": a, "lower": b, "basis": "hypothesis"} for a, b in pairs],
            "aa_pairs": [["haiku-low", "haiku-low-b"]]}


def _agent_pool(task: MetaTask, assets: Path) -> dict:
    from .domains import calendar

    source = task.meta_dir / "subject" / "booking-rules"
    skill, harmful = Path(assets) / "skill" / source.name, Path(assets) / "harmful" / source.name
    skill.parent.mkdir(parents=True, exist_ok=True)
    harmful.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, skill, ignore=shutil.ignore_patterns("__pycache__"))
    calendar.harmful_skill(source, harmful)
    members = {"haiku-low": _llm(mode="agent", io=task.io),
               "haiku-skill": _llm(mode="agent", io=task.io, skill=str(skill)),
               "haiku-harmful-skill": _llm(mode="agent", io=task.io, defect=f"skill:{harmful}"),
               "haiku-hidden-skill": _llm(mode="agent", io=task.io, defect="skill_hidden", skill=str(skill)),
               "sonnet-low": _llm(SONNET, mode="agent", io=task.io)}
    pairs = [("haiku-skill", "haiku-low"), ("haiku-low", "haiku-harmful-skill")]
    return {"members": members, "unconfirmed": [{"higher": a, "lower": b, "basis": "hypothesis"} for a, b in pairs],
            "aa_pairs": [["haiku-low", "haiku-hidden-skill"]]}
