"""Behavioral cases imported by the ``tests.test_tickets_issue`` seam."""

from .common import *  # noqa: F401,F403

class NarrowConsoleTest(unittest.TestCase):
    """A payload quoting ticket prose prints to a console that cannot spell it.

    `worklog --write` raised UnicodeEncodeError from its one `print` over a
    ticket carrying an arrow: the run's whole view was lost to the encoding of
    the terminal it was being shown on. The payload stays UTF-8 by contract --
    `ensure_ascii=False` is what keeps a path or a criterion readable in it --
    so the console's own inability to spell a character is answered where it
    arises, at the stream.
    """

    ARROW = "→"

    def test_a_payload_holding_an_unencodable_character_still_prints(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            sink = use_sink(tmp)
            source = tmp / "T1.md"
            source.write_text(
                GOOD_TICKET.replace("Add `double(n)`.", f"n {self.ARROW} 2n."),
                encoding="utf-8",
            )
            self.assertNotIn(
                "error", run_cmd("new", "testrun", "--file", str(source))
            )
            environment = dict(os.environ)
            environment["PYTHONIOENCODING"] = "cp1252"
            environment[STATE_HOME_ENV_VAR] = str(sink)
            completed = subprocess.run(
                [sys.executable, str(TICKETS_PY), "worklog", "testrun"],
                capture_output=True, cwd=str(tmp), env=environment,
            )
            self.assertEqual(0, completed.returncode, completed.stderr)
            self.assertIn(b"worklog", completed.stdout)
            self.assertNotIn(b"UnicodeEncodeError", completed.stderr)
