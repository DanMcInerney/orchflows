"""State-root resolution and UI discovery regressions."""

from tests.test_ui_cases._web import *  # noqa: F401,F403
class TestRootResolution(unittest.TestCase):
    """Spec criterion 5, at the sink: what the viewer reads no longer depends
    on where it was launched, because run state is not in the repository."""

    def test_every_workspace_reads_the_one_sink(self):
        """What the worktree-versus-main-checkout case used to prove, now
        proved of the thing that decides it. The viewer is run from a main
        checkout, from a linked worktree of it, and from a directory in no
        repository at all: the sink resolves the same three times, and the
        ticket set it yields is the same set."""

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            sink = make_sink(tmp)
            main = tmp / "main"
            (main / ".git" / "worktrees" / "wt").mkdir(parents=True)
            worktree = tmp / "wt"
            worktree.mkdir()
            (worktree / ".git").write_text(
                "gitdir: {0}\n".format(main / ".git" / "worktrees" / "wt"),
                encoding="utf-8",
            )
            nowhere = tmp / "nowhere"
            nowhere.mkdir()

            expected = ticket_paths(ui.discover(sink))
            self.assertEqual(fixture_ticket_count(), len(expected), expected)
            self.assertTrue(expected)
            with mock.patch.dict(os.environ, {SINK_ENV_VAR: str(sink)}):
                for launched_from in (main, worktree, nowhere):
                    with self.subTest(launched_from.name):
                        cwd = os.getcwd()
                        os.chdir(str(launched_from))
                        try:
                            root = ui.default_root()
                        finally:
                            os.chdir(cwd)
                        self.assertEqual(sink, root)
                        self.assertEqual(expected, ticket_paths(ui.discover(root)))

    def test_the_default_root_is_the_resolvers_sink_and_root_overrides_it(self):
        """One owner for the path (`rules/visibility.md` §3): `ui.py` states
        no sink path of its own, and `--root` still points the viewer at a
        copy of a sink."""

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            sink = make_sink(tmp)
            with mock.patch.dict(os.environ, {SINK_ENV_VAR: str(sink)}):
                self.assertEqual(state_root.state_root(), ui.default_root())
                self.assertEqual(sink, ui.default_root())
            elsewhere = tmp / "elsewhere"
            shutil.copytree(str(sink), str(elsewhere))
            # Compared sink-relative, never by rewriting one absolute path
            # into the other: `discover` resolves the root it is handed, and
            # a resolved temporary directory is not always a rewrite away
            # from the unresolved one -- on Windows it loses an 8.3 short
            # name, so the rewrite silently does nothing and the case fails
            # for a reason that is not the one it grades.
            self.assertEqual(
                relative_ticket_paths(ui.discover(sink)),
                relative_ticket_paths(ui.discover(elsewhere)),
            )

    def test_the_source_composes_no_sink_path_of_its_own(self):
        """Criterion 6 for this file: the only `.orch` left in `scripts/ui.py`
        is prose or the installed `~/.orchflows/bin` path, never a joined
        run-state path."""

        source = UI_PY.read_text(encoding="utf-8")
        self.assertNotIn('".orch"', source)
        self.assertNotIn("'.orch'", source)
        self.assertIn("state_root.state_root()", source)

    def test_every_run_directory_is_discovered_including_the_empty_one(self):
        with tempfile.TemporaryDirectory() as tmp:
            discovery = ui.discover(make_sink(Path(tmp)))
            self.assertEqual(
                sorted(FIXTURE_RUNS + (EMPTY_RUN,)),
                [run["run"] for run in discovery["runs"]],
            )
            by_run = {run["run"]: run for run in discovery["runs"]}
            self.assertEqual([], by_run[EMPTY_RUN]["tickets"])
            self.assertEqual(
                ["A1", "A2"], [t["id"] for t in by_run["run-alpha"]["tickets"]]
            )


