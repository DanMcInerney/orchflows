"""Where a record lives, asserted against the files that state it.

Separate from ``tests/test_contracts.py``, which freezes the T0 contracts'
shape and the description budget every skill respects: nothing moved out of
that module. This one holds only the sink invariants — the path each
contract states, the work-item Location invariant's four conjuncts, and
``run.json``'s field list at its writer. Its second half holds the prose
invariants: the amended two-channel law, the one prose owner of the sink
path, and which ``.orch`` mentions may survive.

Its third half is ``tools/validate.py``'s two remaining owned-literal
checks and the cross-tier duplication check that replaced ``validate_sync``
(SPEC-ticket-set.md P2, REVIEW-2026-08-15 T2). ``tests/test_sync.py`` held
them until the sync check it was named for was deleted; what survived it —
``scripts/tickets.py``'s ``PACK_WORKSPACE_MECHANISMS`` against the packs'
own cells, and the friction log's one location against every copy of it —
lives here now, because a copy checked against its owner is the same
subject as a copy the compiler refuses outright.
"""
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
CONTRACTS = ROOT / "contracts"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import scripts.friction as friction_mod  # noqa: E402
import scripts.state_root as state_root  # noqa: E402  the sink resolver's one owner
import scripts.tickets as tickets_mod  # noqa: E402
import tools.validate as validate  # noqa: E402
from tests.tree_removal import remove_repo_tree  # noqa: E402  the removal's one owner

VALIDATE = ROOT / "tools" / "validate.py"
PACKS = ROOT / "packs"
TEMPLATES = ROOT / "templates"
TICKETS_PY = ROOT / "scripts" / "tickets.py"

# The one path each contract states for the record it owns. The resolver's
# rule and the environment variable's semantics stay with their owner,
# `scripts/state_root.py`; a contract states a sub-path under it and links.
SINK_PATHS = {
    "work-item.md": "`<state-root>/tickets/<run>/<id>.md`",
    "worklog.md": "`<state-root>/runs/<run>/worklog.md`",
    "composition.md": "`<state-root>/runs/<run>/composition.md`",
}

# The `.orch` references allowed to survive anywhere in `contracts/`.
# Enumerated, not counted: after the supersession no contract composes a
# run-state path from the repository, so the allow-list is empty.
ALLOWED_ORCH_REFERENCES = ()

# The work-item Location invariant, conjunct by conjunct. The fourth is what
# the supersession buys: before it, the invariant held only while the
# repository existed, because the path was inside it.
LOCATION_CONJUNCTS = (
    "identical from the orchestrator",
    "from every executor workspace",
    "after any workspace is removed",
    "after the repository is removed",
)

# Every field `run.json` carries, from the writer's own recorded shape
# (`scripts/tickets.py`). Its docstring may name these and no others, so
# statement and writer cannot drift in either direction.
RUN_JSON_FIELDS = frozenset({
    "run",
    "sink_convention",
    "opened_at",
    "project",
    "project.root",
    "project.origin",
    "project.name",
    "workspaces",
    "workspaces[].path",
    "workspaces[].first_seen",
})

RUN_JSON_MARKER = "``<sink>/runs/<run>/``"

HEADING = re.compile(r"^#{1,6} .*$", re.M)
BULLET = re.compile(r"^- (.*)$", re.M)
TOKEN = re.compile(r"`([^`]+)`")


def read(name):
    return (CONTRACTS / name).read_text(encoding="utf-8")


def flat(text):
    """Text with whitespace collapsed, so a wrapped clause matches as one."""

    return re.sub(r"\s+", " ", text)


def paragraph(name, needle):
    """The blank-line-delimited paragraph of ``name`` that carries ``needle``.

    Anchored to text rather than to a line number, so rewrapping a contract
    never silently moves what a case is reading.
    """

    for block in read(name).split("\n\n"):
        if needle in block:
            return flat(block).strip()
    return ""


def declared_shape(name):
    """A contract's headings and the field names its bullets declare."""

    text = read(name)
    tokens = []
    for line in BULLET.findall(text):
        tokens.extend(TOKEN.findall(line))
    return tuple(HEADING.findall(text)), tuple(tokens)


