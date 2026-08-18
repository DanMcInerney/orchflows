"""Invariants of this repository's own law, each read from the file that
owns it. Rule 10 (rules/composition.md, the carriage rule) mechanized as
validate_carriage: every call edge's Require item must be lexically
carried in the caller's body; every pack's executor/assembly Require
must carry in the pack's slicing cell; every pack executor/assembly
Return must file per the ticket/work-item filing law (work-item.md).
Then four invariants validate.py does not check: ARCHITECTURE.md naming
the responsibility every `scripts/*.py` owns; every `tickets.py`
subcommand reached by a skill body or recorded operator-only there; and
two clauses read from their owners -- orch-decompose's cut lens on
proving a copy built beside the tree faithful, which
rules/verification.md §8 reaches in one hop, and rules/improvement.md §1
on where the friction fallback writes when the logger is refused.
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
PINS = ROOT / "tests" / "pins.json"

from tools import validate  # noqa: E402  (needs the sys.path insert above)


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
        # The compiler is two files (ARCHITECTURE.md): a tree that runs the
        # copy carries `scripts/doclint.py`, which it asks whether a link
        # resolves and whether two clauses are one clause.
        (self.tmp_path / "scripts").mkdir()
        shutil.copy(ROOT / "scripts" / "doclint.py", self.tmp_path / "scripts" / "doclint.py")
        # Matching pins, so only the synthetic packages can fail. The
        # committed pins.json already matches these very contract bytes --
        # test_validator.py's test_pin_matches_committed_pins_json is what
        # proves it -- so copy it instead of spawning `--pin` per test.
        (self.tmp_path / "tests").mkdir()
        shutil.copy(PINS, self.tmp_path / "tests" / "pins.json")

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
    """The real tree cleared validate_carriage when followup-sweep ticket
    02 made the 9 deferred sites' callers carry their callee's Require
    noun, and ticket 06 then emptied `CARRIAGE_DEFERRED`. Both are now
    settled facts, so this asserts them rather than hedging: the table is
    empty, which makes `_carriage_flag` raise an error and not a WARN for
    every gap, and validate_carriage over the real packages reports
    nothing at all. Runs the checker in process -- the CLI boundary is
    TestValidatorAgainstRepo's job in test_validator.py."""

    @classmethod
    def setUpClass(cls):
        cls.diag = validate.Diagnostics()
        packages = validate.discover_packages()
        for pkg in packages:
            frontmatter, body = validate.parse_frontmatter(
                pkg["skill_md"].read_text(encoding="utf-8-sig"),
                validate.rel(pkg["skill_md"]),
                cls.diag,
            )
            pkg["frontmatter"] = frontmatter or {}
            pkg["body"] = body or ""
        cls.parse_items = list(cls.diag.items)
        validate.validate_carriage(packages, cls.diag)
        cls.carriage_items = cls.diag.items[len(cls.parse_items):]

    def test_the_carriage_deferral_table_is_empty(self):
        self.assertEqual({}, validate.CARRIAGE_DEFERRED)

    def test_the_real_tree_reports_no_carriage_gap(self):
        self.assertEqual([], self.parse_items, "a package failed to parse")
        self.assertEqual(
            [],
            [
                "%s %s: %s" % item
                for item in self.carriage_items
            ],
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
LENS = ROOT / "skills" / "kernel" / "orch-decompose" / "references" / "cut-lens.md"

# What the faithfulness clause has to state, keyed to the measurement that
# named it: `git archive` drops `.git`, which silently moved 61-65
# test_cutcheck verdicts; runtime indicts a copy only when short.
#
# Its owner is the cut lens, not rules/verification.md §8: the git-workspace
# recipe left the rule every pack inherits for the code pack's cut owner
# (REVIEW-2026-08-15 T4). §8 keeps the law and names
# the lens, so both halves are read below -- the recipe from the lens, the
# one hop to it from §8.
_FAITHFULNESS_CLAUSE = {
    "what a faithful copy preserves": ("faithful", "oracle", "unchanged"),
    "clone, never extract": ("clone", "extract", "`.git`"),
    "the one direction runtime indicts in": ("shorter", "longer"),
    "the fingerprint that settles which revision was read": (
        "`git rev-list --count`",
        "which revision",
    ),
}

# The lens with the recipe excised: the heading it lives under, to the end
# of the file.
_RECIPE_HEADING = "## Proving a copy"


def _clause(text, number):
    """One numbered clause of a flat-numbered rules file, whitespace
    collapsed so a wrapped sentence matches and a sentence landing in a
    neighbouring clause cannot satisfy an assertion scoped to this one."""
    match = re.search(rf"(?m)^{number}\. (.*?)(?=^\d+\. |\Z)", text, re.S)
    if match is None:
        raise AssertionError(f"no clause {number}")
    return re.sub(r"\s+", " ", match.group(1))


def _faithfulness_gaps(lens_text):
    """Which parts of the faithfulness clause `lens_text` never states,
    read with its whitespace collapsed so a wrapped sentence matches."""
    flat = re.sub(r"\s+", " ", lens_text)
    return sorted(
        name
        for name, phrases in _FAITHFULNESS_CLAUSE.items()
        if not all(phrase in flat for phrase in phrases)
    )


class CopyFaithfulnessClauseTest(unittest.TestCase):
    """§8 sends every can-fail demonstration to a copy built beside the
    tree and says nothing about how one is built. An unproved copy is worse
    than none: an oracle that reads history answers from whatever the copy
    carries, and reports nothing when that is not the revision under test.
    So the recipe has to exist at the owner §8 names, and §8 has to name
    it -- a law whose method sits nowhere is a law no reader can run."""

    def test_the_lens_states_what_a_copy_preserves_and_how_that_is_evidenced(self):
        gaps = _faithfulness_gaps(LENS.read_text(encoding="utf-8"))
        self.assertEqual(
            [],
            gaps,
            "the cut lens states no faithfulness clause covering: "
            f"{', '.join(gaps)}",
        )

    def test_section_8_reaches_the_owner_in_one_hop(self):
        clause = _clause(VERIFICATION.read_text(encoding="utf-8"), 8)
        self.assertIn(
            "cut-lens.md",
            clause,
            "verification.md §8 requires a copy built beside the tree and "
            "names no owner of how one is built faithfully",
        )

    def test_a_lens_without_the_clause_fails_the_check(self):
        """The can-fail direction, built beside the tree and never by
        mutating it -- under the clause being read here: a copy of the lens
        with the recipe's section excised."""
        real = LENS.read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as tmp:
            beside = Path(tmp) / "cut-lens.md"
            beside.write_text(real, encoding="utf-8")
            self.assertEqual(
                [],
                _faithfulness_gaps(beside.read_text(encoding="utf-8")),
                "the copy must start with the clause intact, or the excision "
                "below is not what the check reacted to",
            )
            self.assertIn(_RECIPE_HEADING, real)
            beside.write_text(
                real[: real.index(_RECIPE_HEADING)],
                encoding="utf-8",
            )
            self.assertEqual(
                sorted(_FAITHFULNESS_CLAUSE),
                _faithfulness_gaps(beside.read_text(encoding="utf-8")),
            )


FRONTIER = ROOT / "skills" / "engines" / "orch-frontier" / "SKILL.md"
WORK_ITEM = CONTRACTS / "work-item.md"
CRITIQUE = ROOT / "skills" / "kernel" / "orch-critique" / "SKILL.md"
DECOMPOSE = ROOT / "skills" / "kernel" / "orch-decompose" / "SKILL.md"
INTEGRATE = ROOT / "skills" / "kernel" / "orch-integrate" / "SKILL.md"
SPEC = ROOT / "skills" / "workflows" / "orch-spec" / "SKILL.md"

# The cut is reviewed by an independent reader before any unit of it is
# dispatched, and `scripts/tickets.py` emits that reader's packet off a root
# ticket. A packet nothing dispatches is dead code: the engine that runs the
# graph has to hold the units back until the pass lands, and the contract has
# to say a root's cut is checked at all. Each owner is read for what only it
# can state -- the engine for what the units wait in, the contract for what
# the checker's authority is and is not.
_FRONTIER_CUT_CHECK = {
    "the units wait rather than promote": ("stay `pending`",),
    "the field whose absence holds them": ("`checked_by`",),
    "the check the cut's correction is accepted on": ("cutcheck",),
    # rules/verification.md §10 wants the checker's correction re-verified by
    # a further context; the cut check is deterministic, so the engine runs
    # it itself and dispatches no re-verifier for a root.
    "the context whose cut-check re-run is the re-verification": (
        "`cutcheck.py`", "re-verification",
    ),
    # A fresh reader over a two-unit cut with a clean cutcheck run reviews
    # what the script already graded; the size and the advisories are what
    # make a cut worth a context of its own.
    "the threshold that buys a cut a fresh reader": ("three or more", "advisory"),
}

_CONTRACT_CUT_CHECK = {
    "a root's cut is checked before its first unit": ("cut is checked", "first unit"),
    "the field that records the cut checker": ("`checked_by`", "cut checker"),
    "what the cut checker corrects, and what it does not": (
        "`tickets.py amend`", "run's workspace",
    ),
    "the threshold that buys a cut a fresh reader": ("three or more", "advisory"),
}

# The clauses as written, so the can-fail copies below read as their files did
# before them.
_FRONTIER_CLAUSE_RE = re.compile(
    r"A\s+root\s+cut\s+reader.*?cut\s+alone\.\s*", re.S
)
_CONTRACT_CLAUSE_RE = re.compile(r"A root's cut is checked.*?cut checker\.\s*", re.S)


def _clause_gaps(text, clause):
    """Which parts of `clause` `text` never states, read with its whitespace
    collapsed so a wrapped sentence matches."""
    flat = re.sub(r"\s+", " ", text)
    return sorted(
        name for name, phrases in clause.items()
        if not all(phrase in flat for phrase in phrases)
    )


def _section(text, heading):
    """One `## `-delimited section of a markdown file, so a phrase landing in
    a neighbouring section cannot satisfy an assertion scoped to this one."""
    match = re.search(
        rf"(?ms)^## {re.escape(heading)}\s*$(.*?)(?=^## |\Z)", text
    )
    if match is None:
        raise AssertionError(f"no section '{heading}'")
    return match.group(1)


class CutCheckOrderingTest(unittest.TestCase):
    """One fresh reader reviews and corrects a cut before the cut is run --
    the call the old system made in one shot, placed where
    rules/verification.md §10 already puts one. `packet --executor
    orch-critique` emits its packet off a root ticket; these are the two
    clauses that make it reachable and bounded: the engine holding every
    `<id>.NN` at `pending` until the root's pass lands, and the contract
    stating that a root's cut is checked and over what."""

    def test_the_engine_holds_the_units_until_the_cut_is_checked(self):
        gaps = _clause_gaps(FRONTIER.read_text(encoding="utf-8"), _FRONTIER_CUT_CHECK)
        self.assertEqual(
            [],
            gaps,
            "orch-frontier's body states no cut-checker clause covering: "
            f"{', '.join(gaps)}",
        )

    def test_the_contract_gives_a_root_ticket_its_cut_checker(self):
        gaps = _clause_gaps(
            _section(WORK_ITEM.read_text(encoding="utf-8"), "Root ticket"),
            _CONTRACT_CUT_CHECK,
        )
        self.assertEqual(
            [],
            gaps,
            "contracts/work-item.md's Root ticket section states no "
            f"cut-checker clause covering: {', '.join(gaps)}",
        )

    def test_an_engine_and_a_contract_without_the_clause_fail_the_check(self):
        """The can-fail direction, built beside the tree and never by
        mutating it (rules/verification.md §8): copies of both owners with
        the clause excised, which is how each read before it."""
        for path, clause, pattern, reader in (
            (FRONTIER, _FRONTIER_CUT_CHECK, _FRONTIER_CLAUSE_RE, lambda t: t),
            (WORK_ITEM, _CONTRACT_CUT_CHECK, _CONTRACT_CLAUSE_RE,
             lambda t: _section(t, "Root ticket")),
        ):
            real = path.read_text(encoding="utf-8")
            with tempfile.TemporaryDirectory() as tmp:
                beside = Path(tmp) / path.name
                beside.write_text(real, encoding="utf-8")
                self.assertEqual(
                    [],
                    _clause_gaps(reader(beside.read_text(encoding="utf-8")), clause),
                    f"the {path.name} copy must start with the clause intact, "
                    "or the excision below is not what the check reacted to",
                )
                excised = re.sub(pattern, "", real, count=1)
                self.assertNotEqual(
                    real, excised,
                    f"the {path.name} excision matched nothing, so the "
                    "assertion below would prove nothing",
                )
                beside.write_text(excised, encoding="utf-8")
                self.assertEqual(
                    sorted(clause),
                    _clause_gaps(reader(beside.read_text(encoding="utf-8")), clause),
                )


# §10 sends the entries a checker invalidated to a further context. Run
# 20260816T191118Z-adhoc-skills-review spent one spawned child per ticket on
# that -- ~76k tokens and ~12 minutes each -- to re-run oracles that were
# deterministic to the last one and failed none of 13. A fresh context buys
# independence only where a verdict is rendered, and re-running a
# deterministic oracle renders none. So the rule has to name which context
# re-runs which oracle, and the engine has to dispatch on that split rather
# than on every checker pass.
_REVERIFICATION_SPLIT = {
    "the context that re-runs a deterministic invalidation": (
        "invalidated", "deterministic", "the join",
    ),
    "the one invalidation that still takes a fresh child": (
        "fresh child", "judged",
    ),
}

_FRONTIER_REVERIFICATION = {
    "the packet form kept for a judged oracle": (
        "`--executor orch-verify`", "judged",
    ),
    "what the engine re-runs itself, and at which identity": (
        "deterministic", "checked identity",
    ),
}

# The clauses as written, so the can-fail copies read as their files did
# before them.
_SPLIT_CLAUSE_RE = re.compile(
    r"—\s+where\s+every\s+invalidated.*?fresh\s+child", re.S
)
_FRONTIER_SPLIT_RE = re.compile(
    r"(?:;\s+then,|\.\s+Then,)\s+where\s+its\s+pass.*?§10\)\.", re.S
)


# Sixteen repair tickets in the same run each ran the whole required-check
# set 4-6 times, twelve lanes deep on one host, and the tip they merged to
# was red anyway on a seam no lane's copy could see. Per-lane suite runs buy
# nothing the integrated tip does not decide, so the engine runs that set
# once per merge batch and a lane runs only what its own ticket names.
_FRONTIER_TIP_CHECK = {
    "what one lane is dispatched to run": (
        "oracles", "nothing wider",
    ),
    "whose checks run at the tip, and how often": (
        "standards owner", "each merge batch",
    ),
    "the revision they run on": ("integrated tip",),
    "where that revision is recorded": ("tip's revision", "run's notes"),
    "what a red tip costs, and what a lane's green is worth before it": (
        "red tip", "next dispatch", "provisional",
    ),
}

_TIP_CLAUSE_RE = re.compile(r"After\s+each\s+merge\s+batch.*?its\s+repair's\.", re.S)


class TipCheckTest(unittest.TestCase):
    """A lane grades its own ticket; only the merged tip carries the seam
    between lanes. The engine owns the tip, so the engine owns the check on
    it -- and owning it is what lets a lane stop paying for it."""

    def test_the_engine_runs_the_required_checks_once_on_the_tip(self):
        gaps = _clause_gaps(FRONTIER.read_text(encoding="utf-8"), _FRONTIER_TIP_CHECK)
        self.assertEqual(
            [],
            gaps,
            "orch-frontier's body states no tip-check clause covering: "
            f"{', '.join(gaps)}",
        )

    def test_an_engine_without_the_clause_fails_the_check(self):
        """The can-fail direction, built beside the tree and never by
        mutating it (rules/verification.md §8): a copy of the engine with
        the tip clause excised, which is how it read before."""
        real = FRONTIER.read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as tmp:
            beside = Path(tmp) / FRONTIER.name
            beside.write_text(real, encoding="utf-8")
            self.assertEqual(
                [],
                _clause_gaps(beside.read_text(encoding="utf-8"), _FRONTIER_TIP_CHECK),
                "the copy must start with the clause intact, or the excision "
                "below is not what the check reacted to",
            )
            excised = re.sub(_TIP_CLAUSE_RE, "", real, count=1)
            self.assertNotEqual(
                real, excised,
                "the excision matched nothing, so the assertion below would "
                "prove nothing",
            )
            beside.write_text(excised, encoding="utf-8")
            self.assertEqual(
                sorted(_FRONTIER_TIP_CHECK),
                _clause_gaps(beside.read_text(encoding="utf-8"), _FRONTIER_TIP_CHECK),
            )


class ReverificationSplitTest(unittest.TestCase):
    """Independence is a property of the context that renders a verdict, not
    a headcount. §10 owns which context re-verifies an invalidated entry;
    orch-frontier owns the dispatch that follows from it. Both are read,
    because a rule no engine acts on costs a child per ticket anyway."""

    def test_the_rule_names_a_context_per_oracle_class(self):
        gaps = _clause_gaps(
            _clause(VERIFICATION.read_text(encoding="utf-8"), 10),
            _REVERIFICATION_SPLIT,
        )
        self.assertEqual(
            [],
            gaps,
            "rules/verification.md §10 states no re-verification split "
            f"covering: {', '.join(gaps)}",
        )

    def test_the_engine_dispatches_a_child_only_for_a_judged_oracle(self):
        gaps = _clause_gaps(
            FRONTIER.read_text(encoding="utf-8"), _FRONTIER_REVERIFICATION
        )
        self.assertEqual(
            [],
            gaps,
            "orch-frontier's checker path states no re-verification split "
            f"covering: {', '.join(gaps)}",
        )

    def test_workflows_carry_successor_runs_selected_independence_and_single_gate(self):
        """Every skill that can select, dispatch, review, or join the path
        carries the same guardrail; no workflow may silently reconstruct the
        older checker-plus-gate or second-root topology."""

        clauses = {
            "orch-spec": (
                SPEC,
                {
                    "successor intake": (
                        "successor run", "predecessor", "result identity",
                        "resolved", "cited",
                    ),
                    "one physical root": ("never", "second root", "same run"),
                },
            ),
            "orch-decompose": (
                DECOMPOSE,
                {
                    "selected gate independence": (
                        "`independence: gate`", "all authored-here criteria",
                        "regardless of oracle class", "`independence: checker`",
                    ),
                    "single composite gate": (
                        "one composite gate", "unique lens", "one repair",
                        "one verification",
                    ),
                },
            ),
            "orch-frontier": (
                FRONTIER,
                {
                    "exclusive dispatch": (
                        "one outside-independence path", "checker packet",
                        "gate-deferred", "already checked", "never",
                    ),
                    "root exception": ("root cut reader", "exception"),
                },
            ),
            "orch-critique": (
                CRITIQUE,
                {
                    "checker refusal": ("Refuse", "non-root", "gate-deferred"),
                    "single checker": ("single immutable", "`checked_by`"),
                    "additional review": (
                        "unique named", "root-gate critique lens",
                    ),
                },
            ),
            "orch-integrate": (
                INTEGRATE,
                {
                    "contradiction refusal": (
                        "reject", "non-root", "`independence: gate`",
                        "`checked_by`",
                    ),
                    "one path": ("one outside-independence path",),
                },
            ),
        }
        gaps = []
        for owner, (path, required) in clauses.items():
            for gap in _clause_gaps(path.read_text(encoding="utf-8"), required):
                gaps.append(f"{owner}: {gap}")
        self.assertEqual(
            [], gaps,
            "workflow owners do not carry the verification split: "
            + ", ".join(gaps),
        )

    def test_a_rule_and_an_engine_without_the_split_fail_the_check(self):
        """The can-fail direction, built beside the tree and never by
        mutating it (rules/verification.md §8): copies of both owners with
        the split excised, which is how each read before it."""
        for path, clause, pattern, reader in (
            (VERIFICATION, _REVERIFICATION_SPLIT, _SPLIT_CLAUSE_RE,
             lambda t: _clause(t, 10)),
            (FRONTIER, _FRONTIER_REVERIFICATION, _FRONTIER_SPLIT_RE, lambda t: t),
        ):
            real = path.read_text(encoding="utf-8")
            with tempfile.TemporaryDirectory() as tmp:
                beside = Path(tmp) / path.name
                beside.write_text(real, encoding="utf-8")
                self.assertEqual(
                    [],
                    _clause_gaps(reader(beside.read_text(encoding="utf-8")), clause),
                    f"the {path.name} copy must start with the split intact, "
                    "or the excision below is not what the check reacted to",
                )
                excised = re.sub(pattern, "", real, count=1)
                self.assertNotEqual(
                    real, excised,
                    f"the {path.name} excision matched nothing, so the "
                    "assertion below would prove nothing",
                )
                beside.write_text(excised, encoding="utf-8")
                self.assertEqual(
                    sorted(clause),
                    _clause_gaps(reader(beside.read_text(encoding="utf-8")), clause),
                )


IMPROVEMENT = ROOT / "rules" / "improvement.md"
HOST_BLOCK = ROOT / "templates" / "host-block.md"

# What the fallback clause has to state, keyed to the refusal that named
# it: the isolation guard refuses writes to any git worktree including the
# main root, and the fallback the host block spells names a path inside the
# repository -- so a destination stated only as repository-internal is no
# destination under the one dispatch that forces the fallback. The host
# block owns the fallback (rules/improvement.md §1 points at it), so the
# block is where the destination is read.
_FALLBACK_DESTINATION = {
    "the refusal the fallback has to survive": ("refusal", "git worktree"),
    "a destination reachable under it": ("outside every worktree", "dispatch permits"),
    "how the entry gets back": ("the return", "collect"),
}

# §1 names the route once and delegates its spelling to the host block. A
# fix that answers a missing destination with a new tool shows up either as
# a second mechanism named here, or as a command or path spelled here.
#
# The route is read by name, never by the sentence carrying it: every
# `<word> logger` in the clause, less the determiners that are not names.
_LOGGER_NAME = re.compile(r"\b([a-z]+) logger\b")
_DETERMINERS = frozenset(
    {"the", "a", "an", "its", "this", "that", "one", "same", "installed"}
)
_SECOND_ROUTE = re.compile(
    r"\b(?:second|third|another|alternative|additional|backup|fallback)\s+"
    r"(?:friction\s+)?(?:logger|tool|script|command)\b"
)
_SPELLED_COMMAND_OR_PATH = re.compile(r"`[^`]*(?:\.py\b|/)[^`]*`")

# The clause the block gained, matched as written so the can-fail copy
# below reads as the block did before it: one destination, and no word on
# where the fallback writes when the refusal covers the worktree itself.
_DESTINATION_CLAUSE_RE = re.compile(
    r" Where the refusal covers writing inside a git worktree,.*?collect it\.",
    re.S,
)

_SECOND_ROUTE_SPLICE = (
    "When the logger cannot run, a second logger at "
    "`scripts/friction_fallback.py` takes the entry. "
)


def _fallback_destination_gaps(host_block_text):
    """Which parts of the fallback-destination clause the host block never
    states. Read from the block, the fallback's one owner: rules/
    improvement.md §1 states the law and points here for the route and the
    destination both, so a gap here is a gap everywhere."""
    return sorted(
        name
        for name, phrases in _FALLBACK_DESTINATION.items()
        if not all(phrase in host_block_text for phrase in phrases)
    )


def _logger_names(improvement_text):
    """Every logger clause 1 names, by name: `friction` for the one installed
    logger, and any second name a fix spliced in beside it."""
    clause = _clause(improvement_text, 1)
    return sorted(
        {
            name
            for name in _LOGGER_NAME.findall(clause)
            if name not in _DETERMINERS
        }
    )


def _routes_beyond_the_one(improvement_text):
    """Everything in clause 1 that names a logging route other than the one
    installed logger: a second mechanism by name, or a command or path
    spelled where §1 delegates the spelling to the host block."""
    clause = _clause(improvement_text, 1)
    return sorted(
        _SECOND_ROUTE.findall(clause) + _SPELLED_COMMAND_OR_PATH.findall(clause)
    )


class FrictionDestinationTest(unittest.TestCase):
    """The fallback exists for the dispatch that refuses the logger, and the
    refusal observed on this host covers writing inside any git worktree
    including the main root. A fallback whose only destination sits inside
    the repository has none exactly when it is reached for."""

    def test_the_block_states_a_destination_that_survives_the_refusal(self):
        gaps = _fallback_destination_gaps(HOST_BLOCK.read_text(encoding="utf-8"))
        self.assertEqual(
            [],
            gaps,
            "templates/host-block.md states no fallback destination covering: "
            f"{', '.join(gaps)}",
        )

    def test_section_one_still_names_exactly_one_primary_route(self):
        self.assertEqual(
            ["friction"],
            _logger_names(IMPROVEMENT.read_text(encoding="utf-8")),
            "§1 names one primary route, the installed friction logger; the "
            "destination gap is not answered by a second one",
        )
        extra = _routes_beyond_the_one(IMPROVEMENT.read_text(encoding="utf-8"))
        self.assertEqual(
            [],
            extra,
            "§1 delegates the command's spelling to the host block and adds "
            f"no route of its own; it names: {', '.join(extra)}",
        )

    def test_a_block_without_the_destination_fails_the_check(self):
        """The can-fail direction, built beside the tree and never by
        mutating it (rules/verification.md §8): a copy of the host block
        carrying the fallback paragraph as it read before this clause. The
        copy carries no history because the check reads block text and
        nothing else."""
        real = HOST_BLOCK.read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as tmp:
            beside = Path(tmp) / "host-block.md"
            beside.write_text(real, encoding="utf-8")
            self.assertEqual(
                [],
                _fallback_destination_gaps(beside.read_text(encoding="utf-8")),
                "the copy must start with the clause intact, or the excision "
                "below is not what the check reacted to",
            )
            excised = re.sub(_DESTINATION_CLAUSE_RE, "", real, count=1)
            self.assertNotEqual(
                real, excised,
                "the excision matched nothing, so the assertion below would "
                "prove nothing",
            )
            beside.write_text(excised, encoding="utf-8")
            self.assertEqual(
                sorted(_FALLBACK_DESTINATION),
                _fallback_destination_gaps(beside.read_text(encoding="utf-8")),
            )

    def test_a_section_one_answering_the_gap_with_a_tool_fails_the_check(self):
        """The can-fail direction for the route count: a copy whose §1
        answers the missing destination the way the ticket forbids -- with a
        second logger, spelled."""
        real = IMPROVEMENT.read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as tmp:
            beside = Path(tmp) / "improvement.md"
            beside.write_text(real, encoding="utf-8")
            self.assertEqual(
                [],
                _routes_beyond_the_one(beside.read_text(encoding="utf-8")),
                "the copy must start with one route, or the splice below is "
                "not what the check reacted to",
            )
            # Spliced at the clause marker, never at a sentence of §1: the
            # marker is what `_clause` reads, so no reword of §1 moves it.
            spliced = real.replace("\n1. ", "\n1. " + _SECOND_ROUTE_SPLICE, 1)
            self.assertNotEqual(
                real, spliced,
                "the splice matched nothing, so the assertion below would "
                "prove nothing",
            )
            beside.write_text(spliced, encoding="utf-8")
            self.assertEqual(
                ["`scripts/friction_fallback.py`", "second logger"],
                _routes_beyond_the_one(beside.read_text(encoding="utf-8")),
            )


if __name__ == "__main__":
    unittest.main()