class TestUiResolvesSink(unittest.TestCase):
    """Item 05 criterion 2. The renderer's three data trees now hang off the
    sink, and the two properties that made it safe against `.orch/` -- it
    writes nothing, and it resolves no ticket outside the tickets root -- are
    re-proved against the sink rather than assumed to have travelled."""

    def test_the_three_streams_render_from_a_sink(self):
        """Tickets, friction and events, each read from its sink-relative
        directory: no route falls back to a repository."""

        with tempfile.TemporaryDirectory() as tmp:
            sink = make_sink(Path(tmp))

            status, index = ui.render_route(sink, "/")
            self.assertEqual(200, status)
            for run in FIXTURE_RUNS + (EMPTY_RUN,):
                self.assertNotEqual("", section_for(index, run), run)

            status, friction = ui.render_route(sink, "/friction")
            self.assertEqual(200, status)
            self.assertNotIn(ui.EMPTY_NO_FRICTION, friction)

            # `run-gamma` is the one fixture run carrying an event log.
            status, graph = ui.render_route(sink, graph_url("run-gamma"))
            self.assertEqual(200, status)
            self.assertIn("<h2>events</h2>", graph)

    def test_a_sink_missing_a_stream_still_renders_the_other_two(self):
        # The three directories are independent: `state_root` creates the
        # sink, and whichever writer runs first creates its own subtree.
        with tempfile.TemporaryDirectory() as tmp:
            sink = make_sink(Path(tmp), friction=False, events=False)

            self.assertFalse((sink / "friction").exists())
            status, page = ui.render_route(sink, "/friction")

            self.assertEqual(200, status)
            self.assertIn(ui.EMPTY_NO_FRICTION, page)
            self.assertEqual(200, ui.render_route(sink, "/")[0])
            self.assertEqual(200, ui.render_route(sink, graph_url("run-gamma"))[0])

    def test_a_full_render_leaves_the_sink_byte_for_byte_unchanged(self):
        """`scripts/ui.py:6` against the sink: every route, then the same
        recursive listing. The renderer opens nothing for writing and makes
        no directory, so a viewer left running never mutates run state."""

        with tempfile.TemporaryDirectory() as tmp:
            sink = make_sink(Path(tmp))
            transcripts = make_transcripts(Path(tmp))
            before = snapshot(sink)
            self.assertTrue(before)

            for url in every_route():
                status, page = ui.render_route(sink, url, transcripts)
                self.assertIn(status, (200, 404), url)
                self.assertTrue(page, url)

            self.assertEqual(before, snapshot(sink))

    def test_an_absent_sink_is_the_named_empty_state_not_a_traceback(self):
        with tempfile.TemporaryDirectory() as tmp:
            absent = Path(tmp) / "never-written"

            for url in ("/", "/friction", graph_url("run-alpha")):
                with self.subTest(url):
                    status, page = ui.render_route(absent, url)
                    # A run absent from an absent sink is the same named 404
                    # a run absent from a populated one gets.
                    self.assertIn(status, (200, 404))
                    self.assertNotIn("Traceback", page)
            self.assertIn(ui.EMPTY_NO_SINK, ui.render_route(absent, "/")[1])
            self.assertFalse(absent.exists())

    def test_no_ticket_resolves_outside_the_sinks_tickets_root(self):
        """`scripts/ui.py:648` at the sink. The secret sits beside the
        tickets root, reachable by a plain join and not by this one."""

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            sink = make_sink(tmp)
            secret = sink / "secret.md"
            secret.write_text("id: S1\n", encoding="utf-8")
            self.assertTrue((sink / "tickets" / ".." / "secret.md").exists())

            for run, ticket_id in (
                ("..", "secret"),
                ("run-alpha", "../../secret"),
                ("../..", "secret"),
            ):
                with self.subTest(run + "/" + ticket_id):
                    self.assertIsNone(ui.find_ticket(sink, run, ticket_id))
            self.assertIsNotNone(ui.find_ticket(sink, "run-alpha", "A1"))

    def test_the_containment_root_moved_with_the_tickets_root(self):
        # A guard still anchored to the old parent would admit anything under
        # the sink, `secret.md` included. It is refused above; here the sink's
        # own parent is refused too, so the root really is `<sink>/tickets`.
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            sink = make_sink(tmp)
            (tmp / "outside.md").write_text("id: O1\n", encoding="utf-8")

            self.assertIsNone(ui.find_ticket(sink, "../..", "outside"))
            self.assertEqual(
                (sink / "tickets" / "run-alpha" / "A1.md").resolve(),
                ui._in_tree(sink / "tickets", "run-alpha", "A1.md"),
            )


