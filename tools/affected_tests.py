#!/usr/bin/env python3
"""Resolve a write scope to the test shard modules that can observe it.

The answer is a pure function of one committed revision. Discovery reads the
tree out of the commit, never off disk, so an untracked file, an uncommitted
edit and a directory that exists only in the working tree are all immaterial:
the same scope run twice in one worktree yields one answer. It is recorded once
per revision and served from a cache keyed by the tree identity, in the
runner's own gitignored runtime directory -- runtime state, never a commit's.

The edges are measured imports. Every ``.py`` file in the revision is parsed
once and its imports resolved to the revision's own files -- relative imports
included, at any level -- so a shard is selected for every file its imports
reach *transitively*. That is what a per-file scan could not see:
``tests/test_tickets_lint.py`` names only the ticket facade, and the facade
imports ``scripts/tickets_lint.py`` on its behalf.

String literals are a signal about the file that spells them, not a path
through the graph. A shard's own files match by every form -- base name and
stem included, as ``spec_from_file_location`` names a file it never imports; a
file the shard only reaches matches by exact repository-relative path alone.
Loose literals as graph edges were measured to fuse this repository into one
component that selects every shard for every scope.

Nothing under the scanned tree is imported: it is parsed. A test file that
cannot be parsed, or that would run work at import, does not decide this answer.
The unit of the answer is the shard ``tools/run_tests.py`` schedules: a
top-level ``tests/test_<x>.py``. An edge inside ``tests/test_<x>_cases/**/*.py``
is attributed to ``tests.test_<x>``, which has the only process. The scan
over-approximates on purpose: a missed module is a regression that ships, a
surplus module only costs time.

Usage:
    python tools/affected_tests.py [--root DIR] [--tests-dir DIR]
        [--format lines|json|argv] [--no-cache] PATH [PATH ...]
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

# Run directly (`python tools/affected_tests.py`) or imported as
# `tools.affected_tests` before the repository is necessarily on
# sys.path; reading `scripts._bootstrap.ROOT` would need this same walk
# to seed the import first, for no fact this file otherwise needs from
# `scripts/`.
ROOT = Path(__file__).resolve().parent.parent
SCHEMA = "orchflows.affected-tests.v1"
# The record's shape is in its kind and its kind is in the cache key, so a
# record written by a resolver that measured something else is never served.
RECORD_KIND = "orchflows.affected-tests.discovery/v2"
CASE_SUFFIX = "_cases"
CACHE_LEAF = "affected_cache"
SKIP_DIRECTORIES = frozenset({".git", "__pycache__"})


# --- reading one revision ---------------------------------------------
def git(root: Path, *arguments: str):
    """Run one git command in ``root``; ``None`` when it cannot answer."""

    try:
        done = subprocess.run(["git"] + list(arguments), cwd=str(root),
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except OSError:  # git itself is absent from this host
        return None
    return None if done.returncode else done.stdout.decode("utf-8", "replace")


def revision_tree(root: Path):
    """``(tree identity, [path], {py path: source})`` for HEAD, or None.

    Every blob is read in one ``git cat-file --batch`` pass, not one per file.
    """

    tree = (git(root, "rev-parse", "HEAD^{tree}") or "").strip()
    listed = git(root, "ls-tree", "-r", "--name-only", "-z", tree) if tree else None
    if listed is None:
        return None
    names = [name for name in listed.split("\0") if name]
    wanted = [name for name in names if name.endswith(".py")]
    try:
        batch = subprocess.Popen(["git", "cat-file", "--batch"], cwd=str(root),
                                 stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
    except OSError:
        return None
    request = "".join("{0}:{1}\n".format(tree, name) for name in wanted)
    payload = batch.communicate(request.encode("utf-8"))[0]
    sources, position = {}, 0
    for name in wanted:
        end = payload.find(b"\n", position)
        header = payload[position:end].decode("utf-8", "replace").split() if end >= 0 else []
        if len(header) != 3:  # "<request> missing", or a truncated stream
            sources[name] = None
            position = end + 1 if end >= 0 else position
            continue
        start, size = end + 1, int(header[2])
        sources[name] = payload[start:start + size].decode("utf-8", "replace")
        position = start + size + 1  # the batch writes one LF after each blob
    return tree, names, sources


def working_tree(root: Path, skip: str):
    """Return ``([path], {py path: source})`` from disk, for a tree with no HEAD."""

    skipped = SKIP_DIRECTORIES | ({skip} if skip else set())
    names, sources = [], {}
    for path in sorted(root.rglob("*")):
        parts = path.relative_to(root).parts
        if not path.is_file() or skipped.intersection(parts):
            continue
        names.append("/".join(parts))
        if names[-1].endswith(".py"):
            try:
                sources[names[-1]] = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                sources[names[-1]] = None
    return names, sources


# --- what one file says -----------------------------------------------
def facts_from_source(source: str, rel: str = ""):
    """Return ({dotted import targets}, {string literals}) for one source.

    A relative import is an edge like any other, and its level says which
    package it counts from. Dropping it lost the entire fan-out behind every
    facade that spells its own family that way.
    """

    imports, literals = set(), set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            parts = rel.split("/")[:-1] if node.level else []
            if node.level > 1:
                parts = parts[: 1 - node.level] if node.level <= len(parts) + 1 else []
            base = ".".join(p for p in (parts + [node.module] if node.module
                                        else parts) if p)
            if base:
                imports.add(base)
                for alias in node.names:
                    imports.add(base + "." + alias.name)
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            literals.add(node.value)
    return imports, literals


def read_facts(path: Path, rel: str = ""):
    """Return ({dotted import targets}, {string literals}) for one file."""

    return facts_from_source(Path(path).read_text(encoding="utf-8"), rel)


# --- describing one scope path ----------------------------------------
def relative(raw, root: Path) -> str:
    """Return the repository-relative POSIX form of one scope path."""

    text = str(raw).replace("\\", "/").strip().rstrip("/")
    candidate = Path(text)
    if candidate.is_absolute():
        try:
            text = candidate.resolve().relative_to(root.resolve()).as_posix()
        except (OSError, ValueError):
            text = candidate.as_posix()
    # Strip a leading ``./`` and a leading root slash, never a character set:
    # this repository's scope paths include ``.github/``, ``.orch/`` and
    # ``.claude/``, whose leading dot is part of the name.
    text = text.lstrip("/")
    while text.startswith("./"):
        text = text[2:]
    return text


def dotted_names(rel: str):
    """Return every dotted module name an importer could spell this path as."""

    parts = [part for part in rel.split("/") if part]
    if parts and parts[-1].endswith(".py"):
        parts[-1] = parts[-1][:-3]
    if parts and parts[-1] == "__init__":
        parts.pop()
    return {".".join(parts[index:]) for index in range(len(parts))}


def literal_forms(rel: str, is_dir: bool):
    """Return the exact string literals that name this path directly.

    ``spec_from_file_location("friction", ROOT / "scripts" / "friction.py")``
    names the module by its stem and the file by its base name; both are
    separate literals in the tree.
    """

    name = rel.split("/")[-1]
    forms = {rel, rel.replace("/", "\\"), name}
    if not is_dir and name.endswith(".py"):
        forms.add(name[:-3])
    return forms


def describe(raw, root: Path, is_dir=None) -> dict:
    """Return the match description for one scope path.

    ``is_dir`` is answered by the revision where one is given, never by the
    filesystem: a directory that exists only on disk must not move an answer.
    """

    rel = relative(raw, root)
    directory = bool(rel) and (
        (root / rel).is_dir() if is_dir is None else is_dir(rel))
    return {"rel": rel, "is_dir": directory, "dotted": dotted_names(rel),
            "literals": literal_forms(rel, directory)}


# --- matching ---------------------------------------------------------
def matches(facts, scope: dict) -> bool:
    """Decide whether one shard's own literals reach one scope path."""

    literals = facts[1]
    rel = scope["rel"]
    for literal in literals:
        text = literal.replace("\\", "/")
        if literal in scope["literals"] or text in scope["literals"]:
            return True
        if not rel:
            continue
        if scope["is_dir"]:
            if (text == rel or text.startswith(rel + "/")
                    or text.endswith("/" + rel) or ("/" + rel + "/") in text):
                return True
        elif rel in text:
            return True
    return False


