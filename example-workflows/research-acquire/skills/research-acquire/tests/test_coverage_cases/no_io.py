"""No-I/O check for the coverage seam."""

from __future__ import annotations

import unittest

from super_research import coverage


class NoIOTest(unittest.TestCase):
    def test_the_module_calls_nothing_that_opens_a_file_or_a_socket(self):
        """The seam's reliability bar, read off the syntax and not the prose.

        Asserted against the AST rather than the source text: the module's own
        docstring says it "reaches no socket", and a substring scan fails on
        the sentence that states the guarantee.
        """

        import ast
        import inspect

        called = set()
        for node in ast.walk(ast.parse(inspect.getsource(coverage))):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if isinstance(func, ast.Name):
                called.add(func.id)
            elif isinstance(func, ast.Attribute):
                called.add(func.attr)

        for forbidden in ("open", "urlopen", "socket", "Path", "read_text", "write_text"):
            self.assertNotIn(forbidden, called, forbidden)
