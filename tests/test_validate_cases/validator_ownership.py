"""Validator ownership and friction-location regression cases."""
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

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import scripts.friction as friction_mod  # noqa: E402
import scripts.state_root as state_root  # noqa: E402
import scripts.tickets as tickets_mod  # noqa: E402
import tools.validate as validate  # noqa: E402
from tests.tree_removal import remove_repo_tree  # noqa: E402

VALIDATE = ROOT / "tools" / "validate.py"
PACKS = ROOT / "packs"
TEMPLATES = ROOT / "templates"
TICKETS_PY = ROOT / "scripts" / "tickets.py"

# --- tools/validate.py: the checks that outlived validate_sync ---------


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


_REAL_TREE_RUN = None


def warning_lines(stdout: str):
    return [line for line in stdout.splitlines() if line.startswith("WARN")]


class TestSyncCheckIsGone(unittest.TestCase):
    """`validate_sync` kept two spellings of one literal equal to each other.
    P2 deletes it: a fact gets one owner and the compiler reports the copy
    rather than repairing it (REVIEW-2026-08-15 T2).
    Asserted on the module rather than on its output, because a check that
    stops running still passes every assertion about a clean tree."""

    def test_the_module_exposes_no_sync_check(self):
        with self.assertRaises(AttributeError):
            validate.validate_sync

    def test_no_sync_helper_survives_in_the_source(self):
        source = VALIDATE.read_text(encoding="utf-8")
        self.assertNotIn("validate_sync", source)
        self.assertNotIn("_sync_", source)

    def test_the_module_that_tested_it_is_gone_too(self):
        self.assertFalse((ROOT / "tests" / "test_sync.py").exists())


def workspace_adapter(skill_md: Path) -> str:
    """The registered adapter key declared by one pack's typed `adapter` leaf.

    Read independently of `tickets_adapters.declared_adapter` so the pack
    data and the parser cannot agree by sharing one implementation.
    """

    for line in skill_md.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        parts = stripped.split("|", 3)
        if len(parts) < 4 or parts[1].strip() != "adapter":
            continue
        key = parts[2].strip().strip("`").strip()
        if not key:
            raise AssertionError(f"{skill_md}: `adapter` leaf is empty")
        return key
    raise AssertionError(f"{skill_md}: no `adapter` row")


class TestPackWorkspaceTableAgainstPacks(unittest.TestCase):
    """Pack data selects only mechanisms the adapter registry implements."""

    def test_every_pack_declares_a_registered_adapter(self):
        declared = {
            workspace_adapter(path / "SKILL.md")
            for path in PACKS.iterdir() if (path / "SKILL.md").is_file()
        }
        self.assertLessEqual(declared, set(tickets_mod.ADAPTER_REGISTRY))

    def test_every_adapter_owns_the_properties_machinery_reads(self):
        for key, adapter in sorted(tickets_mod.ADAPTER_REGISTRY.items()):
            self.assertEqual(key, adapter.key)
            self.assertTrue(adapter.identity_form)
            self.assertIsInstance(adapter.establishes_isolation, bool)
            self.assertIsInstance(adapter.deterministic_gate, bool)
            self.assertTrue(adapter.conflict_semantics)
            self.assertIn(adapter.workspace_strategy, {"git", "evidence-store", "document-tree"})

    def test_no_pack_keyed_workspace_registry_survives(self):
        source = TICKETS_PY.read_text(encoding="utf-8")
        self.assertNotIn("ADAPTER_BY_PACK", source)
        self.assertNotIn("PACK_WORKSPACE_MECHANISMS", source)


class TestPackAdmissionIsDomainBlind(unittest.TestCase):
    def test_no_pack_to_executor_registry_survives(self):
        self.assertFalse(hasattr(tickets_mod, "PACK_EXECUTOR_BINDINGS"))
        for source in (
            ROOT / "scripts" / "tickets.py",
            ROOT / "scripts" / "tickets_format.py",
            ROOT / "scripts" / "tickets_admission.py",
        ):
            self.assertNotIn("PACK_EXECUTOR_BINDINGS", source.read_text(encoding="utf-8"))


class TestPackAdmissionRegistryAgainstPacks(unittest.TestCase):
    def cells(self, skill_md: Path):
        found = {}
        for line in skill_md.read_text(encoding="utf-8").splitlines():
            match = re.match(r"^\|\s*([a-z_]+)\s*\|\s*(.*?)\s*\|$", line)
            if match:
                found[match.group(1)] = match.group(2)
        return found

    def test_flat_signature_declares_only_registered_adapter_keys(self):
        packs = {path.name for path in PACKS.iterdir() if (path / "SKILL.md").is_file()}
        for pack in sorted(packs):
            cells = self.cells(PACKS / pack / "SKILL.md")
            self.assertNotIn("executor", cells, pack)
            self.assertNotIn("skill", cells, pack)
            self.assertIn(cells.get("adapter"), tickets_mod.ADAPTER_REGISTRY, pack)


CROSS_TIER = "cross-tier near-duplicate"

