"""Runs tools/validate.py as a subprocess against the live repo, and
exercises the --pin flag against an isolated copy of contracts/."""
import contextlib
import io
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import tools.validate as validate  # noqa: E402

VALIDATE = ROOT / "tools" / "validate.py"
CONTRACTS = ROOT / "contracts"
PINS = ROOT / "tests" / "pins.json"

# Compiled once: the isolated-tree tests execute this body per run, in a
# namespace whose __file__ points at their own copy.
_VALIDATE_CODE = compile(VALIDATE.read_text(encoding="utf-8"), str(VALIDATE), "exec")


def loop_lint_warnings(stdout):
    """Every WARN validate_loop_lint emitted, by its own words.

    The loop-lint cases below are about one check, and a report carries
    findings from every check that ran -- an isolated tree still holds the
    real contracts/, so the duplication checks read it too. Asserting over
    the whole stream made those cases fail on a finding they are not about,
    and pass on the day the loop lint stops running (tests/test_cell_linter.py
    holds the same line for its ratchets)."""
    return [
        line for line in stdout.splitlines()
        if line.startswith("WARN") and "iteration/loop" in line
    ]


class _Result:
    """The three fields of a CompletedProcess the isolated tests read."""

    def __init__(self, returncode, stdout, stderr):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class _IsolatedTree(unittest.TestCase):
    """A synthetic repo tree -- contracts/, tools/validate.py, the
    committed pins, plus whatever the test writes -- with validate.py run
    against it.

    Two spawns per test bought nothing. The pin spawn is gone because the
    contract bytes here are copied verbatim from the tree pins.json is
    pinned to (TestPinFlagRoundTrip.test_pin_matches_committed_pins_json
    is the proof), so copying the file is the same fixture. The run itself
    is in process because validate.py derives ROOT from its own __file__,
    so executing its body in a namespace rooted at the copy is the run the
    subprocess made. The CLI boundary -- argv, exit status, a real
    interpreter -- stays covered by TestValidatorAgainstRepo and
    TestPinFlagRoundTrip, which still spawn.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.tmp_path = Path(self.tmp.name)
        shutil.copytree(CONTRACTS, self.tmp_path / "contracts")
        (self.tmp_path / "tools").mkdir()
        shutil.copy(VALIDATE, self.tmp_path / "tools" / "validate.py")
        (self.tmp_path / "tests").mkdir()
        shutil.copy(PINS, self.tmp_path / "tests" / "pins.json")

    def _run(self, *args):
        namespace = {
            "__name__": "validate_under_test",
            "__file__": str(self.tmp_path / "tools" / "validate.py"),
        }
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            exec(_VALIDATE_CODE, namespace)  # noqa: S102 -- the file under test
            code = namespace["main"](list(args))
        return _Result(code, out.getvalue(), err.getvalue())


class TestValidatorAgainstRepo(unittest.TestCase):
    def test_repo_passes_clean(self):
        result = subprocess.run(
            [sys.executable, str(VALIDATE)],
            capture_output=True,
            text=True,
        )
        self.assertEqual(
            0,
            result.returncode,
            f"validate.py exited {result.returncode}\n"
            f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}",
        )


class TestPinFlagRoundTrip(unittest.TestCase):
    """--pin runs against an isolated temp copy so it never mutates the
    real tests/pins.json while the suite runs."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmp.name)
        shutil.copytree(CONTRACTS, self.tmp_path / "contracts")
        (self.tmp_path / "tools").mkdir()
        shutil.copy(VALIDATE, self.tmp_path / "tools" / "validate.py")

    def tearDown(self):
        self.tmp.cleanup()

    def _run(self, *args):
        return subprocess.run(
            [sys.executable, str(self.tmp_path / "tools" / "validate.py"), *args],
            capture_output=True,
            text=True,
        )

    def test_pin_creates_pins_matching_contracts(self):
        result = self._run("--pin")
        self.assertEqual(0, result.returncode, result.stderr)

        pins_path = self.tmp_path / "tests" / "pins.json"
        self.assertTrue(pins_path.is_file())
        pins = json.loads(pins_path.read_text(encoding="utf-8"))

        expected_names = {f.name for f in CONTRACTS.glob("*.md")}
        self.assertEqual(expected_names, set(pins))
        for name in expected_names:
            self.assertRegex(pins[name], r"^[0-9a-f]{64}$")

    def test_pin_is_idempotent(self):
        first = self._run("--pin")
        before = (self.tmp_path / "tests" / "pins.json").read_text(encoding="utf-8")
        second = self._run("--pin")
        after = (self.tmp_path / "tests" / "pins.json").read_text(encoding="utf-8")
        self.assertEqual(0, first.returncode)
        self.assertEqual(0, second.returncode)
        self.assertEqual(before, after)

    def test_pin_matches_committed_pins_json(self):
        self._run("--pin")
        generated = json.loads((self.tmp_path / "tests" / "pins.json").read_text(encoding="utf-8"))
        committed = json.loads(PINS.read_text(encoding="utf-8"))
        self.assertEqual(committed, generated)

    def test_missing_or_stale_pin_fails_validation(self):
        (self.tmp_path / "tests").mkdir()
        (self.tmp_path / "tests" / "pins.json").write_text(
            json.dumps({"verdict.md": "0" * 64}), encoding="utf-8"
        )
        result = self._run()
        self.assertEqual(1, result.returncode)
        self.assertIn("T0 contract changed", result.stdout)


