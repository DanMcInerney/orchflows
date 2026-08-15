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
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import scripts.friction as friction_mod  # noqa: E402
import scripts.state_root as state_root  # noqa: E402  the sink resolver's one owner
import scripts.tickets as tickets_mod  # noqa: E402
from tests.tree_removal import remove_repo_tree  # noqa: E402  the removal's one owner

VALIDATE = ROOT / "tools" / "validate.py"
CONTRACTS = ROOT / "contracts"
RULES = ROOT / "rules"
TEMPLATES = ROOT / "templates"


_TEMPLATE_HOLDER = None
_TEMPLATE = None


def setUpModule():
    """Build the isolated tree once, pinned, and copy it per test.

    Building it in every setUp paid `validate.py --pin` -- a subprocess --
    nine times for a tree whose bytes never differ. A filesystem copy of the
    finished template costs a fraction of that and still hands each test a
    private tree it is free to mutate.
    """

    global _TEMPLATE_HOLDER, _TEMPLATE
    _TEMPLATE_HOLDER = tempfile.TemporaryDirectory(prefix="sync-template-")
    _TEMPLATE = Path(_TEMPLATE_HOLDER.name) / "tree"
    _TEMPLATE.mkdir()
    shutil.copytree(CONTRACTS, _TEMPLATE / "contracts")
    (_TEMPLATE / "rules").mkdir()
    shutil.copy(RULES / "composition.md", _TEMPLATE / "rules" / "composition.md")
    shutil.copy(RULES / "improvement.md", _TEMPLATE / "rules" / "improvement.md")
    (_TEMPLATE / "templates").mkdir()
    shutil.copy(TEMPLATES / "host-block.md", _TEMPLATE / "templates" / "host-block.md")
    shutil.copy(ROOT / "AGENTS.md", _TEMPLATE / "AGENTS.md")
    (_TEMPLATE / "tools").mkdir()
    shutil.copy(VALIDATE, _TEMPLATE / "tools" / "validate.py")
    subprocess.run(  # matching pins so only seeded mismatches can fail
        [sys.executable, str(_TEMPLATE / "tools" / "validate.py"), "--pin"],
        capture_output=True,
        text=True,
    )


def tearDownModule():
    _TEMPLATE_HOLDER.cleanup()


_REAL_TREE_RUN = None


def validate_the_real_tree():
    """One `validate.py` run over this repository, shared by every case that
    reads it. Nothing here mutates the tree, so a second run can only return
    the first one's answer half a second later."""

    global _REAL_TREE_RUN
    if _REAL_TREE_RUN is None:
        _REAL_TREE_RUN = subprocess.run(
            [sys.executable, str(VALIDATE)], capture_output=True, text=True
        )
    return _REAL_TREE_RUN


def warning_lines(stdout: str):
    return [line for line in stdout.splitlines() if line.startswith("WARN")]


