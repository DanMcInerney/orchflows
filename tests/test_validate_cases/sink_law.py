"""State-sink law and prose-ownership regression cases."""
import os
import re
import sys
import unittest
from pathlib import Path

from tests._repo_root import ROOT
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import state_root  # noqa: E402

CONTRACTS = ROOT / "contracts"
TOKEN = re.compile(r"`([^`]+)`")


def flat(text):
    """Text with whitespace collapsed, so a wrapped clause matches as one."""

    return re.sub(r"\s+", " ", text)

# --- The prose half: the law and the documentation say what the code does ---

# The one file that states the sink root in prose. `scripts/state_root.py`
# owns it in code; every other markdown file links here rather than
# restating it (spec binding constraint 2, one owner per fact).
PATH_OWNER = "rules/visibility.md"

# What "states the path literally" means: either spelling of the root.
LITERAL_ROOT_TOKENS = ("~/.orchflows/state", state_root.ENV_VAR)

# What §6 must now say about the root, so the law names the sink and not a
# path inside some repository. This is the whole of §6 that is read here:
# the two-channel law belongs to `TestVisibilityChannelLaw` in
# tests/test_contracts.py, which pins both channels by their writers, and
# §6's no-fallback rule is an enforcement claim proved by the enforcement
# -- tests/test_state_root.py's
# `test_run_state_reports_the_failure_and_writes_nothing_under_cwd`.
# Restating either here gave one fact two owners and made every reword of
# §6 a two-file change.
SINK_ROOT_CLAUSES = ("user-scope state sink",) + LITERAL_ROOT_TOKENS

# The two subdirectories a repository keeps, and nothing else (spec A15).
REPOSITORY_ORCH_SUBDIRECTORIES = frozenset({"canary/", "bin/"})

# Vocabulary terms whose definition names a location: each must resolve to
# the sink, since `docs/vocabulary.md` owns every library term of art and a
# term defined against the old place makes every correct use of it wrong.
SINK_TERMS = ("tracker", "friction log", "run state")

# The files outside this item's `write_scope` that name `.orch`
# legitimately — the canary is a git-tracked golden fixture and `bin/` is an
# installed script directory, neither of them state. What is pinned is how
# many times each names it and which path each names, never the sentence
# doing the naming: a second mention appearing in either file is the
# regression, and the sentence around the path is its file's to reword. The
# third file was `skills/kernel/orch-mechanize/SKILL.md`, deleted at P3: the
# run-local `.orch/bin/` landing zone is rules/token-economy.md §4's to
# state, and a skill body no longer restates it.
CANARY_AND_BIN_MENTIONS = {
    "example-workflows/drift-canary/SKILL.md": 1,
}
CANARY_PATH = "`.orch/canary/`"

# The one file carrying the friction-law fallback: the instruction a blocked
# agent follows when the logger cannot run. Stale, it loses evidence in
# silence rather than failing a check, so it has one owner and no copy --
# AGENTS.md pointed a second copy at the same tree until P3 deleted it, and
# `test_agents_md_carries_no_second_fallback_copy` keeps it deleted.
FALLBACK_FILES = ("templates/host-block.md",)
FALLBACK_NEEDLE = "friction/<yyyy-mm>.jsonl"

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


class TestTheLawNamesTheSinkRoot(unittest.TestCase):
    """Spec binding constraint 1: §6 is amended in place, never replaced --
    and the amendment is the root it points at, which is this module's
    half of §6. The law's other halves have their own owners, named at
    `SINK_ROOT_CLAUSES`."""

    def setUp(self):
        self.section = numbered_section(PATH_OWNER, 6)
        self.assertTrue(self.section, "rules/visibility.md states no §6")

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

    def test_the_out_of_scope_files_name_the_canary_path_and_nothing_else(self):
        for relpath, expected in CANARY_AND_BIN_MENTIONS.items():
            with self.subTest(document=relpath):
                found = [
                    line for line in doc(relpath).splitlines()
                    if ORCH_MENTION.search(line)
                ]
                self.assertEqual(expected, len(found), found)
                for line in found:
                    self.assertIn(CANARY_PATH, line)

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
