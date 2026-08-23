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

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

RECORDER = '''\
"""Stub interpreter body: record argv, obey the plan, exit."""
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ARGV = sys.argv[1:]
with (HERE / "record.jsonl").open("a", encoding="utf-8") as stream:
    stream.write(json.dumps(ARGV) + "\\n")
try:
    PLAN = json.loads((HERE / "plan.json").read_text(encoding="utf-8"))
except (OSError, ValueError):
    PLAN = {}
CODE = 0
for token, spec in PLAN.items():
    if any(token in part for part in ARGV):
        time.sleep(spec.get("sleep", 0))
        CODE = spec.get("exit", 0)
        break
sys.stdout.write("stub-out " + " ".join(ARGV) + "\\n")
sys.stderr.write("stub-err " + " ".join(ARGV) + "\\n")
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
        try:
            text = (self.home / "record.jsonl").read_text(encoding="utf-8")
        except OSError:
            return []
        return [json.loads(line) for line in text.splitlines() if line.strip()]

    def calls(self):
        """Every stub invocation that was a check, not the version probe."""

        return [argv for argv in self._records() if argv != VERSION_PROBE]

    def probes(self):
        return [argv for argv in self._records() if argv == VERSION_PROBE]

    def forget(self) -> None:
        try:
            (self.home / "record.jsonl").unlink()
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
        (self.repo / ".gitignore").write_text("ignored/\n", encoding="utf-8")
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

    def named(self, payload, needle: str):
        """The one command record whose argv mentions ``needle``."""

        found = [
            record for record in payload["commands"]
            if any(needle in part for part in record["argv"])
        ]
        self.assertEqual(1, len(found), found)
        return found[0]