class TestFrontmatterBoundaryInputs(unittest.TestCase):
    """parse_frontmatter is the seam every discovered package's SKILL.md
    passes through; these exercise it directly at boundary inputs without
    needing a full synthetic repo tree."""

    def test_empty_file_produces_error_not_traceback(self):
        diag = validate.Diagnostics()
        fm, body = validate.parse_frontmatter("", "empty.md", diag)
        self.assertIsNone(fm)
        self.assertIsNone(body)
        self.assertTrue(diag.has_errors)
        self.assertIn("missing opening frontmatter fence", diag.lines()[0])

    def test_missing_closing_fence_produces_error_not_traceback(self):
        diag = validate.Diagnostics()
        fm, body = validate.parse_frontmatter(
            "---\nname: foo\ndescription: bar\n", "noclose.md", diag
        )
        self.assertIsNone(fm)
        self.assertIsNone(body)
        self.assertTrue(diag.has_errors)
        self.assertIn("missing closing frontmatter fence", diag.lines()[0])

    def test_malformed_line_without_colon_is_an_error_and_parsing_continues(self):
        diag = validate.Diagnostics()
        fm, body = validate.parse_frontmatter(
            "---\nname: foo\nnot-a-kv-line\ndescription: bar\n---\nbody\n",
            "malformed.md", diag,
        )
        self.assertEqual({"name": "foo", "description": "bar"}, fm)
        self.assertEqual("body\n", body)
        self.assertTrue(diag.has_errors)
        self.assertIn("malformed frontmatter line", diag.lines()[0])

    def test_oversized_single_line_body_does_not_crash(self):
        huge_line = "x" * (2 * 1024 * 1024)
        text = f"---\nname: foo\ndescription: bar\n---\n{huge_line}\n"
        diag = validate.Diagnostics()
        fm, body = validate.parse_frontmatter(text, "huge.md", diag)
        self.assertEqual({"name": "foo", "description": "bar"}, fm)
        self.assertEqual(huge_line, body.strip())
        self.assertFalse(diag.has_errors)


