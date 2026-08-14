"""Where a record lives, asserted against the files that state it.

Separate from ``tests/test_contracts.py``, which freezes the T0 contracts'
shape and the description budget every skill respects: nothing moved out of
that module. This one holds only the sink invariants — the path each
contract states, the work-item Location invariant's four conjuncts, and
``run.json``'s field list — so a location supersession is provably a
location change and not a shape change. Its second half holds the prose
invariants: the amended two-channel law, the one prose owner of the sink
path, and which ``.orch`` mentions may survive.
"""
import os
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTRACTS = ROOT / "contracts"

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
# (`scripts/tickets.py`, item 03's `run_json_shape`). The contract may name
# these and no others, so contract and writer cannot drift in either
# direction.
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

RUN_JSON_MARKER = "`<state-root>/runs/<run>/run.json`"

# Each contract's declared shape at this run's baseline `ef336e0`, read with
# `git show ef336e0:contracts/<name>`: the headings it declares, and every
# backticked token on the first line of each top-level bullet — field names
# and the enums they range over. A location supersession changes none of it.
BASELINE_HEADINGS = {
    "work-item.md": ("# Work-item contract (ticket)",),
    "worklog.md": ("# Worklog contract",),
    "composition.md": ("# Composition contract",),
}
BASELINE_FIELDS = {
    "work-item.md": (
        "id", "run", "status", "pending", "ready", "claimed", "suspended",
        "complete", "executor", "pack", "independence", "gate", "checker",
        "checked_by", "depends_on", "write_scope", "authority",
        "excluded_actions", "authority", "isolation", "authority",
        "required", "none", "bound", "bounds", "claimed_by", "claimed_at",
        "workspace_branch", "workspace_baseline", "profile", "profile",
        "## Objective", "objective", "## Fixed inputs", "inputs",
        "## Completion test", "## Return fields", "return_contract",
        "## Result", "## Verification", "## Feedback", "[]", "## Risks",
        "[]", "## Handoff",
    ),
    "worklog.md": (
        "goal", "spec", "tickets", "iterations", "blame_classes",
        "failed_approaches", "queued_scope", "terminal", "complete",
    ),
    "composition.md": (
        "name", "description", "entry", "routed", "named", "scheduled",
        "steps", "id", "unit", "pack", "edges", "seq", "invariants",
        "Never:", "done_check", "Require:", "Return:", "Return:",
    ),
}

# The only shape this supersession adds: `run.json`'s five top-level field
# names, appended to the worklog contract's own list. Enumerated so the
# addition is pinned rather than merely tolerated.
ADDED_FIELDS = {
    "worklog.md": ("run", "sink_convention", "opened_at", "project", "workspaces"),
}

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
    """Spec A5's contract half: `run.json`'s fields, stated where the run's
    other durable file is stated."""

    def block(self):
        text = read("worklog.md")
        self.assertIn(RUN_JSON_MARKER, text, "worklog.md does not state run.json's path")
        return text.split(RUN_JSON_MARKER, 1)[1]

    def test_the_contract_names_every_field_run_json_carries(self):
        self.assertEqual(set(), RUN_JSON_FIELDS - set(TOKEN.findall(self.block())))

    def test_the_contract_names_no_field_run_json_does_not_carry(self):
        self.assertEqual(set(), set(TOKEN.findall(self.block())) - RUN_JSON_FIELDS)


class TestContractShapeUnchanged(unittest.TestCase):
    """Spec A12's other half: a location supersession, never a shape one.

    A shape change is breaking and lands only through its own supersession
    PR (AGENTS.md), so the shape is pinned here as literals read from the
    baseline revision rather than re-derived from whatever is on disk.
    """

    def test_no_contract_declares_a_heading_it_did_not_declare_at_baseline(self):
        for name, headings in BASELINE_HEADINGS.items():
            with self.subTest(contract=name):
                self.assertEqual(headings, declared_shape(name)[0])

    def test_no_contract_gains_or_loses_a_field_beyond_the_enumerated_addition(self):
        for name, fields in BASELINE_FIELDS.items():
            with self.subTest(contract=name):
                self.assertEqual(fields + ADDED_FIELDS.get(name, ()), declared_shape(name)[1])


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

# Both files carrying the friction-law fallback: the instruction a blocked
# agent follows when the logger cannot run. Stale, it loses evidence in
# silence rather than failing a check.
FALLBACK_FILES = ("AGENTS.md", "templates/host-block.md")
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


if __name__ == "__main__":
    unittest.main()
