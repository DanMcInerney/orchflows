"""What `land` does with a candidate once its item has run.

Every case here is one of the 2026-08-31 trunk defects, each pinned by
the reading that was red before its fix: a run's commits merged onto the
incumbent branch of a checkout the run never named, a silent replay over
a delivery nobody committed, and a retirement refusal that prescribed the
one command which would have deleted it.
"""

from unittest import mock

from .common import *  # noqa: F401,F403

from scripts import (  # noqa: F401
    state_root, tickets_report_note, tickets_store, workspace_return,
)


def established(case, tmp, *, ticket_id="T1", repo=None):
    """One repository, one ticket, one established derived candidate."""

    main, run_dir = make_repo(tmp)
    ticket = make_ticket(run_dir, ticket_id)
    done = run_workspace(
        tmp, "establish", "testrun", ticket_id, "--repo", str(repo or main),
    )
    case.assertEqual(0, done.returncode, done.stdout + done.stderr)
    return main, ticket, state_root.candidate_paths("testrun", ticket_id)


def baseline_of(ticket_path) -> str:
    """The `workspace_baseline` `establish` stamped, read back off the ticket.

    Write-once and never corrected: every call this module makes to
    `workspace_return.integrate` after establishment reads the same value
    `_refuse_uncommitted_delivery` grades the branch tip against.
    """

    return tickets._parse_frontmatter(
        Path(ticket_path).read_text(encoding="utf-8")
    ).get(workspace_git.BASELINE_KEY)


