"""validate_sync (spec criterion 3): every literal copy checked against
its owner -- BODY_BUDGET and the description-char budget in
tools/validate.py against rules/composition.md §5; ENVELOPE_UNITS
against contracts/result.md's Binding paragraph; the friction-category
lists and the friction-completion clause in templates/host-block.md
and AGENTS.md against rules/improvement.md rule 1's closed set and
sentence. Follows tests/test_carriage.py's
isolated-tmp-tree-plus-subprocess idiom, scoped to the owner/copy
files this check reads (no skills/packs tree -- validate_sync does not
discover packages).

Also holds the one literal copy that is not validate.py's: scripts/
tickets.py's PACK_WORKSPACE_MECHANISMS against the packs' own workspace
cells. That copy exists because an installed tickets.py has no library
tree to read; nothing else then notices when a cell and the table move
apart, which is what this module is for."""
import ast
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import scripts.tickets as tickets_mod  # noqa: E402

VALIDATE = ROOT / "tools" / "validate.py"
CONTRACTS = ROOT / "contracts"
RULES = ROOT / "rules"
TEMPLATES = ROOT / "templates"


class _IsolatedSyncTree(unittest.TestCase):
    """A synthetic repo tree carrying only what validate_sync and pin
    checking read: contracts/ (for pins), rules/composition.md +
    rules/improvement.md (owners), templates/host-block.md + AGENTS.md
    (copies), and tools/validate.py itself. No skills/ or packs/ tree,
    so every other package-discovery check trivially passes."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmp.name)
        shutil.copytree(CONTRACTS, self.tmp_path / "contracts")
        (self.tmp_path / "rules").mkdir()
        shutil.copy(RULES / "composition.md", self.tmp_path / "rules" / "composition.md")
        shutil.copy(RULES / "improvement.md", self.tmp_path / "rules" / "improvement.md")
        (self.tmp_path / "templates").mkdir()
        shutil.copy(TEMPLATES / "host-block.md", self.tmp_path / "templates" / "host-block.md")
        shutil.copy(ROOT / "AGENTS.md", self.tmp_path / "AGENTS.md")
        (self.tmp_path / "tools").mkdir()
        self.validate_copy = self.tmp_path / "tools" / "validate.py"
        shutil.copy(VALIDATE, self.validate_copy)
        self._run("--pin")  # matching pins so only seeded mismatches can fail

    def tearDown(self):
        self.tmp.cleanup()

    def _run(self, *args):
        return subprocess.run(
            [sys.executable, str(self.validate_copy), *args],
            capture_output=True,
            text=True,
        )

    def _mutate(self, rel_path: str, old: str, new: str):
        path = self.tmp_path / rel_path
        text = path.read_text(encoding="utf-8")
        self.assertIn(old, text, f"fixture assumption stale: {old!r} not found in {rel_path}")
        path.write_text(text.replace(old, new, 1), encoding="utf-8")


class TestSyncCleanCopyPasses(_IsolatedSyncTree):
    def test_unmutated_copies_pass(self):
        result = self._run()
        self.assertEqual(0, result.returncode, result.stdout)
        self.assertNotIn("out of sync", result.stdout)


class TestSyncBudgetMutation(_IsolatedSyncTree):
    def test_mutated_body_budget_is_flagged(self):
        self._mutate("tools/validate.py", '"kernel": 25,', '"kernel": 99,')
        result = self._run()
        self.assertEqual(1, result.returncode, result.stdout)
        self.assertIn("BODY_BUDGET", result.stdout)
        self.assertIn("composition.md", result.stdout)

    def test_mutated_description_budget_is_flagged(self):
        self._mutate("tools/validate.py", "DESCRIPTION_BUDGET = 140", "DESCRIPTION_BUDGET = 99")
        result = self._run()
        self.assertEqual(1, result.returncode, result.stdout)
        self.assertIn("DESCRIPTION_BUDGET", result.stdout)
        self.assertIn("composition.md", result.stdout)


class TestSyncEnvelopeUnitsMutation(_IsolatedSyncTree):
    def test_mutated_envelope_units_is_flagged(self):
        self._mutate(
            "tools/validate.py",
            '    "orch-frontier",\n)',
            '    "orch-frontier",\n    "orch-extra",\n)',
        )
        result = self._run()
        self.assertEqual(1, result.returncode, result.stdout)
        self.assertIn("ENVELOPE_UNITS", result.stdout)
        self.assertIn("result.md", result.stdout)


class TestSyncFrictionCategoryMutation(_IsolatedSyncTree):
    def test_mutated_host_block_category_is_flagged(self):
        self._mutate("templates/host-block.md", "misrouting", "widgetrouting")
        result = self._run()
        self.assertEqual(1, result.returncode, result.stdout)
        self.assertIn("host-block.md", result.stdout)
        self.assertIn("out of sync", result.stdout)

    def test_mutated_agents_md_category_is_flagged(self):
        self._mutate("AGENTS.md", "misrouting", "widgetrouting")
        result = self._run()
        self.assertEqual(1, result.returncode, result.stdout)
        self.assertIn("AGENTS.md", result.stdout)
        self.assertIn("out of sync", result.stdout)


class TestSyncFrictionClauseMutation(_IsolatedSyncTree):
    def test_mutated_host_block_clause_is_flagged(self):
        self._mutate("templates/host-block.md", "silently", "quietly")
        result = self._run()
        self.assertEqual(1, result.returncode, result.stdout)
        self.assertIn("host-block.md", result.stdout)
        self.assertIn("out of sync", result.stdout)
        self.assertIn("friction-completion clause", result.stdout)

    def test_mutated_agents_md_clause_is_flagged(self):
        self._mutate("AGENTS.md", "silently", "quietly")
        result = self._run()
        self.assertEqual(1, result.returncode, result.stdout)
        self.assertIn("AGENTS.md", result.stdout)
        self.assertIn("out of sync", result.stdout)
        self.assertIn("friction-completion clause", result.stdout)


class TestSyncAbsentOwnersIsInert(unittest.TestCase):
    """Other isolated fixtures in this suite (test_carriage.py,
    test_validator.py) copy only contracts/ + tools/validate.py -- no
    rules/, templates/, or AGENTS.md. validate_sync must stay inert
    (never crash, never false-flag) when its owner files are absent,
    or every one of those pre-existing fixtures breaks."""

    def test_missing_owner_files_do_not_crash_or_flag(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            shutil.copytree(CONTRACTS, tmp_path / "contracts")
            (tmp_path / "tools").mkdir()
            shutil.copy(VALIDATE, tmp_path / "tools" / "validate.py")
            subprocess.run(
                [sys.executable, str(tmp_path / "tools" / "validate.py"), "--pin"],
                capture_output=True, text=True,
            )
            result = subprocess.run(
                [sys.executable, str(tmp_path / "tools" / "validate.py")],
                capture_output=True, text=True,
            )
            self.assertEqual(0, result.returncode, result.stdout)
            self.assertEqual("", result.stderr.strip())


class TestSyncAgainstRepo(unittest.TestCase):
    """The real tree's owned copies (BODY_BUDGET/description budget,
    ENVELOPE_UNITS, friction categories) must already be in sync -- this
    ticket's fixed inputs assume so; covered by TestValidatorAgainstRepo's
    exit-0 assertion, this only guards the 'out of sync' message itself
    never appearing."""

    def test_real_tree_owned_copies_are_in_sync(self):
        result = subprocess.run(
            [sys.executable, str(VALIDATE)], capture_output=True, text=True
        )
        self.assertNotIn("out of sync", result.stdout)
        self.assertNotIn("BODY_BUDGET", result.stdout)
        self.assertNotIn("ENVELOPE_UNITS", result.stdout)


PACKS = ROOT / "packs"
TICKETS_PY = ROOT / "scripts" / "tickets.py"


def workspace_mechanism(skill_md: Path) -> str:
    """The mechanism a pack's `workspace` cell names: the text before that
    cell's first colon, which is where every pack states it."""

    for line in skill_md.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        parts = stripped.split("|", 3)
        if len(parts) < 4 or parts[1].strip() != "workspace":
            continue
        cell = parts[2].strip()
        head, sep, _ = cell.partition(":")
        if not sep:
            raise AssertionError(f"{skill_md}: workspace cell names no mechanism: {cell}")
        return head.strip()
    raise AssertionError(f"{skill_md}: no `workspace` row")