class TestASkippedCheckSaysSo(_IsolatedTree):
    """A check that finds nothing to check has not passed.

    The isolated tree is contracts/, tools/ and tests/ -- so the checks
    keyed to skills/, packs/, compositions/, docs/, templates/ and
    scripts/ find no owner and return. Returning is right: a fixture tree
    is not the library. Returning *silently* is the fallback -- the report
    then reads exactly like a run that graded all of it, and the one
    reader of that report is a run deciding whether the tree is admissible.
    """

    SKIP_NOTE = "absent; check skipped"

    def _skipped(self, stdout):
        return [line for line in stdout.splitlines() if self.SKIP_NOTE in line]

    def test_each_absent_owner_is_named_rather_than_passed_over(self):
        result = self._run()
        named = " ".join(self._skipped(result.stdout))

        for owner in (
            "scripts/state_root.py",      # the friction-location copies
            "AGENTS.md",                  # a surface budget
            "templates/host-block.md",    # the other surface budget
            "compositions",               # the template contract
            "ARCHITECTURE.md",            # the backticked-name check
        ):
            with self.subTest(owner=owner):
                self.assertIn(owner, named)

    def test_a_check_that_starts_and_finds_half_its_tree_says_that_too(self):
        # With the friction owner present the check runs and then finds no
        # term owner to compare against -- the half that was silent.
        (self.tmp_path / "scripts").mkdir()
        shutil.copy(
            ROOT / "scripts" / "state_root.py", self.tmp_path / "scripts" / "state_root.py"
        )

        result = self._run()

        self.assertIn("docs/vocabulary.md", " ".join(self._skipped(result.stdout)))

    def test_a_skipped_check_is_a_warning_and_not_an_error(self):
        # Fixture trees are graded by these tests all day; the note may not
        # turn them red, and `has_errors` is what the exit code reads.
        result = self._run()

        self.assertTrue(self._skipped(result.stdout))
        for line in self._skipped(result.stdout):
            self.assertTrue(line.startswith("WARN "), line)
        self.assertEqual(0, result.returncode, result.stdout)

    def test_the_library_itself_skips_nothing(self):
        # The same note over the real tree would mean a check silently
        # stopped running here, which is the finding this closes.
        result = subprocess.run(
            [sys.executable, str(VALIDATE)], capture_output=True, text=True
        )

        self.assertEqual([], self._skipped(result.stdout))


