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


GOOD_COMPOSITION = """---
name: {name}
description: a synthetic composition exercising the contract checks
entry: {entry}
---

Require: a frozen input.

Steps:
- one — `orch-task`.

Edges: seq one.

Invariants — Never: skip the orch-task dispatch or widen its scope.

Done check: the final envelope's verification covers the result.

Return: status, result identity, and verification; then feedback.
"""


class TestCompositionContractChecks(_IsolatedTree):
    """validate_compositions against contracts/composition.md, on the
    same isolated tmp-copy pattern as the synthetic package tests."""

    def setUp(self):
        super().setUp()
        (self.tmp_path / "compositions").mkdir()

    def _write_composition(self, name: str, content: str):
        (self.tmp_path / "compositions" / f"{name}.md").write_text(content, encoding="utf-8")

    def test_contract_conforming_composition_passes(self):
        for entry in ("routed", "named", "scheduled"):
            self._write_composition(f"good-{entry}", GOOD_COMPOSITION.format(name=f"good-{entry}", entry=entry))
        result = self._run()
        self.assertEqual(0, result.returncode, result.stdout)

    def test_entry_outside_the_closed_set_is_error(self):
        self._write_composition("badentry", GOOD_COMPOSITION.format(name="badentry", entry="automatic"))
        result = self._run()
        self.assertEqual(1, result.returncode)
        self.assertIn("entry 'automatic'", result.stdout)
        self.assertIn("contracts/composition.md", result.stdout)

    def test_missing_invariants_and_done_check_are_admission_errors(self):
        bad = GOOD_COMPOSITION.format(name="gutted", entry="named")
        bad = bad.replace("Invariants — Never: skip the orch-task dispatch or widen its scope.\n\n", "")
        bad = bad.replace("Done check: the final envelope's verification covers the result.\n\n", "")
        self._write_composition("gutted", bad)
        result = self._run()
        self.assertEqual(1, result.returncode)
        self.assertIn("missing 'invariants'", result.stdout)
        self.assertIn("missing 'done_check'", result.stdout)
        self.assertIn("admission rejects", result.stdout)

    def test_missing_steps_and_edges_are_errors(self):
        bad = GOOD_COMPOSITION.format(name="stepless", entry="named")
        bad = bad.replace("Steps:\n- one — `orch-task`.\n\n", "")
        bad = bad.replace("Edges: seq one.\n\n", "")
        self._write_composition("stepless", bad)
        result = self._run()
        self.assertEqual(1, result.returncode)
        self.assertIn("required field 'steps'", result.stdout)
        self.assertIn("required field 'edges'", result.stdout)

    def test_name_mismatch_and_missing_frontmatter_are_errors(self):
        self._write_composition("misnamed", GOOD_COMPOSITION.format(name="other", entry="named"))
        self._write_composition("bare", "# bare (no frontmatter)\n\nprose only\n")
        result = self._run()
        self.assertEqual(1, result.returncode)
        self.assertIn("does not match file name 'misnamed'", result.stdout)
        self.assertIn("missing opening frontmatter fence", result.stdout)

    def test_composition_return_missing_the_envelope_is_error(self):
        bad = GOOD_COMPOSITION.format(name="bareret", entry="named")
        bad = bad.replace(
            "Return: status, result identity, and verification; then feedback.",
            "Return: assumptions and feedback.",
        )
        self._write_composition("bareret", bad)
        result = self._run()
        self.assertEqual(1, result.returncode)
        self.assertIn("does not lead with the result envelope", result.stdout)

    def test_invariants_block_vacuous_of_all_step_content_is_error(self):
        """T2: validate.py:903-953 checked presence only -- an
        'invariants' block that shares no vocabulary with any step
        (REVIEW-2026-08-06.md's own example: 'Never: violate the laws
        of physics') passed. Now it is an ERROR naming the unbound
        step(s)."""
        vacuous = """---
name: gapless
description: a synthetic composition with a vacuous invariants block
entry: named
---

Require: a frozen input.

Steps:
- acquire-spec — `orch-spec`: freeze one evidence-acquisition spec.
- materialize — `orch-deliver` of that frozen spec.

Edges: seq acquire-spec → materialize.

Invariants — Never: violate the laws of physics.

Done check: the final envelope's verification covers the result.

Return: status, result identity, and verification; then feedback.
"""
        self._write_composition("gapless", vacuous)
        result = self._run()
        self.assertEqual(1, result.returncode)
        self.assertIn("invariants", result.stdout)
        self.assertIn("gapless", result.stdout)

    def test_invariants_block_binding_at_least_one_step_passes(self):
        bound = """---
name: gapbound
description: a synthetic composition whose invariants bind its steps
entry: named
---

Require: a frozen input.

Steps:
- acquire-spec — `orch-spec`: freeze one evidence-acquisition spec.
- materialize — `orch-deliver` of that frozen spec.

Edges: seq acquire-spec → materialize.

Invariants — Never: materialize before the spec is frozen; skip the
acquire-spec step.

Done check: the final envelope's verification covers the result.

Return: status, result identity, and verification; then feedback.
"""
        self._write_composition("gapbound", bound)
        result = self._run()
        self.assertEqual(0, result.returncode, result.stdout)

    def test_done_check_naming_only_envelope_status_is_error(self):
        """T2: a tautological done_check ('status is complete') names
        only the envelope's own status vocabulary and no external
        oracle -- ERROR."""
        tautological = GOOD_COMPOSITION.format(name="tautdone", entry="named")
        tautological = tautological.replace(
            "Done check: the final envelope's verification covers the result.",
            "Done check: the status is complete.",
        )
        self._write_composition("tautdone", tautological)
        result = self._run()
        self.assertEqual(1, result.returncode)
        self.assertIn("done_check", result.stdout)
        self.assertIn("tautdone", result.stdout)

    def test_done_check_with_filler_qualifiers_only_is_error(self):
        """Gate repair: modal/evaluative fillers and the envelope's own
        field vocabulary do not count as an external oracle -- ERROR."""
        for filler in (
            "the status is complete successfully.",
            "the status must be complete indeed.",
            "status is complete when verified.",
        ):
            with self.subTest(filler=filler):
                gamed = GOOD_COMPOSITION.format(
                    name="fillerdone", entry="named"
                )
                gamed = gamed.replace(
                    "Done check: the final envelope's verification covers the result.",
                    "Done check: " + filler,
                )
                self._write_composition("fillerdone", gamed)
                result = self._run()
                self.assertEqual(1, result.returncode)
                self.assertIn("done_check", result.stdout)

    def test_done_check_naming_an_external_oracle_passes(self):
        real_shaped = GOOD_COMPOSITION.format(name="realdone", entry="named")
        real_shaped = real_shaped.replace(
            "Done check: the final envelope's verification covers the result.",
            "Done check: the sealed manifest's qualification verdict set "
            "covers the benchmark identity.",
        )
        self._write_composition("realdone", real_shaped)
        result = self._run()
        self.assertEqual(0, result.returncode, result.stdout)


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


if __name__ == "__main__":
    unittest.main()