def reaches(facts: dict, scope: dict) -> bool:
    """Decide whether one shard reaches one scope path at all."""

    rel, files = scope["rel"], facts["files"]
    if rel and (rel in files or rel in facts["paths"]
                or (scope["is_dir"]
                    and any(n.startswith(rel + "/") for n in files))):
        return True
    return matches((None, facts["literals"]), scope)


def own_shards(scope: dict, tests_rel: str, modules, prefix: str):
    """Return the shards a scope path under the tests tree names outright."""

    rel = scope["rel"]
    if not tests_rel or not (rel == tests_rel or rel.startswith(tests_rel + "/")):
        return []
    if rel == tests_rel:
        return list(modules)
    head = rel[len(tests_rel) + 1:].split("/")[0]
    stem = head[:-3] if head.endswith(".py") else head
    if stem.endswith(CASE_SUFFIX):
        stem = stem[: -len(CASE_SUFFIX)]
    return [prefix + stem] if prefix + stem in modules else []


# --- the shards a tree holds ------------------------------------------
def shard_names(names, tests_rel: str):
    """Return (prefix, {shard module: [files it owns]}) for one path list.

    ``test*.py`` is the pattern ``tools/run_tests.py`` and ``unittest
    discover`` both use, so the shard set here is the shard set that runs.
    """

    if not tests_rel:
        return "", {}
    listed = set(names)
    prefix = (tests_rel.split("/")[-1] + "."
              if (tests_rel + "/__init__.py") in listed else "")
    owned, cases = {}, {}
    for name in sorted(listed):
        if not name.startswith(tests_rel + "/"):
            continue
        rest = name[len(tests_rel) + 1:]
        head = rest.split("/")[0]
        if "/" not in rest and head.startswith("test") and head.endswith(".py"):
            owned[prefix + head[:-3]] = [name]
        elif head.endswith(CASE_SUFFIX) and name.endswith(".py"):
            cases.setdefault(prefix + head[: -len(CASE_SUFFIX)], []).append(name)
    for module, owned_cases in cases.items():
        if module in owned:
            owned[module].extend(owned_cases)
    return prefix, owned