class TestSyntheticPackageBoundaryInputs(_IsolatedTree):
    """Full runs against a synthetic skills/ tree, so the ERROR/exit-code
    contract is checked at the actual ROOT-relative seam, not just
    parse_frontmatter."""

    def _write_skill(self, name: str, content: bytes, tier: str = "instances"):
        skill_dir = self.tmp_path / "skills" / tier / name
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_bytes(content)

    def _write_pack(self, name: str, content: bytes):
        pack_dir = self.tmp_path / "packs" / name
        pack_dir.mkdir(parents=True)
        (pack_dir / "SKILL.md").write_bytes(content)

    def test_a_references_only_directory_is_no_package_and_no_finding(self):
        """A tier directory holding only `references/` is read as no package
        at all -- not as a package missing its SKILL.md, which would take the
        tree red on a directory the library merely has not finished emptying.
        (Such a home is still no place for a public reference: visibility §4
        wants an owning body naming the path, which is why `profiles.md` now
        sits under `skills/engines/orch-frontier/`.)"""
        refs = self.tmp_path / "skills" / "kernel" / "orch-refsonly" / "references"
        refs.mkdir(parents=True)
        (refs / "profiles.md").write_text("A reference with no skill.\n", encoding="utf-8")
        result = self._run()
        self.assertEqual(0, result.returncode, result.stdout)
        self.assertNotIn("orch-refsonly", result.stdout)
        self.assertEqual("", result.stderr.strip())

    def test_missing_closing_fence_is_error_line_and_exit_1_no_traceback(self):
        self._write_skill(
            "badpkg",
            b"---\nname: badpkg\ndescription: missing closing fence\n"
            b"Require: x.\nNever: y.\nReturn: z.\n",
        )
        result = self._run()
        self.assertEqual(1, result.returncode)
        self.assertIn("missing closing frontmatter fence", result.stdout)
        self.assertEqual("", result.stderr.strip())

    def test_bom_prefixed_valid_skill_md_is_not_falsely_flagged(self):
        body = (
            "---\nname: bompkg\ndescription: a bom-prefixed valid skill\nrole: worker\n---\n"
            "Require: one thing.\nNever: another thing.\nReturn: a result.\n"
        )
        self._write_skill("bompkg", b"\xef\xbb\xbf" + body.encode("utf-8"))
        result = self._run()
        self.assertEqual(0, result.returncode, result.stdout)
        self.assertNotIn("missing opening frontmatter fence", result.stdout)

    def test_empty_skill_md_is_error_line_and_exit_1_no_traceback(self):
        self._write_skill("emptypkg", b"")
        result = self._run()
        self.assertEqual(1, result.returncode)
        self.assertIn("missing opening frontmatter fence", result.stdout)
        self.assertEqual("", result.stderr.strip())

    def test_skill_missing_role_is_error(self):
        self._write_skill(
            "norolepkg",
            b"---\nname: norolepkg\ndescription: a skill without a role\n---\n"
            b"Require: x.\nNever: y.\nReturn: z.\n",
        )
        result = self._run()
        self.assertEqual(1, result.returncode)
        self.assertIn("missing required key 'role'", result.stdout)

    def test_role_value_outside_allowed_set_is_error(self):
        self._write_skill(
            "badrolepkg",
            b"---\nname: badrolepkg\ndescription: a skill with a bad role\nrole: judge\n---\n"
            b"Require: x.\nNever: y.\nReturn: z.\n",
        )
        result = self._run()
        self.assertEqual(1, result.returncode)
        self.assertIn("role", result.stdout)
        self.assertIn("badrolepkg", result.stdout)

    def test_engine_declaring_role_other_than_none_is_error(self):
        self._write_skill(
            "someenginepkg",
            b"---\nname: someenginepkg\ndescription: an engine with a non-none role\nrole: worker\n---\n"
            b"Require: x.\nNever: y.\nReturn: z.\n",
            tier="engines",
        )
        result = self._run()
        self.assertEqual(1, result.returncode)
        self.assertIn("engines skill must declare role: none", result.stdout)

    def test_workflow_declaring_role_other_than_none_is_error(self):
        self._write_skill(
            "someworkflowpkg",
            b"---\nname: someworkflowpkg\ndescription: a workflow with a non-none role\nrole: planner\n---\n"
            b"Require: x.\nNever: y.\nReturn: z.\n",
            tier="workflows",
        )
        result = self._run()
        self.assertEqual(1, result.returncode)
        self.assertIn("workflows skill must declare role: none", result.stdout)

    def test_pack_declaring_role_at_all_is_error(self):
        self._write_pack(
            "somepack",
            b"---\nname: somepack\ndescription: a pack that wrongly declares a role\nrole: worker\n---\n"
            b"| slicing | x |\n",
        )
        result = self._run()
        self.assertEqual(1, result.returncode)
        self.assertIn("pack frontmatter must not declare 'role'", result.stdout)

    def test_orch_worklog_shaped_prose_does_not_warn_loop_lint(self):
        """T7: 'after every iteration or join' (frontmatter description,
        a dispatch-timing adverbial) and 'the loop's done-check' / 'a
        loop run' / 'later iteration' (noun references to another
        skill's loop, not an instruction to iterate) must not trigger
        the loop-term lint -- the false positive named in
        REVIEW-2026-08-06.md thread T7."""
        self._write_skill(
            "worklogshaped",
            b"---\nname: worklogshaped\n"
            b"description: Create or advance state. Use at start and after every iteration or join.\n"
            b"role: none\n---\n"
            b"Require: the run id -- with the spec's objective and acceptance (or\n"
            b"the loop's done-check) at creation.\n"
            b"Maintain the file: append iteration entries, failed approaches; detail\n"
            b"that decides nothing for a later iteration stays out.\n"
            b"Never: edit the frozen goal; delete a failed approach.\n"
            b"Return: the path and the next action it implies.\n",
        )
        result = self._run()
        self.assertEqual(0, result.returncode, result.stdout)
        self.assertEqual([], loop_lint_warnings(result.stdout), result.stdout)

    def test_orch_triage_shaped_prose_does_not_warn_loop_lint(self):
        """T7: 'never a loop' (description) and 'Never: ... an open-ended
        loop' (body) are prohibitions of looping, not instructions to
        iterate -- must not trigger the loop-term lint."""
        self._write_skill(
            "triageshaped",
            b"---\nname: triageshaped\n"
            b"description: Triage a queue into dispositions. A scheduled snapshot, never a loop.\n"
            b"role: none\n---\n"
            b"Require: the queue and the disposition vocabulary.\n"
            b"For each item, decide from the item's own content plus cheap checks.\n"
            b"Never: fix items while triaging; dispose an item on a stale read; let\n"
            b"the snapshot become an open-ended loop.\n"
            b"Return: per-item dispositions, the briefs, and queue statistics.\n",
        )
        result = self._run()
        self.assertEqual(0, result.returncode, result.stdout)
        self.assertEqual([], loop_lint_warnings(result.stdout), result.stdout)

    def test_genuinely_boundless_loop_mention_still_warns(self):
        """A body that actually instructs iteration, with no bound/budget
        or stalled/limited/exit/terminal term anywhere, must still WARN
        -- the narrowed heuristic must not swallow the real signal."""
        self._write_skill(
            "boundlesspkg",
            b"---\nname: boundlesspkg\ndescription: a skill that repeats work\nrole: none\n---\n"
            b"Require: a task.\n"
            b"Iterate on the task until it looks right, then repeat until the\n"
            b"reviewer is satisfied.\n"
            b"Never: skip a step.\n"
            b"Return: the result.\n",
        )
        result = self._run()
        self.assertEqual(0, result.returncode, result.stdout)
        found = loop_lint_warnings(result.stdout)
        self.assertTrue(found, result.stdout)
        self.assertTrue(all("boundlesspkg" in line for line in found), found)


