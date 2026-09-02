#!/usr/bin/env python3
"""Run the selected or exhaustive suite in one interpreter.
The routine selected lane proves exact discovery identity and executes the
committed state sentinels. Exhaustive mode remains the scheduled/manual fallback.
Stdlib only, Python 3.9+, POSIX and Windows.
"""
from __future__ import annotations
import argparse
import ast
import asyncio
import html
import hashlib
import json
import logging
import os
import re
import subprocess
import sys
import threading
import time
import unittest
import warnings
from collections import OrderedDict
from pathlib import Path
# Run directly (`python tools/run_serial_compat.py`), so `scripts/` is
# not yet on sys.path here; reading `scripts._bootstrap.ROOT` would need
# this same walk to seed the import first, for no fact this file
# otherwise needs from `scripts/`.
ROOT = Path(__file__).resolve().parent.parent
TESTS_DIR = ROOT / "tests"
MANIFEST_PATH = TESTS_DIR / "serial_compat_manifest.json"
RECORD_PATH = ROOT / ".orch" / "serial-compat.json"
RESTORABLE_SEAMS = frozenset(
    {"cwd", "environment", "event-loop", "import-path", "logging", "module-cache",
     "monkeypatch", "warnings"}
)
ALL_SEAMS = RESTORABLE_SEAMS | {"threads"}
# The rulings a reviewer may give a mutation owner; the policy says what each means.
RESTORATIONS = frozenset({"selected-module-boundary", "sharded-module-guard"})
REQUIRED_CATEGORIES = frozenset({
    "boundary-restoration", "cutcheck-corpus", "cutcheck-process", "cwd", "discovery",
    "environment", "git-process", "hash-contract", "health-contract", "installer-fidelity",
    "process", "real-hashed-runtime", "receipt-state", "state-sink", "thread-server",
    "ticket-contention", "workspace-state",
})
def _canonical_sentinel_count(canonical: Path = MANIFEST_PATH) -> int:
    """The committed manifest's own sentinel count, read fresh -- never a
    literal restated here for a future add/remove to drift against unseen."""

    return len(json.loads(Path(canonical).read_text(encoding="utf-8"))["sentinels"])