def shard_files(tests_dir: Path):
    """The same shard map, read off disk, with each file as a path."""

    tests_dir = Path(tests_dir)
    listed = [tests_dir.name + "/" + path.relative_to(tests_dir).as_posix()
              for path in sorted(tests_dir.rglob("*")) if path.is_file()]
    prefix, owned = shard_names(listed, tests_dir.name)
    return prefix, {module: [tests_dir.parent / name for name in files]
                    for module, files in owned.items()}


# --- discovery --------------------------------------------------------
def runtime_directory_name() -> str:
    """The gitignored runtime directory, asked of the runner that owns it."""

    try:
        from tools import run_tests
    except ImportError:  # run as ``python tools/affected_tests.py``
        import run_tests

    return run_tests.CACHE_PATH.parent.name


def cache_dir(root: Path) -> Path:
    """Where one checkout's discovery records live. Never a commit's."""

    return Path(root) / runtime_directory_name() / CACHE_LEAF


def cache_entry(root: Path, tree: str, tests_rel: str) -> Path:
    """The one file this revision's discovery is recorded in."""

    hasher = hashlib.sha256()
    for item in (RECORD_KIND, tree, tests_rel):
        hasher.update(item.encode("utf-8") + b"\0")
    return cache_dir(root) / (hasher.hexdigest() + ".json")


def cache_load(path: Path):
    """The stored record, or None when this file is not one of ours."""

    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return record if record.get("kind") == RECORD_KIND else None


def cache_store(path: Path, record: dict) -> None:
    """Write one record atomically; a memo never fails a run for its own sake."""

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        handle, temporary = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            json.dump(record, stream, sort_keys=True)
        os.replace(temporary, str(path))
    except OSError:
        pass


def measure(names, sources, tests_rel: str):
    """Return ``(prefix, {shard: facts}, unreadable)`` for one revision."""

    prefix, owned = shard_names(names, tests_rel)
    facts, reasons, index = {}, {}, {}
    for rel, source in sources.items():
        try:
            facts[rel] = facts_from_source(source, rel)
        except (SyntaxError, ValueError, TypeError) as error:
            facts[rel] = None
            reasons[rel] = "OSError" if source is None else type(error).__name__
        for dotted in dotted_names(rel):
            if dotted:
                index.setdefault(dotted, set()).add(rel)

    # Every resolvable prefix of an import counts: ``import scripts.deep.inner``
    # executes the two package bodies on the way, and either can be what changed.
    edges = {}
    for rel, entry in facts.items():
        reached = set()
        for target in entry[0] if entry else ():
            parts = target.split(".")
            for stop in range(1, len(parts) + 1):
                reached.update(index.get(".".join(parts[:stop]), ()))
        edges[rel] = reached - {rel}

    listed, shards, unreadable = set(names), {}, []
    for module, files in owned.items():
        own = set(files)
        for rel in sorted(own):
            if facts.get(rel, ()) is None:
                unreadable.append({"path": rel, "reason": reasons[rel]})
        literals, paths, seen, pending = set(), set(), set(), list(own)
        while pending:  # every file this shard's imports reach, transitively
            rel = pending.pop()
            if rel in seen:
                continue
            seen.add(rel)
            pending.extend(edges.get(rel, ()))
            entry = facts.get(rel)
            if entry is None:
                continue
            if rel in own:
                literals.update(entry[1])
            else:
                # Only an exact repository-relative path: a reached file's base
                # names and stems are too loose to carry this far.
                paths.update(text for text in
                             (lit.replace("\\", "/") for lit in entry[1])
                             if text in listed)
        shards[module] = {"files": sorted(seen), "literals": sorted(literals),
                          "paths": sorted(paths)}
    return prefix, shards, unreadable