class TestEnvelopeCheck(_IsolatedTree):
    """validate_envelope against contracts/result.md's bound units, on
    the synthetic skills-tree idiom."""

    def _write_skill(self, name: str, body: str, tier: str = "engines"):
        skill_dir = self.tmp_path / "skills" / tier / name
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(
            f"---\nname: {name}\ndescription: a synthetic bound unit\nrole: none\n---\n{body}",
            encoding="utf-8",
        )

    def test_bound_unit_return_without_envelope_is_error(self):
        self._write_skill(
            "orch-loop",
            "Require: a body and a bound.\nNever: exceed the bound.\n"
            "Return: assumptions and feedback.\n",
        )
        result = self._run()
        self.assertEqual(1, result.returncode)
        self.assertIn("orch-loop", result.stdout)
        self.assertIn("does not lead with the result envelope", result.stdout)
        self.assertIn("contracts/result.md", result.stdout)

    def test_bound_unit_leading_with_the_envelope_passes(self):
        self._write_skill(
            "orch-loop",
            "Require: a body and a bound.\nNever: exceed the bound.\n"
            "Return: status, results by identity, and final verification; "
            "then bounds spent. Terminal states are stalled or limited.\n",
        )
        result = self._run()
        self.assertEqual(0, result.returncode, result.stdout)

    def test_bound_unit_return_riding_the_work_item_carrier_passes(self):
        self._write_skill(
            "orch-task",
            "Require: one ready ticket.\nNever: skip the join.\n"
            "Return: the completed ticket per the work-item contract.\n",
        )
        result = self._run()
        self.assertEqual(0, result.returncode, result.stdout)

    def test_unbound_skill_return_is_not_checked(self):
        self._write_skill(
            "orch-elsewise",
            "Require: an input.\nNever: overreach.\nReturn: findings and feedback.\n",
        )
        result = self._run()
        self.assertEqual(0, result.returncode, result.stdout)


