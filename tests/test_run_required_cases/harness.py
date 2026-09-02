"""A temp git checkout plus a stub interpreter that records what it was asked.

The stub is a real executable on this platform -- a `.cmd` shim on Windows,
a `#!/bin/sh` shim elsewhere -- so `--python <stub>` exercises the same
resolution and the same `subprocess` boundary the runner uses in anger, while
none of the repository's own checks can run. The stub writes its record beside
itself, outside the checkout, because a record written inside the checkout
would dirty the very tree whose identity is under test.
"""

from __future__ import annotations

import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime
from pathlib import Path

from tests._repo_root import ROOT as REPO_ROOT
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

RECORDER = '''\
"""Stub interpreter body: record argv, obey the plan, exit.

One file per invocation: three of these run at once, and appends to a
shared file interleave, which would make the record itself the flake.
"""
import json
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ARGV = sys.argv[1:]
RECORDS = HERE / "records"
RECORDS.mkdir(exist_ok=True)
(RECORDS / "{0}-{1}.json".format(os.getpid(), time.time_ns())).write_text(
    json.dumps(ARGV), encoding="utf-8"
)
try:
    PLAN = json.loads((HERE / "plan.json").read_text(encoding="utf-8"))
except (OSError, ValueError):
    PLAN = {}
CODE = 0
for token, spec in PLAN.items():
    if any(token in part for part in ARGV):
        if spec.get("touch"):
            Path(spec["touch"]).write_text("stub touched\\n", encoding="utf-8")
        time.sleep(spec.get("sleep", 0))
        CODE = spec.get("exit", 0)
        break
# Bytes, not text: the runner digests what it captured, so a test
# that checks a digest against its stream must know the exact bytes.
sys.stdout.buffer.write(("stub-out " + " ".join(ARGV) + "\\n").encode("utf-8"))
sys.stderr.buffer.write(("stub-err " + " ".join(ARGV) + "\\n").encode("utf-8"))
sys.exit(CODE)
'''

VERSION_PROBE = ["--version"]


def git(cwd: Path, *args: str) -> str:
    done = subprocess.run(
        ["git"] + list(args),
        cwd=str(cwd),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    return done.stdout.decode("utf-8", "replace").strip()


def runtime_directory_name() -> str:
    """The gitignored runtime directory the unit-test runner already owns."""

    from tools import run_tests

    return run_tests.CACHE_PATH.parent.name


def moment(stamp: str) -> datetime:
    """Parse one record timestamp; 3.9's ``fromisoformat`` rejects the Z."""

    return datetime.fromisoformat(stamp.replace("Z", "+00:00"))


class Stub:
    """A stub interpreter plus the plan that decides its exits and sleeps."""

    def __init__(self, home: Path) -> None:
        self.home = home
        home.mkdir(parents=True, exist_ok=True)
        body = home / "recorder.py"
        body.write_text(RECORDER, encoding="utf-8")
        if os.name == "nt":
            self.path = home / "stub-python.cmd"
            self.path.write_text(
                '@echo off\r\n"{0}" "{1}" %*\r\n'.format(sys.executable, body),
                encoding="utf-8",
            )
        else:
            self.path = home / "stub-python"
            self.path.write_text(
                '#!/bin/sh\nexec "{0}" "{1}" "$@"\n'.format(sys.executable, body),
                encoding="utf-8",
            )
            self.path.chmod(0o755)
        self.plan({})

    def plan(self, spec: dict) -> None:
        (self.home / "plan.json").write_text(
            json.dumps(spec, sort_keys=True), encoding="utf-8"
        )

    def _records(self):
        directory = self.home / "records"
        if not directory.is_dir():
            return []
        return [
            json.loads(path.read_text(encoding="utf-8"))
            for path in sorted(directory.glob("*.json"))
        ]

    def calls(self):
        """Every stub invocation that was a check, not the version probe."""

        return [argv for argv in self._records() if argv != VERSION_PROBE]

    def probes(self):
        return [argv for argv in self._records() if argv == VERSION_PROBE]

    def forget(self) -> None:
        for path in (self.home / "records").glob("*.json"):
            try:
                path.unlink()
            except OSError:
                pass


class RunRequiredCase(unittest.TestCase):
    """A committed one-file checkout and a stub interpreter beside it."""

    def setUp(self) -> None:
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        root = Path(holder.name)
        self.repo = root / "checkout"
        self.repo.mkdir()
        git(self.repo, "init", "--quiet")
        git(self.repo, "config", "user.email", "case@example.invalid")
        git(self.repo, "config", "user.name", "case")
        (self.repo / "README.md").write_text("baseline\n", encoding="utf-8")
        (self.repo / ".gitignore").write_text(
            "ignored/\n{0}/\n".format(runtime_directory_name()), encoding="utf-8"
        )
        git(self.repo, "add", "README.md", ".gitignore")
        git(self.repo, "commit", "--quiet", "-m", "baseline")
        self.stub = Stub(root / "stub")

    def invoke(self, *extra: str):
        """Run the runner in process; return exit status, payload, streams."""

        from tools import run_required

        argv = [
            "--repo", str(self.repo),
            "--python", str(self.stub.path),
            "--format", "json",
        ]
        argv.extend(extra)
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            status = run_required.main(argv)
        text = out.getvalue()
        try:
            payload = json.loads(text)
        except ValueError:
            payload = None
        return status, payload, text, err.getvalue()

    def touch_tracked(self) -> None:
        (self.repo / "README.md").write_text("changed\n", encoding="utf-8")

    def add_untracked(self) -> None:
        (self.repo / "loose.txt").write_text("x", encoding="utf-8")


    def cache_entries(self):
        """Every stored verdict for this checkout, newest name order."""

        from tools.run_required_support import cache

        directory = cache.runtime_cache_dir(self.repo)
        if not directory.is_dir():
            return []
        return sorted(directory.glob("*.json"))

    def named(self, payload, needle: str):
        """The one command record whose argv mentions ``needle``."""

        found = [
            record for record in payload["commands"]
            if any(needle in part for part in record["argv"])
        ]
        self.assertEqual(1, len(found), found)
        return found[0]
