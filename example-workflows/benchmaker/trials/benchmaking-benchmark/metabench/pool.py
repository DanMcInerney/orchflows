"""Pool generation: members under anonymous ids, ORDER.json and the private runtime copy the members import.

A pool is written from a document that names its members (`{"members": {name: spec}, "known_pairs": [...], ...}`):
the committed `meta-tasks/<mt>/dev-pool.json` (exposed, development claims only) or one composed from the
domain's hooks, the generic floors, cheaters and ladders, any private operators in `<store>/private_members/` and,
with `include_llm`, the paid members. A domain's `FLOORS` names the content-blind attempts of its own (heuristics that
know nothing of the task); each is in every pool as a floor, so M1 and M7 can see a task that rewards it. Names exist
only in the document and in ORDER.json `label`; nothing on disk under `members/` carries one.

ORDER.json shape: B.5 of the plan, plus `domain` (module name), `io` (deliverable names), `exposure` and
`generated`. Pairs involving LLM members stay in `unconfirmed` until `confirm` settles them on the slice.
"""
from __future__ import annotations

import importlib.util
import shutil
from datetime import datetime, timezone
from pathlib import Path

from . import registry
from .members import cheaters, floors
from .store import BB, KIT, Store, anon_id, read_json, write_json

LAUNCHER = '''import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, json.loads((HERE / "member.json").read_text(encoding="utf-8"))["runtime"])
from metabench.members.shim import main  # noqa: E402

sys.exit(main(HERE, sys.argv[1:]))
'''
RUNTIME_METABENCH = ("__init__.py", "builders.py", "transcripts.py")
RUNTIME_MEMBERS = ("__init__.py", "shim.py", "floors.py", "cheaters.py", "ladder.py", "llm.py")
RUNTIME_KIT = ("__init__.py", "launch.py")
POOL_KEYS = ("members", "known_pairs", "contrasts", "aa_pairs", "unconfirmed")


def normalize(doc: dict, meta_task: str | None = None) -> dict:
    """One shape for every pool document: the committed dev-pool.json files carry `label` ("exposed"), which becomes
    `exposure`; every list is present and every pair names a member. Raises ValueError listing what does not fit."""
    out = {"meta_task": doc.get("meta_task") or meta_task, "exposure": doc.get("exposure") or doc.get("label") or "private",
           "use": doc.get("use") or "", **{key: doc.get(key, {} if key == "members" else []) for key in POOL_KEYS}}
    problems = []
    if meta_task and out["meta_task"] != meta_task:
        problems.append(f"the document is for {out['meta_task']!r}, not {meta_task!r}")
    if not out["members"]:
        problems.append("no members")
    for name, spec in out["members"].items():
        if not isinstance(spec, dict) or "kind" not in spec:
            problems.append(f"member {name!r} needs a spec with a kind")
    names = set(out["members"])
    for key in ("known_pairs", "contrasts", "unconfirmed"):
        for pair in out[key]:
            problems += [f"{key}: unknown member {pair[end]!r}" for end in ("higher", "lower") if pair.get(end) not in names]
    for pair in out["aa_pairs"]:
        problems += [f"aa_pairs: unknown member {name!r}" for name in pair if name not in names]
    if problems:
        raise ValueError("; ".join(problems))
    return out


def load_dev(task: registry.MetaTask) -> dict:
    return normalize(read_json(task.meta_dir / "dev-pool.json"), task.name)