class TestNameResolution(_IsolatedTree):
    """validate_names: a backticked `orch-*` outside the skill tree still
    names something in it.

    The call-graph check reads skill bodies only, so a rule, a contract, a
    doc or a README naming a skill that no longer exists rode through exit 0
    and a green suite -- which is exactly how `orch-mechanize` survived in
    rules/token-economy.md and `orch-review-fix` in rules/topology.md after
    both packages were deleted. A name is a call edge wherever it is
    backticked (rules/composition.md rule 2), so it resolves or it is a
    defect.
    """

    def _write_skill(self, name: str, tier: str = "kernel"):
        skill_dir = self.tmp_path / "skills" / tier / name
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(
            f"---\nname: {name}\ndescription: a synthetic package\nrole: worker\n---\n"
            "Require: an input.\nNever: overreach.\nReturn: status; result.\n",
            encoding="utf-8",
        )

    def _write_rule(self, text: str):
        # ARCHITECTURE.md is the marker that says this tree is a library
        # whose tiers a name can resolve in; without it the check skips, as
        # it does for every fixture that copies half a tree.
        (self.tmp_path / "ARCHITECTURE.md").write_text("# Tiers\n", encoding="utf-8")
        rules = self.tmp_path / "rules"
        rules.mkdir(exist_ok=True)
        (rules / "synthetic.md").write_text(text, encoding="utf-8")

    def unresolved(self, stdout):
        """The names this check reported, by name.

        Not the exit code: the fixture tree carries the real contracts/
        beside one synthetic skill, so every name the contracts legitimately
        call is unresolvable here for the fixture's own reason. The findings
        this check makes about the file the test wrote are what it decides.
        """

        return sorted(
            line.split("`")[1]
            for line in stdout.splitlines()
            if "names no package" in line and "rules/synthetic.md" in line
        )

    def test_a_backticked_name_with_no_package_is_an_error(self):
        self._write_skill("orch-real")
        self._write_rule("1. Mechanizing a step is `orch-nothing`'s.\n")
        result = self._run()
        self.assertEqual(1, result.returncode, result.stdout)
        self.assertIn("rules/synthetic.md", result.stdout)
        self.assertEqual(["orch-nothing"], self.unresolved(result.stdout))

    def test_a_backticked_name_with_a_package_is_clean(self):
        self._write_skill("orch-real")
        self._write_rule("1. The cut is `orch-real`'s.\n")
        result = self._run()
        self.assertEqual([], self.unresolved(result.stdout))

    def test_a_pack_name_resolves_under_packs(self):
        self._write_skill("orch-real")
        pack_dir = self.tmp_path / "packs" / "orch-synth-pack"
        pack_dir.mkdir(parents=True)
        (pack_dir / "SKILL.md").write_text("---\nname: orch-synth-pack\n"
                                           "description: a synthetic pack\n---\n",
                                           encoding="utf-8")
        self._write_rule("1. The stamp is `orch-synth-pack`'s.\n")
        result = self._run()
        self.assertNotIn("`orch-synth-pack` names no package", result.stdout)

    def test_the_two_role_names_are_allowed(self):
        self._write_skill("orch-real")
        self._write_rule(
            "1. Children take one of two roles: `orch-planner` and `orch-worker`.\n"
        )
        result = self._run()
        self.assertEqual([], self.unresolved(result.stdout))

    def _write_named(self, relative: str, text: str):
        """One file at `relative`, in a tree marked as the library."""

        (self.tmp_path / "ARCHITECTURE.md").write_text("# Tiers\n", encoding="utf-8")
        path = self.tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def test_every_checked_directory_is_checked(self):
        """One case per directory the check reads, because the list was a
        tuple of four names with one synthetic rules/ file behind it: dropping
        "docs", "contracts" or "templates" from it failed nothing, and
        compositions/ — where every template stub lives, each one naming its
        executor — was never in it at all. A stub calling a deleted skill is
        the exact failure this check exists for, and it was outside the
        surface."""

        self._write_skill("orch-real")
        checked = (
            "rules/synthetic.md",
            "docs/synthetic.md",
            "contracts/synthetic.md",
            "templates/synthetic.md",
            "README.md",
            # recursive, all three: a stub, a nested reference, a pack
            # reference and a skill reference are each a file the old
            # non-recursive glob over four top-level directories never saw
            "compositions/demo/00-step.md",
            "compositions/references/protocol.md",
            "packs/orch-synth-pack/references/craft.md",
            "skills/kernel/orch-real/references/notes.md",
        )
        for relative in checked:
            with self.subTest(relative):
                path = self._write_named(relative, "The step is `orch-nothing`'s.\n")
                try:
                    result = self._run()
                    reported = [
                        line for line in result.stdout.splitlines()
                        if "orch-nothing" in line and relative in line.replace("\\", "/")
                    ]
                    self.assertEqual(1, len(reported), result.stdout)
                    self.assertEqual(1, result.returncode, result.stdout)
                finally:
                    path.unlink()

    def test_an_unbackticked_retired_name_is_history_and_not_a_finding(self):
        """DESIGN.md's supersession paragraphs name skills that were
        deleted. Plain text is the library's own way of saying `mentioned,
        not called` (rules/composition.md rule 2), so the check needs no
        per-file allowlist to let history stand."""

        self._write_skill("orch-real")
        self._write_rule("1. Three shapes were skills (orch-fix, orch-evolve).\n")
        result = self._run()
        self.assertEqual([], self.unresolved(result.stdout))


