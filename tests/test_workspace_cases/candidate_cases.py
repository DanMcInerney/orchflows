"""The derived candidate workspace: derive it, establish it, refuse, retire.

``start`` records the tree a caller is standing in; nothing created that
tree, which is why a whole cut could be dispatched into one directory and
why a packet could carry a sibling's workspace. ``establish`` owns the
tree instead, at the path the item's own identity derives.
"""

import time
from unittest import mock

from .common import *  # noqa: F401,F403

from scripts import (  # noqa: F401
    state_root, tickets_dispatch_facade, tickets_store, workspace_candidate,
)

# long enough that a child which was going to stamp would have stamped
LOCK_WAIT = 2.0


class TestDerivedCandidatePaths(unittest.TestCase):
    """`state_root` derives both the path and the branch, and nothing else
    may: a second spelling of either is a second answer to "which tree is
    this item's", and the packet carried the wrong one."""

    def setUp(self):
        self.prior = os.environ.get("ORCHFLOWS_WORKTREES_HOME")

    def tearDown(self):
        if self.prior is None:
            os.environ.pop("ORCHFLOWS_WORKTREES_HOME", None)
        else:
            os.environ["ORCHFLOWS_WORKTREES_HOME"] = self.prior

    def test_the_derived_tree_is_a_sibling_of_the_state_sink(self):
        with tempfile.TemporaryDirectory() as tmp:
            sink = use_sink(Path(tmp))
            os.environ.pop("ORCHFLOWS_WORKTREES_HOME", None)

            derived = state_root.candidate_paths("run-1", "T1")

            self.assertEqual(sink.parent / "worktrees", state_root.worktrees_root())
            self.assertEqual(sink.parent / "worktrees" / "run-1" / "T1", derived["path"])
            self.assertEqual("wt/run-1/T1", derived["branch"])
            # outside the sink's own trees: a worktree is a checkout, and a
            # sink walker that met one would read a repository as records
            self.assertNotIn(sink, derived["path"].parents)

    def test_the_environment_override_moves_every_derived_tree(self):
        with tempfile.TemporaryDirectory() as tmp:
            use_sink(Path(tmp))
            elsewhere = Path(tmp) / "volume" / "trees"
            os.environ["ORCHFLOWS_WORKTREES_HOME"] = str(elsewhere)

            derived = state_root.candidate_paths("run-1", "T1")

            self.assertEqual(elsewhere, state_root.worktrees_root())
            self.assertEqual(elsewhere / "run-1" / "T1", derived["path"])

    def test_two_siblings_of_one_run_derive_two_trees_and_two_branches(self):
        with tempfile.TemporaryDirectory() as tmp:
            use_sink(Path(tmp))
            os.environ.pop("ORCHFLOWS_WORKTREES_HOME", None)

            first = state_root.candidate_paths("run-1", "T1")
            second = state_root.candidate_paths("run-1", "T2")

            self.assertNotEqual(first["path"], second["path"])
            self.assertNotEqual(first["branch"], second["branch"])

    def test_a_segment_that_is_not_one_segment_is_refused_not_joined(self):
        for run, ticket_id in (("..", "T1"), ("run", "../T1"), ("run", "a\\b"),
                               ("", "T1"), ("run", "  ")):
            with self.subTest(run=run, ticket=ticket_id):
                with self.assertRaises(ValueError):
                    state_root.candidate_paths(run, ticket_id)

    def test_a_realistic_identity_stays_far_under_the_windows_path_ceiling(self):
        """The reason the derived root is short and user-scope. An item opens
        files far below its own root, and MAX_PATH is spent by the prefix
        before the item has written a byte."""

        os.environ.pop("ORCHFLOWS_WORKTREES_HOME", None)
        prior = os.environ.get(STATE_HOME_ENV_VAR)
        os.environ[STATE_HOME_ENV_VAR] = str(Path.home() / ".orchflows" / "state")
        try:
            derived = state_root.candidate_paths(
                "20260830T120000Z", "01-workspace-owner.gate.verify"
            )
        finally:
            if prior is not None:
                os.environ[STATE_HOME_ENV_VAR] = prior
        self.assertLess(len(str(derived["path"])), 150, derived["path"])