class _IsolatedSyncTree(unittest.TestCase):
    """A synthetic repo tree carrying only what validate_sync and pin
    checking read: contracts/ (for pins), rules/composition.md +
    rules/improvement.md (owners), templates/host-block.md + AGENTS.md
    (copies), and tools/validate.py itself. No skills/ or packs/ tree,
    so every other package-discovery check trivially passes."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmp.name) / "tree"
        shutil.copytree(_TEMPLATE, self.tmp_path)
        self.validate_copy = self.tmp_path / "tools" / "validate.py"

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
        result = validate_the_real_tree()
        # The returncode first: without it a validate.py that crashed before
        # printing anything satisfies all three assertNotIns below.
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
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


VOCABULARY = ROOT / "docs" / "vocabulary.md"
AGENTS_MD = ROOT / "AGENTS.md"
HOST_BLOCK = TEMPLATES / "host-block.md"
TERM_ENTRY_RE = re.compile(r"^- \*\*friction log\*\*.*?(?=\n- \*\*|\Z)", re.MULTILINE | re.DOTALL)
BLOCKED_CASE_RE = re.compile(r"Whenever the logger cannot run.*?never skip the log\.")


def _collapse(text: str) -> str:
    return re.sub(r"\s+", " ", text)


class FrictionLocationSyncTest(unittest.TestCase):
    """The friction log's one location, resolved by scripts/state_root.py's
    `friction_root`, against every copy of it: docs/vocabulary.md's
    **friction log** term names the sink tree, and so does the
    blocked-case sentence in templates/host-block.md and AGENTS.md --
    rules/improvement.md §1 sends a write its refusal blocks inside a
    worktree outside every worktree, which the sink is, and
    rules/visibility.md §6 leaves no hand-written file under `.orch/`.
    The expectation is derived by running the owner, never restated here."""

    IN_REPOSITORY = ".orch/"

    @staticmethod
    def _resolved_tree():
        """The sink tree the log lands in, spelled as a copy spells it,
        from the logger's own resolver run against a scratch sink: the
        root is user-scope and identical from anywhere, so what a copy
        can name -- and what this compares -- is the tree under it."""

        stamp = datetime(2026, 1, 1, tzinfo=timezone.utc)
        with tempfile.TemporaryDirectory(prefix="friction-sink-") as sink:
            with mock.patch.dict(os.environ, {state_root.ENV_VAR: sink}):
                landed = friction_mod._target_path(stamp).parent
                return landed.relative_to(state_root.state_root()).as_posix() + "/"

    def _blocked_case(self, path: Path) -> str:
        match = BLOCKED_CASE_RE.search(_collapse(path.read_text(encoding="utf-8")))
        self.assertIsNotNone(match, f"{path.name}: no blocked-case friction sentence to read")
        return match.group(0)

    def test_the_term_entry_names_the_location_the_logger_resolves(self):
        match = TERM_ENTRY_RE.search(VOCABULARY.read_text(encoding="utf-8"))
        self.assertIsNotNone(match, "docs/vocabulary.md: no **friction log** term entry")
        entry = _collapse(match.group(0))
        tree = self._resolved_tree()
        self.assertIn(tree, entry, f"the term owner does not name {tree}: {entry}")

    def test_both_copies_spell_the_blocked_case_destination(self):
        tree = self._resolved_tree()
        for path in (HOST_BLOCK, AGENTS_MD):
            with self.subTest(copy=path.name):
                sentence = self._blocked_case(path)
                self.assertIn(tree, sentence, f"{path.name}: blocked case does not spell {tree}")
                self.assertNotIn(
                    self.IN_REPOSITORY, sentence,
                    f"{path.name}: blocked case still sends the entry to {self.IN_REPOSITORY}",
                )

    # --- the two wrong-result readings (rules/verification.md §8) ------

    # Version control, runtime state, caches -- and the two data corpora
    # that hold 1275 of the tree's 1492 files while validate.py grades
    # neither: the copy reports the identical exit code and warning count
    # without them, and `test_the_copy_grades_what_the_tree_grades` is what
    # says so on every run.
    COPY_SKIPS = shutil.ignore_patterns(
        ".git", ".claude", ".orch", "__pycache__", "*.pyc", ".venv", ".mypy_cache",
        "benchmarks", "fixtures",
    )
    _copy = None
    _revisions = None
    _clean = None

    @classmethod
    def _wrong_result_tree(cls):
        """A copy beside the tree -- never the tree itself, which an
        interrupted seeding leaves mutated -- carrying the working-tree
        state of every file the check reads, so an uncommitted slice is what
        gets read.

        A `git clone` would carry the *committed* state and cost four
        seconds; this carries the working tree directly, which is what the
        clone's five-file overlay existed to reconstruct. Dropping `.git`
        costs nothing: validate.py runs no git (it contains no subprocess
        call at all), and the revision this reading is against is read off
        the tree the copy was taken from.
        """

        if cls._copy is None:
            scratch = Path(tempfile.mkdtemp(prefix="friction-locations-"))
            cls.addClassCleanup(setattr, cls, "_copy", None)
            cls.addClassCleanup(setattr, cls, "_clean", None)
            cls.addClassCleanup(remove_repo_tree, scratch)
            copy = scratch / "copy"
            shutil.copytree(ROOT, copy, ignore=cls.COPY_SKIPS, symlinks=True)
            cls._revisions = subprocess.run(
                ["git", "-C", str(ROOT), "rev-list", "--count", "HEAD"],
                capture_output=True, text=True, check=True,
            ).stdout.strip()
            cls._copy = copy
        return cls._copy

    def _reading(self, label: str) -> str:
        return f"{label} [working-tree copy, git rev-list --count {self._revisions}]"

    @staticmethod
    def _validate(root):
        return subprocess.run(
            [sys.executable, str(Path(root) / "tools" / "validate.py")],
            capture_output=True, text=True,
        )

    def _validate_in_copy(self):
        return self._validate(self._wrong_result_tree())

    def _seed(self, rel_path: str, old: str, new: str) -> None:
        path = self._wrong_result_tree() / rel_path
        text = path.read_text(encoding="utf-8")
        self.assertIn(old, text, self._reading(f"{rel_path}: seed assumption stale, {old!r} absent"))
        self.addCleanup(path.write_text, text, "utf-8")
        path.write_text(text.replace(old, new, 1), encoding="utf-8")

    def _assert_clean_first(self):
        """The unseeded reading, taken once and shared. It is the same tree
        in the same state for every case here, and it cost a full validate
        run per case to keep asking."""

        cls = type(self)
        if cls._clean is None:
            cls._clean = self._validate_in_copy()
        self.assertEqual(
            0, cls._clean.returncode,
            self._reading(f"unseeded copy must pass first: {cls._clean.stdout}"),
        )

    def test_the_copy_grades_what_the_tree_grades(self):
        """The copy leaves out benchmarks/ and tests/fixtures/. If validate.py
        ever grades either, the copy stops being a stand-in for the tree and
        every seeded reading above it is taken against something else."""

        self._assert_clean_first()
        tree = validate_the_real_tree()
        self.assertEqual(0, tree.returncode, tree.stdout)
        self.assertEqual(
            warning_lines(tree.stdout),
            warning_lines(self._clean.stdout),
            self._reading("the copy and the tree do not report the same findings"),
        )

    def test_a_copy_naming_the_repository_location_fails(self):
        tree = self._resolved_tree()
        inside = self.IN_REPOSITORY + tree
        self._assert_clean_first()
        # seeded inside the backticked path, which one line carries whole:
        # the prose around it wraps, and `_seed` reads the file unwrapped
        self._seed("AGENTS.md", "`" + tree, "`" + inside)
        seeded = self._validate_in_copy()
        self.assertEqual(1, seeded.returncode, self._reading(f"a blocked case naming {inside} must fail: {seeded.stdout}"))
        self.assertIn("AGENTS.md", seeded.stdout, self._reading(f"the drifted copy goes unnamed: {seeded.stdout}"))
        self.assertNotIn("host-block.md", seeded.stdout, self._reading(f"a copy that did not drift is named: {seeded.stdout}"))

    def test_the_location_is_read_from_its_owner(self):
        self._assert_clean_first()
        self._seed("scripts/state_root.py", '/ "friction"', '/ "friction-moved"')
        seeded = self._validate_in_copy()
        self.assertEqual(1, seeded.returncode, self._reading(f"a location changed in the owner alone must fail: {seeded.stdout}"))
        for copy_name in ("vocabulary.md", "host-block.md", "AGENTS.md"):
            with self.subTest(copy=copy_name):
                self.assertIn(copy_name, seeded.stdout, self._reading(f"{copy_name} still names the location the owner left: {seeded.stdout}"))


if __name__ == "__main__":
    unittest.main()