@unittest.skipUnless(git_available(), "git is required for a real worktree fixture")
class TestTheRunOwnsWhereItsWorkIsIntegrated(unittest.TestCase):
    """A run's commits belong on the branch the run was established from.

    The evidence is commit e18ff25e: integration read the incumbent branch
    of the project root live, the user's checkout happened to be standing
    on an unrelated branch, and a whole run's result plus its `done`
    evaluation landed there.
    """

    def test_the_first_establishment_records_the_target_on_the_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, _ticket, _derived = established(self, Path(tmp))

            recorded = tickets_store.integration_target("testrun")

            self.assertEqual(str(main.resolve()), recorded["root"])
            self.assertEqual(
                git(main, "rev-parse", "--abbrev-ref", "HEAD").strip(),
                recorded["branch"],
            )

    def test_a_later_establishment_never_moves_the_recorded_target(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, _ticket, _derived = established(self, tmp)
            opened = tickets_store.integration_target("testrun")

            git(main, "checkout", "--quiet", "-b", "somewhere-else")
            make_ticket(state_root.tickets_root() / "testrun", "T2")
            second = run_workspace(tmp, "establish", "testrun", "T2", "--repo", str(main))

            self.assertEqual(0, second.returncode, second.stdout + second.stderr)
            self.assertEqual(opened, tickets_store.integration_target("testrun"))

    def test_a_checkout_that_moved_off_the_recorded_branch_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, ticket, derived = established(self, tmp)
            commit_in(derived["path"], {"scratch/work.txt": "delivered\n"}, "the work")
            recorded = tickets_store.integration_target("testrun")
            git(main, "checkout", "--quiet", "-b", "codex/somebody-elses-branch")
            before = git(main, "rev-parse", "HEAD").strip()

            with self.assertRaises(workspace_return.Refused) as refused:
                workspace_return.integrate(
                    "testrun", "T1", derived["path"], derived["branch"],
                    baseline_of(ticket),
                )

            self.assertIn("codex/somebody-elses-branch", str(refused.exception))
            self.assertIn(recorded["branch"], str(refused.exception))
            # the whole point: nothing was written onto the stranger's branch
            self.assertEqual(before, git(main, "rev-parse", "HEAD").strip())

    def test_the_recorded_branch_is_merged_and_reported_as_the_target(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, ticket, derived = established(self, tmp)
            commit_in(derived["path"], {"scratch/work.txt": "delivered\n"}, "the work")
            recorded = tickets_store.integration_target("testrun")

            body, code = workspace_return.integrate(
                "testrun", "T1", derived["path"], derived["branch"],
                baseline_of(ticket),
            )

            self.assertEqual(0, code)
            self.assertEqual("merged", body["integrate"]["outcome"])
            self.assertEqual(recorded["branch"], body["integrate"]["into"])
            self.assertEqual(str(main.resolve()), body["integrate"]["main_root"])
            self.assertTrue((main / "scratch" / "work.txt").is_file())

    def test_a_run_that_recorded_no_target_is_refused_with_the_establishment(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            _main, ticket, derived = established(self, tmp)
            identity = state_root.runs_root() / "testrun" / "run.json"
            document = json.loads(identity.read_text(encoding="utf-8"))
            document.pop(tickets_store.INTEGRATION_KEY)
            identity.write_text(json.dumps(document), encoding="utf-8")

            with self.assertRaises(workspace_return.Refused) as refused:
                workspace_return.integrate(
                    "testrun", "T1", derived["path"], derived["branch"],
                    baseline_of(ticket),
                )

            self.assertIn("records no integration target", str(refused.exception))
            self.assertIn("workspace.py establish testrun T1", str(refused.exception))


@unittest.skipUnless(git_available(), "git is required for a real worktree fixture")
class TestOnlyADeclaringEstablishmentFixesTheTarget(unittest.TestCase):
    """The 2026-09-02 ladder dogfood: two runs died on one write.

    Both were building a repository the driver was not standing in. A call
    that named no `--workspace` established its candidate in the driver's own
    checkout, the run's write-once target was fixed there, and every wave
    after it -- all cut from the repository being built -- landed `absent` at
    exit 0 and merged nothing.
    """

    def test_an_establishment_that_named_no_tree_records_no_target(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, run_dir = make_repo(Path(tmp))
            make_ticket(run_dir, "T1")

            # no `--repo`: the tree is the process's own directory, which is
            # a default and not the caller saying where the work belongs
            done = run_workspace(main, "establish", "testrun", "T1")

            self.assertEqual(0, done.returncode, done.stdout + done.stderr)
            self.assertIsNone(tickets_store.integration_target("testrun"))
            self.assertTrue(payload_of(done)["establish"]["isolated"])

    def test_a_judging_item_establishes_a_candidate_and_fixes_no_target(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, run_dir = make_repo(tmp)
            make_ticket(run_dir, "J1", executor="orch-judge")

            judged = run_workspace(
                tmp, "establish", "testrun", "J1", "--repo", str(main),
            )

            self.assertEqual(0, judged.returncode, judged.stdout + judged.stderr)
            self.assertTrue(payload_of(judged)["establish"]["isolated"])
            self.assertIsNone(tickets_store.integration_target("testrun"))

    def test_the_facade_names_a_repo_to_its_child_only_when_a_caller_did(self):
        """Where the guess entered: the dispatch trunk filled `--repo` in
        from its own directory, and the child could not tell that apart from
        a caller declaring where the run's work belongs."""

        from scripts import tickets_dispatch_facade as facade

        seen = []

        def spy(source, verb, arguments):
            seen.append(list(arguments))
            return {"establish": {workspace_record.PATH_KEY: str(source)}}, None

        with mock.patch.object(facade, "_workspace", side_effect=spy):
            facade._workspace_establish("testrun", "T1", None)
            facade._workspace_establish("testrun", "T1", str(Path.cwd()))

        self.assertNotIn("--repo", seen[0])
        self.assertIn("--repo", seen[1])

    def test_a_document_lane_landed_first_leaves_the_target_to_the_first_do(self):
        """The run in the dogfood table: a content call, then the real waves."""

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, run_dir = make_repo(tmp)
            prose = tmp / "prose"
            prose.mkdir()
            make_ticket(run_dir, "C1", pack="orch-content-pack", isolation=None)
            content = run_workspace(
                prose, "establish", "testrun", "C1", "--repo", str(prose),
            )
            self.assertEqual(0, content.returncode, content.stdout + content.stderr)
            self.assertIsNone(tickets_store.integration_target("testrun"))

            ticket = make_ticket(run_dir, "T1")
            done = run_workspace(
                tmp, "establish", "testrun", "T1", "--repo", str(main),
            )
            self.assertEqual(0, done.returncode, done.stdout + done.stderr)
            derived = state_root.candidate_paths("testrun", "T1")

            recorded = tickets_store.integration_target("testrun")
            self.assertEqual(str(main.resolve()), recorded["root"])
            commit_in(derived["path"], {"scratch/work.txt": "delivered\n"}, "the work")
            body, code = workspace_return.integrate(
                "testrun", "T1", derived["path"], derived["branch"],
                baseline_of(ticket),
            )
            self.assertEqual(0, code)
            self.assertEqual("merged", body["integrate"]["outcome"])
            self.assertTrue((main / "scratch" / "work.txt").is_file())


@unittest.skipUnless(git_available(), "git is required for a real worktree fixture")
class TestAnAbsentIntegrationNamesWhereItLooked(unittest.TestCase):
    """`absent` used to be one word for two findings.

    A candidate cut from a repository the run does not integrate into is the
    defect; a candidate whose tree a previous landing already retired is a
    replay. Only the first names a repository and a branch, and only the
    first stops the landing.
    """

    def repointed(self, tmp: Path, root: Path, branch: str) -> None:
        """Move the recorded target, as a run whose first call guessed did."""

        identity = state_root.runs_root() / "testrun" / "run.json"
        document = json.loads(identity.read_text(encoding="utf-8"))
        document[tickets_store.INTEGRATION_KEY] = dict(
            document[tickets_store.INTEGRATION_KEY], root=str(root), branch=branch,
        )
        identity.write_text(json.dumps(document), encoding="utf-8")

    def test_a_candidate_the_target_does_not_carry_names_the_repo_and_branch(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            _main, ticket, derived = established(self, tmp)
            commit_in(derived["path"], {"scratch/work.txt": "delivered\n"}, "the work")
            elsewhere = tmp / "elsewhere"
            elsewhere.mkdir()
            git(elsewhere, "init", "--quiet")
            (elsewhere / "seed.txt").write_text("seed\n", encoding="utf-8")
            git(elsewhere, "add", "seed.txt")
            git(elsewhere, "commit", "--quiet", "-m", "seed")
            standing = git(elsewhere, "rev-parse", "--abbrev-ref", "HEAD").strip()
            self.repointed(tmp, elsewhere, standing)

            body, code = workspace_return.integrate(
                "testrun", "T1", derived["path"], derived["branch"],
                baseline_of(ticket),
            )

            self.assertEqual(0, code)
            reported = body["integrate"]
            self.assertEqual("absent", reported["outcome"])
            self.assertEqual(str(elsewhere), reported["main_root"])
            self.assertIn(derived["branch"], reported["detail"])
            self.assertIn(str(elsewhere), reported["detail"])

    def test_a_retired_candidate_is_absent_with_nothing_to_name(self):
        """The lawful replay: the tree is gone, so nothing was looked for."""

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            _main, ticket, derived = established(self, tmp)
            commit_in(derived["path"], {"scratch/work.txt": "delivered\n"}, "the work")
            baseline = baseline_of(ticket)
            merged, _code = workspace_return.integrate(
                "testrun", "T1", derived["path"], derived["branch"], baseline,
            )
            self.assertEqual("merged", merged["integrate"]["outcome"])
            retired = run_workspace(tmp, "retire", "testrun", "T1")
            self.assertEqual(0, retired.returncode, retired.stdout + retired.stderr)

            body, code = workspace_return.integrate(
                "testrun", "T1", derived["path"], derived["branch"], baseline,
            )

            self.assertEqual(0, code)
            self.assertEqual("absent", body["integrate"]["outcome"])
            self.assertNotIn("detail", body["integrate"])


class TestOneSystemWrittenNotePerObservation(unittest.TestCase):
    """`## Report` is one channel, and the join writes into it too.

    A `tickets.py result` after the attempt's outcome is refused as out of
    causal order, so the eleven join-overlap resolutions of the 2026-09-02
    ladder run lived only in the driver's journal. These are written into
    the section directly, and each is filed once however often it is
    observed.
    """

    def report_of(self, path: Path) -> str:
        return tickets._sections(
            path.read_text(encoding="utf-8")
        ).get("Report", "")

    def test_a_note_observed_twice_is_filed_once_and_attributed_to_the_join(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            _main, run_dir = make_repo(tmp)
            ticket = make_ticket(run_dir, "T1")
            note = tickets_report_note.resolution_note(
                "wt/testrun/T1", "main", "abc1234", "def5678",
            )

            first, refusal = tickets_report_note.file_once(
                ticket, "root-join", note, "integration evidence",
            )
            second, replayed = tickets_report_note.file_once(
                ticket, "root-join", note, "integration evidence",
            )

            self.assertEqual(("filed", None), (first, refusal))
            self.assertEqual(("replayed", None), (second, replayed))
            report = self.report_of(ticket)
            self.assertEqual(1, report.count(note))
            self.assertIn("`root-join`", report)
            self.assertTrue(tickets_report_note.carries(
                ticket, tickets_report_note.RESOLVED_PREFIX,
            ))
            self.assertFalse(tickets_report_note.carries(
                ticket, tickets_report_note.CONFLICT_PREFIX,
            ))


@unittest.skipUnless(git_available(), "git is required for a real worktree fixture")
class TestAnUncommittedDeliveryIsNotAReplay(unittest.TestCase):
    """Two members of one run landed complete on empty branches.

    Each worker closed without committing. The merge carried nothing, and
    integration answered `replayed` -- the one word that reads exactly
    like a lawful second landing, so nothing downstream looked again.
    """

    def test_a_dirty_candidate_carrying_no_commits_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            _main, ticket, derived = established(self, tmp)
            (derived["path"] / "delivery.txt").write_text(
                "the whole thing, uncommitted\n", encoding="utf-8",
            )

            with self.assertRaises(workspace_return.Refused) as refused:
                workspace_return.integrate(
                    "testrun", "T1", derived["path"], derived["branch"],
                    baseline_of(ticket),
                )

            message = str(refused.exception)
            self.assertIn("delivery.txt", message)
            self.assertIn("never committed", message)
            self.assertIn("Commit it in the candidate", message)

    def test_a_clean_candidate_carrying_no_commits_still_replays(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            _main, ticket, derived = established(self, tmp)

            body, code = workspace_return.integrate(
                "testrun", "T1", derived["path"], derived["branch"],
                baseline_of(ticket),
            )

            self.assertEqual(0, code)
            self.assertEqual("replayed", body["integrate"]["outcome"])

    def test_bytecode_beside_a_replay_is_emission_and_not_a_delivery(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            _main, ticket, derived = established(self, tmp)
            cache = derived["path"] / "__pycache__"
            cache.mkdir(parents=True)
            (cache / "oracle.cpython-39.pyc").write_bytes(b"\x00")

            body, code = workspace_return.integrate(
                "testrun", "T1", derived["path"], derived["branch"],
                baseline_of(ticket),
            )

            self.assertEqual(0, code)
            self.assertEqual("replayed", body["integrate"]["outcome"])

    def test_a_dirty_candidate_that_does_carry_commits_still_merges(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            _main, ticket, derived = established(self, tmp)
            commit_in(derived["path"], {"scratch/work.txt": "delivered\n"}, "the work")
            (derived["path"] / "notes.txt").write_text("scratch\n", encoding="utf-8")

            body, code = workspace_return.integrate(
                "testrun", "T1", derived["path"], derived["branch"],
                baseline_of(ticket),
            )

            self.assertEqual(0, code)
            self.assertEqual("merged", body["integrate"]["outcome"])

    def test_a_replayed_landing_ignores_leftover_scratch_once_commits_are_carried(self):
        """The 2026-09-01 replay-refusal defect, at its own seam.

        Two members of this run's own root landed `complete` on branches
        the merge had already fully absorbed, and each had left its own
        compliant note scratch behind -- `.orch-outcome-B1.2.md` for one
        worker, `outcome-note-B1.3.txt` for the other, no filename pattern
        shared between them. `_refuse_uncommitted_delivery` used to grade
        that by ancestry -- whether the branch tip was already merged into
        the checkout's HEAD -- and a branch replayed after a real delivery
        is just as merged as one that never delivered anything. The
        discriminator is the branch's own `workspace_baseline` now: once it
        has carried a real commit past that baseline, arbitrarily-named
        scratch beside it is the worker's business, not a reason to refuse.
        """

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            _main, ticket, derived = established(self, tmp)
            commit_in(derived["path"], {"scratch/work.txt": "delivered\n"}, "the work")
            baseline = baseline_of(ticket)

            first, code = workspace_return.integrate(
                "testrun", "T1", derived["path"], derived["branch"], baseline,
            )
            self.assertEqual(0, code)
            self.assertEqual("merged", first["integrate"]["outcome"])

            (derived["path"] / ".orch-outcome-B1.2.md").write_text(
                "closing note\n", encoding="utf-8",
            )
            (derived["path"] / "outcome-note-B1.3.txt").write_text(
                "a different worker's own name for the same kind of file\n",
                encoding="utf-8",
            )

            replayed, code = workspace_return.integrate(
                "testrun", "T1", derived["path"], derived["branch"], baseline,
            )

            self.assertEqual(0, code)
            self.assertEqual("replayed", replayed["integrate"]["outcome"])

    def test_a_zero_commit_branch_still_refuses_with_the_baseline_discriminator(self):
        """The other half of the same fix: a branch that never advanced past
        its own established baseline is still refused while its candidate
        holds uncommitted work, whatever that scratch happens to be named."""

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            _main, ticket, derived = established(self, tmp)
            (derived["path"] / "outcome-note-B1.3.txt").write_text(
                "a worker's own differently-named note file\n", encoding="utf-8",
            )

            with self.assertRaises(workspace_return.Refused) as refused:
                workspace_return.integrate(
                    "testrun", "T1", derived["path"], derived["branch"],
                    baseline_of(ticket),
                )

            message = str(refused.exception)
            self.assertIn("outcome-note-B1.3.txt", message)
            self.assertIn("never committed", message)


@unittest.skipUnless(git_available(), "git is required for a real worktree fixture")
class TestARefusedRetirementNeverPrescribesForce(unittest.TestCase):
    """The refusal that saved a worker's only copy also named the command
    that would have deleted it. `--force` stays available to a caller who
    has looked; nothing here ever recommends it."""

    def test_uncommitted_work_is_named_with_the_act_that_preserves_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            _main, _ticket, derived = established(self, tmp)
            (derived["path"] / "unsaved.txt").write_text("work\n", encoding="utf-8")

            kept = run_workspace(tmp, "retire", "testrun", "T1")

            self.assertEqual(1, kept.returncode, kept.stdout)
            message = payload_of(kept)["error"]
            self.assertNotIn("--force", message)
            self.assertIn("unsaved.txt", message)
            self.assertIn("land testrun/T1 again", message)
            self.assertTrue(derived["path"].is_dir())

    def test_the_flag_a_caller_passes_deliberately_still_works(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            _main, _ticket, derived = established(self, tmp)
            (derived["path"] / "unsaved.txt").write_text("work\n", encoding="utf-8")

            forced = run_workspace(tmp, "retire", "testrun", "T1", "--force")

            self.assertEqual(0, forced.returncode, forced.stdout + forced.stderr)
            self.assertFalse(derived["path"].exists())