class TestDuplicationCorpus(_IsolatedTree):
    """validate_cross_tier_duplication's corpus and its one licensed pair.

    The check read packs, skills, rules, contracts and the host block —
    compositions/ and docs/ were outside it, which is why seven templates
    could copy a reference they were told to link, and two skills could
    carry a byte-identical clause with the linter flagging each of them
    against an innocent third file instead of against each other.
    """

    CLAUSE = "\n- The cut names the acceptance the executor is graded on.\n"

    def _write_skill(self, name: str, body: str = "", tier: str = "kernel"):
        skill_dir = self.tmp_path / "skills" / tier / name
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(
            f"---\nname: {name}\ndescription: a synthetic package\nrole: worker\n---\n"
            f"Require: an input.\nNever: overreach.\nReturn: status; result.\n{body}",
            encoding="utf-8",
        )

    def _write(self, relative: str, text: str):
        path = self.tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def duplicates(self, stdout, *labels):
        return [
            line for line in stdout.splitlines()
            if "near-duplicate" in line
            and all(label in line.replace("\\", "/") for label in labels)
        ]

    def test_a_template_stub_restating_a_rule_is_reported(self):
        self._write_skill("orch-real")
        self._write("rules/synthetic.md", "# Rule\n" + self.CLAUSE)
        self._write("compositions/demo/00-step.md", "# Stub\n" + self.CLAUSE)
        result = self._run()
        self.assertTrue(
            self.duplicates(result.stdout, "compositions/demo/00-step.md",
                            "rules/synthetic.md"),
            result.stdout,
        )

    def test_a_doc_restating_a_rule_is_reported(self):
        self._write_skill("orch-real")
        self._write("rules/synthetic.md", "# Rule\n" + self.CLAUSE)
        self._write("docs/guide.md", "# Guide\n" + self.CLAUSE)
        result = self._run()
        self.assertTrue(
            self.duplicates(result.stdout, "docs/guide.md", "rules/synthetic.md"),
            result.stdout,
        )

    def test_two_skills_carrying_one_clause_are_reported_against_each_other(self):
        """Same-tier pairs were skipped whole, on the reasoning that one
        tier's internal business is the pack linter's — which is true of
        packs and false of skills, where no per-tier linter runs at all. So
        two byte-identical skill clauses were invisible while each was
        flagged against some unrelated pack cell."""

        self._write_skill("orch-real", self.CLAUSE)
        self._write_skill("orch-other", self.CLAUSE, tier="instances")
        result = self._run()
        self.assertTrue(
            self.duplicates(
                result.stdout,
                "skills/instances/orch-other/SKILL.md",
                "skills/kernel/orch-real/SKILL.md",
            ),
            result.stdout,
        )


class TestLicensedCopies(unittest.TestCase):
    """A copy the library licensed and named an owner for is not a finding.

    templates/host-block.md carries rules/visibility.md §6's untrusted-data
    clause on purpose — the block is the one text a host reads before it can
    reach the rule — and names the owner one line above the copy. Counting
    it as an unowned duplication asks for the copy to be deleted, which
    would delete the licence with it."""

    def test_the_visibility_copy_in_the_host_block_is_licensed(self):
        pairs = {
            frozenset((left, right)) for left, right, _ in validate.LICENSED_COPIES
        }
        self.assertIn(
            frozenset(("rules/visibility.md", "templates/host-block.md")), pairs
        )

    def test_the_licensed_pair_is_not_reported_against_the_real_tree(self):
        result = subprocess.run(
            [sys.executable, str(VALIDATE)], capture_output=True, text=True,
        )
        # the reported file and the file it is reported against, not any
        # line that happens to quote either path inside a clause
        pair = ("rules/visibility.md", "templates/host-block.md")
        reported = [
            line for line in result.stdout.splitlines()
            if "near-duplicate" in line
            and any(
                line.replace("\\", "/").startswith(f"WARN {owner}:")
                and f"with {copy}:" in line.replace("\\", "/")
                for owner, copy in (pair, pair[::-1])
            )
        ]
        self.assertEqual([], reported, result.stdout)


