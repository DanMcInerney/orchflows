#!/usr/bin/env python3
"""Run the five required checks once, and never twice for the same tree.

The order and the membership are `AGENTS.md`'s; this runner only decides
when a check may be skipped, and the answer is: only when an identical tree
has already been proved green. A skip is served as a replay and named one,
never as a run, and `--no-cache` is how a caller whose job is an execution
-- a gate's -- demands one. Stdlib only, 3.9+, POSIX and Windows.

Usage:
    python tools/run_required.py [--repo DIR] [--python EXE]
                                 [--no-cache] [--format text|json]

Exit 0 when all five exit 0, 1 when any does not, 2 on refusal.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

# This is the entry point that puts the repository on sys.path for the
# `tools.run_required_support` import below, so it cannot read
# `scripts._bootstrap.ROOT` for the same fact -- nothing is importable yet.
_FACADE_ROOT = Path(__file__).resolve().parent.parent
if str(_FACADE_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACADE_ROOT))

from tools.run_required_support import cache, execution, identity  # noqa: E402

ROOT = _FACADE_ROOT
RECORD_KIND = "required-check-run/v1"
# A served verdict answers under its own name. The kind is what a reader of
# the JSON matches on, so a replay carrying the run's kind would be a memo
# passing itself off as the execution its caller asked for.
REPLAY_KIND = "required-check-replay/v1"
REFUSAL_KIND = "required-check-refusal/v1"

# `AGENTS.md`'s five, in `AGENTS.md`'s order. `cheap` is what may share a
# phase: the two long checks each want the whole machine, so they are run
# alone and last, in the order the surface lists them.
REQUIRED_CHECKS = (
    {"name": "validate", "args": ("tools/validate.py",), "cheap": True},
    {"name": "unit tests", "args": ("tools/run_tests.py",), "cheap": False},
    {"name": "serial compatibility", "args": ("tools/run_serial_compat.py",),
     "cheap": False},
    {"name": "install dry run", "args": ("install.py", "--dry-run"),
     "cheap": True},
    {"name": "whitespace", "args": None, "cheap": True,
     "argv": ("git", "diff", "--check")},
)


class Refusal(Exception):
    """The runner cannot honestly attempt the five checks."""


def resolve_interpreter(name: str):
    """The absolute path the checks will actually be run through, or None."""

    candidate = Path(name)
    if candidate.is_file():
        return str(candidate.resolve())
    found = shutil.which(name)
    return str(Path(found).resolve()) if found else None


def interpreter_version(interpreter: str) -> str:
    """Ask the resolved interpreter what it is; refuse if it cannot say."""

    try:
        done = subprocess.run(
            [interpreter, "--version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
    except OSError as error:
        raise Refusal("interpreter is not runnable: {0}".format(error))
    if done.returncode != 0:
        raise Refusal(
            "interpreter refused --version: {0}".format(interpreter)
        )
    return done.stdout.decode("utf-8", "replace").strip()


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo", default=str(ROOT),
        help="the checkout whose required checks are run (default: this one)",
    )
    parser.add_argument(
        "--python", default=sys.executable,
        help="the interpreter the four python checks are run through",
    )
    parser.add_argument(
        "--no-cache", action="store_true",
        help="neither read nor write the verdict cache: a gate's execution",
    )
    parser.add_argument(
        "--format", choices=("text", "json"), default="text",
        help="text for a reader, json for the record itself",
    )
    return parser.parse_args(argv)


def emit(stream, text: str) -> None:
    """Write one string without asking the console's codec for permission.

    A report is evidence, and evidence a cp1252 console refuses to spell is
    evidence nobody reads: five green checks were lost once to a crash while
    printing their own output. Bytes go straight past the text layer
    whenever the stream has one; a stream with no buffer -- a test's
    ``StringIO`` -- takes the same text through its own codec's
    replacements, which is a mangled glyph rather than a lost run.
    """

    buffer = getattr(stream, "buffer", None)
    if buffer is not None:
        stream.flush()  # keep whatever the text layer holds in front of this
        buffer.write(text.encode("utf-8"))
        buffer.flush()
        return
    encoding = getattr(stream, "encoding", None) or "utf-8"
    stream.write(text.encode(encoding, "replace").decode(encoding, "replace"))


def main(argv=None) -> int:
    args = parse_args(argv)
    try:
        return _run(args)
    except (Refusal, identity.NotAGitCheckout) as error:
        emit(sys.stderr, "run_required: {0}\n".format(error))
        if args.format == "json":
            emit(
                sys.stdout,
                json.dumps(
                    {"kind": REFUSAL_KIND, "reason": str(error)},
                    indent=1, sort_keys=True,
                ) + "\n",
            )
        return 2


def plan_commands(interpreter: str):
    """The five, as ``(name, argv)`` in the surface's order."""

    planned = []
    for check in REQUIRED_CHECKS:
        if check["args"] is None:
            argv = list(check["argv"])
        else:
            argv = [interpreter] + list(check["args"])
        planned.append((check["name"], argv))
    return planned