class TestWorkItemLocationInvariant(unittest.TestCase):
    """Spec A13: the invariant is strengthened, not weakened."""

    def setUp(self):
        self.clause = paragraph("work-item.md", "Location:")
        self.assertTrue(self.clause, "work-item.md carries no Location paragraph")

    def test_the_clause_carries_all_four_conjuncts(self):
        for conjunct in LOCATION_CONJUNCTS:
            self.assertIn(
                conjunct, self.clause,
                "the work-item Location invariant does not state {0!r}".format(conjunct),
            )

    def test_the_clause_states_exactly_one_path(self):
        paths = [t for t in TOKEN.findall(self.clause) if t.endswith(".md")]
        self.assertEqual(
            [SINK_PATHS["work-item.md"].strip("`")], paths,
            "the Location clause must state exactly one ticket path",
        )

    def test_the_one_path_survives_the_repository_it_was_cut_in(self):
        """The fourth conjunct holds only of a root outside every clone.

        So the clause has to say that, and has to name the owner that
        resolves it rather than restating the rule.
        """

        self.assertIn("outside every repository", self.clause)
        self.assertIn("`scripts/state_root.py`", self.clause)


class TestContractsNameTheSink(unittest.TestCase):
    """Spec A12's text half: all three contracts state a sink path."""

    def test_each_contract_states_its_sink_path(self):
        for name, path in SINK_PATHS.items():
            with self.subTest(contract=name):
                self.assertIn(
                    path, read(name),
                    "{0} does not state its record's path under the state root".format(name),
                )

    def test_no_contract_composes_a_run_state_path_from_the_repository(self):
        found = []
        for path in sorted(CONTRACTS.glob("*.md")):
            for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if ".orch" in line:
                    found.append("{0}:{1}: {2}".format(path.name, number, line.strip()))
        self.assertEqual(list(ALLOWED_ORCH_REFERENCES), found)


class TestWorklogStatesRunIdentity(unittest.TestCase):
    """`run.json`'s fields, stated by its one writer: the field list lives in
    scripts/tickets.py's module docstring (SPEC-ticket-set.md P2), and the
    docstring may name these fields and no others, so writer and statement
    cannot drift in either direction."""

    def block(self):
        text = (ROOT / "scripts" / "tickets.py").read_text(encoding="utf-8")
        docstring = text.split('"""', 2)[1]
        self.assertIn(RUN_JSON_MARKER, docstring, "tickets.py's docstring does not state run.json's path")
        return docstring.split(RUN_JSON_MARKER, 1)[1].replace("``", "`")

    def test_the_contract_names_every_field_run_json_carries(self):
        self.assertEqual(set(), RUN_JSON_FIELDS - set(TOKEN.findall(self.block())))

    def test_the_contract_names_no_field_run_json_does_not_carry(self):
        self.assertEqual(set(), set(TOKEN.findall(self.block())) - RUN_JSON_FIELDS)


# --- The prose half: the law and the documentation say what the code does ---

# The one file that states the sink root in prose. `scripts/state_root.py`
# owns it in code; every other markdown file links here rather than
# restating it (spec binding constraint 2, one owner per fact).
PATH_OWNER = "rules/visibility.md"

# What "states the path literally" means: either spelling of the root.
LITERAL_ROOT_TOKENS = ("~/.orchflows/state", "ORCHFLOWS_STATE_HOME")

# §6's load-bearing clauses, amended in place (spec binding constraint 1):
# only the root they point at changed. The spec paraphrases the last as "a
# write that cannot reach that root fails loudly"; §6's own words are pinned
# instead, because asserting the paraphrase would mean rewriting the very
# sentence the constraint preserves.
TWO_CHANNEL_CLAUSES = (
    "content is written with file tools inside the workspace",
    "run state is written only through the installed scripts",
    "There is no fallback",
    "a run-state write that cannot reach that root",
)

# What §6 must now say about the root, so the law names the sink and not a
# path inside some repository.
SINK_ROOT_CLAUSES = ("user-scope state sink",) + LITERAL_ROOT_TOKENS

