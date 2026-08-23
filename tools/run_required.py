#!/usr/bin/env python3
"""Run the five required checks once, and never twice for the same tree.

The order and the membership are `AGENTS.md`'s; this runner only decides
when a check may be skipped, and the answer is: only when an identical tree
has already been proved green. Stdlib only, Python 3.9+, POSIX and Windows.

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

_FACADE_ROOT = Path(__file__).resolve().parent.parent
if str(_FACADE_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACADE_ROOT))

from tools.run_required_support import execution, identity  # noqa: E402

ROOT = _FACADE_ROOT
RECORD_KIND = "required-check-run/v1"
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
        help="neither read nor write the verdict cache",
    )
    parser.add_argument(
        "--format", choices=("text", "json"), default="text",
        help="text for a reader, json for the record itself",
    )
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    try:
        return _run(args)
    except (Refusal, identity.NotAGitCheckout) as error:
        sys.stderr.write("run_required: {0}\n".format(error))
        if args.format == "json":
            sys.stdout.write(
                json.dumps(
                    {"kind": REFUSAL_KIND, "reason": str(error)},
                    indent=1, sort_keys=True,
                ) + "\n"
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


def report(outcomes, payload, form: str) -> None:
    """Put every check's own output in front of a reader, then the verdict."""

    stream = sys.stdout if form == "text" else sys.stderr
    for _, record, out, err in outcomes:
        stream.write("--- {0}\n".format(" ".join(record["argv"][1:])))
        for raw in (out, err):
            if raw:
                stream.write(raw.decode("utf-8", "replace"))
    if form == "json":
        sys.stdout.write(json.dumps(payload, indent=1, sort_keys=True) + "\n")
        return
    for record in payload["commands"]:
        stream.write(
            "{0:>4}  {1}{2}\n".format(
                record["exit_status"],
                " ".join(record["argv"][1:]),
                "  (cached)" if record["cached"] else "",
            )
        )
    stream.write(
        "exit {0}  tree {1}{2}\n".format(
            payload["exit"], payload["tree_identity"][:12],
            "  (dirty)" if payload["dirty"] else "",
        )
    )


def _run(args) -> int:
    repo = Path(args.repo).resolve()
    if not repo.is_dir():
        raise Refusal("no such directory: {0}".format(repo))
    commit = identity.head_commit(repo)
    tree = identity.tree_identity(repo)
    _working, dirty = identity.working_digest(repo)
    interpreter = resolve_interpreter(args.python)
    if interpreter is None:
        raise Refusal("interpreter not found: {0}".format(args.python))
    interpreter_version(interpreter)
    planned = plan_commands(interpreter)
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
    report(outcomes, payload, args.format)
    return payload["exit"]


if __name__ == "__main__":
    sys.exit(main())
