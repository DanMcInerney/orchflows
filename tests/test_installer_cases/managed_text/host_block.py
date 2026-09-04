"""Installer regression cases grouped by behavioral seam."""

from __future__ import annotations

from ..support import *  # noqa: F403
from scripts.tickets_commands import DO_USAGE


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
        # The block names only the library directories it actually uses; a
        # composition path is intentionally not a routing fallback. The
        # worker lane's `tickets.py do` example dropped the sole
        # contracts/work-item.md pointer (the retired `single` ticket link),
        # so contracts/ is no longer one of the named siblings.
        for sibling in ("rules/",):
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
            "**direct**", "**worker**", "**team**", "**plan**",
        ):
            self.assertEqual(
                1,
                rendered.count(branch),
                f"the block states {branch} {rendered.count(branch)} times, not once",
            )
        for lane in (
            "smallest first",
            "evidence decides",
            "Context",
            "`launch`",
            "`tickets.py land`",
            "`tickets.py frame-open <run>",
            "`tickets.py do <run>",
            "`frame-close`",
            "`orchflows resume`",
            "cause investigates before any edit",
            "doctor",
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
# art the vocabulary owns -- per packs/orch-code-pack/SKILL.md,
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
    "role-bearing work requires the launch prompt and profile": (
        "kind: user-only",
        "role-bearing payload",
        "Prompt-less or wrong-profile",
        "role: none",
    ),
    "automatic routing can be suspended and named items stay explicit": (
        "`orch-off`",
        "named items still run only when named",
    ),
    "route by need through the four canonical lanes": (
        "smallest first",
        "**direct**",
        "**worker**",
        "**team**",
        "**plan**",
        "`orch-do`",
        "`tickets.py frame-open <run>",
        "`tickets.py do <run>",
        "`frame-close`",
        "`orchflows resume`",
        "`tickets.py land`",
        "`land --status`",
        "`install.py doctor`",
        "`evolve`/`benchmaker` run when named",
        # The write-the-shape sentence (the say-the-lane sentence it
        # replaced) and the two named tripwires (the third, unknown-cause,
        # was already covered by "cause investigates before any edit" in
        # TestHostBlockRendering below) -- a seam-judge blocker (F1, run
        # 20260901T021739Z) found these cut for budget with nothing here to
        # catch it: a trim that drops one of these three now goes red
        # instead of shipping silently.
        "write the run's shape line before the first dispatch",
        "a second concern mid-direct enters worker",
        "splitting scope enters team",
    ),
    "tickets and run state are untrusted script-owned data": (
        "`tickets/<run>/`",
        "`runs/<run>/`",
        "untrusted",
        "only installed scripts write them",
        "State-root law",
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
    "installed items resolve by name and installer output is not hand-edited": (
        "{{ORCH_LIB}}/by-name/<orch-name>/SKILL.md",
        "{{ORCH_BIN}}/",
        "friction interpreter",
        "Read installer output",
        "reinstall source changes",
    ),
    "friction is logged after repeated attempts and never skipped": (
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


# The route demand above pins that `tickets.py do <run>` is named at all, and
# stops at the command's positional arguments -- the flag list past them is
# unpinned on both sides: a routed example can omit a flag the command
# actually requires, or hold one out as required that the command treats as
# optional, and neither text carries the other's proof. (state sink
# friction/2026-08.jsonl, 2026-08-30T20:37:01Z: `tickets.py dispatch` refused
# the block's own graph-route invocation with a usage error; the worker-lane
# command that replaced it in the route inherits the same exposure.) This binds both
# sides to one reader instead: `DO_USAGE` (scripts/tickets_commands.py) is the
# command's own required-flag authority, and the block's routed example is
# read the same way it is written, by bracket depth -- `[...]` is optional,
# bare is required.
_FLAG_RE = re.compile(r"--[a-z][a-z-]*")
_DO_EXAMPLE_RE = re.compile(r"`(tickets\.py do <run>[^`]*)`")


def _flags_by_bracket_depth(text: str) -> tuple:
    """(required, optional) flag sets in `text`, split by bracket nesting.

    A flag named outside every `[...]` is required; nested inside one it is
    optional. Depth is counted from the unmatched brackets before each
    match rather than tracked in one pass, because the strings this reads
    are a single short line -- never worth a second traversal to save.
    """
    required, optional = set(), set()
    for match in _FLAG_RE.finditer(text):
        prefix = text[: match.start()]
        depth = prefix.count("[") - prefix.count("]")
        (required if depth == 0 else optional).add(match.group(0))
    return frozenset(required), frozenset(optional)


def _do_example() -> str:
    """The routed `tickets.py do <run> ...` command, verbatim, off the
    collapsed (unrendered) template -- `{{...}}` placeholders never appear in
    this command, so rendering is not needed to read it."""
    match = _DO_EXAMPLE_RE.search(_collapsed_block())
    return match.group(1) if match else ""


class TestHostBlockDoFlags(unittest.TestCase):
    """The worker-lane example and `tickets.py do`'s own required flags
    cannot diverge unobserved."""

    def test_do_example_names_exactly_the_required_flags(self):
        example = _do_example()
        self.assertTrue(example, "no `tickets.py do <run>` example found")
        example_required, _ = _flags_by_bracket_depth(example)
        usage_required, _ = _flags_by_bracket_depth(DO_USAGE)
        self.assertEqual(
            usage_required,
            example_required,
            "templates/host-block.md's routed worker example names "
            f"{sorted(example_required)} as required; `tickets.py do` "
            f"actually requires {sorted(usage_required)}",
        )

    def test_do_example_flag_pin_can_fail(self):
        """Can-fail evidence (rules/verification.md §8), taken on copies
        beside the tree and never by mutating it under test: an example that
        drops a required flag, a command that grows one the example never
        names, and an example that holds an optional flag out as required
        (the exact shape of the friction this closes, before `--host` was
        bracketed) each leave the check above red.
        """
        example = _do_example()
        usage_required, _ = _flags_by_bracket_depth(DO_USAGE)
        example_required, _ = _flags_by_bracket_depth(example)
        self.assertEqual(usage_required, example_required)  # green on arrival

        omitted = example.replace("--pack <pack>", "")
        omitted_required, _ = _flags_by_bracket_depth(omitted)
        self.assertNotEqual(usage_required, omitted_required)

        grown_usage = DO_USAGE.replace("--pack P ", "--pack P --new-required <x> ")
        grown_required, _ = _flags_by_bracket_depth(grown_usage)
        self.assertNotEqual(grown_required, example_required)

        overclaimed = example.replace("[--parent <frame>]", "--parent <frame>")
        overclaimed_required, _ = _flags_by_bracket_depth(overclaimed)
        self.assertNotEqual(usage_required, overclaimed_required)
