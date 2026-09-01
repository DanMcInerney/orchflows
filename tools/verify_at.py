#!/usr/bin/env python3
"""Run one command in a detached worktree at an exact revision, then leave.

A checker's verdict is only worth what its vantage is worth: the wrong
revision, or the right one in the wrong place, and the verdict answers a
question nobody asked. Roughly eight contexts across two runs composed the
same `git worktree add --detach` / run / `remove --force` / `prune`
choreography by hand and disagreed on three points, so all three are settled
here once.

Where. The checkout is created outside `tempfile.gettempdir()`, and a root
inside it is refused rather than silently used. A checkout under the system
temp root is not merely untidy: `tools/run_tests.py`'s `meaningful_sys_path`
treats paths there as dead scratch, so the suite reads differently about
itself depending on where it happens to be standing, and a red that means
only "you ran me in the temp root" is indistinguishable from a real one.

What comes back. The command's own exit status is this tool's own, so a
caller reads a verdict rather than a translation of one. `125` -- git's
"could not run it" status -- is what this runner returns when it refuses,
every refusal included, a usage error among them: argparse would spend `2`
there, and `2` is a status a command could have returned. One ambiguity
survives and is worth naming rather than glossing: a command may itself exit
`125`. The report line is what separates the two -- a run names the worktree
it stood in, a refusal names why it never got one -- so a caller who must
tell them apart reads that line and not the status.

Which stream. The two streams are never merged. The command inherits this
process's stdout and stderr, so its output stays live and stays sorted; this
tool's own one-line report goes to stderr, leaving stdout carrying the
command's output alone.

Stdlib only, Python 3.9+, POSIX and Windows.

Usage:
    python tools/verify_at.py REVISION [--repo DIR] [--root DIR] [--keep]
                              -- COMMAND [ARG ...]

Exit: the command's status, or 125 when this runner refuses.
    `--help` prints this usage without a command or a `--` separator.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path

# This is the walk that makes `scripts/state_root` (below) importable at
# all, so it cannot itself come from `scripts._bootstrap.ROOT`.
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Where a path lies is `scripts/state_root.py`'s fact, not this file's:
# `scripts/isolate.py` asks the same question about the tree it builds,
# and two copies of one rule are two rules the moment either is edited.
# `tools` may import `scripts`; the reverse is what is forbidden.
from scripts.state_root import inside_temp_root  # noqa: E402
# git's own "the harness could not run it" status, borrowed for the same
# meaning: every other status this process returns is the command's.
REFUSAL_STATUS = 125
# The seams that aim a git command at a repository other than the one named
# on the command line. Inherited, they point the new worktree's git -- and
# the command's own git calls -- back at the caller's index.
GIT_SEAMS = ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR")
# Kept out of the temp root by construction, not by luck: the home
# directory is writable, stable across a host's runs, and is not swept by
# whatever cleans the system scratch area mid-run.
ROOT_LEAF = ".orchflows-verify-at"


class Refusal(Exception):
    """The runner cannot honestly run that command at that revision."""


def child_env() -> dict:
    """This process's environment with every git seam dropped."""

    env = dict(os.environ)
    for name in GIT_SEAMS:
        env.pop(name, None)
    return env


