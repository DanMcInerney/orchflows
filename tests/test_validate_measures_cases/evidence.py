"""Evidence-level validation regression cases."""

from tests import test_validate_measures as common
from tests.test_validate_measures import (
    DECLARED_BOUND,
    FULL_PLAN,
    PROTECTED,
    REPO_ROOT,
    Path,
    RecordCase,
    World,
    contextlib,
    entry_text,
    full,
    mutate,
    record_text,
    tempfile,
    vm,
)


def setUpModule():
    common.setUpModule()
    globals()["WORLD"] = common.WORLD


def tearDownModule():
    common.tearDownModule()


# --------------------------------------------------------------------
# C5 (A8) — every verdict traces to an artifact and an exit code
# --------------------------------------------------------------------


class TestTraceability(RecordCase):
    def test_missing_artifact_identity_is_reported(self):
        def change(row):
            del row["rungs"]["strong"]["artifact_identity"]

        rows = mutate(FULL_PLAN, "cs-cli-fresh", change)
        self.assertViolation(record_text([entry_text(rows)]), "lacks 'artifact_identity'", count=1)

    def test_missing_probe_exit_code_is_reported(self):
        def change(row):
            del row["rungs"]["weak"]["probe_exit_code"]

        rows = mutate(FULL_PLAN, "cs-cli-fresh", change)
        lines = self.assertViolation(record_text([entry_text(rows)]), "lacks 'probe_exit_code'")
        self.assertTrue(any("does not govern its trials" in line for line in lines))

    def test_artifact_identity_that_does_not_recompute_is_reported(self):
        def change(row):
            row["rungs"]["strong"]["artifact_identity"] = "sha256:" + "c" * 64

        rows = mutate(FULL_PLAN, "cs-cli-fresh", change)
        self.assertViolation(record_text([entry_text(rows)]), "does not recompute over", count=1)

    def test_artifact_path_that_does_not_resolve_is_reported(self):
        def change(row):
            row["rungs"]["weak"]["artifact_path"] = str(WORLD.root / "no-such-artifact")

        rows = mutate(FULL_PLAN, "cs-cli-fresh", change)
        self.assertViolation(record_text([entry_text(rows)]), "does not resolve to a directory", count=1)

    def test_artifact_file_count_that_disagrees_is_reported(self):
        def change(row):
            row["rungs"]["strong"]["artifact_files"] = 99

        rows = mutate(FULL_PLAN, "cs-cli-fresh", change)
        self.assertViolation(record_text([entry_text(rows)]), "artifact_files 99 but", count=1)

    def test_probe_exit_code_that_does_not_govern_its_trials_is_reported(self):
        def change(row):
            row["rungs"]["weak"]["probe_exit_code"] = 0

        rows = mutate(FULL_PLAN, "cs-cli-fresh", change)
        self.assertViolation(record_text([entry_text(rows)]), "does not govern its trials", count=1)


# --------------------------------------------------------------------
# C6 (A9) — candidate identity per rung, and the incomparability statement
# --------------------------------------------------------------------


class TestRungIdentity(RecordCase):
    def test_rung_row_without_an_effort_cell_is_reported(self):
        table = (
            "| rung | model id | effort | host binding | scaffold |\n"
            "| --- | --- | --- | --- | --- |\n"
            "| strong | `claude-opus-5` |  | Claude Code, this worktree | `benchmaker` |\n"
            "| weak | `claude-sonnet-5` | `high` | same | same |"
        )
        self.assertViolation(full(rung_table=table), "must name model id, effort", count=1)

    def test_absent_rung_row_is_reported(self):
        table = (
            "| rung | model id | effort | host binding | scaffold |\n"
            "| --- | --- | --- | --- | --- |\n"
            "| strong | `claude-opus-5` | `xhigh` | Claude Code | `benchmaker` |"
        )
        self.assertViolation(full(rung_table=table), "has no 'weak' row", count=1)

    def test_row_model_that_contradicts_the_rungs_table_is_reported(self):
        def change(row):
            row["rungs"]["strong"]["model"] = "claude-haiku-5"

        rows = mutate(FULL_PLAN, "cs-cli-fresh", change)
        self.assertViolation(
            record_text([entry_text(rows)]), "but the Rungs table declares", count=1
        )

    def test_row_effort_that_contradicts_the_rungs_table_is_reported(self):
        def change(row):
            row["rungs"]["weak"]["effort_requested"] = "xhigh"

        rows = mutate(FULL_PLAN, "cs-cli-fresh", change)
        self.assertViolation(record_text([entry_text(rows)]), "effort_requested", count=1)

    def test_absent_incomparability_section_is_reported(self):
        record = full(sections=("case set", "rungs", "scope", "figures"))
        self.assertViolation(record, "has no '### Incomparability' section", count=1)

    def test_empty_incomparability_statement_is_reported(self):
        self.assertViolation(full(incomparability="See above."), "states no incomparability", count=1)


# --------------------------------------------------------------------
# C7 (A10) — measured scope
# --------------------------------------------------------------------


class TestScope(RecordCase):
    def test_absent_scope_section_is_reported(self):
        record = full(sections=("case set", "rungs", "incomparability", "figures"))
        self.assertViolation(record, "has no '### Measured scope' section", count=1)

    def test_scope_that_omits_the_protected_workload_is_reported(self):
        scope = (
            "Public subset. Unavailable: `cs-nondet-fresh/streams.json`, `stream-held-1.json`, "
            "`stream-held-2.json`, `stream-held-3.json`. Withheld from candidates: "
            "`expected.md`, `seeds/`, `probe/`."
        )
        self.assertViolation(
            full(scope=scope), "does not name cs-antigoodhart-2/workload.json", count=1
        )

    def test_scope_that_omits_a_withheld_input_is_reported(self):
        scope = (
            "Public subset. Unavailable: " + ", ".join("`%s`" % p for p in PROTECTED)
            + ". Withheld from candidates: `expected.md`, `probe/`."
        )
        self.assertViolation(full(scope=scope), "does not name seeds/ as withheld", count=1)


