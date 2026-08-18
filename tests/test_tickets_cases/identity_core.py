"""Behavioral ticket regression cases."""

from .packet_execution import *  # noqa: F401,F403

def identity_of(run: str = "testrun") -> Path:
    return run_dir_of(run) / "run.json"


def identity_doc(run: str = "testrun") -> dict:
    """The run's identity document, or an assertion that none was written.

    Absence is the wrong *behavior*, not broken plumbing: a can-fail run
    against a revision that stamps no identity must read here as a failure,
    never as a `FileNotFoundError` from the fixture.
    """

    path = identity_of(run)
    if not path.is_file():
        raise AssertionError(f"no run identity was written at {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def identity_bytes(run: str = "testrun") -> bytes:
    identity_doc(run)  # the same assertion, for the same reason
    return identity_of(run).read_bytes()


def workspaces_of(run: str = "testrun") -> list:
    return [entry["path"] for entry in identity_doc(run)["workspaces"]]


def make_clone(root: Path, url=None, *, remote: str = "origin") -> Path:
    """A checkout at ``root`` whose ``.git/config`` names ``url``.

    ``url=None`` leaves it rootless — no remote at all — which is the other
    half of the identity rule and the shape `make_repo` already produces.
    """

    (root / ".git").mkdir(parents=True)
    if url is not None:
        (root / ".git" / "config").write_text(
            GIT_CONFIG.format(remote=remote, url=url), encoding="utf-8"
        )
    return root


class TestRunIdentity(unittest.TestCase):
    """One sink holds every project's runs, so each run says whose it is:
    which project opened it, when, and which workspaces of that project have
    written to it since."""

    def test_a_first_note_stamps_the_identity_document(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            use_sink(tmp)
            repo = make_clone(tmp / "repo", ALPHA)
            payload = run_cmd(repo, "run-state", "testrun", "--note", "one")
            self.assertNotIn("error", payload)
            doc = identity_doc()
            self.assertEqual("testrun", doc["run"])
            self.assertEqual(2, doc["sink_convention"])
            self.assertEqual(
                {"root": str(repo.resolve()), "origin": ALPHA, "name": "repo"},
                doc["project"],
            )
            self.assertRegex(doc["opened_at"], STAMP_RE)
            self.assertEqual([str(repo.resolve())], workspaces_of())
            self.assertEqual(doc["opened_at"], doc["workspaces"][0]["first_seen"])
            self.assertEqual("one\n", notes_of().read_text(encoding="utf-8"))

    def test_receipt_metadata_all_opening_paths_and_legacy_nulls(self):
        commit = "a" * 40
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            sink = use_sink(tmp)
            make_clone(tmp / "repo", ALPHA)
            (sink.parent / "receipt.json").write_text(
                json.dumps({"version": 4, "source_commit": commit}),
                encoding="utf-8",
            )
            run_cmd(tmp / "repo", "run-state", "from-state", "--note", "opened")
            self.assertEqual(
                {"receipt_version": 4, "source_commit": commit},
                identity_doc("from-state")["orchflows"],
            )
            run_cmd(
                tmp / "repo", "new", "from-new", "T1", "--executor", "orch-tdd",
                "--objective", "one", "--criterion",
                "x | oracle: y | oracle_class: deterministic",
            )
            self.assertEqual(
                {"receipt_version": 4, "source_commit": commit},
                identity_doc("from-new")["orchflows"],
            )

        for label, receipt in (
            ("missing", None),
            ("corrupt", "{not json"),
            ("legacy", json.dumps({"scope": "user"})),
        ):
            with self.subTest(label=label), tempfile.TemporaryDirectory() as tmp:
                tmp = Path(tmp)
                sink = use_sink(tmp)
                repo = make_clone(tmp / "repo", ALPHA)
                if receipt is not None:
                    (sink.parent / "receipt.json").write_text(receipt, encoding="utf-8")
                run_cmd(repo, "run-state", label, "--note", "opened")
                self.assertEqual(
                    {"receipt_version": None, "source_commit": None},
                    identity_doc(label)["orchflows"],
                )

    def test_the_timestamp_shape_has_one_owner_in_this_script(self):
        """A second literal is how `claimed_at` and `opened_at` come to
        disagree. The count is what catches one being pasted back in; a
        `UTC_STAMP` that merely exists beside two literals would not."""

        source = TICKETS_PY.read_text(encoding="utf-8")
        # graded before the constant is named, so a revision that has no
        # `UTC_STAMP` reads as the wrong shape rather than a missing attribute
        self.assertEqual(1, source.count('"%Y-%m-%dT%H:%M:%SZ"'), "shape restated")
        # a census of the sites that stamp, not a bound on them: `claim`,
        # `grant`, run opening and terminal transition, each through the one
        # constant
        self.assertEqual(4, source.count("strftime(UTC_STAMP)"), "stamped elsewhere")
        self.assertEqual("%Y-%m-%dT%H:%M:%SZ", tickets_mod.UTC_STAMP)

    def test_an_existing_run_directory_without_an_identity_gains_one(self):
        """The shape this repository's own live run is in: a worklog written
        before `run.json` existed. A missing identity is the ordinary first
        write, never an error, or a run in flight cannot record its own
        progress."""

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            use_sink(tmp)
            repo = make_clone(tmp / "repo", None)
            run_dir_of().mkdir(parents=True)
            notes_of().write_text("a line from before\n", encoding="utf-8")
            self.assertNotIn(
                "error", run_cmd(repo, "run-state", "testrun", "--note", "after")
            )
            self.assertEqual(
                ["a line from before", "after"],
                notes_of().read_text(encoding="utf-8").splitlines(),
            )
            doc = identity_doc()
            self.assertEqual(str(repo.resolve()), doc["project"]["root"])
            self.assertIsNone(doc["project"]["origin"])

    def test_a_second_clone_of_one_origin_appends_and_never_rewrites(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            use_sink(tmp)
            first = make_clone(tmp / "first", ALPHA)
            second = make_clone(tmp / "second", ALPHA)
            run_cmd(first, "run-state", "testrun", "--note", "from the first clone")
            opened = identity_doc()
            payload = run_cmd(second, "run-state", "testrun", "--note", "from the second")
            self.assertNotIn("error", payload)
            doc = identity_doc()
            self.assertEqual(opened["project"], doc["project"])
            self.assertEqual(opened["opened_at"], doc["opened_at"])
            self.assertEqual(
                [str(first.resolve()), str(second.resolve())], workspaces_of()
            )
            self.assertEqual(
                ["from the first clone", "from the second"],
                notes_of().read_text(encoding="utf-8").splitlines(),
            )

    def test_one_url_spelled_two_ways_by_one_transport_is_one_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            use_sink(tmp)
            first = make_clone(tmp / "first", "https://example.invalid/acme/alpha.git")
            second = make_clone(tmp / "second", "https://example.invalid/acme/alpha/")
            run_cmd(first, "run-state", "testrun", "--note", "one")
            self.assertNotIn(
                "error", run_cmd(second, "run-state", "testrun", "--note", "two")
            )
            self.assertEqual(2, len(workspaces_of()))

    def test_a_linked_worktree_appends_as_its_own_workspace(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, worktree, _ = make_worktree(tmp, {"T1": ("claimed", "[]")})
            run_cmd(main, "run-state", "testrun", "--note", "from the main checkout")
            run_cmd(worktree, "run-state", "testrun", "--note", "from the linked tree")
            doc = identity_doc()
            # one project: the pointer file is dereferenced to the main root,
            # while the workspace recorded is the tree the write came from
            self.assertEqual(str(main.resolve()), doc["project"]["root"])
            self.assertEqual(
                [str(main.resolve()), str(worktree.resolve())], workspaces_of()
            )

    def test_a_repeat_write_from_a_recorded_workspace_changes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            use_sink(tmp)
            repo = make_clone(tmp / "repo", ALPHA)
            run_cmd(repo, "run-state", "testrun", "--note", "one")
            opened = identity_bytes()
            for note in ("two", "three"):
                run_cmd(repo, "run-state", "testrun", "--note", note)
            self.assertEqual(1, len(workspaces_of()))
            # not merely deduplicated: no write is owed, so the file is
            # byte-untouched rather than rewritten identically each note
            self.assertEqual(opened, identity_of().read_bytes())
            self.assertEqual(
                ["one", "two", "three"],
                notes_of().read_text(encoding="utf-8").splitlines(),
            )

    def test_the_origin_is_read_from_the_main_checkouts_config(self):
        """The write comes from a linked worktree, whose own `.git` is a
        pointer file with no config in it at all: the pointer is dereferenced
        first and the main checkout's config is what is read."""

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, worktree, _ = make_worktree(tmp, {"T1": ("claimed", "[]")})
            (main / ".git" / "config").write_text(
                GIT_CONFIG.format(remote="origin", url=ALPHA), encoding="utf-8"
            )
            self.assertTrue((worktree / ".git").is_file())
            run_cmd(worktree, "run-state", "testrun", "--note", "from the linked tree")
            doc = identity_doc()
            self.assertEqual(ALPHA, doc["project"]["origin"])
            self.assertEqual(str(main.resolve()), doc["project"]["root"])

    @staticmethod
    def origin_reader():
        """The script's config reader, fetched by name rather than dotted.

        A revision that has none must read here as *cannot read a remote at
        all* — a failure about behavior — rather than as an AttributeError
        raised while collecting the case.
        """

        reader = getattr(tickets_mod, "_origin_url", None)
        if reader is None:
            raise AssertionError("this script cannot read a remote's url at all")
        return reader

    def test_the_config_reader_finds_origin_and_only_origin(self):
        reader = self.origin_reader()
        cases = (
            ("quoted", '[remote "origin"]\n\turl = ' + ALPHA + "\n", ALPHA),
            ("dotted", "[remote.origin]\n\turl = " + ALPHA + "\n", ALPHA),
            ("no-space", '[remote "origin"]\n\turl=' + ALPHA + "\n", ALPHA),
            ("upstream-only", '[remote "upstream"]\n\turl = ' + BETA + "\n", None),
            ("origin-without-url", '[remote "origin"]\n\tfetch = +refs/*\n', None),
            ("commented-out", '#[remote "origin"]\n\turl = ' + ALPHA + "\n", None),
            ("later-section-closes-it",
             '[remote "origin"]\n[user]\n\turl = ' + BETA + "\n", None),
        )
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            for name, text, expected in cases:
                with self.subTest(name):
                    root = tmp / name
                    (root / ".git").mkdir(parents=True)
                    (root / ".git" / "config").write_text(text, encoding="utf-8")
                    self.assertEqual(expected, reader(root))

    def test_a_repository_with_no_config_at_all_has_no_origin(self):
        reader = self.origin_reader()
        with tempfile.TemporaryDirectory() as tmp:
            root = make_clone(Path(tmp) / "bare", None)
            self.assertIsNone(reader(root))

    def test_two_concurrent_openings_leave_one_well_formed_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            use_sink(tmp)
            repo = make_clone(tmp / "repo", ALPHA)
            notes = [f"opener-{i}" for i in range(8)]
            with ThreadPoolExecutor(max_workers=8) as pool:
                payloads = list(
                    pool.map(
                        lambda note: run_cmd(repo, "run-state", "testrun", "--note", note),
                        notes,
                    )
                )
            for payload in payloads:
                self.assertNotIn("error", payload)
            # exactly two files: one identity, one worklog, no `.tmp` left behind
            self.assertEqual(
                ["notes.md", "run.json"],
                sorted(path.name for path in run_dir_of().iterdir()),
            )
            doc = identity_doc()  # parses, so no writer saw a torn file
            self.assertEqual("testrun", doc["run"])
            self.assertEqual([str(repo.resolve())], workspaces_of())
            self.assertEqual(
                sorted(notes),
                sorted(notes_of().read_text(encoding="utf-8").splitlines()),
            )

    def test_a_failed_first_payload_does_not_freeze_an_opening_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            use_sink(tmp)
            repo = make_clone(tmp / "repo", ALPHA)
            with mock.patch.object(
                tickets_mod, "_append_one_line", side_effect=OSError("payload failed")
            ):
                payload = run_cmd(
                    repo, "run-state", "testrun", "--note", "does not land"
                )
            self.assertIn("payload failed", payload["error"])
            self.assertFalse(identity_of().exists())

    def test_adopting_a_legacy_identity_never_invents_opened_at(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            use_sink(tmp)
            repo = make_clone(tmp / "repo", ALPHA)
            identity_of().parent.mkdir(parents=True)
            identity_of().write_text(
                json.dumps({"run": "testrun", "workspaces": []}) + "\n",
                encoding="utf-8",
            )
            self.assertNotIn(
                "error", run_cmd(repo, "run-state", "testrun", "--note", "legacy")
            )
            self.assertNotIn("opened_at", identity_doc())

    def test_the_identity_is_moved_into_place_never_written_over(self):
        """Atomicity is the claim `_write_identity` makes, and a plain write
        would pass the concurrency case above most days it ran. What is
        graded is the mechanism: the target is only ever reached by a move,
        so a reader cannot meet a half-written identity, and the move is the
        one `_replace_atomically` owns."""

        source = inspect.getsource(tickets_mod._write_identity)
        self.assertIn("_replace_atomically(temporary, run_dir / RUN_IDENTITY_NAME)", source)
        self.assertNotIn("write_text", source)
        mover = inspect.getsource(tickets_mod._replace_atomically)
        self.assertIn("temporary.replace(target)", mover)
        self.assertNotIn("write_text", mover)

    @unittest.skipUnless(git_available(), "git is not on PATH")
    def test_a_real_git_worktree_appends_to_the_same_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            main, worktree = make_real_worktree(Path(tmp))
            run_cmd(main, "run-state", "testrun", "--note", "from main")
            run_cmd(worktree, "run-state", "testrun", "--note", "from the worktree")
            doc = identity_doc()
            self.assertEqual(str(main.resolve()), doc["project"]["root"])
            self.assertEqual(
                [str(main.resolve()), str(worktree.resolve())], workspaces_of()
            )