@unittest.skipUnless(git_available(), "git is required for a real worktree fixture")
class TestEstablishCreatesTheDerivedCandidate(unittest.TestCase):
    """An isolation-required item is handed a tree, not asked to find one."""

    def establish(self, tmp, main, *extra, ticket="T1"):
        return run_workspace(tmp, "establish", "testrun", ticket, "--repo", str(main), *extra)

    def test_it_creates_the_derived_worktree_and_records_what_it_created(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, run_dir = make_repo(tmp)
            ticket = make_ticket(run_dir, "T1")
            head = git(main, "rev-parse", "HEAD").strip()
            derived = state_root.candidate_paths("testrun", "T1")

            done = self.establish(tmp, main)

            self.assertEqual(0, done.returncode, done.stdout + done.stderr)
            body = payload_of(done)["establish"]
            self.assertTrue(derived["path"].is_dir(), derived["path"])
            self.assertEqual(str(derived["path"]), body[workspace.PATH_KEY])
            self.assertEqual(derived["branch"], body[workspace.BRANCH_KEY])
            self.assertEqual(f"{head} clean", body[workspace.BASELINE_KEY])
            self.assertFalse(body["replayed"])
            self.assertTrue(body["isolated"])
            self.assertEqual([], body["shared_with"])
            after = ticket.read_text(encoding="utf-8")
            self.assertIn(f"workspace_path: {derived['path']}\n", after)
            self.assertIn(f"workspace_branch: {derived['branch']}\n", after)
            self.assertIn(
                str(derived["path"]).replace("\\", "/"),
                git(main, "worktree", "list", "--porcelain").replace("\\", "/"),
            )

    def test_a_second_establishment_replays_without_moving_a_byte(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, run_dir = make_repo(tmp)
            ticket = make_ticket(run_dir, "T1")

            first = self.establish(tmp, main)
            self.assertEqual(0, first.returncode, first.stdout + first.stderr)
            stamped = ticket.read_bytes()
            # the tree moves on: a replay must not rewrite the baseline the
            # join measures the item's own change against
            commit_in(main, {"README.md": "moved on\n"}, "the source advances")

            second = self.establish(tmp, main)

            self.assertEqual(0, second.returncode, second.stdout + second.stderr)
            body = payload_of(second)["establish"]
            self.assertTrue(body["replayed"])
            self.assertEqual(
                payload_of(first)["establish"][workspace.BASELINE_KEY],
                body[workspace.BASELINE_KEY],
            )
            self.assertEqual(stamped, ticket.read_bytes())

    def test_a_stamped_baseline_decides_the_revision_the_tree_is_cut_from(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, run_dir = make_repo(tmp)
            cut_from = git(main, "rev-parse", "HEAD").strip()
            make_ticket(
                run_dir, "T1",
                extra=((workspace.BASELINE_KEY, f"{cut_from} clean"),),
            )
            commit_in(main, {"README.md": "moved on\n"}, "the source advances")
            derived = state_root.candidate_paths("testrun", "T1")

            done = self.establish(tmp, main)

            self.assertEqual(0, done.returncode, done.stdout + done.stderr)
            self.assertEqual(
                cut_from, git(derived["path"], "rev-parse", "HEAD").strip()
            )
            self.assertEqual(
                f"{cut_from} clean",
                payload_of(done)["establish"][workspace.BASELINE_KEY],
            )

    def test_two_siblings_of_one_run_are_established_into_two_trees(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, run_dir = make_repo(tmp)
            make_ticket(run_dir, "T1")
            make_ticket(run_dir, "T2")

            first = self.establish(tmp, main, ticket="T1")
            second = self.establish(tmp, main, ticket="T2")

            self.assertEqual(0, first.returncode, first.stdout + first.stderr)
            self.assertEqual(0, second.returncode, second.stdout + second.stderr)
            paths = {
                payload_of(answer)["establish"][workspace.PATH_KEY]
                for answer in (first, second)
            }
            self.assertEqual(2, len(paths), paths)
            for path in paths:
                self.assertTrue(Path(path).is_dir(), path)
            # the sharing verdict that flagged a shared directory is now
            # unreachable for these items: neither can be standing in the other
            for answer in (first, second):
                self.assertEqual([], payload_of(answer)["establish"]["shared_with"])

    def test_an_item_that_declares_no_isolation_observes_the_source_tree(self):
        """The Git adapter's admission refuses an unisolated candidate, so
        this shape reaches ``establish`` only from a legacy record. It must
        still observe the tree it is given rather than derive one: deriving a
        tree for an item nothing will grade as isolated buys nothing and
        leaves a checkout behind."""

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, run_dir = make_repo(tmp)
            ticket = make_ticket(run_dir, "T1")
            ticket.write_text(
                tickets._set_frontmatter_field(
                    ticket.read_text(encoding="utf-8"), workspace.ISOLATION_KEY, "none"
                ),
                encoding="utf-8",
            )
            derived = state_root.candidate_paths("testrun", "T1")

            done = self.establish(tmp, main)

            self.assertEqual(0, done.returncode, done.stdout + done.stderr)
            body = payload_of(done)["establish"]
            self.assertEqual(str(main.resolve()), body[workspace.PATH_KEY])
            self.assertFalse(derived["path"].exists())

    def test_the_tree_is_cut_before_the_run_lock_and_stamped_inside_it(self):
        """The lock protects the ticket's bytes, not git's seconds. Cutting
        the tree under it would make every sibling of a run wait through a
        checkout it has no stake in -- safe to leave outside precisely
        because the path is derived and belongs to one ticket of one run."""

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, run_dir = make_repo(tmp)
            ticket = make_ticket(run_dir, "T1")
            derived = state_root.candidate_paths("testrun", "T1")

            with tickets_store._run_lock("testrun"):
                child = subprocess.Popen(
                    [sys.executable, str(WORKSPACE_PY), "establish", "testrun", "T1",
                     "--repo", str(main)],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                    encoding="utf-8", errors="replace", cwd=str(tmp), env=git_env(),
                )
                time.sleep(LOCK_WAIT)
                early = child.poll()
                cut = derived["path"].is_dir()
                stamped = workspace.PATH_KEY in ticket.read_text(encoding="utf-8")
            out, err = child.communicate(timeout=120)

            self.assertTrue(cut, "the derived tree waited for a lock it does not need")
            self.assertFalse(stamped, "the stamp landed inside another writer's lock")
            self.assertIsNone(early, out or err)
            self.assertEqual(0, child.returncode, out or err)
            self.assertIn(workspace.PATH_KEY, ticket.read_text(encoding="utf-8"))

    def test_a_research_lane_establishes_its_run_scoped_evidence_store(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, run_dir = make_repo(tmp)
            make_ticket(run_dir, "T1", extra=(("pack", "orch-research-pack"),))
            sink = Path(os.environ[STATE_HOME_ENV_VAR])

            done = self.establish(tmp, main)

            self.assertEqual(0, done.returncode, done.stdout + done.stderr)
            body = payload_of(done)["establish"]
            self.assertEqual("evidence-store", body["mechanism"])
            self.assertEqual(
                str((sink / "research" / "testrun").resolve()),
                body[workspace.PATH_KEY],
            )


@unittest.skipUnless(git_available(), "git is required for a real worktree fixture")
class TestEstablishRefusesRatherThanRecording(unittest.TestCase):
    """A refused establishment records nothing and never falls back to the
    tree the caller was standing in: an unisolated item that believes it is
    isolated writes its work into somebody else's checkout."""

    def establish(self, tmp, main, ticket="T1"):
        return run_workspace(tmp, "establish", "testrun", ticket, "--repo", str(main))

    def test_a_foreign_tree_at_the_derived_path_is_refused_unstamped(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, run_dir = make_repo(tmp)
            ticket = make_ticket(run_dir, "T1")
            before = ticket.read_bytes()
            derived = state_root.candidate_paths("testrun", "T1")
            derived["path"].mkdir(parents=True)
            (derived["path"] / "stranger.txt").write_text("x\n", encoding="utf-8")

            done = self.establish(tmp, main)

            self.assertEqual(1, done.returncode, done.stdout)
            self.assertIn("occupied", payload_of(done)["error"])
            self.assertEqual(before, ticket.read_bytes())

    def test_a_branch_no_ticket_records_is_never_adopted(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, run_dir = make_repo(tmp)
            ticket = make_ticket(run_dir, "T1")
            before = ticket.read_bytes()
            derived = state_root.candidate_paths("testrun", "T1")
            git(main, "branch", derived["branch"])

            done = self.establish(tmp, main)

            self.assertEqual(1, done.returncode, done.stdout)
            error = payload_of(done)["error"]
            self.assertIn(derived["branch"], error)
            self.assertIn("no ticket records it", error)
            self.assertEqual(before, ticket.read_bytes())
            self.assertFalse(derived["path"].exists())

    def test_a_retired_tree_comes_back_onto_the_items_own_commits(self):
        """Retire removes the tree, not the work. Re-establishing an item
        whose ticket already records its derived branch has to put the tree
        back on that branch: cutting it from the baseline again would orphan
        every commit the item made."""

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, run_dir = make_repo(tmp)
            make_ticket(run_dir, "T1")
            derived = state_root.candidate_paths("testrun", "T1")
            self.assertEqual(0, self.establish(tmp, main).returncode)
            tip = commit_in(derived["path"], {"scratch/a.txt": "work\n"}, "item work")
            retired = run_workspace(tmp, "retire", "testrun", "T1")
            self.assertEqual(0, retired.returncode, retired.stdout + retired.stderr)

            done = self.establish(tmp, main)

            self.assertEqual(0, done.returncode, done.stdout + done.stderr)
            self.assertEqual(tip, git(derived["path"], "rev-parse", "HEAD").strip())

    def test_a_repo_that_is_not_a_directory_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, run_dir = make_repo(tmp)
            make_ticket(run_dir, "T1")

            done = run_workspace(
                tmp, "establish", "testrun", "T1", "--repo", str(tmp / "nowhere")
            )

            self.assertEqual(1, done.returncode, done.stdout)
            self.assertIn("not a directory", payload_of(done)["error"])


@unittest.skipUnless(git_available(), "git is required for a real worktree fixture")
class TestRetireRemovesTheDerivedCandidate(unittest.TestCase):
    def _established(self, tmp):
        main, run_dir = make_repo(tmp)
        ticket = make_ticket(run_dir, "T1")
        done = run_workspace(tmp, "establish", "testrun", "T1", "--repo", str(main))
        self.assertEqual(0, done.returncode, done.stdout + done.stderr)
        return main, ticket, state_root.candidate_paths("testrun", "T1")

    def test_it_removes_the_tree_and_leaves_every_stamp_that_names_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, ticket, derived = self._established(tmp)
            stamped = ticket.read_bytes()

            done = run_workspace(tmp, "retire", "testrun", "T1")

            self.assertEqual(0, done.returncode, done.stdout + done.stderr)
            body = payload_of(done)["retire"]
            self.assertEqual("removed", body["outcome"])
            self.assertFalse(derived["path"].exists())
            # the join grades the item by these long after the tree is gone
            self.assertEqual(stamped, ticket.read_bytes())
            self.assertNotIn(
                str(derived["path"]).replace("\\", "/"),
                git(main, "worktree", "list", "--porcelain").replace("\\", "/"),
            )

    def test_retiring_a_tree_that_was_never_created_is_a_no_op(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            make_repo(tmp)

            done = run_workspace(tmp, "retire", "testrun", "never-established")

            self.assertEqual(0, done.returncode, done.stdout + done.stderr)
            self.assertEqual("absent", payload_of(done)["retire"]["outcome"])

    def test_a_tree_with_uncommitted_bytes_is_kept_unless_force_is_given(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, _ticket, derived = self._established(tmp)
            (derived["path"] / "unsaved.txt").write_text("work\n", encoding="utf-8")

            kept = run_workspace(tmp, "retire", "testrun", "T1")

            self.assertEqual(1, kept.returncode, kept.stdout)
            self.assertIn("worktree remove --force", payload_of(kept)["error"])
            self.assertTrue(derived["path"].is_dir())

            forced = run_workspace(tmp, "retire", "testrun", "T1", "--force")

            self.assertEqual(0, forced.returncode, forced.stdout + forced.stderr)
            self.assertFalse(derived["path"].exists())

    def test_a_directory_that_is_no_worktree_is_refused_naming_the_manual_step(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            make_repo(tmp)
            derived = state_root.candidate_paths("testrun", "T1")
            derived["path"].mkdir(parents=True)

            done = run_workspace(tmp, "retire", "testrun", "T1")

            self.assertEqual(1, done.returncode, done.stdout)
            self.assertIn("workspace.py retire testrun T1", payload_of(done)["error"])
            self.assertTrue(derived["path"].is_dir())


class TestEveryExitPathEmitsOneDocument(unittest.TestCase):
    """A caller parses this stdout. Silence read as a workspace it never got
    is the failure mode; ``--help`` is the one documented reader's answer."""

    def test_every_argument_shape_prints_exactly_one_json_document(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, run_dir = make_repo(tmp)
            make_ticket(run_dir, "T1")
            for args in (
                (),
                ("dance", "testrun", "T1"),
                ("establish",),
                ("establish", "testrun"),
                ("establish", "testrun", "T1", "--repo"),
                ("establish", "testrun", "MISSING", "--repo", str(main)),
                ("retire",),
                ("retire", "testrun", "T1"),
                ("start", "testrun", "MISSING"),
                ("check", "testrun", "T1"),
            ):
                with self.subTest(args=args):
                    done = run_workspace(main, *args)
                    self.assertTrue(done.stdout.strip(), (args, done.stderr))
                    self.assertIsInstance(json.loads(done.stdout), dict)

    def test_a_payload_that_will_not_serialize_still_prints_one_document(self):
        """The hole this closed: ``json.dumps`` used to run past the guard,
        so a payload carrying an unencodable value raised, printed nothing,
        and left the caller reading an empty stdout as an answer."""

        noise = io.StringIO()
        original = workspace._cmd_retire
        workspace._cmd_retire = lambda rest: ({"retire": object()}, 0)
        try:
            with redirect_stdout(noise), redirect_stderr(noise):
                code = workspace.main(["retire", "testrun", "T1"])
        finally:
            workspace._cmd_retire = original

        self.assertEqual(workspace.EXIT_ERROR, code)
        document = noise.getvalue().splitlines()[0]
        self.assertIn("error", json.loads(document))


@unittest.skipUnless(git_available(), "git is required for a real worktree fixture")
class TestFacadeDispatchesDistinctCandidates(unittest.TestCase):
    """`--workspace` names the tree to cut from; the packet's workspace comes
    only from establishment's own answer. The neighbours of that one hop are
    stubbed: what is under test is which tree reaches the projection, not the
    admission machinery that decides whether a ticket may be dispatched."""

    def test_two_dispatched_siblings_project_two_distinct_workspaces(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, run_dir = make_repo(tmp)
            tickets_by_id = {
                ticket_id: make_ticket(run_dir, ticket_id)
                for ticket_id in ("T1", "T2")
            }
            projected = []

            def packet(args, *, _lock_held=False):
                projected.append(args[args.index("--workspace") + 1])
                return {"packet": {"workspace": projected[-1]}}

            def opened(_args, *, _lock_held=False):
                return {"dispatch": {"outcome": "opened", "assignment_seal": "s",
                                     "dispatch_id": "D"}}

            facade = tickets_dispatch_facade
            with (
                mock.patch.object(facade, "_cmd_ready", return_value={"ready": []}),
                mock.patch.object(facade, "_cmd_dispatch_open", side_effect=opened),
                mock.patch.object(facade, "_cmd_dispatch_packet", side_effect=packet),
                # the launch is one more neighbour of the hop under test: the
                # fixture ticket binds no role, and resolving one is what the
                # dispatch-launch suite is for
                mock.patch.object(
                    facade, "precheck", return_value=({"id": "claude"}, None)
                ),
                mock.patch.object(
                    facade, "launch_spec", return_value=({"verb": "Agent"}, None)
                ),
            ):
                for ticket_id in ("T1", "T2"):
                    result = facade._cmd_dispatch([
                        "testrun", ticket_id, "--by", f"worker-{ticket_id}",
                        "--dispatch-id", f"D-{ticket_id}",
                        "--lease-expires-at", "2099-01-01T00:00:00Z",
                        "--reply-to", "root", "--workspace", str(main),
                    ])
                    self.assertNotIn("error", result, result)

            self.assertEqual(2, len(set(projected)), projected)
            for ticket_id, workspace_path in zip(("T1", "T2"), projected):
                derived = state_root.candidate_paths("testrun", ticket_id)
                # the packet's value is the derived tree, not the --workspace
                # the caller named, and it is the value the ticket now stamps
                self.assertEqual(str(derived["path"]), workspace_path)
                self.assertNotEqual(str(main.resolve()), workspace_path)
                self.assertTrue(derived["path"].is_dir())
                self.assertIn(
                    f"workspace_path: {derived['path']}\n",
                    tickets_by_id[ticket_id].read_text(encoding="utf-8"),
                )

    def test_a_failed_establishment_refuses_the_dispatch_as_one_transaction(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, run_dir = make_repo(tmp)
            ticket = make_ticket(run_dir, "T1")
            before = ticket.read_bytes()
            derived = state_root.candidate_paths("testrun", "T1")
            derived["path"].mkdir(parents=True)
            (derived["path"] / "stranger.txt").write_text("x\n", encoding="utf-8")
            retired = []

            def opened(_args, *, _lock_held=False):
                return {"dispatch": {"outcome": "opened", "assignment_seal": "s",
                                     "dispatch_id": "D-T1"}}

            facade = tickets_dispatch_facade
            with (
                mock.patch.object(facade, "_cmd_ready", return_value={"ready": []}),
                mock.patch.object(facade, "_cmd_dispatch_open", side_effect=opened),
                mock.patch.object(facade, "_cmd_dispatch_packet") as packet,
                mock.patch.object(
                    facade, "_cmd_dispatch_retire",
                    side_effect=lambda args, **kw: retired.append(args) or {"dispatch": {}},
                ),
            ):
                result = facade._cmd_dispatch([
                    "testrun", "T1", "--by", "worker", "--dispatch-id", "D-T1",
                    "--lease-expires-at", "2099-01-01T00:00:00Z",
                    "--reply-to", "root", "--workspace", str(main),
                ])

            self.assertIn("error", result)
            packet.assert_not_called()
            self.assertEqual(1, len(retired), retired)
            self.assertEqual(before, ticket.read_bytes())


class TestOwnershipOfTheEstablishmentLanes(unittest.TestCase):
    def test_only_state_root_derives_a_candidate_path_or_branch(self):
        """Grep-shaped on purpose: the defect this unit exists to end was a
        second place computing where an item's tree goes."""

        scripts = Path(workspace_candidate.__file__).resolve().parent
        offenders = []
        for path in sorted(scripts.glob("*.py")):
            if path.name == "state_root.py":
                continue
            source = path.read_text(encoding="utf-8")
            if '"worktrees"' in source or "'worktrees'" in source:
                offenders.append(path.name)
        self.assertEqual([], offenders)

    def test_the_candidate_owner_never_imports_the_workspace_facade(self):
        source = Path(workspace_candidate.__file__).read_text(encoding="utf-8")
        for reached in ("import workspace\n", "from workspace import",
                        "__import__(\"workspace\")"):
            self.assertNotIn(reached, source)