# The two subdirectories a repository keeps, and nothing else (spec A15).
REPOSITORY_ORCH_SUBDIRECTORIES = frozenset({"canary/", "bin/"})

# Vocabulary terms whose definition names a location: each must resolve to
# the sink, since `docs/vocabulary.md` owns every library term of art and a
# term defined against the old place makes every correct use of it wrong.
SINK_TERMS = ("tracker", "friction log", "run state")

# The three files outside this item's `write_scope` that name `.orch`
# legitimately — the canary is a git-tracked golden fixture and `bin/` is an
# installed script directory, neither of them state. Their `.orch` lines are
# pinned as the bytes they carried at this item's `run_revision`.
CANARY_AND_BIN_LINES = {
    "compositions/drift-canary.md": (
        "`.orch/canary/`, spanning the kernel boundaries: one delegation, one",
    ),
    "skills/workflows/orch-fixture/SKILL.md": (
        "README line. Freeze into `.orch/canary/<name>/`: the spec excerpt the",
    ),
    "skills/kernel/orch-mechanize/SKILL.md": (
        "Write the script in stdlib Python 3, cross-platform, to `.orch/bin/` for",
    ),
}

# The one file carrying the friction-law fallback: the instruction a blocked
# agent follows when the logger cannot run. Stale, it loses evidence in
# silence rather than failing a check, so it has one owner and no copy --
# AGENTS.md pointed a second copy at the same tree until P3 deleted it, and
# `test_agents_md_carries_no_second_fallback_copy` keeps it deleted.
FALLBACK_FILES = ("templates/host-block.md",)
FALLBACK_NEEDLE = "friction/<yyyy-mm>.jsonl"

SELF_IMPROVE = "skills/workflows/orch-self-improve/SKILL.md"

# The writer item 10 returned, quoted from its `subcommand` field. Both
# improvement records reach the sink through it and through nothing else.
IMPROVEMENT_WRITER = (
    "scripts/tickets.py improvement --proposal",
    "scripts/tickets.py improvement --covered",
)

# Directories holding no owner: recorded data and a dated review record.
SKIPPED_DIRECTORIES = frozenset({"benchmarks"})
SKIPPED_PAIRS = frozenset({("tests", "fixtures")})
SKIPPED_FILES = frozenset({"REVIEW-2026-08-06.md"})

# A run-state directory reference, and not the installed library root:
# `~/.orchflows/` shares the first five characters and is not a mention.
ORCH_MENTION = re.compile(r"\.orch\b")


def doc(relpath):
    return (ROOT / relpath).read_text(encoding="utf-8")


def markdown_files():
    """Every markdown file a reader could take as an owner, path and text.

    Dot-directories are pruned during the walk, not filtered after it: they
    hold runtime state (`.orch/`) and host adapters (`.claude/`,
    `.orchflows/`), and one of them can contain a whole second checkout.
    """

    for base, dirnames, filenames in os.walk(str(ROOT)):
        rel_base = Path(base).relative_to(ROOT)
        dirnames[:] = [
            name for name in sorted(dirnames)
            if not name.startswith(".")
            and name not in SKIPPED_DIRECTORIES
            and (rel_base.parts + (name,))[:2] not in SKIPPED_PAIRS
        ]
        for filename in sorted(filenames):
            if not filename.endswith(".md") or filename in SKIPPED_FILES:
                continue
            rel = (rel_base / filename).as_posix()
            yield rel, doc(rel)


def enclosing_block(lines, index):
    """The bullet or paragraph carrying ``lines[index]``, whitespace collapsed.

    The unit is the bullet, not the paragraph: `ARCHITECTURE.md`'s list puts
    no blank line between items, so a paragraph there is the whole list.
    """

    start = index
    while start > 0:
        if lines[start].startswith(("- ", "* ")):
            break
        if not lines[start].strip():
            start += 1
            break
        start -= 1
    end = index + 1
    while end < len(lines):
        if not lines[end].strip() or lines[end].startswith(("- ", "* ")):
            break
        end += 1
    return flat(" ".join(lines[start:end])).strip()


