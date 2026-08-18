"""Row-level validation regression cases."""

from tests import test_validate_measures as common
from tests.test_validate_measures import (
    DECLARED_BOUND,
    FULL_PLAN,
    ONE_PLAN,
    REPO_ROOT,
    Path,
    RecordCase,
    World,
    ast,
    contextlib,
    copy,
    entry_text,
    full,
    hashlib,
    io,
    json,
    make_row,
    mutate,
    record_text,
    rows_for,
    run,
    tempfile,
    unittest,
    vm,
)


def setUpModule():
    common.setUpModule()
    globals()["WORLD"] = common.WORLD


def tearDownModule():
    common.tearDownModule()


# the row schema T01-tracer-cs-cli-fresh froze
# --------------------------------------------------------------------


class TestRowSchema(RecordCase):
    def rows_with(self, case, change):
        return record_text([entry_text(mutate(FULL_PLAN, case, change))])

    def test_ambiguous_status_without_both_readings_is_reported(self):
        """§5: a both-fail row is genuinely hard or broken, and says both."""

        def change(row):
            row["readings"] = []

        self.assertViolation(
            self.rows_with("cs-judged-fresh", change), "admits two readings", count=1
        )

    def test_unambiguous_status_carrying_readings_is_reported(self):
        def change(row):
            row["readings"] = ["one reading too many"]

        self.assertViolation(self.rows_with("cs-cli-fresh", change), "must be empty", count=1)

    def test_discriminating_flag_that_is_not_the_split_flag_is_reported(self):
        def change(row):
            row["discriminating"] = True

        self.assertViolation(
            self.rows_with("cs-cost-fresh", change), "'discriminating' must be true", count=1
        )

    def test_passing_rung_that_lists_a_failed_check_is_reported(self):
        def change(row):
            row["failed_checks"]["strong"] = ["P0.a: something"]

        self.assertViolation(
            self.rows_with("cs-cost-fresh", change), "is PASS but lists failed checks", count=1
        )

    def test_failing_rung_that_names_no_failed_check_is_reported(self):
        def change(row):
            row["failed_checks"]["weak"] = []

        self.assertViolation(
            self.rows_with("cs-judged-fresh", change), "is FAIL but names no failed check", count=1
        )

    def test_failed_checks_missing_a_rung_is_reported(self):
        def change(row):
            del row["failed_checks"]["weak"]

        self.assertViolation(self.rows_with("cs-cli-fresh", change), "'failed_checks' must be")

    def test_trial_count_that_is_not_the_declared_count_is_reported(self):
        def change(row):
            row["rungs"]["weak"]["trial_exit_codes"] = [1, 1]

        self.assertViolation(
            self.rows_with("cs-judged-fresh", change), "against 1 declared trial(s)"
        )

    def test_trials_declared_that_is_not_positive_is_reported(self):
        def change(row):
            row["trials_declared"] = 0

        self.assertViolation(
            self.rows_with("cs-cli-fresh", change), "'trials_declared' must be a positive integer"
        )

    def test_angle_that_contradicts_case_toml_is_reported(self):
        def change(row):
            row["angle"] = "invented-angle"

        self.assertViolation(self.rows_with("cs-cli-fresh", change), "but case.toml declares", count=1)

    def test_size_that_contradicts_case_toml_is_reported(self):
        def change(row):
            row["size"] = "large"

        self.assertViolation(self.rows_with("cs-cli-fresh", change), "'size' is 'large'", count=1)

    def test_canary_outside_its_two_values_is_reported(self):
        def change(row):
            row["rungs"]["strong"]["canary"] = "probably fine"

        self.assertViolation(self.rows_with("cs-cli-fresh", change), "is not 'clean' or 'hit'", count=1)

    def test_artifact_identity_that_is_not_a_sha256_is_reported(self):
        def change(row):
            row["rungs"]["weak"]["artifact_identity"] = "the weak one"

        self.assertViolation(
            self.rows_with("cs-cli-fresh", change), "is not a sha256:<64 hex> identity"
        )

    def test_missing_top_level_key_is_reported(self):
        def change(row):
            del row["observations"]

        self.assertViolation(self.rows_with("cs-cli-fresh", change), "row lacks 'observations'")

    def test_empty_observations_list_is_reported(self):
        def change(row):
            row["observations"] = []

        self.assertViolation(
            self.rows_with("cs-cli-fresh", change), "'observations' must be a non-empty list", count=1
        )

    def test_empty_scope_statement_is_reported(self):
        def change(row):
            row["scope"] = "   "

        self.assertViolation(self.rows_with("cs-cli-fresh", change), "'scope' must be a non-empty", count=1)

    def test_verdict_outside_the_enumeration_is_reported(self):
        def change(row):
            row["rungs"]["strong"]["verdict"] = "GREEN"

        self.assertViolation(self.rows_with("cs-cli-fresh", change), "verdict 'GREEN' is not one of")

    def test_row_key_outside_the_schema_is_tolerated(self):
        """T01 froze the required keys, not a closed set: a lane may add."""
        record = record_text([entry_text(rows_for(ONE_PLAN), incomplete=1)]).replace(
            '"case": "cs-cli-fresh"', '"case": "cs-cli-fresh", "extra": 1', 1
        )
        self.assertClean(record)