def git(repo, *args: str):
    """One git command in `repo`, its streams captured for a reader."""

    return subprocess.run(
        ["git", "-C", os.fspath(repo), *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=child_env(),
    )


def _text(raw: bytes) -> str:
    return raw.decode("utf-8", "replace").strip()


def default_root() -> Path:
    """Where worktrees go when the caller names no root."""

    return Path.home() / ROOT_LEAF


def resolve_revision(repo, revision: str) -> str:
    """The one commit `revision` names, refusing every other answer.

    `^{commit}` is what makes this exact: a tag, a branch, or an ambiguous
    short name either resolves to one commit or does not resolve.
    """

    done = git(repo, "rev-parse", "--verify", "--quiet", revision + "^{commit}")
    commit = _text(done.stdout)
    if done.returncode != 0 or not commit:
        raise Refusal(
            "no such revision in {0}: {1}".format(os.fspath(repo), revision)
        )
    return commit


def remove(repo, path) -> None:
    """Take the checkout out of the tree and out of the repository's records.

    Both halves run: `remove --force` deletes a checkout the command may have
    dirtied along with its administrative entry, and `prune` is what clears
    that entry when the directory went away by some other hand.
    """

    if git(repo, "worktree", "remove", "--force", os.fspath(path)).returncode != 0:
        shutil.rmtree(os.fspath(path), ignore_errors=True)
    git(repo, "worktree", "prune")


def run_at(repo, revision, command, root=None, keep=False,
           stdout=None, stderr=None) -> dict:
    """Run `command` at `revision`, and clean up whatever it did.

    `stdout` and `stderr` are handed to the child unchanged and default to
    this process's own, which is what keeps the two apart: there is no
    argument that would merge them.
    """

    repo = Path(repo).resolve()
    if git(repo, "rev-parse", "--git-dir").returncode != 0:
        raise Refusal("not a git checkout: {0}".format(os.fspath(repo)))
    root = default_root() if root is None else Path(root).resolve()
    if inside_temp_root(root):
        raise Refusal(
            "worktree root is inside the system temp root ({0}): a checkout "
            "there changes what the suite's own scratch-path rules say about "
            "it, so its verdict would not be the repository's -- name a "
            "--root elsewhere".format(tempfile.gettempdir())
        )
    commit = resolve_revision(repo, revision)
    root.mkdir(parents=True, exist_ok=True)
    # Unique per run: two checkers may hold the same revision at once.
    path = root / "{0}-{1}-{2}".format(repo.name, commit[:12], uuid.uuid4().hex[:8])
    added = git(repo, "worktree", "add", "--detach", os.fspath(path), commit)
    if added.returncode != 0:
        raise Refusal("git worktree add failed: {0}".format(_text(added.stderr)))
    try:
        try:
            done = subprocess.run(
                list(command),
                cwd=os.fspath(path),
                env=child_env(),
                stdout=stdout,
                stderr=stderr,
            )
        except OSError as error:
            raise Refusal("command is not runnable: {0}".format(error))
        status = done.returncode
    finally:
        if not keep:
            remove(repo, path)
    return {
        "exit": status,
        "revision": commit,
        "worktree": os.fspath(path),
        "kept": bool(keep),
        # Observed, never inferred from the flag. `remove` falls back to
        # `rmtree(ignore_errors=True)`, which swallows its own failure, so a
        # report reading `keep` alone can announce a clean vantage the run
        # never reached. `None` where no removal was attempted at all.
        "removed": None if keep else not path.exists(),
        "repository": os.fspath(repo),
        "command": list(command),
    }


def split_command(argv):
    """This tool's own arguments, then everything after the first bare `--`.

    Partitioned before argparse sees any of it: the command is passed
    through verbatim, so a command carrying `--repo` of its own is the
    command's business and never this tool's.
    """

    argv = list(argv)
    if "--" not in argv:
        raise Refusal("no command: put the command after a bare -- separator")
    index = argv.index("--")
    command = argv[index + 1:]
    if not command:
        raise Refusal("no command after the -- separator")
    return argv[:index], command


class _Parser(argparse.ArgumentParser):
    """argparse's usage errors, spoken as this runner's refusals.

    The base class exits `2` on a mistyped flag, and `2` is a status the
    command could have returned. A refusal a caller cannot tell from a
    verdict is the one thing REFUSAL_STATUS exists to prevent.
    """

    def error(self, message):
        raise Refusal(message)


def build_parser():
    parser = _Parser(
        prog="verify_at.py",
        description="Run one command in a detached worktree at one revision.",
    )
    parser.add_argument(
        "revision", help="the commit the command is run at, exactly",
    )
    parser.add_argument(
        "--repo", default=str(ROOT),
        help="the checkout the worktree is added to (default: this one)",
    )
    parser.add_argument(
        "--root", default=None,
        help="where the worktree is created (default: ~/{0})".format(ROOT_LEAF),
    )
    parser.add_argument(
        "--keep", action="store_true",
        help="leave the worktree in place for a reader to inspect",
    )
    return parser


def parse_args(argv):
    return build_parser().parse_args(argv)


def wants_usage(argv) -> bool:
    """Whether the caller asked what this tool is, before the `--` rule bites.

    The separator is this tool's own convention, and the caller reaching for
    the usage is precisely the one who has not learned it yet; making them
    satisfy it first is asking them to read the page they are asking for.
    """

    own = argv[:argv.index("--")] if "--" in argv else argv
    return any(item in ("-h", "--help") for item in own)


def emit(stream, text: str) -> None:
    """Say it whatever the console's codec is; a lost report is evidence lost."""

    encoding = getattr(stream, "encoding", None) or "utf-8"
    stream.write(text.encode(encoding, "replace").decode(encoding, "replace"))


def disposition(record: dict) -> str:
    """What became of the checkout, as observed rather than as requested.

    Three states, not two: asked to stay, gone, and still there after a
    removal that was meant to take it. The third is the one a word derived
    from `--keep` cannot say, and the one a reader most needs.
    """

    if record["kept"]:
        return "kept"
    return "removed" if record.get("removed") else "not removed"


def summary(record: dict) -> str:
    """The one line a reader needs to know what answered, and from where."""

    return "verify_at: exit {0}  revision {1}  worktree {2} ({3})\n".format(
        record["exit"],
        record["revision"][:12],
        record["worktree"],
        disposition(record),
    )


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else list(argv)
    if wants_usage(argv):
        # No command ran, so stdout is nobody's but ours to write on here.
        build_parser().print_help(sys.stdout)
        return 0
    try:
        own, command = split_command(argv)
        args = parse_args(own)
        record = run_at(
            args.repo, args.revision, command, root=args.root, keep=args.keep,
        )
    except Refusal as error:
        emit(sys.stderr, "verify_at: {0}\n".format(error))
        return REFUSAL_STATUS
    emit(sys.stderr, summary(record))
    return record["exit"]


if __name__ == "__main__":
    sys.exit(main())
