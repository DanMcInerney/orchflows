"""Shared transcript fixtures and canonical reader test case base."""

import contextlib
import tempfile
import unittest
from pathlib import Path

from reader.scripts import ui_sessions
from reader.tests.test_ui_cases._base import make_sink, make_transcripts
from reader.tests.test_ui_cases._web import snapshot


def build_fixture(stack) -> tuple:
    """Return a temporary sink and transcript tree for one test class."""

    tmp = Path(stack.enter_context(tempfile.TemporaryDirectory()))
    return tmp, make_sink(tmp), make_transcripts(tmp)


class TranscriptCase(unittest.TestCase):
    """A fixture transcript root with cache and write-isolation guards."""

    @classmethod
    def setUpClass(cls):
        stack = contextlib.ExitStack()
        cls.addClassCleanup(stack.close)
        cls.tmp, cls.main, cls.transcripts = build_fixture(stack)
        cls.pristine = snapshot(cls.tmp)

    def setUp(self):
        ui_sessions.TRANSCRIPT_CACHE.clear()
        self.addCleanup(ui_sessions.TRANSCRIPT_CACHE.clear)
        self.addCleanup(self.shared_tree_is_intact)

    def own_fixture(self):
        """Give a mutating case an isolated copy of the class fixture."""

        if "tmp" in vars(self):
            return
        stack = contextlib.ExitStack()
        self.addCleanup(stack.close)
        self.tmp, self.main, self.transcripts = build_fixture(stack)

    def shared_tree_is_intact(self):
        if "tmp" not in vars(self):
            self.assertEqual(
                type(self).pristine,
                snapshot(type(self).tmp),
                "wrote into the class fixture; call own_fixture() first",
            )