def block_starting(relpath, marker):
    """The block of ``relpath`` whose first line starts with ``marker``."""

    lines = doc(relpath).splitlines()
    for index, line in enumerate(lines):
        if line.startswith(marker):
            return enclosing_block(lines, index)
    return ""


def block_carrying(relpath, needle):
    """The blank-line-delimited paragraph of ``relpath`` carrying ``needle``."""

    for block in doc(relpath).split("\n\n"):
        if needle in block:
            return flat(block).strip()
    return ""


def numbered_section(relpath, number):
    """One numbered rule, from its own number to the next one or the end."""

    text = doc(relpath)
    opening = re.search(r"^{0}\. ".format(number), text, re.M)
    if opening is None:
        return ""
    tail = text[opening.start():]
    following = re.search(r"^\d+\. ", tail[1:], re.M)
    return flat(tail if following is None else tail[: following.start() + 1]).strip()


class TestTwoChannelLawAmended(unittest.TestCase):
    """Spec binding constraint 1: §6 is amended in place, never replaced."""

    def setUp(self):
        self.section = numbered_section(PATH_OWNER, 6)
        self.assertTrue(self.section, "rules/visibility.md states no §6")

    def test_both_channels_and_the_no_fallback_clause_survive(self):
        for clause in TWO_CHANNEL_CLAUSES:
            with self.subTest(clause=clause):
                self.assertIn(
                    clause, self.section,
                    "§6 no longer carries {0!r}".format(clause),
                )

    def test_the_root_the_law_names_is_the_sink(self):
        for clause in SINK_ROOT_CLAUSES:
            with self.subTest(clause=clause):
                self.assertIn(
                    clause, self.section,
                    "§6 does not name the sink: {0!r} is missing".format(clause),
                )

    def test_the_law_no_longer_points_into_a_repository(self):
        self.assertIsNone(ORCH_MENTION.search(self.section))

    def test_the_law_names_the_resolver_rather_than_restating_its_rule(self):
        self.assertIn("`scripts/state_root.py`", self.section)


class TestRepositoryKeepsTwoSubdirectories(unittest.TestCase):
    """Spec A15: `.orch/` holds the canary and, project-scope, `bin/`."""

    def setUp(self):
        self.bullet = block_starting("ARCHITECTURE.md", "- `.orch/`")
        self.assertTrue(self.bullet, "ARCHITECTURE.md has no `.orch/` bullet")

    def test_the_bullet_names_canary_and_bin_and_no_third_subdirectory(self):
        named = {
            token for token in TOKEN.findall(self.bullet)
            if token.endswith("/") and token != ".orch/"
        }
        self.assertEqual(REPOSITORY_ORCH_SUBDIRECTORIES, named)

    def test_the_sink_has_its_own_bullet(self):
        bullet = block_starting("ARCHITECTURE.md", "- state sink")
        self.assertTrue(bullet, "ARCHITECTURE.md documents no state sink")
        self.assertIn("rules/visibility.md", bullet)


class TestVocabularyResolvesToTheSink(unittest.TestCase):
    """`docs/vocabulary.md` owns every term of art, locations included."""

    def test_each_located_term_resolves_to_the_sink(self):
        for term in SINK_TERMS:
            with self.subTest(term=term):
                entry = block_starting("docs/vocabulary.md", "- **{0}** —".format(term))
                self.assertTrue(entry, "vocabulary defines no {0!r}".format(term))
                self.assertIn("sink", entry)
                self.assertIsNone(ORCH_MENTION.search(entry))

    def test_the_sink_itself_is_a_term_pointing_at_its_owner(self):
        entry = block_starting("docs/vocabulary.md", "- **state sink** —")
        self.assertTrue(entry, "vocabulary defines no state sink")
        self.assertIn("rules/visibility.md", entry)


class TestOneProseOwnerForThePath(unittest.TestCase):
    """Spec binding constraint 2: one owner per fact, and it is §6."""

    def test_exactly_one_markdown_file_states_the_root_literally(self):
        stating = [
            relpath for relpath, text in markdown_files()
            if any(token in text for token in LITERAL_ROOT_TOKENS)
        ]
        self.assertEqual([PATH_OWNER], stating)


