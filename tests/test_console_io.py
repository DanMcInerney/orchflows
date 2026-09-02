"""Every entrypoint prints through one console, and survives a closed one.

Three failures this file pins, and none of them is a tool failing at its
work: a console codec that cannot spell the verdict, a reader that stopped
reading, and a file whose bytes depend on which platform wrote it. The
structural cases are the ones that matter over time -- a new entrypoint
that forgets the discipline is caught here rather than on the Windows host
that first pipes it.
"""

from __future__ import annotations

import ast
import io
import os
import subprocess
import sys
import unittest

from tests._repo_root import ROOT
SCRIPTS = ROOT / "scripts"

from scripts import console  # noqa: E402


class Reconfigurable:
    """A text stream that records the one call the discipline makes."""

    def __init__(self):
        self.calls = []
        self.flushes = 0

    def reconfigure(self, **keywords):
        self.calls.append(keywords)

    def flush(self):
        self.flushes += 1


class Refusing(Reconfigurable):
    """A stream whose codec will not take the reconfiguration."""

    def reconfigure(self, **keywords):
        raise ValueError("underlying stream is detached")


class TestHardenNeverCostsTheReport(unittest.TestCase):
    def test_both_streams_are_put_on_utf8_replacing(self):
        out, err = Reconfigurable(), Reconfigurable()

        console.harden((out, err))

        expected = {"encoding": "utf-8", "errors": "replace"}
        self.assertEqual([expected], out.calls)
        self.assertEqual([expected], err.calls)

    def test_a_stream_that_cannot_reconfigure_is_not_an_error(self):
        """A `StringIO` under `redirect_stdout` has no `reconfigure` at all,
        and a detached stream raises. Either way the caller still prints."""

        console.harden((io.StringIO(), Refusing()))


class TestAClosedReaderIsNotAFailure(unittest.TestCase):
    def test_run_answers_zero_and_says_nothing_when_stdout_breaks(self):
        class Broken(io.StringIO):
            def flush(self):
                raise BrokenPipeError(32, "broken pipe")

        errors = io.StringIO()
        stdout, stderr = sys.stdout, sys.stderr
        sys.stdout, sys.stderr = Broken(), errors
        try:
            code = console.run(lambda: 0)
        finally:
            sys.stdout, sys.stderr = stdout, stderr

        self.assertEqual(0, code)
        self.assertEqual("", errors.getvalue())

    def test_a_tool_piped_into_a_closed_pipe_exits_clean(self):
        """The head-pipe crash, reproduced: the read end is closed before the
        child's interpreter has started, so its first write is on a broken
        pipe. Without the discipline CPython reports it at shutdown and exits
        120, which a caller reading exit codes reads as a failed tool."""

        for name in ("tickets.py", "workspace.py", "packs.py", "trace.py"):
            with self.subTest(script=name):
                read_end, write_end = os.pipe()
                try:
                    child = subprocess.Popen(
                        [sys.executable, str(SCRIPTS / name), "--help"],
                        stdout=write_end, stderr=subprocess.PIPE, cwd=str(ROOT),
                    )
                finally:
                    os.close(write_end)
                os.close(read_end)
                _, errors = child.communicate(timeout=120)
                text = errors.decode("utf-8", "replace")

                self.assertEqual(0, child.returncode, text)
                self.assertNotIn("BrokenPipeError", text)
                self.assertNotIn("Exception ignored", text)


class TestEveryEntrypointTakesTheConsoleFirst(unittest.TestCase):
    """The list is derived, never spelled: a script that grows an
    `if __name__` guard joins this case by existing."""

    def entrypoints(self):
        found = []
        for path in sorted(SCRIPTS.glob("*.py")):
            text = path.read_text(encoding="utf-8")
            if '__name__ == "__main__"' in text or "__name__ == '__main__'" in text:
                found.append((path, text))
        return found

    def test_the_set_is_not_empty(self):
        self.assertGreaterEqual(len(self.entrypoints()), 10)

    def test_no_guard_calls_its_main_without_the_console(self):
        """Both halves, because one alone is passable: the module has to
        reach ``console.run`` somewhere, and its guard must not step past it
        into ``main``. ``friction.py`` reaches it through a helper -- its
        reliability bar forbids importing anything at module scope -- so the
        two are asserted separately rather than as one line."""

        for path, text in self.entrypoints():
            with self.subTest(script=path.name):
                self.assertIn("console.run(", text)
                guard = text.rpartition('if __name__ == "__main__":')[2]
                self.assertNotRegex(guard, r"(SystemExit|sys\.exit)\(main\(")

    def test_each_module_reaches_the_one_owner_rather_than_reconfiguring(self):
        """The 21-sites lesson, applied to streams: a second spelling of the
        reconfiguration is a second place the `errors=` argument can be
        forgotten, which is how one script printed and another crashed."""

        offenders = []
        for path in sorted(SCRIPTS.glob("*.py")):
            if path.name == "console.py":
                continue
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
                if (
                    isinstance(node, ast.Attribute)
                    and node.attr == "reconfigure"
                ):
                    offenders.append(f"{path.name}:{node.lineno}")
        self.assertEqual([], offenders)


class TestAFileThisLibraryWritesIsTheSameFileEverywhere(unittest.TestCase):
    """A tool's output file is read on another host than the one that wrote
    it, so its bytes may not depend on the writer's platform."""

    def calls(self, tree):
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                yield node

    def keyword(self, node, name):
        return next((k for k in node.keywords if k.arg == name), None)

    def test_no_text_write_leaves_its_line_ending_to_the_platform(self):
        offenders = []
        for path in sorted(SCRIPTS.glob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in self.calls(tree):
                name = getattr(node.func, "attr", None) or getattr(node.func, "id", None)
                if name == "open" and any(
                    isinstance(argument, ast.Constant) and argument.value == "w"
                    for argument in node.args
                ) and self.keyword(node, "newline") is None:
                    offenders.append(f"{path.name}:{node.lineno} open")
        self.assertEqual([], offenders)

    def test_no_module_asks_for_a_keyword_the_floor_does_not_have(self):
        """`Path.write_text(newline=...)` arrived in 3.10 and this library's
        floor is 3.9, where the same call is a `TypeError` -- a defect no
        host above the floor can see, which is what makes it worth pinning."""

        offenders = []
        for path in sorted(SCRIPTS.glob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in self.calls(tree):
                if (
                    getattr(node.func, "attr", None) == "write_text"
                    and self.keyword(node, "newline") is not None
                ):
                    offenders.append(f"{path.name}:{node.lineno}")
        self.assertEqual([], offenders)


if __name__ == "__main__":
    unittest.main()