def execute(planned, repo: Path):
    """Run the cheap phase at once, then each long check on its own."""

    by_name = dict(planned)
    cheap = [
        (check["name"], by_name[check["name"]])
        for check in REQUIRED_CHECKS if check["cheap"]
    ]
    outcomes = execution.run_phase(cheap, repo)
    for check in REQUIRED_CHECKS:
        if check["cheap"]:
            continue
        name = check["name"]
        outcomes.update(execution.run_phase([(name, by_name[name])], repo))
    return [outcomes[name] for name, _ in planned]


def display(argv) -> str:
    """The command as a reader would type it; only the interpreter is noise.

    Every python check carries the resolved interpreter's absolute path as
    its own first word; the whitespace check's first word is ``git``, and
    dropping that would name a command nobody could run.
    """

    return " ".join(argv[1:] if Path(argv[0]).is_absolute() else argv)


def verdict_note(payload) -> str:
    """What the verdict line carries beyond the exit status and the tree.

    A replay says so on the one line every reader reads. The per-command
    ``(cached)`` marks are true, but they are five easy things to skim
    past, and a caller whose job is an execution -- a gate owes its run
    one -- should not have to infer that none happened, nor go looking for
    the spelling that would make one happen. The two notes never meet:
    only a clean tree is ever stored, so a served verdict is never dirty.
    """

    if payload["kind"] == REPLAY_KIND:
        return "  (replay; --no-cache executes the five)"
    return "  (dirty)" if payload["dirty"] else ""


def report(outcomes, payload, form: str) -> None:
    """Put every check's own output in front of a reader, then the verdict."""

    stream = sys.stdout if form == "text" else sys.stderr
    for _, record, out, err in outcomes:
        emit(stream, "--- {0}\n".format(display(record["argv"])))
        for raw in (out, err):
            if raw:
                emit(stream, raw.decode("utf-8", "replace"))
    if form == "json":
        emit(sys.stdout, json.dumps(payload, indent=1, sort_keys=True) + "\n")
        return
    for record in payload["commands"]:
        emit(
            stream,
            "{0:>4}  {1}{2}\n".format(
                record["exit_status"],
                display(record["argv"]),
                "  (cached)" if record["cached"] else "",
            ),
        )
    emit(
        stream,
        "exit {0}  tree {1}{2}\n".format(
            payload["exit"], payload["tree_identity"][:12], verdict_note(payload),
        ),
    )


def key_for(tree: str, working: str, planned, interpreter: str, version: str) -> str:
    """Everything that could change a verdict, in one sha256."""

    return identity.cache_key([
        RECORD_KIND,
        tree,
        working,
        json.dumps([argv for _, argv in planned], sort_keys=False),
        interpreter,
        sys.platform,
        version,
    ])


def _run(args) -> int:
    repo = Path(args.repo).resolve()
    if not repo.is_dir():
        raise Refusal("no such directory: {0}".format(repo))
    skip = cache.runtime_directory_name()
    commit = identity.head_commit(repo)
    tree = identity.tree_identity(repo)
    working, dirty = identity.working_digest(repo, skip)
    interpreter = resolve_interpreter(args.python)
    if interpreter is None:
        raise Refusal("interpreter not found: {0}".format(args.python))
    version = interpreter_version(interpreter)
    planned = plan_commands(interpreter)
    key = key_for(tree, working, planned, interpreter, version)

    # A memo is served only for a clean tree: a dirty one was never stored,
    # so looking is a question whose answer cannot be yes.
    if not args.no_cache and not dirty:
        stored = cache.load(repo, key)
        if stored is not None:
            served = cache.serve(stored, REPLAY_KIND)
            report([], served, args.format)
            return 0

    outcomes = execute(planned, repo)
    records = [record for _, record, _, _ in outcomes]
    payload = {
        "kind": RECORD_KIND,
        "repository_identity": commit,
        "tree_identity": tree,
        "dirty": dirty,
        "commands": records,
        "exit": 0 if all(r["exit_status"] == 0 for r in records) else 1,
    }
    if _storable(args, repo, skip, tree, working, dirty, payload):
        cache.store(repo, key, payload)
    report(outcomes, payload, args.format)
    return payload["exit"]


def _storable(args, repo: Path, skip: str, tree: str, working: str,
              dirty: bool, payload: dict) -> bool:
    """A verdict is stored only for the tree it actually judged, all green.

    The tree is read again at the end: a check that writes into the checkout
    judged a tree that no longer exists, and a memo for it would answer for
    work nobody did.
    """

    if args.no_cache or dirty or payload["exit"] != 0:
        return False
    after_working, after_dirty = identity.working_digest(repo, skip)
    return (
        not after_dirty
        and after_working == working
        and identity.tree_identity(repo) == tree
    )


if __name__ == "__main__":
    sys.exit(main())