class TestPackWorkspaceTableAgainstPacks(unittest.TestCase):
    """scripts/tickets.py's PACK_WORKSPACE_MECHANISMS against its owners, the
    packs' own `workspace` cells. `packet` emits the establishment step only
    for a git mechanism, so a cell that changes mechanism without the table
    changing with it silently stops -- or starts -- stamping a lane."""

    def test_the_table_covers_exactly_the_packs_that_exist(self):
        packs = {path.name for path in PACKS.iterdir() if (path / "SKILL.md").is_file()}
        self.assertEqual(packs, set(tickets_mod.PACK_WORKSPACE_MECHANISMS))

    def test_every_entry_matches_its_cell(self):
        for pack, mechanism in sorted(tickets_mod.PACK_WORKSPACE_MECHANISMS.items()):
            self.assertEqual(
                mechanism,
                workspace_mechanism(PACKS / pack / "SKILL.md"),
                f"{pack}: table and workspace cell disagree",
            )

    def test_the_git_set_names_only_mechanisms_the_cells_name(self):
        named = set(tickets_mod.PACK_WORKSPACE_MECHANISMS.values())
        self.assertLessEqual(set(tickets_mod.GIT_WORKSPACE_MECHANISMS), named)

    def test_the_table_is_a_literal_not_a_read_of_the_tree(self):
        """Without this the two checks above are vacuous: a table computed
        from `packs/` matches `packs/` by construction, and the installed
        script that has no `packs/` is the one that breaks."""

        tree = ast.parse(TICKETS_PY.read_text(encoding="utf-8"))
        found = [
            node.value
            for node in tree.body
            if isinstance(node, ast.Assign)
            and any(
                isinstance(target, ast.Name)
                and target.id == "PACK_WORKSPACE_MECHANISMS"
                for target in node.targets
            )
        ]
        self.assertEqual(1, len(found), "expected one module-level assignment")
        self.assertIsInstance(found[0], ast.Dict)
        for node in [*found[0].keys, *found[0].values]:
            self.assertIsInstance(node, ast.Constant, ast.dump(node))


if __name__ == "__main__":
    unittest.main()