def private_modules(store: Store, task: registry.MetaTask) -> list[tuple[Path, object]]:
    """The private operator modules for this meta-task; a module may limit itself with META_TASKS."""
    found = []
    for path in sorted(store.private_members().glob("*.py")) if store.private_members().is_dir() else []:
        spec = importlib.util.spec_from_file_location(f"private_{path.stem}", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        if task.name in (getattr(module, "META_TASKS", None) or [task.name]):
            found.append((path, module))
    return found


def _pair(higher, lower, basis="construction", **extra):
    return {"higher": higher, "lower": lower, "basis": basis, **extra}


def compose(task: registry.MetaTask, domain, store: Store) -> dict:
    """The default held-out pool for a meta-task, composed from hooks, generic members and private operators."""
    members = {"oracle": {"kind": "scripted", "behavior": "oracle", "origin": "-"}}
    diagnostic = set(getattr(domain, "DIAGNOSTIC", ()))
    below = []                                     # members the oracle must beat by construction
    for name in sorted(getattr(domain, "DEFECTS", {})):
        members[f"defect:{name}"] = {"kind": "scripted", "behavior": "defect", "defect": name, "origin": "synthetic",
                                     **({"diagnostic": True} if name in diagnostic else {})}
        below += [] if name in diagnostic else [f"defect:{name}"]
    for name in sorted(getattr(domain, "HEURISTICS", {})):
        if name in ("random_valid_format",):
            members[f"floor:{name}"] = {"kind": "scripted", "behavior": "floor", "name": name}
        else:
            members[f"heuristic:{name}"] = {"kind": "scripted", "behavior": "heuristic", "name": name, "origin": "natural"}
            below.append(f"heuristic:{name}")
    for module_path, module in private_modules(store, task):
        for source in ("DEFECTS", "HEURISTICS"):
            for name in sorted(getattr(module, source, {})):
                key = f"private:{module_path.stem}:{name}"
                members[key] = {"kind": "private", "module": f"private_members/{module_path.name}", "behavior": name,
                                "source": source, "origin": "synthetic"}
                below.append(key)
    rungs = [f"ladder:{q}" for q in task.ladders]
    for q, key in zip(task.ladders, rungs):
        members[key] = {"kind": "scripted", "behavior": "ladder", "q": q, "origin": "synthetic"}
    middle = rungs[len(rungs) // 2]
    members[f"{middle}-b"] = dict(members[middle])
    for name in floors.GENERIC:
        members[f"floor:{name}"] = {"kind": "scripted", "behavior": "floor", "name": name}
    for name in getattr(domain, "FLOORS", ()):       # the domain's own content-blind attempt, always in the pool
        members.setdefault(f"floor:{name}", {"kind": "scripted", "behavior": "floor", "name": name})
    trivial = [key for key, spec in members.items() if spec.get("behavior") == "floor"]
    for name in cheaters.NAMES:
        members[f"cheater:{name}"] = {"kind": "scripted", "behavior": "cheater", "name": name}
        trivial.append(f"cheater:{name}")
    known = [_pair("oracle", key) for key in [*below, *rungs]] + [_pair(a, b) for a, b in zip(rungs, rungs[1:])]
    known += [_pair(who, key) for key in trivial for who in ("oracle", rungs[-1])]
    contrasts = [{**_pair(a, b), "must_resolve": True} for a, b in task.contrasts if a in members and b in members]
    return {"meta_task": task.name, "exposure": "private", "use": "held-out pool", "members": members,
            "known_pairs": known, "contrasts": contrasts, "aa_pairs": [[middle, f"{middle}-b"]], "unconfirmed": []}


def add_llm(document: dict, task: registry.MetaTask, assets: Path) -> dict:
    extra = registry.llm_pool(task, assets)
    return {**document, "members": {**document["members"], **extra["members"]},
            "unconfirmed": [*document["unconfirmed"], *extra["unconfirmed"]],
            "aa_pairs": [*document["aa_pairs"], *extra["aa_pairs"]]}


def copy_runtime(store: Store, pool_id: str, task: registry.MetaTask) -> Path:
    """The private copy of the code members import; the repository is not read again after this."""
    root = store.runtime(pool_id)
    shutil.rmtree(root, ignore_errors=True)
    package = BB / "metabench"
    jobs = [(package / name, root / "metabench" / name) for name in RUNTIME_METABENCH]
    jobs += [(package / "members" / name, root / "metabench" / "members" / name) for name in RUNTIME_MEMBERS]
    jobs += [(path, root / "metabench" / "domains" / path.name) for path in (package / "domains").glob("*.py")]
    jobs += [(KIT / "benchkit" / name, root / "benchkit" / name) for name in RUNTIME_KIT]
    if task.domain_file:
        jobs.append((Path(task.domain_file), root / "metabench" / "domains" / f"{task.domain}.py"))
    for source, target in jobs:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    return root


def assemble(task: registry.MetaTask, document: dict, store: Store, *, pool_id: str | None = None) -> tuple[str, Path]:
    """Write the pool for a normalized document; returns its id and directory."""
    pool_id = pool_id or anon_id("p")
    pool = store.pool(task.name, pool_id)
    if (pool / "ORDER.json").exists():
        raise FileExistsError(f"pool {pool_id} already exists")
    ids = {}
    for name in document["members"]:
        ids[name] = anon_id("m", ids.values())

    def translate(pairs):
        return [{**pair, "higher": ids[pair["higher"]], "lower": ids[pair["lower"]]} for pair in pairs]

    order_path = pool / "ORDER.json"
    runtime = copy_runtime(store, pool_id, task)
    for name, member in ids.items():
        folder = pool / "members" / member
        folder.mkdir(parents=True)
        (folder / "run_agent.py").write_text(LAUNCHER, encoding="utf-8", newline="\n")
        write_json(folder / "member.json", {"id": member, "order": str(order_path), "runtime": str(runtime),
                                            "store": str(store.root)})
    write_json(order_path, {
        "meta_task": task.name, "domain": task.domain, "io": task.io, "exposure": document["exposure"],
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "members": {ids[name]: {**spec, "label": name} for name, spec in document["members"].items()},
        "known_pairs": translate(document["known_pairs"]), "contrasts": translate(document["contrasts"]),
        "aa_pairs": [[ids[a], ids[b]] for a, b in document["aa_pairs"]], "killable": {},
        "unconfirmed": translate(document["unconfirmed"])})
    return pool_id, pool


def generate(meta_task: str, store: Store, *, dev: bool = False, include_llm: bool = False,
             pool_id: str | None = None) -> tuple[str, Path]:
    """Generate a pool for a meta-task into the store; returns (pool id, pool directory)."""
    task = registry.get(meta_task)
    registry.configure(domain := registry.load_domain(task), store.root)
    document = load_dev(task) if dev else normalize(compose(task, domain, store), task.name)
    pool_id = pool_id or anon_id("p")
    if include_llm:
        document = normalize(add_llm(document, task, store.pool(task.name, pool_id) / "assets" / anon_id("a")), task.name)
    return assemble(task, document, store, pool_id=pool_id)


def read_order(store: Store, meta_task: str, pool_id: str) -> dict:
    return read_json(store.pool(meta_task, pool_id) / "ORDER.json")


def members_of(order: dict, *, llm: bool) -> list[str]:
    """Member ids to run: every scripted and private member, and the LLM ones only when asked."""
    return sorted(m for m, spec in order["members"].items() if llm or spec.get("kind") != "llm")