def discover(root: Path, tests_dir: Path, use_cache: bool = True) -> dict:
    """Record this revision's shard facts once, and serve them thereafter."""

    try:
        tests_rel = tests_dir.resolve().relative_to(root.resolve()).as_posix()
    except (OSError, ValueError):
        tests_rel = ""
    revision = revision_tree(root) if tests_rel else None
    if revision is None:
        tree, entry = None, None
        names, sources = working_tree(root, runtime_directory_name())
    else:
        tree, names, sources = revision
        entry = cache_entry(root, tree, tests_rel)
        stored = cache_load(entry) if use_cache else None
        if stored is not None:
            return dict(stored, cached=True)
    prefix, shards, unreadable = measure(names, sources, tests_rel)
    record = {
        "kind": RECORD_KIND, "source": "filesystem" if tree is None else "git",
        "tree": tree, "tests_rel": tests_rel, "prefix": prefix,
        "shards": shards, "unreadable": unreadable, "cached": False,
        "directories": sorted({n.rsplit("/", 1)[0] for n in names if "/" in n}),
    }
    if entry is not None and use_cache:
        cache_store(entry, record)
    return record


# --- the answer -------------------------------------------------------
def affected(paths, root=ROOT, tests_dir=None, use_cache: bool = True) -> dict:
    """Return the shard modules every given scope path can be observed by."""

    root = Path(root)
    tests_dir = Path(tests_dir) if tests_dir else root / "tests"
    record = discover(root, tests_dir, use_cache)
    shards, prefix = record["shards"], record["prefix"]
    directories = set(record["directories"])

    selected, no_tests, scope_rels = set(), [], []
    for raw in paths:
        scope = describe(raw, root, lambda rel: rel in directories)
        scope_rels.append(scope["rel"])
        hits = set(own_shards(scope, record["tests_rel"], shards, prefix))
        hits.update(module for module, facts in shards.items()
                    if reaches(facts, scope))
        if hits:
            selected.update(hits)
        else:
            no_tests.append(scope["rel"])
    return {
        "root": root.as_posix(),
        "scope": scope_rels,
        "modules": sorted(selected),
        "no_tests": no_tests,
        "unreadable": sorted(record["unreadable"], key=lambda e: e["path"]),
        "discovery": {key: record[key] for key in ("source", "tree", "cached")},
    }


# --- entry point ------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="affected_tests.py",
        description="Print the test shard modules a write scope can be seen by.")
    parser.add_argument("paths", metavar="PATH", nargs="+", help="scope file or directory")
    parser.add_argument("--root", default=str(ROOT), help="repository root (default: this checkout)")
    parser.add_argument("--tests-dir", help="directory of test*.py (default: <root>/tests)")
    parser.add_argument(
        "--no-cache", action="store_true",
        help="neither read nor write the discovery record for this revision")
    parser.add_argument(
        "--format", choices=("lines", "json", "argv"), default="lines",
        help="lines: one module per line; argv: the run_tests.py MODULE list; json: the record")
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    result = affected(args.paths, root=Path(args.root), tests_dir=args.tests_dir,
                      use_cache=not args.no_cache)
    # Residue goes to the error stream in every format, so that
    # `run_tests.py $(affected_tests.py --format argv ...)` stays a clean list.
    for entry in result["unreadable"]:
        print("affected_tests: unreadable %s (%s)" % (entry["path"], entry["reason"]), file=sys.stderr)
    for path in result["no_tests"]:
        print("no-tests: " + path, file=sys.stderr)
    if args.format == "json":
        print(json.dumps(dict(result, schema=SCHEMA), indent=1, sort_keys=True))
    elif args.format == "argv":
        if result["modules"]:
            print(" ".join(result["modules"]))
    else:
        for module in result["modules"]:
            print(module)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
