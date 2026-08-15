"""Rule 10 (rules/composition.md, the carriage rule) mechanized as
validate_carriage: every call edge's Require item must be lexically
carried in the caller's body; every pack's executor/assembly Require
must carry in the pack's slicing cell; every pack executor/assembly
Return must file per the ticket/work-item filing law (work-item.md).
Follows tests/test_validator.py's isolated-tmp-tree-plus-subprocess
idiom for CLI-level fixtures."""
import re
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


SCRIPTS = ROOT / "scripts"
ARCHITECTURE = ROOT / "ARCHITECTURE.md"

# The form ARCHITECTURE.md's script clauses already take:
# `scripts/<name>.py` owns <responsibility>. A bare mention names no owner.
_OWNERSHIP_CLAUSE = re.compile(r"`scripts/([^`/]+\.py)`\s+owns\s+([^;.]+)")


def _scripts_without_owners(scripts_dir, architecture_text):
    """Every `*.py` in scripts_dir whose responsibility architecture_text
    never states. Enumerated from disk, never from a pinned list, so a
    script added later is checked without editing this file."""
    flat = re.sub(r"\s+", " ", architecture_text)
    owned = {m.group(1): m.group(2).strip() for m in _OWNERSHIP_CLAUSE.finditer(flat)}
    return sorted(p.name for p in scripts_dir.glob("*.py") if not owned.get(p.name))


class ScriptOwnershipTest(unittest.TestCase):
    """ARCHITECTURE.md owns ownership (AGENTS.md), so a script whose
    responsibility it never states has no owner in the repository."""

    def test_every_script_is_named_with_the_responsibility_it_owns(self):
        unowned = _scripts_without_owners(
            SCRIPTS, ARCHITECTURE.read_text(encoding="utf-8")
        )
        self.assertEqual(
            [],
            unowned,
            "ARCHITECTURE.md states no '`scripts/<name>` owns <responsibility>' "
            f"clause for: {', '.join(unowned)}",
        )

    def test_a_script_with_no_owner_fails_the_check(self):
        """The can-fail direction, built beside the tree and never by
        mutating it (rules/verification.md §8): a scripts/ copy carrying
        one extra script, read against the real ARCHITECTURE.md, which
        cannot name it."""
        architecture_text = ARCHITECTURE.read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as tmp:
            beside = Path(tmp) / "scripts"
            beside.mkdir()
            for script in SCRIPTS.glob("*.py"):
                (beside / script.name).write_text("", encoding="utf-8")
            self.assertEqual(
                [],
                _scripts_without_owners(beside, architecture_text),
                "the copy must start fully owned, or the newcomer below is "
                "not what the check reacted to",
            )
            (beside / "unowned_newcomer.py").write_text("", encoding="utf-8")
            self.assertEqual(
                ["unowned_newcomer.py"],
                _scripts_without_owners(beside, architecture_text),
            )


TICKETS = SCRIPTS / "tickets.py"
SKILLS = ROOT / "skills"

# scripts/tickets.py declares one `_cmd_<name>` per subcommand and dashes the
# name on the command line (its `_dispatch`).
_SUBCOMMAND_DEF = re.compile(r"^def _cmd_([a-z_]+)\(", re.MULTILINE)
# A skill body reaches a subcommand by naming it inside a code span.
_SKILL_CALL = re.compile(r"`[^`]*tickets\.py ([a-z-]+)[^`]*`")
# The form ARCHITECTURE.md records for a subcommand no skill body runs.
_OPERATOR_ONLY_CLAUSE = re.compile(r"`tickets\.py ([a-z-]+)` is operator-only: ([^;.]+)")


def _subcommands_without_reach(tickets_source, skill_bodies, architecture_text):
    """Every tickets.py subcommand that no skill body names and that
    architecture_text records no operator-only status for. Enumerated from
    the script's own `_cmd_*` declarations, never from a pinned list, so a
    subcommand added later is checked without editing this file."""
    called = set()
    for body in skill_bodies:
        called.update(_SKILL_CALL.findall(re.sub(r"\s+", " ", body)))
    flat = re.sub(r"\s+", " ", architecture_text)
    recorded = {
        name for name, reason in _OPERATOR_ONLY_CLAUSE.findall(flat) if reason.strip()
    }
    return sorted(
        name.replace("_", "-")
        for name in _SUBCOMMAND_DEF.findall(tickets_source)
        if name.replace("_", "-") not in called | recorded
    )