class TestLensAnchor(_IsolatedTree):
    """validate_lens_anchor: a pack's lens cell anchor lands on a heading.

    The lens row is compared as three words of text and deliberately not
    resolved, so deleting `## Lens` from a craft reference left the
    validator at exit 0 and the suite green while every gate lane the pack
    stamps pointed at a section that was not there.
    """

    def _write_pack(self, name: str, craft: str):
        pack_dir = self.tmp_path / "packs" / name
        (pack_dir / "references").mkdir(parents=True)
        (pack_dir / "SKILL.md").write_text(
            f"---\nname: {name}\ndescription: a synthetic pack\n---\n\n"
            "| cell | binding |\n| --- | --- |\n"
            "| lens | `orch-critique` with "
            "[references/craft.md#lens](references/craft.md#lens) |\n",
            encoding="utf-8",
        )
        (pack_dir / "references" / "craft.md").write_text(craft, encoding="utf-8")

    def test_a_lens_anchor_with_no_heading_is_an_error(self):
        self._write_pack("orch-synth-pack", "# Craft\n\n## Vocabulary\n\nterms.\n")
        result = self._run()
        self.assertEqual(1, result.returncode, result.stdout)
        self.assertIn("craft.md#lens", result.stdout)
        self.assertIn("## Lens", result.stdout)

    def test_a_lens_anchor_resolving_to_the_heading_is_clean(self):
        self._write_pack(
            "orch-synth-pack", "# Craft\n\n## Vocabulary\n\nterms.\n\n## Lens\n\ncriteria.\n"
        )
        result = self._run()
        self.assertNotIn("craft.md#lens", result.stdout)


class TestWordBudgetAndLinks(_IsolatedTree):
    """rules/composition.md §5 counts words with link targets stripped, and
    docs/documentation.md law 5's oracle resolves every markdown link."""

    def _write_skill(self, name, body, tier="instances"):
        skill_dir = self.tmp_path / "skills" / tier / name
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(
            f"---\nname: {name}\ndescription: a synthetic body\nrole: worker\n---\n"
            f"Require: one thing.\n\n{body}\n\nNever: another thing.\n\nReturn: a result.\n",
            encoding="utf-8",
        )

    def test_a_wide_body_over_the_word_budget_is_refused(self):
        wide = " ".join(["word"] * 320)  # one line, 320 words
        self._write_skill("orch-wide", wide)
        result = self._run()
        self.assertEqual(1, result.returncode, result.stdout)
        self.assertIn("words, exceeds the instances budget of 300", result.stdout)

    def test_link_targets_do_not_count_and_a_narrow_body_under_budget_passes(self):
        links = "\n".join(
            f"- see [contract](../../../contracts/work-item.md#a-long-anchor-{i})"
            for i in range(60)
        )
        self._write_skill("orch-linky", links)
        result = self._run()
        self.assertNotIn("exceeds the instances budget", result.stdout)

    def test_a_dangling_markdown_link_in_docs_is_an_error(self):
        for root in validate.LINKED_MD_ROOTS:
            (self.tmp_path / root).mkdir(exist_ok=True)
        docs = self.tmp_path / "docs"
        (docs / "x.md").write_text("see [gone](gone.md) and [ok](../contracts/verdict.md)\n", encoding="utf-8")
        result = self._run()
        self.assertEqual(1, result.returncode, result.stdout)
        self.assertIn("markdown link does not resolve: gone.md", result.stdout)
        # A resolving link raises no diagnostic — asserted on the target
        # the diagnostic names, not on membership of a bare name in a list
        # of lines no line can equal. (The copied contracts' own links to
        # ../docs and ../rules dangle in this synthetic tree by design.)
        self.assertNotIn("does not resolve: ../contracts/verdict.md", result.stdout)


if __name__ == "__main__":
    unittest.main()


class TestSurfaceBudgets(_IsolatedTree):
    """rules/token-economy.md §11: the every-turn surfaces carry the tightest
    ceilings, and the check reads them from the tree it runs in."""

    def test_a_host_block_over_its_budget_is_refused(self):
        (self.tmp_path / "templates").mkdir()
        (self.tmp_path / "templates" / "host-block.md").write_text(
            " ".join(["word"] * (validate.SURFACE_BUDGET["templates/host-block.md"] + 10)),
            encoding="utf-8",
        )
        result = self._run()
        self.assertEqual(1, result.returncode, result.stdout)
        self.assertIn("templates/host-block.md", result.stdout)
        self.assertIn("exceeds the every-turn budget", result.stdout)

    def test_the_real_surfaces_sit_under_their_ceilings(self):
        for name, limit in validate.SURFACE_BUDGET.items():
            with self.subTest(surface=name):
                text = (ROOT / name).read_text(encoding="utf-8")
                self.assertLessEqual(validate.body_words(text), limit)