class TestProtectedEvidence(RecordCase):
    """The scope check's own input: the covered manifest.

    The one live file this suite reads. A shape change to it must fail
    here, because the alternative is what happened on 2026-08-09 — the
    reader answered "no protected files", the scope check required
    nothing, and the run stayed green.
    """

    @contextlib.contextmanager
    def package(self, manifest):
        """A second synthetic package carrying ``manifest``, or none."""
        with tempfile.TemporaryDirectory() as tmp:
            path = World(Path(tmp).resolve()).root / "manifest.json"
            if manifest is None:
                path.unlink()
            else:
                path.write_text(manifest, encoding="utf-8")
            yield path.parent / "cases"

    def test_the_live_manifest_yields_its_five_protected_paths(self):
        live = REPO_ROOT / "benchmarks" / "benchmaker" / "cases"
        self.assertEqual(vm.protected_files(live), PROTECTED)

    def test_scope_that_omits_a_path_only_the_manifest_names_is_reported(self):
        """`stream-held-3.json` is in no module constant: only the
        manifest requires it, so this fails if the manifest goes unread."""
        scope = (
            "Public subset. Unavailable: " + ", ".join("`%s`" % p for p in PROTECTED[:-1])
            + ". Withheld from candidates: `expected.md`, `seeds/`, `probe/`."
        )
        self.assertViolation(full(scope=scope), "does not name stream-held-3.json", count=1)

    def test_a_manifest_that_names_no_protected_files_is_refused(self):
        with self.package('{"anchors": {}}') as cases_dir:
            self.assertViolation(
                full(), "protected-evidence: ", count=1, cases_dir=cases_dir
            )

    def test_a_manifest_whose_protected_files_is_not_a_list_is_refused(self):
        """The 2026-08-09 shape change, inverted: the old map form."""
        with self.package('{"protected_evidence": {"files": {"a.json": "sha256:0"}}}') as cases_dir:
            self.assertViolation(
                full(), "states no 'protected_evidence.files' list", count=1, cases_dir=cases_dir
            )

    def test_an_absent_manifest_is_refused(self):
        with self.package(None) as cases_dir:
            self.assertViolation(
                full(), "protected-evidence: cannot read", count=1, cases_dir=cases_dir
            )

    def test_a_manifest_that_does_not_parse_is_refused(self):
        with self.package("{not json") as cases_dir:
            self.assertViolation(
                full(), "protected-evidence: cannot read", count=1, cases_dir=cases_dir
            )


# --------------------------------------------------------------------
# C8 (A11) — the §5 figures, recomputed from the rows
# --------------------------------------------------------------------


# --------------------------------------------------------------------
# C9 (A12) — measured cost per case per rung, against the declared bound
# --------------------------------------------------------------------


class TestCost(RecordCase):
    def test_weak_rung_without_a_cost_block_is_reported(self):
        def change(row):
            del row["rungs"]["weak"]["cost_actual"]

        rows = mutate(FULL_PLAN, "cs-cli-fresh", change)
        lines = self.assertViolation(record_text([entry_text(rows)]), "lacks 'cost_actual'")
        self.assertTrue(any("'cost_actual' is not an object" in line for line in lines))

    def test_cost_field_that_is_not_a_number_is_reported(self):
        def change(row):
            row["rungs"]["strong"]["cost_actual"]["subagent_tokens"] = "lots"

        rows = mutate(FULL_PLAN, "cs-cli-fresh", change)
        self.assertViolation(
            record_text([entry_text(rows)]), "cost_actual 'subagent_tokens' must be", count=1
        )

    def test_missing_cost_key_is_reported(self):
        def change(row):
            del row["rungs"]["weak"]["cost_actual"]["wall_ms"]

        rows = mutate(FULL_PLAN, "cs-cli-fresh", change)
        self.assertViolation(record_text([entry_text(rows)]), "cost_actual lacks 'wall_ms'", count=1)

    def test_bound_that_is_not_the_case_declared_bound_is_reported(self):
        def change(row):
            row["rungs"]["strong"]["bound"]["declared"] = "two BC1 shares"

        rows = mutate(FULL_PLAN, "cs-cli-fresh", change)
        self.assertViolation(
            record_text([entry_text(rows)]),
            "does not match the case's declared execution bound",
            count=1,
        )

    def test_predecessor_format_bound_still_matches(self):
        # A row recorded before `bound` became `exec_bound` quotes the
        # conflated string. The record is a fact and is not rewritten;
        # the checker strips the construction clause before comparing.
        def change(row):
            row["rungs"]["strong"]["bound"]["declared"] = (
                "one BC1 share; " + DECLARED_BOUND
            )

        rows = mutate(FULL_PLAN, "cs-cli-fresh", change)
        self.assertClean(record_text([entry_text(rows)]))

    def test_predecessor_format_with_the_wrong_tier_still_fails(self):
        # The normalization drops the construction clause, not the check.
        def change(row):
            row["rungs"]["strong"]["bound"]["declared"] = (
                "one BC1 share; probe within large tier"
            )

        rows = mutate(FULL_PLAN, "cs-cli-fresh", change)
        self.assertViolation(
            record_text([entry_text(rows)]),
            "does not match the case's declared execution bound",
            count=1,
        )