class TestSelfImproveSelectsByScopeAndProject(unittest.TestCase):
    """Spec A9: the sink holds every project, so selection is by field."""

    def setUp(self):
        self.text = doc(SELF_IMPROVE)

    def test_the_evidence_streams_resolve_to_the_sink(self):
        self.assertIn("improvement/covered.jsonl", self.text)
        self.assertIn("state sink", self.text)
        self.assertIsNone(ORCH_MENTION.search(self.text))

    def test_the_sink_it_mines_points_at_the_law_that_owns_it(self):
        """Every stream this cycle reads is agent-written. Naming the sink
        without §6 leaves the untrusted-data law to a reader who already
        knows it — the shape `TestFrictionFallbackNamesTheSink` holds the
        other agent-facing sink reference to."""

        block = block_carrying(SELF_IMPROVE, "state sink")
        self.assertTrue(block, "{0} names no state sink".format(SELF_IMPROVE))
        self.assertIn("visibility.md", block)
        self.assertIn("untrusted", block)

    def test_selection_is_by_project_field_and_cluster_scope(self):
        collapsed = flat(self.text)
        self.assertIn("`project` field", collapsed)
        self.assertIn("scope", collapsed)
        self.assertIn("never by the repository the session stands in", collapsed)

    def test_both_records_are_written_through_the_installed_writer(self):
        for invocation in IMPROVEMENT_WRITER:
            with self.subTest(invocation=invocation):
                self.assertIn(invocation, self.text)

    def test_the_coverage_record_is_named_once(self):
        self.assertEqual(1, self.text.count("covered.jsonl"))


class TestFrictionFallbackNamesTheSink(unittest.TestCase):
    """The one instruction whose staleness loses evidence in silence."""

    def test_a_blocked_agent_is_sent_to_the_sink_not_to_a_repository(self):
        for relpath in FALLBACK_FILES:
            with self.subTest(document=relpath):
                block = block_carrying(relpath, FALLBACK_NEEDLE)
                self.assertTrue(
                    block, "{0} states no friction fallback".format(relpath),
                )
                self.assertIn("state sink", block)
                self.assertIn("visibility.md", block)
                self.assertIsNone(ORCH_MENTION.search(block))


class TestOnlyCanaryAndBinMentionsSurvive(unittest.TestCase):
    """What may still say `.orch`: a golden fixture and an install target."""

    def test_the_out_of_scope_files_carry_their_run_revision_lines(self):
        for relpath, expected in CANARY_AND_BIN_LINES.items():
            with self.subTest(document=relpath):
                found = tuple(
                    line for line in doc(relpath).splitlines()
                    if ORCH_MENTION.search(line)
                )
                self.assertEqual(expected, found)

    def test_every_surviving_mention_names_canary_or_bin(self):
        stray = []
        for relpath, text in markdown_files():
            lines = text.splitlines()
            for index, line in enumerate(lines):
                if not ORCH_MENTION.search(line):
                    continue
                block = enclosing_block(lines, index)
                if "canary" not in block and "bin/" not in block:
                    stray.append("{0}:{1}: {2}".format(relpath, index + 1, line.strip()))
        self.assertEqual([], stray)


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
    rather than repairing it (SPEC-ticket-set.md §1, REVIEW-2026-08-15 T2).
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
    changing with it silently stops -- or starts -- stamping a lane. The one
    literal copy that was never validate.py's, and so outlives the check that
    was."""

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
    (SPEC-ticket-set.md §1, REVIEW-2026-08-15 T2).

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

    def test_two_files_in_one_tier_are_not_a_cross_tier_pair(self):
        """The check is about a fact with two owners in two places. Two
        skills sharing a clause is the skills tier's own business, and the
        pack linter already owns the same question inside packs."""

        self._write("Nothing here.", COPIED_SENTENCE + ".")
        self._write_skill("orch-mimic", COPIED_SENTENCE + ".")
        result, findings = self._findings()
        self.assertEqual([], findings, result.stdout)


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


if __name__ == "__main__":
    unittest.main()