def load_manifest(path: Path = MANIFEST_PATH) -> dict:
    """Load the committed identity, sentinel, and mutation-owner contract."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if data.get("schema") != "orchflows.serial-compat.v1":
        raise ValueError("unsupported serial compatibility manifest")
    discovery = data.get("discovery")
    identities = discovery.get("identities") if isinstance(discovery, dict) else None
    if (not isinstance(identities, list)
            or any(not isinstance(identity, str) or not identity for identity in identities)
            or identities != sorted(set(identities))
            or discovery.get("count") != len(identities)
            or discovery.get("sha256") != hashlib.sha256(
                "\n".join(identities).encode("utf-8")).hexdigest()):
        raise ValueError("serial compatibility exact discovery is invalid")
    entries = data.get("sentinels")
    if not isinstance(entries, list) or not entries:
        raise ValueError("serial compatibility manifest has no sentinels")
    ids = [entry.get("id") for entry in entries]
    categories = {category for entry in entries for category in entry.get("categories", [])}
    allowed = {seam for entry in entries for seam in entry.get("allowed_seams", [])}
    if len(ids) != len(set(ids)) or any(not identity for identity in ids):
        raise ValueError("serial compatibility sentinel identities must be unique")
    if not REQUIRED_CATEGORIES.issubset(categories):
        raise ValueError("serial compatibility sentinel categories are incomplete")
    expected = _canonical_sentinel_count()
    if len(entries) != expected:
        raise ValueError(f"serial compatibility manifest must contain exactly {expected} sentinels")
    if not allowed.issubset(RESTORABLE_SEAMS):
        raise ValueError("serial compatibility manifest allows an unrestorable seam")
    owners = data.get("mutation_owners")
    owner_keys = [(owner.get("module"), owner.get("owner")) for owner in owners or []]
    if not isinstance(owners, list) or len(owner_keys) != len(set(owner_keys)):
        raise ValueError("serial compatibility mutation owners are missing or duplicated")
    if any(not set(owner.get("seams", [])).issubset(ALL_SEAMS) for owner in owners):
        raise ValueError("serial compatibility mutation owner names an unknown seam")
    unruled = [(owner.get("module"), owner.get("owner")) for owner in owners
               if owner.get("restoration") not in RESTORATIONS]
    if unruled:
        raise ValueError("serial compatibility mutation owner has no restoration: "
                         + ", ".join("%s::%s" % pair for pair in unruled))
    return data
def manifest_identity(manifest: dict) -> dict:
    encoded = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return {"sha256": hashlib.sha256(encoded).hexdigest()}
def flatten(suite):
    """Yield cases from a unittest suite without executing its fixtures."""
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from flatten(item)
        else:
            yield item
def discover_cases(tests_dir: Path = TESTS_DIR):
    """Discover the same identities as ``unittest discover -s tests``."""
    tests_dir = Path(tests_dir).resolve()
    for path in tests_dir.glob("test*.py"):
        cached = sys.modules.get(path.stem)
        if cached is None:
            continue
        cached_file = getattr(cached, "__file__", None)
        if cached_file is None:
            sys.modules.pop(path.stem, None)
            continue
        try:
            same_module = Path(cached_file).resolve() == path.resolve()
        except OSError:
            same_module = False
        if not same_module:
            sys.modules.pop(path.stem, None)
    before = list(sys.path)
    try:
        import_paths = [str(tests_dir), str(tests_dir.parent)]
        sys.path[:] = import_paths + [path for path in before if path not in import_paths]
        suite = unittest.TestLoader().discover(str(tests_dir), top_level_dir=str(tests_dir))
        return list(flatten(suite))
    finally:
        sys.path[:] = before
def _logger_state(logger):
    return (logger, tuple(logger.handlers), tuple(logger.filters), logger.level,
            logger.disabled, logger.propagate)
def capture_state() -> dict:
    """Snapshot process seams selected modules may borrow but must return."""
    root_logger = logging.getLogger()
    logger_dict = logging.root.manager.loggerDict
    logger_states = {name: _logger_state(logger) for name, logger in logger_dict.items()
                     if isinstance(logger, logging.Logger)}
    policy = asyncio.get_event_loop_policy()
    loop_local = getattr(policy, "_local", None)
    return {
        "environment": (os.environ, dict(os.environ)),
        "cwd": (os.chdir, os.getcwd()),
        "import-path": (sys.path, tuple(sys.path)),
        "warnings": (warnings.filters, tuple(warnings.filters), warnings.showwarning,
                     warnings.formatwarning, warnings.defaultaction),
        "logging": (
            root_logger,
            tuple(root_logger.handlers),
            tuple(root_logger.filters),
            root_logger.level,
            root_logger.disabled,
            logging.root.manager.disable,
            logger_dict,
            dict(logger_dict),
            logger_states,
        ),
        "event-loop": (policy, loop_local, dict(vars(loop_local)) if loop_local else None),
        "module-cache": (sys.modules, dict(sys.modules)),
        "threads": frozenset(id(thread) for thread in threading.enumerate()),
        "monkeypatch": (dict(vars(Path)), html.escape),
    }
def changed_state(before: dict) -> list[str]:
    """Return stable seam names whose identity or value changed."""
    changed = []
    env_object, env_value = before["environment"]
    if os.environ is not env_object or dict(os.environ) != env_value:
        changed.append("environment")
    chdir, cwd = before["cwd"]
    try:
        cwd_changed = os.getcwd() != cwd
    except OSError:
        cwd_changed = True
    if os.chdir is not chdir or cwd_changed:
        changed.append("cwd")
    path_object, path_value = before["import-path"]
    if sys.path is not path_object or tuple(sys.path) != path_value:
        changed.append("import-path")
    filters_object, filters_value, showwarning, formatwarning, defaultaction = before["warnings"]
    if (warnings.filters is not filters_object or tuple(warnings.filters) != filters_value
            or warnings.showwarning is not showwarning or warnings.formatwarning is not formatwarning
            or warnings.defaultaction != defaultaction):
        changed.append("warnings")
    root, handlers, root_filters, level, disabled, manager_disable, logger_dict, loggers, states = before["logging"]
    if (
        logging.getLogger() is not root
        or tuple(root.handlers) != handlers
        or tuple(root.filters) != root_filters
        or root.level != level
        or root.disabled != disabled
        or logging.root.manager.disable != manager_disable
        or logging.root.manager.loggerDict is not logger_dict
        or dict(logger_dict) != loggers
        or any(_logger_state(state[0]) != state for state in states.values())
    ):
        changed.append("logging")
    policy, loop_local, loop_state = before["event-loop"]
    current_local = getattr(asyncio.get_event_loop_policy(), "_local", None)
    if (asyncio.get_event_loop_policy() is not policy or current_local is not loop_local
            or (dict(vars(current_local)) if current_local else None) != loop_state):
        changed.append("event-loop")
    modules_object, modules_value = before["module-cache"]
    if sys.modules is not modules_object or dict(sys.modules) != modules_value:
        changed.append("module-cache")
    if frozenset(id(thread) for thread in threading.enumerate()) != before["threads"]:
        changed.append("threads")
    path_namespace, escape = before["monkeypatch"]
    if dict(vars(Path)) != path_namespace or html.escape is not escape:
        changed.append("monkeypatch")
    return sorted(changed)
def restore_state(before: dict) -> list[str]:
    """Restore every safely restorable seam and return what was restored."""
    changed = changed_state(before)
    if "environment" in changed:
        env_object, env_value = before["environment"]
        os.environ = env_object
        os.environ.clear()
        os.environ.update(env_value)
    if "cwd" in changed:
        chdir, cwd = before["cwd"]
        os.chdir = chdir
        os.chdir(cwd)
    if "import-path" in changed:
        path_object, path_value = before["import-path"]
        sys.path = path_object
        sys.path[:] = path_value
    if "warnings" in changed:
        filters_object, filters_value, showwarning, formatwarning, defaultaction = before["warnings"]
        warnings.filters = filters_object
        warnings.filters[:] = filters_value
        warnings.showwarning, warnings.formatwarning = showwarning, formatwarning
        warnings.defaultaction = defaultaction
    if "logging" in changed:
        root, handlers, root_filters, level, disabled, manager_disable, logger_dict, loggers, states = before["logging"]
        root.handlers[:] = handlers
        root.filters[:] = root_filters
        root.setLevel(level)
        root.disabled = disabled
        logging.disable(manager_disable)
        logging.root.manager.loggerDict = logger_dict
        logger_dict.clear()
        logger_dict.update(loggers)
        for logger, handlers, filters, level, disabled, propagate in states.values():
            logger.handlers[:], logger.filters[:] = handlers, filters
            logger.level, logger.disabled, logger.propagate = level, disabled, propagate
    if "event-loop" in changed:
        policy, loop_local, loop_state = before["event-loop"]
        current_loop = getattr(getattr(asyncio.get_event_loop_policy(), "_local", None), "_loop", None)
        if current_loop is not None and current_loop is not (loop_state or {}).get("_loop"):
            if not current_loop.is_running():
                current_loop.close()
        asyncio.set_event_loop_policy(policy)
        if loop_local is not None:
            vars(loop_local).clear()
            vars(loop_local).update(loop_state)
    if "module-cache" in changed:
        modules_object, modules_value = before["module-cache"]
        sys.modules = modules_object
        sys.modules.clear()
        sys.modules.update(modules_value)
    if "monkeypatch" in changed:
        path_namespace, escape = before["monkeypatch"]
        for name in set(vars(Path)) - set(path_namespace):
            delattr(Path, name)
        for name, value in path_namespace.items():
            if vars(Path).get(name) is not value:
                setattr(Path, name, value)
        html.escape = escape
    return sorted(set(changed) & RESTORABLE_SEAMS)
class _MutationVisitor(ast.NodeVisitor):
    """Conservative syntactic inventory of process-mutating test owners."""
    def __init__(self, module: str, source: str):
        self.module = module
        self.source = source
        self.stack = []
        self.owners = {}
        self.aliases = {}
    def visit_Import(self, node):
        for name in node.names:
            self.aliases[name.asname or name.name.split(".")[0]] = name.name
    def visit_ImportFrom(self, node):
        for name in node.names:
            if node.module and name.name != "*":
                self.aliases[name.asname or name.name] = node.module + "." + name.name
    def _visit_owner(self, node):
        self.stack.append(node.name)
        self.generic_visit(node)
        self.stack.pop()
    visit_FunctionDef = _visit_owner
    visit_AsyncFunctionDef = _visit_owner
    visit_ClassDef = _visit_owner
    def _record(self, node):
        text = ast.get_source_segment(self.source, node) or ""
        for alias, target in sorted(self.aliases.items(), key=lambda item: -len(item[0])):
            text = re.sub(r"\b%s\b" % re.escape(alias), target, text)
        seams = set()
        if "os.environ" in text or "putenv(" in text or "unsetenv(" in text:
            seams.add("environment")
        if "os.chdir" in text:
            seams.add("cwd")
        if "sys.path" in text:
            seams.add("import-path")
        if "sys.modules" in text:
            seams.add("module-cache")
        if "warnings." in text:
            seams.add("warnings")
        if "logging." in text:
            seams.add("logging")
        if "asyncio." in text or "set_event_loop" in text:
            seams.add("event-loop")
        if any(token in text for token in ("Thread(", "ThreadPoolExecutor(", ".serve_forever(", ".start()")):
            seams.add("threads")
        if "patch.object(" in text or re.search(r"\b(?:[\w.]*Path\.\w+|html\.escape)\s*=", text):
            seams.add("monkeypatch")
        if seams:
            owner = ".".join(self.stack) or "<module>"
            self.owners.setdefault(owner, set()).update(seams)
    def visit_Call(self, node):
        self._record(node)
        self.generic_visit(node)
    def visit_Assign(self, node):
        self._record(node)
        self.generic_visit(node)
    def visit_AnnAssign(self, node):
        self._record(node)
        self.generic_visit(node)
    def visit_AugAssign(self, node):
        self._record(node)
        self.generic_visit(node)
    def visit_Delete(self, node):
        self._record(node)
        self.generic_visit(node)
def scan_mutation_owners(tests_dir: Path) -> list[dict]:
    """Return the deterministic review surface the committed manifest pins."""
    tests_dir = Path(tests_dir).resolve()
    records = [{
        "module": "<suite>",
        "owner": "discovery-baseline",
        "seams": sorted({"cwd", "environment", "event-loop", "import-path", "logging",
                         "module-cache", "monkeypatch", "threads", "warnings"}),
    }]
    for path in sorted(tests_dir.rglob("*.py")):
        source = path.read_text(encoding="utf-8")
        visitor = _MutationVisitor(
            ".".join(path.relative_to(tests_dir.parent).with_suffix("").parts), source
        )
        visitor.visit(ast.parse(source))
        records.extend(
            {"module": visitor.module, "owner": owner, "seams": sorted(seams)}
            for owner, seams in visitor.owners.items()
        )
    return sorted(records, key=lambda record: (record["module"], record["owner"]))
def revision(root: Path = ROOT):
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(root),
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
    except OSError:
        return None
    if completed.returncode:
        return None
    return completed.stdout.decode("ascii", "replace").strip() or None
def worktree_clean(root: Path = ROOT) -> bool:
    try:
        completed = subprocess.run(
            ["git", "status", "--porcelain=v1", "--untracked-files=all"], cwd=str(root),
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        )
    except OSError:
        return False
    return completed.returncode == 0 and not completed.stdout.strip()
def _summary(results):
    return {
        "tests": sum(result.testsRun for result in results),
        "failures": sum(len(result.failures) for result in results),
        "errors": sum(len(result.errors) for result in results),
        "skipped": sum(len(result.skipped) for result in results),
        "expected_failures": sum(len(result.expectedFailures) for result in results),
        "unexpected_successes": sum(len(result.unexpectedSuccesses) for result in results),
    }
def _require_discovery(cases, manifest):
    identities = sorted(case.id() for case in cases)
    identity_hash = hashlib.sha256("\n".join(identities).encode("utf-8")).hexdigest()
    expected = manifest.get("discovery")
    if expected is not None and (
        expected.get("count") != len(identities)
        or expected.get("sha256") != identity_hash
        or ("identities" in expected and expected["identities"] != identities)
    ):
        raise ValueError(
            "discovery identity drift: expected %s/%s, observed %d/%s"
            % (expected.get("count"), expected.get("sha256"), len(identities), identity_hash)
        )
    return identities, identity_hash
def run_selected(tests_dir: Path, manifest: dict, stream=None, verbosity: int = 1) -> dict:
    """Discover all cases, then run only committed sentinels in this process."""
    started = time.monotonic()
    cases = discover_cases(tests_dir)
    _, identity_hash = _require_discovery(cases, manifest)
    by_id = {}
    for case in cases:
        by_id.setdefault(case.id(), []).append(case)
    entries = manifest.get("sentinels", [])
    missing = [entry["id"] for entry in entries if len(by_id.get(entry["id"], ())) != 1]
    if missing:
        raise ValueError("selected identity missing or duplicated: " + ", ".join(missing))
    groups = OrderedDict()
    for entry in entries:
        groups.setdefault(entry["module"], []).append(by_id[entry["id"]][0])
    output = stream if stream is not None else sys.stderr
    results = []
    boundaries = []
    allowed = {}
    for owner in manifest.get("mutation_owners", []):
        if owner.get("restoration") == "selected-module-boundary":
            allowed.setdefault(owner["module"], set()).update(owner["seams"])
    for entry in entries:
        allowed.setdefault(entry["module"], set()).update(entry.get("allowed_seams", []))
    for module, selected in groups.items():
        output.write("selected module: %s (%d sentinels)\n" % (module, len(selected)))
        before = capture_state()
        result = unittest.TextTestRunner(stream=output, verbosity=verbosity).run(
            unittest.TestSuite(selected)
        )
        changed = changed_state(before)
        restored = restore_state(before)
        remaining = changed_state(before)
        unexpected = sorted(set(changed) - allowed.get(module, set()))
        if "threads" in changed:
            unexpected = sorted(set(unexpected) | {"threads"})
        unexpected = sorted(set(unexpected) | set(remaining))
        boundaries.append({
            "module": module,
            "changed": changed,
            "restored": restored,
            "remaining": remaining,
            "unexpected": unexpected,
        })
        results.append(result)
    outcomes = _summary(results)
    ok = (
        bool(entries)
        and all(result.wasSuccessful() for result in results)
        and not any(boundary["unexpected"] for boundary in boundaries)
    )
    return {
        "schema": "orchflows.serial-compat-observation.v1",
        "mode": "selected",
        "revision": revision(),
        "worktree_clean": worktree_clean(),
        "manifest": manifest_identity(manifest),
        "recorded_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "interpreter": {
            "pid": os.getpid(),
            "version": sys.version.split()[0],
            "executable": sys.executable,
        },
        "discovery": {"count": len(cases), "sha256": identity_hash},
        "sentinels": {"count": len(entries)},
        "boundaries": boundaries,
        "outcomes": outcomes,
        "wall_time_seconds": round(time.monotonic() - started, 6),
        "ok": ok,
    }
def run_exhaustive(tests_dir: Path, manifest: dict, stream=None, verbosity: int = 1) -> dict:
    """Run every discovered case sequentially as the compatibility oracle."""
    started = time.monotonic()
    cases = discover_cases(tests_dir)
    _, identity_hash = _require_discovery(cases, manifest)
    result = unittest.TextTestRunner(
        stream=stream if stream is not None else sys.stderr, verbosity=verbosity
    ).run(unittest.TestSuite(cases))
    return {
        "schema": "orchflows.serial-compat-observation.v1",
        "mode": "exhaustive",
        "revision": revision(),
        "worktree_clean": worktree_clean(),
        "manifest": manifest_identity(manifest),
        "recorded_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "interpreter": {
            "pid": os.getpid(), "version": sys.version.split()[0], "executable": sys.executable,
        },
        "discovery": {"count": len(cases), "sha256": identity_hash},
        "outcomes": _summary([result]),
        "wall_time_seconds": round(time.monotonic() - started, 6),
        "ok": result.wasSuccessful(),
    }
def build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("selected", "exhaustive"), default="selected")
    parser.add_argument("--manifest", default=str(MANIFEST_PATH))
    parser.add_argument("--tests-dir", default=str(TESTS_DIR))
    parser.add_argument("--record", default=str(RECORD_PATH))
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("--write-manifest", action="store_true")
    return parser
def main(argv=None):
    args = build_parser().parse_args(argv)
    if args.write_manifest:
        sys.path.insert(0, str(ROOT))
        from tools import serial_manifest  # noqa: E402
        return serial_manifest.write_manifest(
            Path(args.manifest), Path(args.tests_dir), discover_cases,
            scan_mutation_owners)
    runner = run_selected if args.mode == "selected" else run_exhaustive
    record = runner(
        Path(args.tests_dir),
        load_manifest(Path(args.manifest)),
        verbosity=2 if args.verbose else 1,
    )
    path = Path(args.record)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, sort_keys=True, indent=1), encoding="utf-8")
    print(json.dumps(record, sort_keys=True))
    return 0 if record["ok"] else 1
if __name__ == "__main__":
    raise SystemExit(main())
