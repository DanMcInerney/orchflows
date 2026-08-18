"""Behavioral cases imported by the ``tests.test_tickets_issue`` seam."""

from .common import *  # noqa: F401,F403

class SurfaceTest(unittest.TestCase):
    """The two subcommands are on every surface a reader meets: the module
    docstring, the usage table, and `--help`."""

    def test_the_module_docstring_lists_both(self):
        docstring = tickets_mod.__doc__ or ""
        self.assertIn("new <run> <id>", docstring)
        self.assertIn("instantiate <template-dir>", docstring)

    def test_the_usage_table_and_summary_carry_both(self):
        for name in ("new", "instantiate"):
            with self.subTest(name):
                self.assertIn(name, tickets_mod.SUBCOMMAND_USAGE)
                self.assertIn(name, tickets_mod.SUBCOMMAND_SUMMARY)

    def test_help_answers_for_both_and_names_them_at_the_top_level(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            use_sink(tmp)
            top = run_full(tmp, "--help")
            self.assertEqual(0, top.returncode, top.stdout)
            for name in ("new", "instantiate"):
                with self.subTest(name):
                    self.assertIn(name, top.stdout)
                    answer = run_full(tmp, name, "--help")
                    self.assertEqual(0, answer.returncode, answer.stdout)
                    self.assertNotIn("error", json.loads(answer.stdout))