# One sentence long enough to be content by CELL_CLAUSE_MIN_WORDS, written
# so it carries no span MANDATED_FORM_RES strips: what is compared is the
# whole of it, and a fixture that matched a mandated form would be measuring
# the stripper instead of the check.
COPIED_SENTENCE = (
    "A claim reaches the record only when the check that decides it has "
    "already been shown to fail against a wrong result"
)
# The two forms the check must not read as content: a markdown link and a
# backticked skill name, each standing alone as its own clause. Neither
# opens with `](../`, so nothing here is exempt by the pack linter's
# outside-the-pack citation rule -- the exemption under test is the
# cross-tier one.
CITATION_ONLY = "[the work-item contract](contracts/work-item.md)"
NAME_ONLY = "`orch-mimic`"

RULE_MD = "# A rule\n\n{body}\n"
SKILL_MD = (
    "---\nname: {name}\ndescription: a synthetic skill standing in for a "
    "tier the cross-tier check reads\nrole: worker\n---\n"
    "Require: one ticket.\nNever: guess.\nReturn: the ticket.\n{body}\n"
)


class CrossTierDuplicationTest(unittest.TestCase):
    """One clause carried by two tiers is a fact with two owners, and the
    compiler reports it rather than holding the two spellings equal
    (REVIEW-2026-08-15 T2).

    Runs on the isolated tmp-tree harness tests/test_validator.py owns, so
    the seam exercised is the real ROOT-relative one, and the tree carries
    exactly the two files the case is about.
    """

    def setUp(self):
        from tests.test_validator import _IsolatedTree  # the harness's one owner

        self.harness = _IsolatedTree("run")
        self.harness.setUp()
        self.addCleanup(self.harness.doCleanups)
        self.tmp_path = self.harness.tmp_path

    def _write(self, rule_body: str, skill_body: str, name: str = "orch-echo"):
        rules = self.tmp_path / "rules"
        rules.mkdir(parents=True, exist_ok=True)
        (rules / "duplication.md").write_text(
            RULE_MD.format(body=rule_body), encoding="utf-8"
        )
        self._write_skill(name, skill_body)

    def _write_skill(self, name: str, body: str):
        skill = self.tmp_path / "skills" / "instances" / name
        skill.mkdir(parents=True, exist_ok=True)
        (skill / "SKILL.md").write_text(
            SKILL_MD.format(name=name, body=body), encoding="utf-8"
        )

    def _findings(self):
        result = self.harness._run()
        return result, [
            line for line in result.stdout.splitlines() if CROSS_TIER in line
        ]

    def test_a_rule_sentence_copied_into_a_skill_body_is_reported(self):
        self._write(COPIED_SENTENCE + ".", COPIED_SENTENCE + ".")
        result, findings = self._findings()
        self.assertEqual(1, len(findings), result.stdout)
        self.assertTrue(findings[0].startswith("WARN "), findings[0])
        self.assertIn("rules/duplication.md", findings[0])
        self.assertIn("skills/instances/orch-echo/SKILL.md", findings[0])
        self.assertIn("at 1.00", findings[0])
        self.assertEqual(0, result.returncode, result.stdout)

    def test_the_level_is_the_one_the_module_declares(self):
        """WARN is a phase, not a verdict: the tree carries the copies P3
        deletes. The constant is what P3 flips, so the level a finding is
        emitted at has to be read from it rather than hardcoded here."""

        self.assertEqual("WARN", validate.CROSS_TIER_DUPLICATE_LEVEL)

    def test_a_shared_link_and_a_shared_name_are_not_duplication(self):
        """Every tier cites the same contracts and names the same skills.
        A clause that is nothing but a citation or a name is the library's
        shared vocabulary; convicting it would drive files to stop
        pointing at their owners."""

        shared = f"- {CITATION_ONLY}\n- {NAME_ONLY}\n"
        self._write(shared, shared)
        self._write_skill("orch-mimic", "Nothing shared.")
        result, findings = self._findings()
        self.assertEqual([], findings, result.stdout)
        self.assertEqual(0, result.returncode, result.stdout)

    def test_two_skills_sharing_a_clause_are_reported_and_two_packs_are_not(self):
        """One tier's internal business is a second linter's — where there
        is one. Inside packs the pack linter already asks this question, and
        the cross-tier pass stays out. skills/ has no such check at all, so
        skipping same-tier pairs there meant two skill bodies could carry a
        clause byte for byte while each was flagged against an innocent third
        file in another tier: the one pair that mattered was the one pair
        nothing compared.
        """

        self._write("Nothing here.", COPIED_SENTENCE + ".")
        self._write_skill("orch-mimic", COPIED_SENTENCE + ".")
        result, findings = self._findings()
        self.assertEqual(1, len(findings), result.stdout)
        self.assertIn("skills/instances/orch-echo/SKILL.md", findings[0])
        self.assertIn("skills/instances/orch-mimic/SKILL.md", findings[0])
        self.assertIn("(within skills)", findings[0])
        self.assertEqual(("skills",), tuple(sorted(validate.SAME_TIER_COMPARED)))

    def test_two_packs_sharing_a_clause_stay_the_pack_linters(self):
        self._write("Nothing here.", "Nothing shared.")
        for name in ("orch-alpha-pack", "orch-beta-pack"):
            pack = self.tmp_path / "packs" / name
            pack.mkdir(parents=True, exist_ok=True)
            (pack / "SKILL.md").write_text(
                f"---\nname: {name}\ndescription: a synthetic pack\n---\n\n"
                f"| cell | binding |\n| --- | --- |\n| slicing | {COPIED_SENTENCE} |\n",
                encoding="utf-8",
            )
        result, findings = self._findings()
        self.assertEqual([], findings, result.stdout)


