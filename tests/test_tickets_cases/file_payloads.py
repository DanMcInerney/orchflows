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


def ticket(ticket_id, *, executor="orch-tdd", goal="deliver", result=""):
    fields = {
        "id": ticket_id, "run": "run", "status": "pending",
        "admission": "pending", "executor": executor, "pack": "orch-code-pack",
        "independence": "gate", "depends_on": [],
        "isolation": "required" if executor == "orch-tdd" else "none",
        "bound": "30m", "claimed_by": "", "claimed_at": "",
    }
    sections = [
        ("Goal", goal), ("Context", "Use the exact sealed run snapshot."),
        ("Result", result), ("Verification", ""), ("Feedback", "[]"),
        ("Risks", "[]"),
    ]
    return _render_ticket(fields, sections)


def snapshot():
    return {
        "00-root": ticket("00-root", executor="orch-decompose", goal="root"),
        "00-root.01": ticket("00-root.01"),
    }

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


class AmendmentRecordFilePayloadTest(unittest.TestCase):
    def _sealed_worker(self, directory: Path):
        run_dir = directory / "tickets" / "run"
        run_dir.mkdir(parents=True)
        for ticket_id, value in snapshot().items():
            (run_dir / f"{ticket_id}.md").write_text(value, encoding="utf-8")
        _dispatch(["stamp-generation", "run", "00-root"])
        cut = _dispatch(["draft-validate", "run", "00-root"])["draft_validation"]["cut_generation"]
        _dispatch(["seal", "run", "00-root", "--cut-generation", cut])
        _dispatch(["claim", "run", "00-root.01", "--by", "worker"])
        data = _parse_frontmatter((run_dir / "00-root.01.md").read_text(encoding="utf-8"))
        return run_dir, {
            "bound-state": "available", "change-kind": "authority",
            "cut-generation": data["cut_generation"],
            "evidence-identities": ["artifact:failure"],
            "parent-ticket": "00-root", "reason": HOSTILE, "request-id": "req-1",
            "requester-ticket": "00-root.01", "root-generation": data["root_generation"],
            "target-fields": ["write_scope"],
        }

    def test_a_record_read_from_a_file_round_trips_byte_exactly(self):
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            with mock.patch.dict(os.environ, {STATE_HOME_ENV_VAR: str(directory)}):
                run_dir, record = self._sealed_worker(directory)
                encoded = generations.canonical_json(record)
                payload = directory / "record.json"
                payload.write_text(encoded + "\n", encoding="utf-8")
                written = _dispatch(
                    ["amendment-request", "run", "00-root.01", "--record-file", str(payload)]
                )
            self.assertNotIn("error", written)
            handoff = (run_dir / "00-root.01.md").read_text(encoding="utf-8")
            self.assertIn("- amendment-request: " + encoded, handoff)

    def test_a_record_read_from_stdin_round_trips_byte_exactly(self):
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            with mock.patch.dict(os.environ, {STATE_HOME_ENV_VAR: str(directory)}):
                run_dir, record = self._sealed_worker(directory)
                encoded = generations.canonical_json(record)
                stream = io.TextIOWrapper(io.BytesIO(encoded.encode("utf-8")), encoding="utf-8")
                with mock.patch.object(sys, "stdin", stream):
                    written = _dispatch(
                        ["amendment-request", "run", "00-root.01", "--record-file", "-"]
                    )
            self.assertNotIn("error", written)
            handoff = (run_dir / "00-root.01.md").read_text(encoding="utf-8")
            self.assertIn("- amendment-request: " + encoded, handoff)

    def test_a_record_file_naming_no_path_is_one_refusal(self):
        refusal = _dispatch(["amendment-request", "run", "00-root.01", "--record-file"])
        self.assertIn("--record-file takes one path", refusal["error"])


if __name__ == "__main__":
    unittest.main()
