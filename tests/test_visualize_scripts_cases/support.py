"""Shared in-process harness for the visualization script cases.

Both subjects sit in skills/utilities/orch-visualize/scripts/. Neither
has a fallback tier: the verifier judges a diagram only when the pinned
Mermaid CLI read it, and the renderer produces inline SVG or nothing. So
the CLI is stubbed at the one boundary either script crosses --
``subprocess.run`` -- by :class:`_StubCli`, which chooses the exit code,
the diagnostic text and the SVG left behind; the scripts' own reading of
that output stays under test.
"""

import contextlib
import io
import os
import subprocess
import sys
import tempfile
import unittest
from collections import namedtuple
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "skills" / "utilities" / "orch-visualize" / "scripts"
# The one path mutation this collection makes, at import and for both
# subjects, replacing the per-test insert render_html's salting case used
# to do inside its own body.
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import render_html  # noqa: E402
import verify_mermaid  # noqa: E402

VERIFIER = SCRIPTS / "verify_mermaid.py"
RENDERER = SCRIPTS / "render_html.py"

SAMPLE = (
    "# Sample viz — unicode ∥ 中文\n"
    "\n"
    "One terse paragraph with `code` and **bold**.\n"
    "\n"
    "```mermaid\n"
    "flowchart TD\n"
    '    a["start"] --> b["done"]\n'
    "```\n"
)

# One node box inside a viewBox that contains it: the geometry checks
# read this and find nothing wrong, so a case that wants a geometry
# finding says so with its own SVG rather than by accident of this one.
FAKE_SVG = (
    b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200">'
    b'<g class="node" transform="translate(10,10)">'
    b'<rect x="0" y="0" width="40" height="20"/></g></svg>'
)

# An empty PATH is a PATH shutil.which can resolve nothing on, whatever
# the host really has installed, so the no-CLI cases refuse by decision
# rather than by accident of what is on the machine.
NO_NPX = {"PATH": ""}

Result = namedtuple("Result", "returncode stdout stderr")


def _no_npx_env():
    """Return ``NO_NPX`` over the real environment for process cases."""
    env = dict(os.environ)
    env.update(NO_NPX)
    return env


class _StubCli:
    """The pinned Mermaid CLI, stubbed at ``subprocess.run``.

    A case names the CLI's exit code, the text it writes and the bytes it
    leaves at the ``-o`` path. Everything the scripts do with that output
    still runs for real.
    """

    def __init__(self, returncode: int = 0, stderr: str = "", svg=FAKE_SVG):
        self.returncode = returncode
        self.stderr = stderr
        self.svg = svg
        self.calls = 0

    def __call__(self, command, **kwargs):
        self.calls += 1
        if self.svg is not None:
            Path(command[-1]).write_bytes(self.svg)
        return subprocess.CompletedProcess(command, self.returncode, "", self.stderr)


class _ScriptCase(unittest.TestCase):
    """A private directory and in-process script entry points per case."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.directory = Path(self.tmp.name)

    def call(self, module, argv, cli=None):
        out, err = io.StringIO(), io.StringIO()
        patches = [mock.patch.dict(os.environ, NO_NPX)]
        if cli is not None:
            patches.append(mock.patch.object(module, "_find_npx", lambda: "npx"))
            patches.append(mock.patch.object(subprocess, "run", cli))
        with contextlib.ExitStack() as stack:
            for patch in patches:
                stack.enter_context(patch)
            stack.enter_context(contextlib.redirect_stdout(out))
            stack.enter_context(contextlib.redirect_stderr(err))
            returncode = module.main([str(argument) for argument in argv])
        return Result(returncode, out.getvalue(), err.getvalue())

    def run_verifier(self, markdown: str, *extra_args: str, cli=_StubCli()):
        path = self.directory / "diagram.md"
        path.write_text(markdown, encoding="utf-8")
        return self.call(verify_mermaid, [path, *extra_args], cli=cli)

    def run_verifier_bytes(self, raw: bytes, cli=_StubCli()):
        path = self.directory / "diagram.md"
        path.write_bytes(raw)
        return self.call(verify_mermaid, [path], cli=cli)

    def run_renderer(
        self, markdown: str, *extra_args: str, name: str = "page.md", cli=None
    ):
        md = self.directory / name
        md.write_text(markdown, encoding="utf-8")
        return self.call(render_html, [md, *extra_args], cli=cli)

    def run_renderer_bytes(self, raw: bytes, name: str = "page.md"):
        md = self.directory / name
        md.write_bytes(raw)
        return self.call(render_html, [md])
