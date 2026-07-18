"""Rule 10 (rules/composition.md, the carriage rule) mechanized as
validate_carriage: every call edge's Require item must be lexically
carried in the caller's body; every pack's executor/assembly Require
must carry in the pack's slicing cell; every pack executor/assembly
Return must file per the ticket/work-item filing law (work-item.md).
Follows tests/test_validator.py's isolated-tmp-tree-plus-subprocess
idiom for CLI-level fixtures."""
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

VALIDATE = ROOT / "tools" / "validate.py"
CONTRACTS = ROOT / "contracts"


class _IsolatedTree(unittest.TestCase):
    """A synthetic repo tree with only contracts/ + tools/validate.py +
    whatever skills/packs the test writes -- the real skills/ and packs/
    trees are absent, so only the synthetic packages are checked."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmp.name)
        shutil.copytree(CONTRACTS, self.tmp_path / "contracts")
        (self.tmp_path / "tools").mkdir()
        shutil.copy(VALIDATE, self.tmp_path / "tools" / "validate.py")
        self._run("--pin")  # matching pins so only synthetic packages can fail

    def tearDown(self):
        self.tmp.cleanup()

    def _run(self, *args):
        return subprocess.run(
            [sys.executable, str(self.tmp_path / "tools" / "validate.py"), *args],
            capture_output=True,
            text=True,
        )

    def _write_skill(self, name: str, content: str, tier: str = "instances"):
        skill_dir = self.tmp_path / "skills" / tier / name
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(content, encoding="utf-8")

    def _write_pack(self, name: str, content: str):
        pack_dir = self.tmp_path / "packs" / name
        pack_dir.mkdir(parents=True)
        (pack_dir / "SKILL.md").write_text(content, encoding="utf-8")


CALLEE_SKILL = """---
name: orch-calleepkg
description: synthetic callee whose Require item no caller carries.
role: worker
---

Require: a distinctive telemetry beacon.

Do the callee's own step.

Never: skip the beacon check.

Return: the beacon reading.
"""

CALLER_SKILL_VIOLATING = """---
name: orch-callerpkg
description: synthetic caller that never mentions the callee's beacon.
role: worker
---

Require: the user's request.

Dispatch through `orch-calleepkg` for the next step.

Never: skip the dispatch.

Return: status and the orch-calleepkg result.
"""

CALLER_SKILL_CARRYING = """---
name: orch-callerpkg
description: synthetic caller that names the callee's beacon by hand.
role: worker
---

Require: the user's request and a fixed telemetry beacon to forward.

Dispatch through `orch-calleepkg`, carrying the beacon.

Never: skip the dispatch.

Return: status and the orch-calleepkg result.
"""


MULTI_SEGMENT_CALLEE = """---
name: orch-calleepkg
description: synthetic callee with a two-input Require plus an elaboration segment.
role: worker
---

Require: a distinctive telemetry beacon, each naming its wavelength,
and a frozen calibration ledger.

Do the callee's own step.

Never: skip the beacon check.

Return: the beacon reading.
"""

MULTI_SEGMENT_CALLER_PARTIAL = """---
name: orch-callerpkg
description: synthetic caller carrying the beacon but never the ledger.
role: worker
---

Require: a work order.

Build against the beacon through `orch-calleepkg`.

Never: skip the beacon.

Return: status and the orch-calleepkg result.
"""


class TestCarriageSeededViolation(_IsolatedTree):
    def test_second_segment_uncarried_is_flagged_and_elaboration_skipped(self):
        self._write_skill("orch-calleepkg", MULTI_SEGMENT_CALLEE)
        self._write_skill("orch-callerpkg", MULTI_SEGMENT_CALLER_PARTIAL)
        result = self._run()
        self.assertEqual(1, result.returncode, result.stdout)
        self.assertIn("not carried", result.stdout)
        self.assertIn("(head noun 'ledger')", result.stdout)
        error_lines = [ln for ln in result.stdout.splitlines() if ln.startswith("ERROR")]
        self.assertEqual(1, len(error_lines), result.stdout)

    def test_uncarried_require_item_is_flagged(self):
        self._write_skill("orch-calleepkg", CALLEE_SKILL)
        self._write_skill("orch-callerpkg", CALLER_SKILL_VIOLATING)
        result = self._run()
        self.assertEqual(1, result.returncode, result.stdout)
        self.assertIn("not carried", result.stdout)
        self.assertIn("orch-callerpkg", result.stdout)
        self.assertIn("beacon", result.stdout)

    def test_carried_require_item_is_not_flagged(self):
        self._write_skill("orch-calleepkg", CALLEE_SKILL)
        self._write_skill("orch-callerpkg", CALLER_SKILL_CARRYING)
        result = self._run()
        self.assertEqual(0, result.returncode, result.stdout)
        self.assertNotIn("not carried", result.stdout)


PACK_WITH_BAD_RETURN = """---
name: badreturnpack
description: synthetic pack whose executor Return never files per the ticket/work-item filing law.
---

