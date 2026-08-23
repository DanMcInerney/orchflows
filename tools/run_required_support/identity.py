"""What the working tree is right now, as bytes a memo can be keyed on.

`dirty` is the whole answer to whether a verdict may be stored, so it is
computed from both halves of what a checkout can hide: the tracked diff
against HEAD, and the files git can see but has not been told about.
Ignored files are deliberately excluded -- a build directory is not a
change to the tree the checks read.
"""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path


class NotAGitCheckout(Exception):
    """Raised when the named directory cannot answer for a tree."""


def git(repo: Path, *args: str):
    """Run one git command in ``repo``; never raise on a non-zero exit."""

    try:
        return subprocess.run(
            ["git"] + list(args),
            cwd=str(repo),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except OSError as error:  # git itself is absent from this host
        raise NotAGitCheckout("git is not runnable here: {0}".format(error))


def _text(repo: Path, *args: str) -> str:
    done = git(repo, *args)
    if done.returncode != 0:
        raise NotAGitCheckout(
            "git {0} failed in {1}: {2}".format(
                " ".join(args), repo,
                done.stderr.decode("utf-8", "replace").strip(),
            )
        )
    return done.stdout.decode("utf-8", "replace").strip()


def head_commit(repo: Path) -> str:
    """The repository identity: the commit the tree was checked out from."""

    return _text(repo, "rev-parse", "HEAD")


def tree_identity(repo: Path) -> str:
    """The identity of HEAD's tree, which is what the checks actually read."""

    return _text(repo, "rev-parse", "HEAD^{tree}")


def untracked_files(repo: Path, skip: str = None):
    """Paths git can see and has not been told about, ignored ones excluded.

    ``skip`` drops one directory prefix -- the runner's own runtime state.
    A checkout that has not ignored it would otherwise report itself changed
    the moment a verdict was stored, and no run could ever be served.
    """

    done = git(repo, "ls-files", "--others", "--exclude-standard", "-z")
    if done.returncode != 0:
        raise NotAGitCheckout("git ls-files failed in {0}".format(repo))
    raw = done.stdout.decode("utf-8", "replace")
    names = (name for name in raw.split("\0") if name)
    if skip:
        prefix = skip.rstrip("/") + "/"
        names = (name for name in names if not name.startswith(prefix))
    return sorted(names)


def working_digest(repo: Path, skip: str = None):
    """Return ``(digest, dirty)`` for everything HEAD's tree does not say.

    The digest covers the tracked diff and every untracked-but-not-ignored
    file's bytes, so a memo cannot survive an edit that no commit records.
    """

    done = git(repo, "diff", "HEAD")
    if done.returncode != 0:
        raise NotAGitCheckout("git diff HEAD failed in {0}".format(repo))
    hasher = hashlib.sha256()
    hasher.update(done.stdout)
    names = untracked_files(repo, skip)
    for name in names:
        hasher.update(b"\0")
        hasher.update(name.encode("utf-8"))
        hasher.update(b"\0")
        try:
            hasher.update(hashlib.sha256((repo / name).read_bytes()).digest())
        except OSError:
            hasher.update(b"unreadable")
    dirty = bool(done.stdout) or bool(names)
    return hasher.hexdigest(), dirty


def cache_key(material) -> str:
    """One sha256 over every input that could change a verdict."""

    hasher = hashlib.sha256()
    for item in material:
        hasher.update(item.encode("utf-8"))
        hasher.update(b"\0")
    return hasher.hexdigest()


def digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()
