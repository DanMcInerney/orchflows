"""Installer regression cases grouped by behavioral seam."""

from __future__ import annotations

from ..support import *  # noqa: F403


class TestDayZeroBootstrap(unittest.TestCase):
    """``--project`` also bootstraps the day-zero documents
    ``docs/documentation.md`` §6 names -- an empty vocabulary and an
    ownership map -- each carrying the factory that produced it. Day zero
    happens once: a document the project already holds is left alone, so
    the second install is never it.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name) / "home"
        self.project = Path(self.tmp.name) / "project"
        self.project.mkdir(parents=True)
        # Unresolved, for the reason test_project_plan_writes_only_...
        # states: the rendered text carries this spelling, and resolving
        # it here disagrees on any host whose temp dir holds a symlink.
        self.user_docs = str(self.home / ".orchflows" / "lib" / "docs")

    def project_plan(self):
        with patch.object(install.Path, "home", return_value=self.home):
            return install.build_plan("project", self.project)

    def documents(self, plan) -> dict:
        return {doc.dest: doc for doc in plan.day_zero}

    def test_a_project_bootstrap_plans_both_day_zero_documents(self):
        plan = self.project_plan()

        self.assertEqual(
            {self.project / "docs" / "vocabulary.md", self.project / "ARCHITECTURE.md"},
            set(self.documents(plan)),
        )

    def test_each_bootstrapped_document_carries_its_factory(self):
        documents = self.documents(self.project_plan())
        vocabulary = documents[self.project / "docs" / "vocabulary.md"].content
        ownership_map = documents[self.project / "ARCHITECTURE.md"].content

        # One native path per factory, not a directory plus a separator
        # the host may not use: this is what the reader opens.
        self.assertIn(str(Path(self.user_docs) / "vocabulary-authoring.md"), vocabulary)
        self.assertIn(str(Path(self.user_docs) / "documentation.md"), ownership_map)
        for content in (vocabulary, ownership_map):
            # Rendered against the user library, like the host block: a
            # project install carries no library of its own to point at.
            self.assertNotIn(str(self.project), content)

    def test_the_bootstrapped_vocabulary_is_the_preamble_and_empty_sections(self):
        vocabulary = self.documents(self.project_plan())[
            self.project / "docs" / "vocabulary.md"
        ].content
        lines = vocabulary.splitlines()

        self.assertEqual("# Vocabulary", lines[0])
        sections = [line for line in lines if line.startswith("## ")]
        self.assertEqual(["## Structure", "## Work", "## Verification"], sections)
        # Empty means empty: an entry is a bullet, and a skeleton has none.
        self.assertEqual([], [line for line in lines if line.startswith("- ")])

    def test_the_bootstrapped_ownership_map_is_a_one_row_tiers_table(self):
        ownership_map = self.documents(self.project_plan())[
            self.project / "ARCHITECTURE.md"
        ].content
        rows = [line for line in ownership_map.splitlines() if line.startswith("|")]

        self.assertEqual(3, len(rows), rows)  # header, separator, one row
        self.assertIn("tier", rows[0])
        self.assertIn("owner", rows[0])

    def test_a_project_bootstrap_counts_and_prints_its_two_documents(self):
        plan = self.project_plan()
        printed = io.StringIO()
        with redirect_stdout(printed):
            install.print_plan(plan)
        output = printed.getvalue()

        self.assertEqual(len(plan.blocks) + 2, install.plan_entry_count(plan))
        self.assertIn("day-zero documents (2):", output)
        for dest in self.documents(plan):
            self.assertIn(str(dest), output)

    def bootstrap(self) -> dict:
        with patch.object(install.Path, "home", return_value=self.home):
            return install.apply_plan(install.build_plan("project", self.project))

    def recorded(self, receipt) -> dict:
        return {
            entry["path"]: entry
            for entry in receipt["files"]
            if entry.get("kind") == "day-zero"
        }

    def test_a_bootstrap_run_writes_both_documents_and_records_them(self):
        entries = self.recorded(self.bootstrap())

        self.assertEqual(
            {
                str(self.project / "docs" / "vocabulary.md"),
                str(self.project / "ARCHITECTURE.md"),
            },
            set(entries),
        )
        for path, entry in entries.items():
            self.assertTrue(Path(path).is_file(), path)
            self.assertEqual("created", entry["install_action"])
            self.assertEqual(digest(Path(path)), entry["sha256"])

    def test_a_bootstrap_leaves_a_document_the_project_already_holds_byte_identical(self):
        ours = self.project / "ARCHITECTURE.md"
        ours.write_bytes(b"# Ours\r\n\r\nnot the skeleton\n")
        before = ours.read_bytes()

        entry = self.recorded(self.bootstrap())[str(ours)]

        self.assertEqual(before, ours.read_bytes())
        self.assertEqual("kept", entry["install_action"])
        self.assertEqual(digest(ours), entry["sha256"])
        # Can-fail: the absent document beside it was written on the same
        # run, so the equality above is a refusal, not an installer that
        # wrote nothing at all.
        self.assertTrue((self.project / "docs" / "vocabulary.md").is_file())

    def test_a_second_bootstrap_never_reverts_what_day_one_wrote(self):
        self.bootstrap()
        vocabulary = self.project / "docs" / "vocabulary.md"
        grown = "# Vocabulary\n\n## Structure\n\n- **widget** — ours.\n"
        vocabulary.write_text(grown, encoding="utf-8")

        entry = self.recorded(self.bootstrap())[str(vocabulary)]

        self.assertEqual(grown, vocabulary.read_text(encoding="utf-8"))
        # Still "created": the installer wrote this one on day one, and a
        # receipt that forgot that would tell uninstall the wrong story.
        self.assertEqual("created", entry["install_action"])
        self.assertEqual(digest(vocabulary), entry["sha256"])

    def test_a_bootstrap_that_rewrites_a_document_the_project_removed_records_created(self):
        ours = self.project / "ARCHITECTURE.md"
        ours.write_text("# Ours\n", encoding="utf-8")
        self.assertEqual("kept", self.recorded(self.bootstrap())[str(ours)]["install_action"])
        ours.unlink()

        entry = self.recorded(self.bootstrap())[str(ours)]

        # The installer wrote it this run, whatever day one recorded: a
        # receipt still saying "kept" would tell uninstall to leave alone a
        # file the installer wrote.
        self.assertTrue(ours.is_file())
        self.assertEqual("created", entry["install_action"])
        self.assertEqual(digest(ours), entry["sha256"])

    def test_a_bootstrap_uninstall_removes_no_day_zero_document_and_says_which_it_wrote(self):
        ours = self.project / "ARCHITECTURE.md"
        ours.write_text("# Ours\n", encoding="utf-8")
        self.bootstrap()

        with patch.object(install.Path, "home", return_value=self.home):
            report = install.run_uninstall("project", self.project, dry_run=True)

        actions = {entry["path"]: entry["action"] for entry in report["manual_actions"]}
        self.assertIn("delete", actions[str(self.project / "docs" / "vocabulary.md")])
        self.assertIn("never wrote it", actions[str(ours)])
        self.assertEqual(
            [], [entry for entry in report["skill_actions"] if "ARCHITECTURE" in entry["path"]]
        )

    def test_the_bootstrap_is_named_where_its_reader_meets_it(self):
        """One fact, one owner, twice over: the installer's docstring owns
        what project scope writes, and ``docs/documentation.md`` §6 owns
        what day zero creates. Neither reader reaches the other's file."""

        collapsed = " ".join((install.__doc__ or "").split())
        self.assertIn("day-zero documents", collapsed)

        documentation = (
            Path(install.__file__).resolve().parent / "docs" / "documentation.md"
        ).read_text(encoding="utf-8")
        section = documentation.split("## 6. Bootstrap", 1)[1].split("\n## ", 1)[0]
        self.assertIn("install.py --project", section)
        self.assertIn("never overwriting", section)

    def test_a_user_install_bootstraps_no_day_zero_document(self):
        """The library is not a project day zero: a user install writes
        neither document, and its planned-entry count does not move."""

        (self.home / ".claude").mkdir(parents=True)
        with patch.object(install.Path, "home", return_value=self.home), mock_host_clis(
            "claude", "codex"
        ):
            user_plan = install.build_plan("user", None)

        self.assertEqual([], list(user_plan.day_zero))


if __name__ == "__main__":
    unittest.main()