Cells per [contracts/pack-signature.md](../../contracts/pack-signature.md):

| cell | binding |
| --- | --- |
| slicing | inline: cut by widget |
| executor | `badreturnexecutor` |
| assembly | none |
| lens | inline: none |
| oracle_policy | inline: none |
| workspace | inline: none |
| required_spec_fields | inline: none |
| craft | [references/craft.md](references/craft.md) |
"""

SYNTHETIC_CRAFT = "# Synthetic craft\n\nNo domain terms; this pack exists only to exercise the validator.\n"

EXECUTOR_WITH_BAD_RETURN = """---
name: badreturnexecutor
description: synthetic executor whose Return never files per the ticket/work-item filing law.
role: worker
---

Require: one claimed widget ticket.

Build the widget.

Never: skip the widget.

Return: the finished widget path.
"""

PACK_WITH_SLICING_GAP = """---
name: gappack
description: synthetic pack whose executor Require outruns its slicing cell.
---

Cells per [contracts/pack-signature.md](../../contracts/pack-signature.md):

| cell | binding |
| --- | --- |
| slicing | [references/slicing.md](references/slicing.md) |
| executor | `gapexecutor` |
| assembly | none |
| lens | inline: none |
| oracle_policy | inline: none |
| workspace | inline: none |
| required_spec_fields | inline: none |
| craft | [references/craft.md](references/craft.md) |
"""

GAP_SLICING_REFERENCE = """# Gap slicing

Cut the spec into widgets. Each ticket names one widget.
"""

GAP_EXECUTOR_SKILL = """---
name: gapexecutor
description: synthetic executor whose Require noun never reaches slicing.
role: worker
---

Require: a distinctive telemetry beacon.

Build against the beacon.

Never: skip the beacon.

Return: the beacon report.
"""


class TestCarriagePackChecks(_IsolatedTree):
    def test_executor_return_not_naming_the_filing_is_flagged(self):
        self._write_pack("badreturnpack", PACK_WITH_BAD_RETURN)
        pack_dir = self.tmp_path / "packs" / "badreturnpack"
        (pack_dir / "references").mkdir()
        (pack_dir / "references" / "craft.md").write_text(SYNTHETIC_CRAFT, encoding="utf-8")
        self._write_skill("badreturnexecutor", EXECUTOR_WITH_BAD_RETURN)
        result = self._run()
        self.assertEqual(1, result.returncode, result.stdout)
        self.assertIn("ticket/work-item filing", result.stdout)
        self.assertIn("badreturnexecutor", result.stdout)

    def test_executor_require_not_in_slicing_cell_is_flagged(self):
        self._write_pack("gappack", PACK_WITH_SLICING_GAP)
        pack_dir = self.tmp_path / "packs" / "gappack"
        (pack_dir / "references").mkdir()
        (pack_dir / "references" / "slicing.md").write_text(GAP_SLICING_REFERENCE, encoding="utf-8")
        (pack_dir / "references" / "craft.md").write_text(SYNTHETIC_CRAFT, encoding="utf-8")
        self._write_skill("gapexecutor", GAP_EXECUTOR_SKILL)
        result = self._run()
        self.assertEqual(1, result.returncode, result.stdout)
        self.assertIn("slicing cell", result.stdout)
        self.assertIn("beacon", result.stdout)


class TestCarriageAgainstRepo(unittest.TestCase):
    """The real tree, post followup-sweep ticket 02 (the 9 carriage-
    deferred sites' callers now carry their callee's Require noun),
    must clear validate_carriage with zero 'not carried' WARN lines --
    covered by TestValidatorAgainstRepo's exit-0 assertion in
    test_validator.py; this guards the fixed state so a caller-noun
    carriage gap reopening surfaces here instead of silently passing.
    CARRIAGE_DEFERRED may still hold entries (ticket 06 empties the
    table) -- this asserts on WARN lines containing 'not carried', not
    on the table itself, so it tolerates either state."""

    def test_no_carriage_gaps_surface_as_warn(self):
        result = subprocess.run(
            [sys.executable, str(VALIDATE)], capture_output=True, text=True
        )
        self.assertEqual(0, result.returncode, result.stdout)
        warn_lines = [ln for ln in result.stdout.splitlines() if ln.startswith("WARN")]
        carriage_warns = [ln for ln in warn_lines if "not carried" in ln]
        self.assertEqual(
            [],
            carriage_warns,
            "expected zero carriage 'not carried' WARN lines on the real "
            f"tree; got:\n{result.stdout}",
        )


if __name__ == "__main__":
    unittest.main()