# --------------------------------------------------------------------
# the row check's other input: the case's own declaration
# --------------------------------------------------------------------


class TestCaseSchema(RecordCase):
    """One injected lie, every state of `case.toml`.

    A row's angle is checked against what the case declares, so a
    `case.toml` the reader cannot use turns the comparison off rather
    than red — the shape T07 closed in `protected_files`. The same lie
    must be caught whether the declaration is readable or not.
    """

    LIE = "time-semantics"

    @contextlib.contextmanager
    def case_toml(self, text):
        """A second synthetic package whose cs-cli-fresh declaration is ``text``."""
        with tempfile.TemporaryDirectory() as tmp:
            cases = World(Path(tmp).resolve()).cases_dir
            path = cases / "cs-cli-fresh" / "case.toml"
            if text is None:
                path.unlink()
            else:
                path.write_text(text, encoding="utf-8")
            yield cases

    def lying_record(self):
        def change(row):
            row["angle"] = self.LIE

        return record_text([entry_text(mutate(FULL_PLAN, "cs-cli-fresh", change))])

    def assertLieCaught(self, declaration, needle):
        with self.case_toml(declaration) as cases_dir:
            lines = self.assertViolation(self.lying_record(), needle, cases_dir=cases_dir)
            self.assertEqual(
                1, len(lines), "the lie must be caught exactly once:\n" + "\n".join(lines)
            )

    def test_the_lie_is_caught_against_a_readable_declaration(self):
        """The control: the comparison itself works."""
        self.assertViolation(
            self.lying_record(), "but case.toml declares 'angle-1'", count=1
        )

    def test_the_lie_is_caught_when_the_declaration_carries_a_trailing_comment(self):
        """`validate_cases.py` blesses this line; this reader cannot use it."""
        self.assertLieCaught(
            'id = "cs-cli-fresh"\nangle = "angle-1"  # the CLI row\n'
            'size = "small"\nexec_bound = "%s"\n' % DECLARED_BOUND,
            "case-schema",
        )

    def test_the_lie_is_caught_when_the_declaration_uses_a_literal_string(self):
        self.assertLieCaught(
            "id = 'cs-cli-fresh'\nangle = 'angle-1'\n"
            "size = 'small'\nexec_bound = '%s'\n" % DECLARED_BOUND,
            "case-schema",
        )

    def test_the_lie_is_caught_when_the_declaration_is_absent(self):
        with tempfile.TemporaryDirectory() as tmp:
            cases = World(Path(tmp).resolve()).cases_dir
            (cases / "cs-cli-fresh" / "case.toml").unlink()
            lines = self.assertViolation(
                self.lying_record(), "case-schema: cannot read", cases_dir=cases
            )
            self.assertEqual(1, len(lines), "\n".join(lines))

    def test_a_declaration_outside_the_subset_is_refused_with_no_lie_present(self):
        """The refusal is the missing reading, not the contradiction."""
        with self.case_toml(
            'id = "cs-cli-fresh"\nangle = "angle-1"\nsize = "small"\n'
        ) as cases_dir:
            self.assertViolation(
                full(), "states no 'exec_bound'", count=1, cases_dir=cases_dir
            )

    def test_case_keys_reads_every_live_case(self):
        """The narrow subset is a claim about the frozen set; here it is checked."""
        live = REPO_ROOT / "benchmarks" / "benchmaker" / "cases"
        for case in sorted(entry.name for entry in live.iterdir() if entry.is_dir()):
            self.assertEqual(set(vm.CASE_KEYS), set(vm.case_keys(live, case)), case)


