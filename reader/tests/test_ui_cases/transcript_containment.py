"""Transcript-root containment and addressing regressions."""

from pathlib import Path

from reader.scripts import ui_discovery
from reader.tests.test_ui_cases import _base as fixture
from reader.tests.test_ui_cases._transcript_support import TranscriptCase


class TestTranscriptContainment(TranscriptCase):
    """Transcript project and session walks stay below their root."""

    LEAKED_TITLE = "LEAKED-TITLE"

    def link_out(self):
        outside = self.tmp / "outside"
        outside.mkdir()
        (outside / "1e6f0000-0000-4000-8000-00000000beef.jsonl").write_text(
            '{"type":"ai-title","aiTitle":"%s"}\n' % self.LEAKED_TITLE,
            encoding="utf-8",
        )
        link = self.transcripts / "-Users-dmcinerney-tools-leaked"
        try:
            link.symlink_to(outside, target_is_directory=True)
        except (OSError, NotImplementedError) as error:
            self.skipTest("cannot create a directory symlink here: %s" % error)
        return link

    def test_project_symlink_outside_root_is_not_walked(self):
        self.own_fixture()
        link = self.link_out()
        self.assertIn(link, list(self.transcripts.iterdir()))
        self.assertNotIn(link, ui_discovery._project_directories(self.transcripts))
        self.assertEqual(
            sorted(set(fixture.SESSION_PROJECT.values())),
            sorted(path.name for path in ui_discovery._project_directories(self.transcripts)),
        )

    def test_transcript_file_symlink_outside_root_is_not_a_session(self):
        self.own_fixture()
        outside = self.tmp / "outside-session.jsonl"
        outside.write_text(
            '{"type":"ai-title","aiTitle":"%s"}\n' % self.LEAKED_TITLE,
            encoding="utf-8",
        )
        link = self.transcripts / fixture.ALPHA_PROJECT / "1e6f0000-0000-4000-8000-00000000beef.jsonl"
        try:
            link.symlink_to(outside)
        except (OSError, NotImplementedError) as error:
            self.skipTest("cannot create a file symlink here: %s" % error)
        found = ui_discovery.discover_sessions(self.transcripts)
        self.assertNotIn("1e6f0000-0000-4000-8000-00000000beef", {item["id"] for item in found["sessions"]})

    def test_unaddressable_session_name_is_reported_and_not_looked_up(self):
        self.own_fixture()
        path = self.transcripts / fixture.ALPHA_PROJECT / "..jsonl"
        path.write_text('{"type":"ai-title","aiTitle":"Nameless"}\n', encoding="utf-8")
        found = ui_discovery.discover_sessions(self.transcripts)
        self.assertIsNone(ui_discovery.find_session(self.transcripts, path.stem))
        self.assertTrue(any(path.name in item for item in found["diagnostics"]))

    def test_transcript_root_reports_only_the_declared_unencoded_project(self):
        found = ui_discovery.discover_sessions(self.transcripts)
        self.assertEqual(
            ["project directory name is not an encoded path: {0}".format(fixture.UNDECODABLE_PROJECT)],
            found["diagnostics"],
        )
