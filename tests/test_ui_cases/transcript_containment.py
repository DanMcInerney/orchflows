"""Transcript containment, addressing, and session-case regressions."""

from tests.test_ui_cases._transcript_support import *  # noqa: F401,F403
class TestTranscriptContainment(TranscriptCase):
    """`_in_tree`'s guarantee, over the tree it was not yet applied to.

    The transcript root is the entire scope of what this viewer may open, and
    `~/.claude/projects` is a directory anything on the machine can be linked
    into. `_subagent_files` already checks containment; the project walk one
    level above it is the same question about the same tree.
    """

    LEAKED_TITLE = "LEAKED-TITLE"

    def link_out(self, name: str = "-Users-dmcinerney-tools-leaked") -> Path:
        """A project-shaped symlink under the root, pointing out of it."""

        outside = self.tmp / "outside"
        outside.mkdir()
        (outside / "1e6f0000-0000-4000-8000-00000000beef.jsonl").write_text(
            '{"type":"ai-title","aiTitle":"%s"}\n' % self.LEAKED_TITLE,
            encoding="utf-8",
        )
        link = self.transcripts / name
        try:
            link.symlink_to(outside, target_is_directory=True)
        except (OSError, NotImplementedError) as error:
            # Windows only permits this under Developer Mode or admin.
            self.skipTest("cannot create a directory symlink here: %s" % error)
        return link

    def test_the_link_is_an_entry_the_walk_would_otherwise_take(self):
        # The premise. Without it the two cases below are proved by a link
        # `iterdir` never returned or `is_dir` already rejected.
        self.own_fixture()
        link = self.link_out()

        self.assertIn(link, list(self.transcripts.iterdir()))
        self.assertTrue(link.is_dir())

    def test_a_project_linked_out_of_the_root_is_not_a_project(self):
        self.own_fixture()
        link = self.link_out()

        self.assertNotIn(link, ui._project_directories(self.transcripts))
        # Not by returning nothing: the real projects are still walked.
        self.assertEqual(
            sorted(set(SESSION_PROJECT.values())),
            sorted(path.name for path in ui._project_directories(self.transcripts)),
        )

    def test_nothing_outside_the_root_reaches_any_route(self):
        self.own_fixture()
        self.link_out()

        with serving(self.main, self.transcripts) as server:
            for route in every_route():
                self.assertNotIn(self.LEAKED_TITLE, get(server, route)[1], route)

        self.assertEqual(list(SESSIONS_NEWEST_FIRST), session_ids(self.sessions()))


class TestUnaddressableSessions(TranscriptCase):
    """A row is a promise that the link on it opens.

    `/session` takes its id in a query string and `_safe_name` is the
    boundary that query crosses, so a filename the walk finds and the
    boundary refuses cannot be both listed and linked: the reader clicks it
    and is told there is no such session, about a file this page just drew.
    """

    # `Path("..jsonl").stem` is `"."`, which `_safe_name` refuses outright.
    # An ordinary filename on every filesystem this suite runs on, Windows
    # included -- not a traversal, and not a control character Windows
    # forbids.
    UNADDRESSABLE = "..jsonl"

    def plant(self) -> Path:
        path = self.transcripts / ALPHA_PROJECT / self.UNADDRESSABLE
        path.write_text('{"type":"ai-title","aiTitle":"Nameless"}\n', encoding="utf-8")
        return path

    def test_the_walk_finds_it_and_the_lookup_boundary_refuses_it(self):
        # The premise, on both sides. Without it the cases below are proved
        # by a file the glob never returned or a name the boundary allows.
        self.own_fixture()
        path = self.plant()

        self.assertIn(path, list((self.transcripts / ALPHA_PROJECT).glob("*.jsonl")))
        self.assertEqual("", ui._safe_name(path.stem))
        self.assertIsNone(ui.find_session(self.transcripts, path.stem))

    def test_a_session_that_cannot_be_opened_is_not_offered_as_a_link(self):
        self.own_fixture()
        self.plant()

        self.assertEqual(list(SESSIONS_NEWEST_FIRST), session_ids(self.sessions()))

    def test_the_page_says_why_rather_than_dropping_it_in_silence(self):
        self.own_fixture()
        self.plant()
        notes = block_for(self.sessions(), "diagnostics", "</ul>")

        self.assertIn(ui.DIAGNOSTIC_UNADDRESSABLE_SESSION, notes)
        self.assertIn(self.UNADDRESSABLE, notes)

    def test_a_healthy_root_carries_no_such_diagnostic(self):
        # Otherwise the case above is satisfied by a page that warns about
        # every session it lists.
        self.assertNotIn(
            ui.DIAGNOSTIC_UNADDRESSABLE_SESSION,
            block_for(self.sessions(), "diagnostics", "</ul>"),
        )

    def test_the_validator_moves_when_such_a_file_appears(self):
        # The diagnostic is part of the page, so a basis blind to the file
        # behind it serves a 304 to a page that has moved -- `U3` again. No
        # directory is stat'd by this walk, so nothing else here would notice.
        self.own_fixture()
        with frozen_clock():
            before = ui.entity_tag(self.main, ui.SESSIONS_ROUTE, None, self.transcripts)
            self.plant()
            after = ui.entity_tag(self.main, ui.SESSIONS_ROUTE, None, self.transcripts)

        self.assertNotEqual(before, after)


class TestSessionRouteRegistration(unittest.TestCase):
    """`S1` completion test 10. `U1`'s tuple is what makes the read-only,
    no-network and escaping guards sweep a route at all."""

    def test_the_route_is_declared_and_carries_concrete_examples(self):
        self.assertIn(ui.SESSIONS_ROUTE, ui.ROUTES)
        self.assertTrue(ROUTE_EXAMPLES[ui.SESSIONS_ROUTE])
        self.assertIn(ui.SESSIONS_ROUTE, every_route())


class SessionCase(TranscriptCase):
    """One session's flowchart, fetched through the route rather than built
    from the renderer, so every assertion below is about a served page."""

    def flowchart(self, session=TITLED_SESSION, transcripts=True) -> str:
        root = self.transcripts if transcripts is True else transcripts
        status, page = ui.render_route(self.main, session_url(session), root)
        self.assertEqual(200, status)
        return page

    def read(self, session=TITLED_SESSION) -> dict:
        found = ui.find_session(self.transcripts, session)
        self.assertIsNotNone(found, session)
        return ui.read_session(found)

    def graph(self, session=TITLED_SESSION) -> tuple:
        return ui.session_graph(self.read(session)["agents"])

    def subagents(self, session: str) -> Path:
        return self.transcripts / SESSION_PROJECT[session] / session / "subagents"