# --------------------------------------------------------------------
# C11 (A13) — the checker's own shape
# --------------------------------------------------------------------


STDLIB = frozenset(
    """__future__ argparse ast collections contextlib copy hashlib io json os pathlib
    re shlex subprocess sys tempfile unittest""".split()
)


class TestCheckerShape(unittest.TestCase):
    def test_checker_imports_only_the_standard_library(self):
        tree = ast.parse((REPO_ROOT / "tools" / "validate_measures.py").read_text(encoding="utf-8"))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                imported.add(node.module.split(".")[0])
        self.assertEqual(imported - STDLIB, set())

    def test_clean_record_prints_nothing_at_all(self):
        path = WORLD.write_record(full())
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            code = vm.main(["--record", str(path), "--cases-dir", str(WORLD.cases_dir)])
        self.assertEqual((code, stream.getvalue()), (0, ""))

    def test_every_violation_line_carries_one_scope_and_one_message(self):
        rows = rows_for(FULL_PLAN)
        rows[1]["status"] = "both-pass"
        del rows[3]["rungs"]["weak"]["cost_actual"]
        rows[5]["rungs"]["strong"]["canary"] = "hit"
        code, lines = run(record_text([entry_text(rows)]))
        self.assertEqual(code, 1)
        self.assertTrue(lines)
        for line in lines:
            scope, separator, message = line.partition(": ")
            self.assertTrue(scope.startswith("ERROR "), line)
            self.assertEqual(separator, ": ", line)
            self.assertTrue(message.strip(), line)

    def test_no_violation_is_reported_twice(self):
        rows = rows_for(FULL_PLAN)
        rows[1]["rungs"]["strong"]["canary"] = "hit"
        _, lines = run(record_text([entry_text(rows)]))
        self.assertEqual(len(set(lines)), len(lines), "\n".join(lines))


# --------------------------------------------------------------------
# --row: the single-row convenience the case lanes use
# --------------------------------------------------------------------


class TestRowMode(unittest.TestCase):
    def row_file(self, text):
        """One file per distinct row text, named for the text.

        Every test in this class wrote the same ``row.md``, so each one
        depended on the previous one's content being overwritten before it
        read: a test that failed after writing left the next one a file it
        did not author. Named for the text, no two tests share a path.
        """

        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
        path = WORLD.root / ("row-%s.md" % digest)
        path.write_text(text, encoding="utf-8")
        return path

    def run_row(self, path):
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            code = vm.main(["--row", str(path), "--cases-dir", str(WORLD.cases_dir)])
        return code, [line for line in stream.getvalue().splitlines() if line]

    def block(self, row):
        return "# Row\n\n```json\n%s\n```\n" % json.dumps(row, indent=2, ensure_ascii=False)

    def test_valid_row_file_is_clean(self):
        path = self.row_file(self.block(make_row("cs-cli-fresh", "split")))
        self.assertEqual(self.run_row(path), (0, []))

    def test_row_file_violation_is_reported(self):
        row = copy.deepcopy(make_row("cs-cli-fresh", "split"))
        row["status"] = "both-pass"
        path = self.row_file(self.block(row))
        code, lines = self.run_row(path)
        self.assertEqual(code, 1)
        self.assertTrue(any("derives 'split'" in line for line in lines))

    def test_row_file_with_two_blocks_is_reported(self):
        row = make_row("cs-cli-fresh", "split")
        path = self.row_file(self.block(row) + self.block(row))
        code, lines = self.run_row(path)
        self.assertEqual(code, 1)
        self.assertTrue(any("expected exactly 1" in line for line in lines))

    def test_absent_row_file_is_reported(self):
        code, lines = self.run_row(WORLD.root / "no-such-row.md")
        self.assertEqual(code, 1)
        self.assertTrue(any("no such file" in line for line in lines))
