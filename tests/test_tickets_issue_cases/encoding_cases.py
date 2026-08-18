"""Behavioral cases imported by the ``tests.test_tickets_issue`` seam."""

from .common import *  # noqa: F401,F403

class NonUtf8BytesTest(unittest.TestCase):
    """Bytes that are not UTF-8 are the one shape of unreadable file that
    crashed instead of reporting: `UnicodeDecodeError` is a `ValueError`, so
    every `except OSError` around a read let it through as a traceback on a
    channel whose whole contract is one JSON document. A ticket arrives from
    a hand edit, a copy off another host, a template checked out with a
    different encoding — none of which is exotic enough to earn a stack
    trace."""

    def corrupt(self, path: Path) -> Path:
        # a lone 0xFF: valid latin-1, invalid UTF-8 at the first byte, so no
        # decoder guesses its way past it
        path.write_bytes(b"\xff" + path.read_bytes())
        return path

    def test_an_unreadable_ticket_is_a_named_error_from_list_and_packet(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            sink = use_sink(tmp)
            self.corrupt(place(sink, "testrun", "T1", GOOD_TICKET))

            listed = run_cmd("list", "--run", "testrun")["tickets"]
            self.assertEqual(1, len(listed), listed)
            self.assertIn("unreadable ticket", listed[0]["error"])

            done = run_full(tmp, "packet", "testrun", "T1", "--reply-to", "main")
            self.assertEqual(1, done.returncode, done.stdout)
            self.assertIn("unreadable ticket", json.loads(done.stdout)["error"])

    def test_an_unreadable_stub_refuses_the_instantiation_by_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            use_sink(tmp)
            directory = make_template(tmp, three_stubs())
            self.corrupt(directory / "B.md")

            done = run_full(
                tmp, "instantiate", str(directory), "--run", "testrun",
                "--set", "target=scripts/a.py",
            )
            self.assertEqual(1, done.returncode, done.stdout)
            error = json.loads(done.stdout)["error"]
            self.assertIn("unreadable stub B.md", error)

    def test_an_unreadable_manifest_refuses_the_instantiation_by_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            use_sink(tmp)
            directory = make_template(tmp, three_stubs())
            self.corrupt(directory / "template.md")

            done = run_full(
                tmp, "instantiate", str(directory), "--run", "testrun",
                "--set", "target=scripts/a.py",
            )
            self.assertEqual(1, done.returncode, done.stdout)
            self.assertIn("unreadable template.md", json.loads(done.stdout)["error"])

    def test_an_unreadable_body_file_refuses_the_amend(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            sink = use_sink(tmp)
            place(sink, "testrun", "T1", GOOD_TICKET)
            body = tmp / "body.md"
            body.write_text("a repaired objective\n", encoding="utf-8")
            self.corrupt(body)

            done = run_full(
                tmp, "amend", "testrun", "T1", "--section", "Objective",
                "--file", str(body),
            )
            self.assertEqual(1, done.returncode, done.stdout)
            self.assertIn("unreadable body file", json.loads(done.stdout)["error"])

    def test_an_unreadable_source_refuses_the_new(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            use_sink(tmp)
            source = tmp / "source.md"
            source.write_text(GOOD_TICKET, encoding="utf-8")
            self.corrupt(source)

            done = run_full(tmp, "new", "testrun", "T1", "--file", str(source))
            self.assertEqual(1, done.returncode, done.stdout)
            self.assertIn("unreadable ticket file", json.loads(done.stdout)["error"])

    def test_an_unreadable_ticket_still_renders_the_run_view(self):
        """`worklog` sections one file per ticket after `_load_ticket` has
        already graded it; the second read had no guard of its own, so the
        whole view died on one bad file."""

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            sink = use_sink(tmp)
            place(sink, "testrun", "T1", GOOD_TICKET)
            self.corrupt(place(sink, "testrun", "T2", GOOD_TICKET.replace("id: T1", "id: T2")))

            done = run_full(tmp, "worklog", "testrun")
            payload = json.loads(done.stdout)
            self.assertEqual(0, done.returncode, done.stdout)
            self.assertNotIn("error", payload)
