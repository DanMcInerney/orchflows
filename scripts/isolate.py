#!/usr/bin/env python3
"""Build an isolated tree to read a run's oracles on. Stdlib only, 3.9+.

Sibling lanes share one worktree, so a required check run in it reads
every lane at once. This exports one revision, overlays a caller-named
path set from the working tree, and copies the `.orch/runs/<id>/`
directories git ignores but a measurement record's artifact identities
recompute over. `--baseline` stops after the export, so the comparison
reading comes from the same harness rather than a second recipe.

    python scripts/isolate.py /tmp/mine --dirty --exclude docs/notes.md
    python scripts/isolate.py /tmp/base --baseline

A named path absent from the working tree is a deletion and is unlinked
from the export; a named directory is overlaid whole. Anything the
harness cannot do — an unresolvable revision, a path escaping the
repository, a named path present in neither the working tree nor the
export, a named run directory that is not there or that cannot be
copied — is refused by name, never skipped: a tree quietly missing what
a check reads is the same defect as a check that quietly passes.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

ORCH_RUNS = ".orch/runs"


class Refused(Exception):
    """The harness cannot honestly build what was asked for."""


def _git(repo: Path, *args: str) -> str:
    done = subprocess.run(
        ["git", "-C", str(repo)] + list(args),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if done.returncode != 0:
        raise Refused(
            "git {}: {}".format(
                " ".join(args), done.stderr.decode("utf-8", "replace").strip()
            )
        )
    return done.stdout.decode("utf-8", "replace")


def normalize(declared: str) -> str:
    """A repository-relative posix path, or Refused."""
    if not declared or declared.startswith("/") or "\\" in declared:
        raise Refused("path must be relative and forward-slashed: {!r}".format(declared))
    if len(declared) > 1 and declared[1] == ":":
        raise Refused("path must be relative: {!r}".format(declared))
    parts = [part for part in declared.split("/") if part not in ("", ".")]
    if ".." in parts:
        raise Refused("path escapes the repository: {!r}".format(declared))
    if not parts:
        raise Refused("path names the repository root: {!r}".format(declared))
    return "/".join(parts)


def excluded_by(name: str, prefixes) -> bool:
    """A path prefix, compared on whole segments: `docs` never takes `docsmith`."""
    return any(name == prefix or name.startswith(prefix + "/") for prefix in prefixes)


def dirty_paths(repo: Path) -> list:
    """Every path `git status` reports, both ends of a rename included."""
    fields = _git(repo, "status", "--porcelain", "-z").split("\0")
    found, index = [], 0
    while index < len(fields):
        entry = fields[index]
        index += 1
        if not entry:
            continue
        status, path = entry[:2], entry[3:]
        found.append(path)
        if "R" in status or "C" in status:
            if index < len(fields):
                found.append(fields[index])
                index += 1
    return found


def export(repo: Path, rev: str, dest: Path) -> None:
    scratch = tempfile.mkdtemp(prefix="isolate-")
    try:
        archive = str(Path(scratch) / "rev.tar")
        _git(repo, "archive", "--format=tar", "-o", archive, rev)
        with tarfile.open(archive) as tar:
            try:
                tar.extractall(str(dest), filter="tar")
            except TypeError:  # filter= is 3.11.4+
                tar.extractall(str(dest))
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def prune(dest: Path, target: Path) -> None:
    """Drop directories a deletion emptied; a scanner still sees an empty one."""
    parent = target.parent
    while parent != dest and dest in parent.parents:
        try:
            parent.rmdir()
        except OSError:
            return
        parent = parent.parent


def overlay(repo: Path, dest: Path, paths) -> tuple:
    copied = removed = 0
    for name in paths:
        source, target = repo / name, dest / name
        if source.is_dir():
            if target.is_dir():
                shutil.rmtree(str(target))
            elif target.exists():
                target.unlink()
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(str(source), str(target))
            copied += 1
        elif source.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.is_dir():
                shutil.rmtree(str(target))
            shutil.copy2(str(source), str(target))
            copied += 1
        elif target.is_dir():
            shutil.rmtree(str(target))
            prune(dest, target)
            removed += 1
        elif target.exists():
            target.unlink()
            prune(dest, target)
            removed += 1
        else:
            raise Refused(
                "nothing at {} in the working tree or at the revision: a named "
                "path that is nowhere overlays nothing, and the tree then reads "
                "the baseline under a result's name".format(name)
            )
    return copied, removed


def copy_runs(repo: Path, dest: Path, runs) -> None:
    for declared in runs:
        run = normalize(declared)
        source = repo / ORCH_RUNS / run
        if not source.is_dir():
            raise Refused("no run directory at {}/{}".format(ORCH_RUNS, run))
        target = dest / ORCH_RUNS / run
        try:
            if target.exists():
                shutil.rmtree(str(target))
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(str(source), str(target))
        except OSError as error:
            raise Refused("cannot copy {}/{}: {}".format(ORCH_RUNS, run, error))


def build(args) -> str:
    repo = Path(args.repo).resolve()
    dest = Path(args.dest).resolve()
    if dest.exists() and any(dest.iterdir()):
        if not args.force:
            raise Refused("{} is not empty; pass --force to replace it".format(dest))
        shutil.rmtree(str(dest))
    dest.mkdir(parents=True, exist_ok=True)

    declared = list(args.path) + (dirty_paths(repo) if args.dirty else [])
    excluded = tuple(normalize(prefix) for prefix in args.exclude)
    named = sorted(
        {
            name
            for name in (normalize(item) for item in declared)
            if not excluded_by(name, excluded)
        }
    )
    # Baseline ignores the set; it never skips validating it, or the same
    # path would be refused in one mode and accepted in the other.
    paths = [] if args.baseline else named

    export(repo, args.rev, dest)
    copied, removed = overlay(repo, dest, paths)
    copy_runs(repo, dest, args.orch_run)
    return "{} at {}: {} overlaid, {} removed, {} run director{}".format(
        "baseline" if args.baseline else "isolated result",
        args.rev,
        copied,
        removed,
        len(args.orch_run),
        "y" if len(args.orch_run) == 1 else "ies",
    )


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("dest", help="destination directory")
    parser.add_argument("--repo", default=".", help="repository or worktree to read")
    parser.add_argument("--rev", default="HEAD", help="revision to export")
    parser.add_argument("--path", action="append", default=[], help="path to overlay; repeatable")
    parser.add_argument("--dirty", action="store_true", help="overlay every path git status reports")
    parser.add_argument("--exclude", action="append", default=[],
                        help="path prefix, matched on whole segments, to leave at the revision")
    parser.add_argument("--orch-run", action="append", default=[], metavar="RUN_ID",
                        help="gitignored .orch/runs/<RUN_ID>/ to copy in; repeatable")
    parser.add_argument("--baseline", action="store_true", help="export the revision alone")
    parser.add_argument("--force", action="store_true", help="replace a non-empty destination")
    args = parser.parse_args(argv)
    try:
        print(build(args))
    except Refused as refusal:
        print("isolate: {}".format(refusal), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