VOCABULARY = ROOT / "docs" / "vocabulary.md"
AGENTS_MD = ROOT / "AGENTS.md"
HOST_BLOCK = TEMPLATES / "host-block.md"
TERM_ENTRY_RE = re.compile(r"^- \*\*friction log\*\*.*?(?=\n- \*\*|\Z)", re.MULTILINE | re.DOTALL)
BLOCKED_CASE_RE = re.compile(r"If the logger cannot run.*?never skip (?:the log|it)\.")


def _collapse(text: str) -> str:
    return re.sub(r"\s+", " ", text)


class FrictionLocationSyncTest(unittest.TestCase):
    """The friction log's one location, resolved by scripts/state_root.py's
    `friction_root`, against every copy of it: docs/vocabulary.md's
    **friction log** term names the sink tree, and so does the
    blocked-case sentence in templates/host-block.md --
    rules/improvement.md §1 sends a write its refusal blocks inside a
    worktree outside every worktree, which the sink is, and
    rules/visibility.md §6 leaves no hand-written file under `.orch/`.
    The expectation is derived by running the owner, never restated here.

    AGENTS.md carries the same sentence and the validator no longer reads
    it: P3 deletes that copy, and until then the compiler reports it as a
    cross-tier duplicate rather than requiring it to stay word-perfect."""

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

    def test_the_checked_copy_spells_the_blocked_case_destination(self):
        tree = self._resolved_tree()
        sentence = self._blocked_case(HOST_BLOCK)
        self.assertIn(tree, sentence, f"host-block.md: blocked case does not spell {tree}")
        self.assertNotIn(
            self.IN_REPOSITORY, sentence,
            f"host-block.md: blocked case still sends the entry to {self.IN_REPOSITORY}",
        )

    # --- the two wrong-result readings (rules/verification.md §8) ------

    # Version control, runtime state, caches -- and `tests/fixtures`, the
    # corpus validate.py does not grade. `benchmarks` used to be skipped
    # beside it on the same reasoning, and that reasoning was wrong: it is
    # one of `LINKED_MD_ROOTS`, so a copy without it made
    # `validate_markdown_links` skip link resolution over the whole copy --
    # silently, until the check learned to say so. The copy carries it now,
    # and `test_the_copy_grades_what_the_tree_grades` is what says on every
    # run that the copy is still the tree's stand-in.
    COPY_SKIPS = shutil.ignore_patterns(
        ".git", ".claude", ".orch", "__pycache__", "*.pyc", ".venv", ".mypy_cache",
        "fixtures",
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
        """The copy leaves out tests/fixtures/ alone. If validate.py ever
        grades it, the copy stops being a stand-in for the tree and every
        seeded reading above it is taken against something else."""

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
        self._seed("templates/host-block.md", "`" + tree, "`" + inside)
        seeded = self._validate_in_copy()
        self.assertEqual(1, seeded.returncode, self._reading(f"a blocked case naming {inside} must fail: {seeded.stdout}"))
        self.assertIn("host-block.md", seeded.stdout, self._reading(f"the drifted copy goes unnamed: {seeded.stdout}"))

    def test_agents_md_carries_no_second_fallback_copy(self):
        """AGENTS.md carried the same blocked-case instruction until P3
        deleted it. A copy no check requires is a copy free to drift, so
        what is checkable now is that it stays gone: AGENTS.md names the
        owner and no tree of the sink."""

        self._assert_clean_first()
        agents = (self._wrong_result_tree() / "AGENTS.md").read_text(encoding="utf-8")
        self.assertNotIn(
            self._resolved_tree(), agents,
            self._reading("AGENTS.md names a sink tree again: one owner, no copy"),
        )
        self.assertIn(
            "templates/host-block.md", agents,
            self._reading("AGENTS.md points a blocked agent at no owner"),
        )

    def test_the_location_is_read_from_its_owner(self):
        self._assert_clean_first()
        self._seed("scripts/state_root.py", '/ "friction"', '/ "friction-moved"')
        seeded = self._validate_in_copy()
        self.assertEqual(1, seeded.returncode, self._reading(f"a location changed in the owner alone must fail: {seeded.stdout}"))
        for copy_name in ("vocabulary.md", "host-block.md"):
            with self.subTest(copy=copy_name):
                self.assertIn(copy_name, seeded.stdout, self._reading(f"{copy_name} still names the location the owner left: {seeded.stdout}"))
