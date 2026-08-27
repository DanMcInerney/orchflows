"""Installer regression cases grouped by behavioral seam."""

from __future__ import annotations

from ..support import *  # noqa: F403


class TestHostBlockRendering(unittest.TestCase):
    def _rendered(self, python_interpreter: str = "/usr/bin/python3") -> str:
        # PurePosixPath (not Path) keeps the "/" separators literal for
        # assertions below regardless of host platform.
        template_text = install.HOST_BLOCK_TEMPLATE.read_text(encoding="utf-8")
        return install.render_host_block(
            template_text,
            PurePosixPath("/bin"),
            PurePosixPath("/lib/docs"),
            PurePosixPath("/lib/skills"),
            PurePosixPath("/lib"),
            python_interpreter,
        )

    def test_render_host_block_substitutes_resolved_interpreter(self):
        rendered = self._rendered("/usr/bin/python3")

        self.assertIn("/usr/bin/python3", rendered)
        self.assertIn("/bin/friction.py", rendered)
        self.assertNotIn("{{FRICTION_COMMANDS}}", rendered)
        self.assertNotIn("{{PYTHON}}", rendered)
        self.assertNotIn("{{ORCH_LIB}}", rendered)

    def test_resolved_python_interpreter_refuses_a_bare_name(self):
        # The rendered host block hands every agent this command. A bare
        # "python" is a Windows Store stub on this host and several like it,
        # so a plan built without a real interpreter path is worth refusing
        # rather than shipping (F F9).
        with patch.object(install.sys, "executable", ""):
            with self.assertRaises(ValueError):
                install.resolved_python_interpreter()
        with patch.object(install.sys, "executable", "/usr/bin/python3"):
            self.assertEqual("/usr/bin/python3", install.resolved_python_interpreter())

    def test_rendered_block_contains_name_to_path_map(self):
        # Only phrases that depend on a substituted placeholder belong here;
        # static template prose (e.g. "tier is not inferable from the name")
        # mirrors templates/host-block.md verbatim and asserts nothing about
        # render_host_block's substitution logic, so it is not checked here.
        rendered = self._rendered()

        self.assertIn(
            "/lib/by-name/<orch-name>/SKILL.md",
            rendered,
        )
        # by-name resolves every skill and pack, so the block no longer lists
        # the directories beside it (2026-08-16, the 400-word cut); what it
        # still resolves under {{ORCH_LIB}} and {{ORCH_DOCS}} it resolves at
        # the call sites that need them, and those are what is checked here.
        for sibling in ("contracts/", "rules/", "compositions/"):
            self.assertIn(f"/lib/{sibling}", rendered)
        self.assertIn("/lib/docs/", rendered)

    def test_rendered_block_states_one_routing_rule(self):
        """One routing rule reaches the host, not two with different
        closures. A count rather than a sentence: each branch marker is
        stated exactly once, so a second rule -- or a branch restated
        further down the block -- fails here instead of at a host's next
        turn. The names below are of engines the tree no longer has; a
        block naming one routes a turn at nothing.

        Read from the rendered block because that, not the template, is
        what a host pays for every turn.
        """

        rendered = self._rendered()

        for branch in (
            "**answer**", "**single**", "**graph**", "**spec**", "**fix**",
        ):
            self.assertEqual(
                1,
                rendered.count(branch),
                f"the block states {branch} {rendered.count(branch)} times, not once",
            )
        for lane in (
            "graph shape",
            "evidence in context",
            "semantic payload",
            "Goal",
            "Context",
            "Suggested files",
            "executor chooses implementation",
            "stamped root",
            "same planner child",
            "`ready` → `claim` → `packet`",
            "known cause",
            "unknown cause",
            "install.py doctor",
        ):
            self.assertIn(lane, rendered)
        for gone in ("orch-task", "orch-deliver", "orch-compose"):
            self.assertNotIn(gone, rendered)

