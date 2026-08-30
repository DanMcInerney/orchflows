"""Payloads that arrive by file rather than through a shell.

A note and an amendment request are both text a caller composed, and both
used to reach the sink only as one argv token. Every host that failed on
this run failed the same way -- PowerShell ate the backtick, cmd ate the
percent, the console codepage ate the glyph -- so the payload is read from a
file, or from stdin, and compared byte for byte here.
"""

import io

from .common import *  # noqa: F401,F403
from scripts import tickets_generations as generations
from scripts.tickets_dispatch import _dispatch
from scripts.tickets_format import _parse_frontmatter
from scripts.tickets_issue_render import _render_ticket


# Everything a shell is entitled to mangle, plus one glyph with no cp1252
# encoding at all, so a wrong-codepage write cannot pass by round-tripping.
HOSTILE = (
    'a "double" quote, an \'apostrophe\', a `backtick`, a $dollar, a %percent%,\n'
    "a trailing backslash \\\n"
    "a snowman ☃ and a clef \U0001d11e\n"
    "  indented, and a blank line follows\n"
    "\n"
    "the last line"
)


class NoteFilePayloadTest(unittest.TestCase):
    def test_a_note_read_from_a_file_lands_byte_exactly(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            sink = tmp / "sink"
            payload = tmp / "note.md"
            payload.write_text(HOSTILE, encoding="utf-8")
            with mock.patch.dict(os.environ, {STATE_HOME_ENV_VAR: str(sink)}):
                written = _dispatch(
                    ["run-state", "testrun", "--note", "--file", str(payload)]
                )
            self.assertNotIn("error", written)
            notes = Path(written["run_state"]["path"]).read_text(encoding="utf-8")
            self.assertIn(HOSTILE, notes)

    def test_a_note_read_from_stdin_lands_byte_exactly(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            sink = tmp / "sink"
            stream = io.TextIOWrapper(io.BytesIO(HOSTILE.encode("utf-8")), encoding="utf-8")
            with mock.patch.dict(os.environ, {STATE_HOME_ENV_VAR: str(sink)}):
                with mock.patch.object(sys, "stdin", stream):
                    written = _dispatch(["run-state", "testrun", "--note", "--file", "-"])
            self.assertNotIn("error", written)
            notes = Path(written["run_state"]["path"]).read_text(encoding="utf-8")
            self.assertIn(HOSTILE, notes)

    def test_a_missing_note_file_is_one_refusal_and_no_write(self):
        with tempfile.TemporaryDirectory() as raw:
            sink = Path(raw) / "sink"
            with mock.patch.dict(os.environ, {STATE_HOME_ENV_VAR: str(sink)}):
                refusal = _dispatch(
                    ["run-state", "testrun", "--note", "--file", str(Path(raw) / "absent.md")]
                )
            self.assertIn("unreadable note file", refusal["error"])
            self.assertFalse(sink.exists())

    def test_a_note_given_inline_still_reaches_the_sink(self):
        """The by-file path is additive: the one-token spelling is untouched."""
        with tempfile.TemporaryDirectory() as raw:
            sink = Path(raw) / "sink"
            with mock.patch.dict(os.environ, {STATE_HOME_ENV_VAR: str(sink)}):
                written = _dispatch(["run-state", "testrun", "--note", "one plain line"])
            self.assertNotIn("error", written)
            notes = Path(written["run_state"]["path"]).read_text(encoding="utf-8")
            self.assertIn("one plain line", notes)


if __name__ == "__main__":
    unittest.main()
