#!/usr/bin/env python3
"""Build an isolated tree to read a run's oracles on. Stdlib only, 3.9+.

Sibling lanes share one worktree, so a required check run in it reads
every lane at once. This exports one revision, overlays a caller-named
path set from the working tree, and copies caller-named runs out of the
user-scope state sink into a snapshot inside the tree, which a
measurement record's artifact identities recompute over. A check reading
run state in the tree points `ORCHFLOWS_STATE_HOME` at that snapshot, so
it reads the revision's state rather than whatever the live sink holds
by then. `--baseline` stops after the export, so the comparison reading
comes from the same harness rather than a second recipe.

    python scripts/isolate.py ../isolated/mine --dirty --exclude docs/notes.md
    python scripts/isolate.py ../isolated/base --baseline

A destination inside the host's system temp root is built, and said so:
`tools/run_tests.py`'s `meaningful_sys_path` reads paths there as dead
scratch, so a suite run in one reads differently about itself and a red
there can mean only "you ran me in the temp root". The harness refuses
nothing over it -- a caller who meant it gets the tree -- but the report
names it rather than leaving the reader to discover it in a verdict.

A named path absent from the working tree is a deletion and is unlinked
from the export; a named directory is overlaid whole. Anything the
harness cannot do — an unresolvable revision, a path escaping the
repository, a named path present in neither the working tree nor the
export, a named run directory that is not there or that cannot be
copied — is refused by name, never skipped: a tree quietly missing what
a check reads is the same defect as a check that quietly passes. The one
thing it does with less than it asked for is extract without
`tarfile`'s `filter=` on an interpreter that predates it — 3.12, or the
3.8.17/3.9.17/3.10.12/3.11.4 backports — and that is named on stderr
rather than taken silently.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

try:  # in-repo; the installed copy sits flat beside tickets.py
    from scripts import console, state_root
    from scripts.workspace_git import dirty_paths as _walk_dirty_paths
except ImportError:  # pragma: no cover - the installed copy's path
    import console
    import state_root
    from workspace_git import dirty_paths as _walk_dirty_paths

# Where the snapshot lands inside the isolated tree. Not a second sink root
# -- `scripts/state_root.py` owns that -- but a copy of one, laid out the
# same way, so `ORCHFLOWS_STATE_HOME` can be pointed at it unchanged.
SINK_COPY = ".orchflows-state"


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
    """`workspace_git.dirty_paths`, read through this harness's own git.

    The porcelain walk is one fact and has one owner. What differs between
    the two callers is how each reaches git and how each refuses, so those
    stay here: `_git` raises this module's `Refused` with its own sentence,
    which is why the adapter never has a non-zero code to report.
    """
    return _walk_dirty_paths(repo, lambda cwd, *args: (0, _git(cwd, *args), ""))


def export(repo: Path, rev: str, dest: Path) -> None:
    scratch = tempfile.mkdtemp(prefix="isolate-")
    try:
        archive = str(Path(scratch) / "rev.tar")
        _git(repo, "archive", "--format=tar", "-o", archive, rev)
        with tarfile.open(archive) as tar:
            try:
                tar.extractall(str(dest), filter="tar")
            except TypeError:  # filter= is 3.12+ and the backports
                # (3.8.17/3.9.17/3.10.12/3.11.4), so "below 3.12" does not
                # settle it and this asks rather than reads a version.
                # Nothing here is skipped without saying so: this host's
                # interpreter cannot ask for the filter, so the extraction
                # is the unfiltered one and the report says which it was.
                print(
                    "isolate: this interpreter has no tarfile filter= "
                    "(3.12, or the 3.8.17/3.9.17/3.10.12/3.11.4 backports); "
                    "extracting unfiltered",
                    file=sys.stderr,
                )
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


def copy_runs(dest: Path, runs) -> None:
    """Snapshot each named run out of the sink into the isolated tree.

    The source is the one user-scope sink, so a run is copyable from any
    workspace in any repository -- including one whose repository never held
    run state at all. The layout inside the snapshot is the sink's own,
    derived from it rather than restated here.
    """

    sink = state_root.state_root()
    for declared in runs:
        run = normalize(declared)
        source = state_root.runs_root() / run
        # `normalize` has already refused every `..`, so this stays inside.
        relative = source.relative_to(sink).as_posix()
        if not source.is_dir():
            raise Refused("no run directory in the state sink at {}".format(relative))
        target = dest / SINK_COPY / relative
        try:
            if target.exists():
                shutil.rmtree(str(target))
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(str(source), str(target))
        except OSError as error:
            raise Refused("cannot copy {}: {}".format(relative, error))


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
    copy_runs(dest, args.orch_run)
    report = "{} at {}: {} overlaid, {} removed, {} run director{}".format(
        "baseline" if args.baseline else "isolated result",
        args.rev,
        copied,
        removed,
        len(args.orch_run),
        "y" if len(args.orch_run) == 1 else "ies",
    )
    # Where to point `ORCHFLOWS_STATE_HOME`; silent when nothing was copied,
    # because naming an empty snapshot invites a check to read one.
    if args.orch_run:
        report = "{} in {}/".format(report, SINK_COPY)
    # Named, never refused. The rule is `state_root.inside_temp_root`'s and
    # `tools/verify_at.py` refuses on it, because a checker's verdict has to
    # be the repository's. This harness builds trees a caller reads by hand
    # as often as a check does, so it says what it built and hands it over.
    if state_root.inside_temp_root(dest):
        report += (
            "\nisolate: warning: {} is inside the system temp root; a suite "
            "run there reads its own scratch paths as dead and can go red for "
            "its location alone".format(dest)
        )
    return report


def main(argv=None) -> int:
    console.harden()
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("dest", help="destination directory")
    parser.add_argument("--repo", default=".", help="repository or worktree to read")
    parser.add_argument("--rev", default="HEAD", help="revision to export")
    parser.add_argument("--path", action="append", default=[], help="path to overlay; repeatable")
    parser.add_argument("--dirty", action="store_true", help="overlay every path git status reports")
    parser.add_argument("--exclude", action="append", default=[],
                        help="path prefix, matched on whole segments, to leave at the revision")
    parser.add_argument("--orch-run", action="append", default=[], metavar="RUN_ID",
                        help="run id to copy from the state sink into "
                             "{}/runs/<RUN_ID>/; repeatable".format(SINK_COPY))
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
    sys.exit(console.run(main))