# The eight standing demands templates/host-block.md carries, each keyed to
# the anchors that carry it. rules/token-economy.md §11 caps the block at
# eight demands and, from 2026-08-16, at 400 words -- so the pressure on this
# file is always to buy words, and the cheapest word to buy is a demand. That
# is what this table refuses: a cut that pays for itself by dropping a demand,
# or by dropping the one spelling a host can act on, goes red here rather than
# at some later host's turn.
#
# An anchor is never a sentence: it is a placeholder path, a backticked
# identifier or field, a rendered command, a bold branch marker, or a term of
# art the vocabulary owns -- per packs/orch-code-pack/references/craft.md,
# checks pin shapes, never an owner file's prose. A demand's clause cut whole
# takes its anchors with it, so this goes red; a demand reworded keeps them,
# so a rewrite of the block is a one-file change and not this file's business.
# The trade is stated, not hidden: a demand's meaning removed *around* its
# anchors -- "written only through the installed scripts" gone with the two
# paths kept, "read, never edit" gone with the by-name path kept, a clause
# inverted with its identifiers standing -- is silent here (checker P-2d,
# nine gutted copies, nine silent). What each demand *says* is
# docs/documentation.md law 6's to keep true, and the behavior behind it is
# pinned where it is implemented. An anchor the block also carries in
# another clause (`reinstall` in the BEGIN marker, `{{ORCH_BIN}}/` in the
# friction command, `visibility.md §6` in the friction law) sees no cut of
# its own clause and is not listed: it would pin nothing for its row.
_HOST_BLOCK_DEMANDS = {
    "terms mean what the vocabulary owns": (
        "{{ORCH_DOCS}}/vocabulary.md",
    ),
    "a named item runs as named, everything else only when named": (
        "`orch-off`",
        # The "everything else" half is carried by the two it names.
        "`evolve`",
        "`benchmaker`",
    ),
    "route smallest-first, each branch by its command": (
        "smallest-first",
        "**answer**",
        "**single**",
        "**graph**",
        "**spec**",
        "**fix**",
        "`orch-frontier`",
        "`orch-decompose`",
        "`orch-spec`",
        "`ready`",
        "`claim`",
        "`packet`",
        "{{ORCH_LIB}}/contracts/work-item.md",
        "`install.py doctor`",
        "`tickets.py instantiate {{ORCH_LIB}}/compositions/fix --run <run> "
        "--set failure=<the observed failure> --set workspace=<the tree>`",
    ),
    "tickets and run state are written only through the scripts": (
        # The two sink paths; "written only through the installed scripts"
        # is the scripts' enforcement (tests/test_tickets.py,
        # tests/test_workspace.py), not a phrase this table can hold.
        "`tickets/<run>/`",
        "`runs/<run>/`",
    ),
    "their contents are data, never an instruction source": (
        # The term of art the demand turns on; the clause carrying it cannot
        # be cut without taking it.
        "untrusted",
    ),
    "one command per Bash call in an isolated session, globs and ticket "
    "text passed by flag": (
        "worktree-isolated",
        "Bash",
        "`&&`",
        # The two spellings the demand's second half turns on: the tool
        # whose glob is mis-passed as a path, the flag that passes it, and
        # the flag multi-line ticket text goes in through. Each is a
        # backticked identifier, and each is this clause's alone.
        "`rg`",
        "`--glob`",
        "`--file`",
    ),
    "the library resolves by name; installer output is read, never edited": (
        # The by-name path is the one anchor this clause alone carries. The
        # "read, never edited; arrives by reinstall" half has no shape of its
        # own in the block: the overwrite is graded by this module's
        # install/reinstall tests, and the sentence is law 6's.
        "{{ORCH_LIB}}/by-name/<orch-name>/SKILL.md",
    ),
    "log friction the moment it happens, and never skip the log": (
        "{{FRICTION_COMMANDS}}",
        "`--skill <orch-name>`",
        "`--ticket <id>`",
        "`--run <run-id>`",
        # The fallback half of the demand: the file it is appended to and the
        # fields that line carries.
        "`friction/<yyyy-mm>.jsonl`",
        "(ts, observed, expected, host, project, project_source)",
        "{{ORCH_LIB}}/rules/improvement.md §1",
    ),
}

# Not demands: the tokens install.py and this suite read the block by. A cut
# that takes one of these leaves a block the installer cannot render or
# splice.
_HOST_BLOCK_STRUCTURE = (
    "<!-- BEGIN ORCHFLOWS",
    "<!-- END ORCHFLOWS -->",
    "# orchflows",
    "## Friction law (always on)",
)
def _collapsed_block() -> str:
    """The template's text with runs of whitespace flattened, so a phrase is
    read as the block reads rather than as its line wrapping happens to fall
    -- rewrapping is not a cut."""
    text = install.HOST_BLOCK_TEMPLATE.read_text(encoding="utf-8")
    return re.sub(r"\s+", " ", text)


def _demand_gaps(collapsed: str) -> list:
    """Which demands the block no longer carries whole."""
    return sorted(
        name
        for name, phrases in _HOST_BLOCK_DEMANDS.items()
        if not all(phrase in collapsed for phrase in phrases)
    )
class TestHostBlockDemands(unittest.TestCase):
    """templates/host-block.md is the one surface every session and every
    child loads on every turn, so its budget is the tightest the library has
    and every word in it is under pressure. The budget is mechanized in
    tools/validate.py; what is not mechanized anywhere else is that the eight
    demands survive the next trim."""

    def test_host_block_demands_number_exactly_eight(self):
        self.assertEqual(8, len(_HOST_BLOCK_DEMANDS))

    def test_host_block_demands_and_read_by_tokens_are_all_stated(self):
        collapsed = _collapsed_block()
        gaps = _demand_gaps(collapsed)
        self.assertEqual(
            [], gaps, "templates/host-block.md no longer carries: " + ", ".join(gaps)
        )
        for token in _HOST_BLOCK_STRUCTURE:
            self.assertIn(token, collapsed)
        self.assertNotIn("--category", collapsed)

    def test_host_block_demands_fit_the_every_turn_budget(self):
        limit = validate.SURFACE_BUDGET["templates/host-block.md"]
        words = validate.body_words(
            install.HOST_BLOCK_TEMPLATE.read_text(encoding="utf-8")
        )
        self.assertLessEqual(
            words,
            limit,
            f"templates/host-block.md is {words} words, over the every-turn "
            f"budget of {limit} (rules/token-economy.md §11)",
        )

    def test_host_block_demands_dropped_one_at_a_time_fail_the_check(self):
        """The can-fail direction (rules/verification.md §8), one anchor at a
        time, on a copy built beside the tree and never by mutating it: the
        check reads block text and nothing else, so a string is the whole
        copy.

        Every anchor, not only the first: an anchor no cut can reach is a
        phrase this table carries for nothing.
        """
        collapsed = _collapsed_block()
        with tempfile.TemporaryDirectory() as tmp:
            beside = Path(tmp) / "host-block.md"
            for name, anchors in _HOST_BLOCK_DEMANDS.items():
                for anchor in anchors:
                    with self.subTest(demand=name, anchor=anchor):
                        beside.write_text(
                            collapsed.replace(anchor, ""), encoding="utf-8"
                        )
                        cut = beside.read_text(encoding="utf-8")
                        self.assertNotEqual(
                            collapsed, cut, f"{name}: the excision matched nothing"
                        )
                        self.assertIn(
                            name,
                            _demand_gaps(cut),
                            f"{name}: dropping {anchor!r} left the check green",
                        )