class SubcommandReachTest(unittest.TestCase):
    """An unreached subcommand is a decision, not an accident: either the
    skill body that runs it names it, or ARCHITECTURE.md -- which owns
    ownership (AGENTS.md) -- records that no skill body does and why."""

    def _skill_bodies(self):
        return [
            path.read_text(encoding="utf-8")
            for path in sorted(SKILLS.glob("*/*/SKILL.md"))
        ]

    def test_every_subcommand_is_called_by_a_skill_or_recorded_operator_only(self):
        unreached = _subcommands_without_reach(
            TICKETS.read_text(encoding="utf-8"),
            self._skill_bodies(),
            ARCHITECTURE.read_text(encoding="utf-8"),
        )
        self.assertEqual(
            [],
            unreached,
            "no skill body names `tickets.py <name>` and ARCHITECTURE.md "
            "records no '`tickets.py <name>` is operator-only: <reason>' "
            f"clause for: {', '.join(unreached)}",
        )

    def test_a_subcommand_with_neither_caller_nor_status_fails_the_check(self):
        """The can-fail direction, built beside the tree and never by
        mutating it (rules/verification.md §8): a scratch copy of
        scripts/tickets.py carrying one extra subcommand, read against the
        real skill bodies and the real ARCHITECTURE.md, which cannot name
        it."""
        bodies = self._skill_bodies()
        architecture_text = ARCHITECTURE.read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as tmp:
            beside = Path(tmp) / "tickets.py"
            beside.write_text(TICKETS.read_text(encoding="utf-8"), encoding="utf-8")
            self.assertEqual(
                [],
                _subcommands_without_reach(
                    beside.read_text(encoding="utf-8"), bodies, architecture_text
                ),
                "the copy must start fully reached, or the newcomer below is "
                "not what the check reacted to",
            )
            with open(beside, "a", encoding="utf-8") as handle:
                handle.write("\n\ndef _cmd_newcomer(rest):\n    return {}\n")
            self.assertEqual(
                ["newcomer"],
                _subcommands_without_reach(
                    beside.read_text(encoding="utf-8"), bodies, architecture_text
                ),
            )


VERIFICATION = ROOT / "rules" / "verification.md"

# What §8's faithfulness clause has to state, keyed to the measurement that
# named it: `git archive` drops `.git`, which silently moved 61-65
# test_cutcheck verdicts; `git rev-list --count` fingerprints a tip (417 at
# 2c8d484, 420 at 7d94c46), so a count recorded beside a reading settles
# which revision it was taken at; runtime indicts a copy only when short.
_FAITHFULNESS_CLAUSE = {
    "what a faithful copy preserves": ("faithful", "everything the oracles read"),
    "clone, never extract": ("clone", "extract", "`.git`"),
    "the fingerprint that evidences it": ("`git rev-list --count`", "which revision"),
    "the one direction runtime indicts in": ("shorter", "longer"),
}

# §8 as it read before the clause landed: it required the wrong result be
# built beside the tree and never said how to build one.
_SECTION_8_UNAMENDED = """8. An oracle must be able to fail: a check that cannot FAIL when the
   claim it stands for is false decides nothing, and its PASS is void.
   Show it against a wrong result built beside the tree, never by
   mutating the tree under test, which an interrupted pass leaves mutated.
"""


def _clause(text, number):
    """One numbered clause of a flat-numbered rules file, whitespace
    collapsed so a wrapped sentence matches and a sentence landing in a
    neighbouring clause cannot satisfy an assertion scoped to this one."""
    match = re.search(rf"(?m)^{number}\. (.*?)(?=^\d+\. |\Z)", text, re.S)
    if match is None:
        raise AssertionError(f"rules/verification.md has no clause {number}")
    return re.sub(r"\s+", " ", match.group(1))


def _faithfulness_gaps(verification_text):
    """Which parts of the faithfulness clause verification_text never
    states. Read from clause 8 alone, which owns how a copy built beside the
    tree is proved faithful."""
    clause = _clause(verification_text, 8)
    return sorted(
        name
        for name, phrases in _FAITHFULNESS_CLAUSE.items()
        if not all(phrase in clause for phrase in phrases)
    )


class CopyFaithfulnessClauseTest(unittest.TestCase):
    """§8 sends every can-fail demonstration to a copy built beside the
    tree and, until this clause, never said how to build one. An unproved
    copy is worse than none: an oracle that reads history answers from
    whatever the copy carries, and reports nothing when that is not the
    revision under test."""

    def test_section_8_states_what_a_copy_preserves_and_how_that_is_evidenced(self):
        gaps = _faithfulness_gaps(VERIFICATION.read_text(encoding="utf-8"))
        self.assertEqual(
            [],
            gaps,
            "rules/verification.md §8 states no faithfulness clause covering: "
            f"{', '.join(gaps)}",
        )

    def test_the_clause_names_rev_list_count_as_the_fingerprint(self):
        clause = _clause(VERIFICATION.read_text(encoding="utf-8"), 8)
        self.assertIn(
            "`git rev-list --count`",
            clause,
            "verification.md §8 names no fingerprint that proves the copy "
            "carries the history it is read for",
        )
        self.assertIn(
            "which revision",
            clause,
            "verification.md §8 names `git rev-list --count` without saying "
            "it settles which revision a reading was taken at; a count that "
            "settles nothing is not re-readable",
        )

    def test_a_section_8_without_the_clause_fails_the_check(self):
        """The can-fail direction, built beside the tree and never by
        mutating it -- under the clause being added here: a copy of
        rules/verification.md carrying the §8 that preceded it."""
        real = VERIFICATION.read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as tmp:
            beside = Path(tmp) / "verification.md"
            beside.write_text(real, encoding="utf-8")
            self.assertEqual(
                [],
                _faithfulness_gaps(beside.read_text(encoding="utf-8")),
                "the copy must start with the clause intact, or the excision "
                "below is not what the check reacted to",
            )
            beside.write_text(
                re.sub(
                    r"(?ms)^8\. .*?(?=^9\. )",
                    lambda _: _SECTION_8_UNAMENDED,
                    real,
                ),
                encoding="utf-8",
            )
            self.assertEqual(
                sorted(_FAITHFULNESS_CLAUSE),
                _faithfulness_gaps(beside.read_text(encoding="utf-8")),
            )


if __name__ == "__main__":
    unittest.main()
