#!/usr/bin/env python3
"""Resolve a write scope to the test shard modules that can observe it.

Static AST and string-literal scan only: nothing under the scanned tree is
imported, so a test file that cannot be parsed -- or that would run work at
import -- can sit in the tree without deciding this answer.

The unit of the answer is the shard ``tools/run_tests.py`` schedules: a
top-level ``tests/test_<x>.py``. An edge found inside
``tests/test_<x>_cases/**/*.py`` is attributed to ``tests.test_<x>``, because
that case module has no process of its own.

The scan over-approximates on purpose. A missed module is a regression that
ships; a surplus module only costs time.

Usage:
    python tools/affected_tests.py [--root DIR] [--tests-dir DIR]
        [--format lines|json|argv] PATH [PATH ...]
"""

from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCHEMA = "orchflows.affected-tests.v1"
CASE_SUFFIX = "_cases"


# --- reading the tree -------------------------------------------------
def shard_files(tests_dir: Path):
    """Return (module-name prefix, {shard module: [files it owns]}).

    ``test*.py`` is the pattern ``tools/run_tests.py`` and ``unittest
    discover`` both use, so the shard set here is the shard set that runs.
    """

    prefix = tests_dir.name + "." if (tests_dir / "__init__.py").is_file() else ""
    owned = {}
    for path in sorted(tests_dir.glob("test*.py")):
        files = [path]
        cases = tests_dir / (path.stem + CASE_SUFFIX)
        if cases.is_dir():
            files.extend(sorted(cases.rglob("*.py")))
        owned[prefix + path.stem] = files
    return prefix, owned


def read_facts(path: Path):
    """Return ({dotted import targets}, {string literals}) for one file."""

    tree = ast.parse(path.read_text(encoding="utf-8"))
    imports, literals = set(), set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
            imports.add(node.module)
            for alias in node.names:
                imports.add(node.module + "." + alias.name)
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            literals.add(node.value)
    return imports, literals


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
    return text.lstrip("./") or text


def dotted_names(rel: str):
    """Return every dotted module name an importer could spell this path as."""

    parts = [part for part in rel.split("/") if part]
    if parts and parts[-1].endswith(".py"):
        parts[-1] = parts[-1][:-3]
    if parts and parts[-1] == "__init__":
        parts.pop()
    return {".".join(parts[index:]) for index in range(len(parts))}


def literal_forms(rel: str, is_dir: bool):
    """Return the exact string literals that name this path directly."""

    name = rel.split("/")[-1]
    forms = {rel, rel.replace("/", "\\"), name}
    if not is_dir and name.endswith(".py"):
        # ``spec_from_file_location("friction", ROOT / "scripts" / "friction.py")``
        # names the module by its stem and the file by its base name; both are
        # separate literals in the tree.
        forms.add(name[:-3])
    return forms


def describe(raw, root: Path) -> dict:
    """Return the match description for one scope path."""

    rel = relative(raw, root)
    is_dir = (root / rel).is_dir() if rel else False
    return {
        "rel": rel,
        "is_dir": is_dir,
        "dotted": dotted_names(rel),
        "literals": literal_forms(rel, is_dir),
    }


# --- matching ---------------------------------------------------------
def matches(facts, scope: dict) -> bool:
    """Decide whether one test file's facts reach one scope path."""

    imports, literals = facts
    for target in imports:
        for dotted in scope["dotted"]:
            if dotted and (target == dotted or target.startswith(dotted + ".")):
                return True
    rel = scope["rel"]
    for literal in literals:
        text = literal.replace("\\", "/")
        if literal in scope["literals"] or text in scope["literals"]:
            return True
        if not rel:
            continue
        if scope["is_dir"]:
            if (
                text == rel
                or text.startswith(rel + "/")
                or text.endswith("/" + rel)
                or ("/" + rel + "/") in text
            ):
                return True
        elif rel in text:
            return True
    return False


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


# --- the answer -------------------------------------------------------
def affected(paths, root=ROOT, tests_dir=None) -> dict:
    """Return the shard modules every given scope path can be observed by."""

    root = Path(root)
    tests_dir = Path(tests_dir) if tests_dir else root / "tests"
    prefix, owned = shard_files(tests_dir)
    try:
        tests_rel = tests_dir.resolve().relative_to(root.resolve()).as_posix()
    except (OSError, ValueError):
        tests_rel = ""

    facts, unreadable = {}, []
    for module, files in owned.items():
        for path in files:
            try:
                facts.setdefault(module, []).append(read_facts(path))
            except (OSError, UnicodeDecodeError, SyntaxError, ValueError) as error:
                unreadable.append(
                    {"path": relative(path, root), "reason": type(error).__name__}
                )

    selected, no_tests, scope_rels = set(), [], []
    for raw in paths:
        scope = describe(raw, root)
        scope_rels.append(scope["rel"])
        hits = set(own_shards(scope, tests_rel, owned, prefix))
        hits.update(
            module
            for module, module_facts in facts.items()
            if any(matches(entry, scope) for entry in module_facts)
        )
        if hits:
            selected.update(hits)
        else:
            no_tests.append(scope["rel"])
    return {
        "root": root.as_posix(),
        "scope": scope_rels,
        "modules": sorted(selected),
        "no_tests": no_tests,
        "unreadable": sorted(unreadable, key=lambda entry: entry["path"]),
    }


# --- entry point ------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="affected_tests.py",
        description="Print the test shard modules a write scope can be seen by.",
    )
    parser.add_argument("paths", metavar="PATH", nargs="+", help="scope file or directory")
    parser.add_argument("--root", default=str(ROOT), help="repository root (default: this checkout)")
    parser.add_argument("--tests-dir", help="directory of test*.py (default: <root>/tests)")
    parser.add_argument(
        "--format",
        choices=("lines", "json", "argv"),
        default="lines",
        help="lines: one module per line; argv: the run_tests.py MODULE list; json: the record",
    )
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    result = affected(args.paths, root=Path(args.root), tests_dir=args.tests_dir)
    # Residue and refusals go to the error stream in every format, so that
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
