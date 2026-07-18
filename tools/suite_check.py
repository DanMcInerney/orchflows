#!/usr/bin/env python3
"""Suite-guard harness. Stdlib-only, decides three acceptance criteria
mechanically:

(a) skip-audit — runs the unit suite with ``-m unittest discover -v``
    and fails on non-zero exit or any skip line whose reason is empty.
(b) snapshot guard — hashes ``.orch/friction/*.jsonl`` and lists
    ``.orch/``, ``~/.claude``, ``~/.codex``, ``~/.orchflows`` before
    and after the run, failing on any difference (the harness itself
    writes only to stdout).
(c) stripped-PATH run — re-runs the suite with PATH rebuilt to only
    the running interpreter's own directory (and a ``Scripts``/``bin``
    sibling, if present), so no `claude`, `codex`, or `npx` on the
    real PATH is resolvable.

Prints one JSON verdict object to stdout: top-level keys ``ok``
(bool), ``phases`` (``suite``, ``snapshot``, ``stripped_path``, each
with their own ``ok``), and ``failures`` (list of human-readable
strings). Exits 0 when ``ok`` is true, 1 otherwise.

Usage:
    python suite_check.py [--repo-root DIR] [--tests-dir DIR]
        [--python EXE] [--home-dir DIR] [--no-home-watch]
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

SKIP_LINE_RE = re.compile(r"^(?P<test_id>\S.*?) \.\.\. skipped (?P<repr>.+?)\s*$")


def audit_skips(output: str) -> list[str]:
    """Return test ids whose skip reason is empty, given -v suite output."""

    violations = []
    for line in output.splitlines():
        match = SKIP_LINE_RE.match(line.rstrip())
        if not match:
            continue
        raw_reason = match.group("repr").strip()
        try:
            reason = ast.literal_eval(raw_reason)
        except (ValueError, SyntaxError):
            reason = raw_reason
        if not str(reason).strip():
            violations.append(match.group("test_id").strip())
    return violations


def hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def snapshot_friction_hashes(repo_root: Path) -> dict[str, str]:
    """Hash every .orch/friction/*.jsonl file, keyed by repo-relative path."""

    friction_dir = repo_root / ".orch" / "friction"
    result: dict[str, str] = {}
    if not friction_dir.is_dir():
        return result
    for path in sorted(friction_dir.glob("*.jsonl")):
        result[str(path.relative_to(repo_root))] = hash_file(path)
    return result


def _is_link_like(path: Path) -> bool:
    """True for symlinks and Windows junctions/reparse points.

    Real home trees (``~/.codex`` worktrees especially) contain pnpm/
    rush-style junctions that point anywhere on the filesystem,
    including outside the watched root — these must be recorded but
    never descended into.
    """

    if path.is_symlink():
        return True
    isjunction = getattr(os.path, "isjunction", None)
    return bool(isjunction and isjunction(path))


def snapshot_tree(root: Path) -> dict[str, str]:
    """Recursively list a tree's entries as {relative_path: marker}.

    Files map to ``file:<size>``, directories to ``dir``, and
    symlinks/junctions to ``link`` (recorded but never descended into,
    since a junction may point outside ``root`` or into a cycle).
    Returns an empty dict when ``root`` does not exist.
    """

    if not root.exists():
        return {}
    root = root.resolve()
    entries: dict[str, str] = {}
    for dirpath, dirnames, filenames in os.walk(root):
        rel_dir = os.path.relpath(dirpath, root)

        real_dirnames = []
        for name in dirnames:
            full = Path(dirpath) / name
            rel = name if rel_dir == "." else str(Path(rel_dir) / name)
            if _is_link_like(full):
                entries[rel] = "link"
                continue
            entries[rel] = "dir"
            real_dirnames.append(name)
        real_dirnames.sort()
        dirnames[:] = real_dirnames
        filenames.sort()

        for name in filenames:
            full = Path(dirpath) / name
            rel = name if rel_dir == "." else str(Path(rel_dir) / name)
            try:
                size = full.stat().st_size
            except OSError:
                size = -1
            entries[rel] = f"file:{size}"
    return entries


def diff_snapshots(
    before: dict[str, str], after: dict[str, str], label: str, added_only: bool = False
) -> list[str]:
    """Return human-readable problems for any added, removed, or changed key.

    With added_only, only additions are problems: the spec bans creating
    new files in watched trees, while live hosts legitimately grow their
    own existing files (e.g. the running session's transcript) during
    any in-session run. Byte-identity is still enforced where required
    via the friction hashes, which never use added_only.
    """

    problems: list[str] = []
    before_keys = set(before)
    after_keys = set(after)
    for added in sorted(after_keys - before_keys):
        problems.append(f"{label}: added {added}")
    if added_only:
        return problems
    for removed in sorted(before_keys - after_keys):
        problems.append(f"{label}: removed {removed}")
    for common in sorted(before_keys & after_keys):
        if before[common] != after[common]:
            problems.append(f"{label}: changed {common}")
    return problems


def build_stripped_path(executable: str) -> str:
    """Return a PATH string of only the running interpreter's directories."""

    exe_dir = Path(executable).resolve().parent
    dirs = [str(exe_dir)]
    for sibling_name in ("Scripts", "bin"):
        candidate = exe_dir / sibling_name
        if candidate.is_dir():
            dirs.append(str(candidate))
    return os.pathsep.join(dict.fromkeys(dirs))


HOME_WATCH_DIRS = (
    ("claude_home", ".claude"),
    ("codex_home", ".codex"),
    ("orchflows_home", ".orchflows"),
)


def collect_snapshot(repo_root: Path, home: Path, watch_home: bool) -> dict:
    snapshot = {
        "friction_hashes": snapshot_friction_hashes(repo_root),
        "trees": {"orch": snapshot_tree(repo_root / ".orch")},
    }
    if watch_home:
        for name, dirname in HOME_WATCH_DIRS:
            snapshot["trees"][name] = snapshot_tree(home / dirname)
    return snapshot


def diff_full_snapshot(before: dict, after: dict) -> list[str]:
    problems = diff_snapshots(before["friction_hashes"], after["friction_hashes"], "friction")
    tree_names = set(before["trees"]) | set(after["trees"])
    for name in sorted(tree_names):
        problems += diff_snapshots(
            before["trees"].get(name, {}), after["trees"].get(name, {}), name, added_only=True
        )
    return problems


def run_suite(python_exe: str, tests_dir: str, cwd: Path, env: dict | None = None) -> tuple[int, str]:
    cmd = [python_exe, "-m", "unittest", "discover", "-s", tests_dir, "-v"]
    completed = subprocess.run(
        cmd,
        cwd=str(cwd),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    return completed.returncode, completed.stdout


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--tests-dir", default="tests")
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument("--home-dir", default=None)
    parser.add_argument("--no-home-watch", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_arg_parser().parse_args(argv)
    repo_root = Path(args.repo_root).resolve()
    home = Path(args.home_dir).resolve() if args.home_dir else Path.home()
    watch_home = not args.no_home_watch

    verdict: dict = {"ok": True, "phases": {}, "failures": []}

    before = collect_snapshot(repo_root, home, watch_home)
    returncode, output = run_suite(args.python, args.tests_dir, repo_root)

    skip_violations = audit_skips(output)
    suite_ok = returncode == 0 and not skip_violations
    verdict["phases"]["suite"] = {
        "ok": suite_ok,
        "returncode": returncode,
        "skip_violations": skip_violations,
    }
    if not suite_ok:
        verdict["ok"] = False
        if returncode != 0:
            verdict["failures"].append(f"suite exited {returncode}")
        for test_id in skip_violations:
            verdict["failures"].append(f"skip without reason: {test_id}")

    stripped_path = build_stripped_path(args.python)
    env = dict(os.environ)
    env["PATH"] = stripped_path
    sp_returncode, sp_output = run_suite(args.python, args.tests_dir, repo_root, env=env)
    sp_skip_violations = audit_skips(sp_output)
    sp_ok = sp_returncode == 0 and not sp_skip_violations
    verdict["phases"]["stripped_path"] = {
        "ok": sp_ok,
        "returncode": sp_returncode,
        "path": stripped_path,
        "skip_violations": sp_skip_violations,
    }
    if not sp_ok:
        verdict["ok"] = False
        verdict["failures"].append(f"stripped-path suite exited {sp_returncode}")
        for test_id in sp_skip_violations:
            verdict["failures"].append(f"stripped-path skip without reason: {test_id}")

    # Closing snapshot taken only after the stripped-path rerun, so
    # contamination from either suite run is caught.
    after = collect_snapshot(repo_root, home, watch_home)
    snapshot_problems = diff_full_snapshot(before, after)
    verdict["phases"]["snapshot"] = {"ok": not snapshot_problems, "violations": snapshot_problems}
    if snapshot_problems:
        verdict["ok"] = False
        verdict["failures"].extend(snapshot_problems)

    print(json.dumps(verdict))
    return 0 if verdict["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
