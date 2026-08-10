"""Reader UI: main-checkout resolution, discovery, escaping, empty states,
status presentation, verification degradation, the elapsed meter, and the
read-only, no-network and loopback-only guarantees."""

import ast
import contextlib
import http.client
import io
import ipaddress
import os
import re
import shutil
import sys
import tempfile
import threading
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch
from urllib.parse import quote

PAYLOAD = "<script>alert(1)</script>"
# Spec criterion 12: an asset reference is remote when its value starts
# with a scheme or with a protocol-relative `//`.
REMOTE_ASSET_RE = re.compile(r"""(?:src|href)\s*=\s*["']?\s*(?:https?:)?//""", re.IGNORECASE)

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import scripts.tickets as tickets_mod  # noqa: E402
import scripts.ui as ui  # noqa: E402

UI_PY = ROOT / "scripts" / "ui.py"
WORK_ITEM_CONTRACT = ROOT / "contracts" / "work-item.md"
FIXTURES = Path(__file__).resolve().parent / "fixtures" / "ui"
FIXTURE_RUNS = ("run-alpha", "run-beta", "run-gamma", "run-delta", "run-epsilon")
EMPTY_RUN = "run-empty"
# Every ticket in `run-delta` is terminal and none is claimed, so it is the
# corpus's settled run: the case where the band is absent and the poll
# interval must not be the live one.
SETTLED_RUN = "run-delta"
CYCLIC_RUN = "run-epsilon"


def contract_statuses() -> tuple:
    """The closed status set exactly as `contracts/work-item.md` states it.

    Read from the contract rather than restated here, so the presentation
    map is held to its owner: a status added there and missed here fails
    this suite instead of rendering as the unknown fallback."""

    text = WORK_ITEM_CONTRACT.read_text(encoding="utf-8")
    declaration = re.search(r"^- `status`:(.+?)—", text, re.MULTILINE | re.DOTALL)
    if declaration is None:
        return ()
    return tuple(re.findall(r"`([a-z]+)`", declaration.group(1)))


def contract_sections() -> tuple:
    """The body section names `contracts/work-item.md` fixes, read from the
    contract for the same reason as the status set."""

    text = WORK_ITEM_CONTRACT.read_text(encoding="utf-8")
    return tuple(re.findall(r"^- `## (.+?)` —", text, re.MULTILINE))


def copy_logs(source: Path, dest: Path):
    """One fixture log directory materialized under a temporary ``.orch/``."""

    dest.mkdir(parents=True)
    for src in sorted(source.glob("*.jsonl")):
        shutil.copyfile(str(src), str(dest / src.name))


def make_checkout(tmp: Path, runs=FIXTURE_RUNS, friction=True, events=True) -> Path:
    """A main checkout: a ``.git`` directory plus ``.orch/tickets/<run>/``
    materialized from the flat tracked fixtures, one run with no tickets
    (git tracks no empty directory, so it is built here), the friction log
    and the deferred hooks seam's event log. ``runs`` narrows the corpus for
    a test that needs a run set the whole corpus does not exhibit."""

    root = tmp / "main"
    (root / ".git").mkdir(parents=True)
    tickets = root / ".orch" / "tickets"
    for run in runs:
        dest = tickets / run
        dest.mkdir(parents=True)
        for src in sorted((FIXTURES / run).glob("*.md")):
            shutil.copyfile(str(src), str(dest / src.name))
    (tickets / EMPTY_RUN).mkdir(parents=True)
    if friction:
        copy_logs(FIXTURES / "friction", root / ".orch" / "friction")
    if events:
        copy_logs(FIXTURES / "events", root / ".orch" / "events")
    return root


def make_worktree(tmp: Path, main_root: Path) -> Path:
    """A linked worktree: a ``.git`` *file* pointing at
    ``<main>/.git/worktrees/<name>``, the shape ``git worktree add`` writes."""

    worktree = tmp / "wt"
    worktree.mkdir()
    gitdir = main_root / ".git" / "worktrees" / "wt"
    gitdir.mkdir(parents=True)
    (worktree / ".git").write_text("gitdir: {0}\n".format(gitdir), encoding="utf-8")
    return worktree


def ticket_paths(discovery: dict) -> list:
    return [ticket["path"] for run in discovery["runs"] for ticket in run["tickets"]]


def fixture_ticket_count() -> int:
    """Derived from the corpus on disk, so adding a fixture never silently
    weakens a count that exists to keep a test non-vacuous."""

    return sum(len(list((FIXTURES / run).glob("*.md"))) for run in FIXTURE_RUNS)


def row_for(page: str, ticket_id: str) -> str:
    """The table row carrying ``ticket_id``, so a field is proved to sit
    with its own ticket rather than merely somewhere on the page."""

    for fragment in page.split("<tr")[1:]:
        row = fragment.split("</tr>")[0]
        if ">{0}<".format(ticket_id) in row:
            return row
    return ""


def block_for(page: str, class_name: str, close: str = "</section>") -> str:
    """The element carrying ``class_name``, so an assertion about one part
    of the page cannot be satisfied by another part of it."""

    fragments = page.split('class="{0}"'.format(class_name))[1:]
    return fragments[0].split(close)[0] if fragments else ""


def detail_url(run: str, ticket_id: str) -> str:
    return "/ticket?run={0}&id={1}".format(run, ticket_id)


def graph_url(run: str) -> str:
    return "/graph?run={0}".format(run)


NODE_RE = re.compile(
    r'<g class="nd (nd-[a-z]+)"[^>]*>.*?<text class="nd-id"[^>]*>([^<]+)</text>'
)


def node_for(page: str, ticket_id: str) -> str:
    """The status class the graph drew on ``ticket_id``'s own node. Every
    status name also appears in the stylesheet, so a bare substring search
    over the page proves nothing about what was drawn."""

    for status_class, drawn in NODE_RE.findall(page):
        if drawn == ticket_id:
            return status_class
    return ""


def section_for(page: str, run: str) -> str:
    for fragment in page.split('<section class="run">')[1:]:
        body = fragment.split("</section>")[0]
        if ">{0}<".format(run) in body:
            return body
    return ""


# A bare route name exercises almost none of a route's behaviour: `/ticket`
# with no query is the one branch that never reads a file. Each served route
# is paired with the concrete URLs that reach its real work, so the whole-page
# guarantees -- writes nothing, fetches nothing -- are proved where the page
# is actually built.
ROUTE_EXAMPLES = {
    ui.INDEX_ROUTE: ("/",),
    ui.TICKET_ROUTE: (
        "/ticket",
        detail_url("run-gamma", "G1"),
        detail_url("run-gamma", "G6"),
        detail_url("run-gamma", "G7"),
        detail_url("run-gamma", "no-such-ticket"),
        detail_url("run-empty", "G1"),
    ),
    ui.GRAPH_ROUTE: (
        "/graph",
        graph_url(SETTLED_RUN),
        graph_url(CYCLIC_RUN),
        graph_url("run-gamma"),
        graph_url(EMPTY_RUN),
        graph_url("no-such-run"),
    ),
    ui.FRICTION_ROUTE: ("/friction",),
}


def every_route() -> tuple:
    """Every served route by concrete example, plus one that is not served,
    so the 404 page is held to the same guarantees as the index."""

    urls = tuple(url for route in ui.ROUTES for url in ROUTE_EXAMPLES.get(route, ()))
    return urls + ("/no-such-route",)


# `run-gamma/G4.md` is claimed at this instant with a 90m bound: the only
# fixture from which an elapsed meter may be drawn.
CLAIMED_AT = datetime(2026, 1, 1, 0, 20, 0, tzinfo=timezone.utc)
FROZEN_NOW = datetime(2026, 1, 1, 1, 0, 0, tzinfo=timezone.utc)


@contextlib.contextmanager
def frozen_clock(now=FROZEN_NOW):
    """Hold the reader's clock still.

    A live elapsed meter is an input to the page and therefore to the
    validator the page is served under, so two requests straddling a minute
    boundary honestly disagree. A test about an unchanged *directory* must
    not also be a test about the second it happened to run in.
    """

    with patch.object(ui, "_now", return_value=now):
        yield


def freeze(case, now=FROZEN_NOW):
    """`frozen_clock` for a whole case, for the cases whose every assertion
    spans two requests."""

    stack = contextlib.ExitStack()
    case.addCleanup(stack.close)
    stack.enter_context(frozen_clock(now))


@contextlib.contextmanager
def serving(root: Path):
    """The real server on an ephemeral loopback port."""

    server = ui.create_server(root, 0)
    thread = threading.Thread(target=server.serve_forever)
    thread.daemon = True
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def write_ticket(run_dir: Path, ticket_id: str, **fields) -> Path:
    """One ticket with exactly the frontmatter a test names, for cases the
    shared fixtures deliberately do not carry."""

    run_dir.mkdir(parents=True, exist_ok=True)
    lines = ["---", "id: {0}".format(ticket_id)]
    lines.extend("{0}: {1}".format(key, value) for key, value in fields.items())
    lines.extend(["---", ""])
    path = run_dir / "{0}.md".format(ticket_id)
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def fetch(server, route: str, headers=None) -> tuple:
    """``(status, headers, body)`` over the real socket."""

    host, port = server.server_address[0], server.server_address[1]
    connection = http.client.HTTPConnection(host, port, timeout=5)
    try:
        connection.request("GET", route, headers=headers or {})
        response = connection.getresponse()
        return response.status, response.headers, response.read().decode("utf-8")
    finally:
        connection.close()


def get(server, route: str) -> tuple:
    status, _headers, body = fetch(server, route)
    return status, body


def snapshot(tree: Path) -> dict:
    """Name, size and mtime of every entry under ``tree``, recursively."""

    entries = {}
    for path in sorted(tree.rglob("*")):
        stat = path.stat()
        key = path.relative_to(tree).as_posix()
        entries[key] = (path.is_dir(), stat.st_size, stat.st_mtime_ns)
    return entries


class TestRootResolution(unittest.TestCase):
    """Spec criterion 5."""

    def test_worktree_and_main_checkout_yield_identical_ticket_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main = make_checkout(tmp)
            worktree = make_worktree(tmp, main)

            from_main = ui.discover(main)
            from_worktree = ui.discover(worktree)

            self.assertEqual(main.resolve(), from_worktree["root"])
            paths = ticket_paths(from_main)
            self.assertEqual(fixture_ticket_count(), len(paths), paths)
            self.assertTrue(paths)
            self.assertEqual(paths, ticket_paths(from_worktree))
            for path in ticket_paths(from_worktree):
                self.assertNotIn(str(worktree.resolve()), path)

    def test_every_run_directory_is_discovered_including_the_empty_one(self):
        with tempfile.TemporaryDirectory() as tmp:
            discovery = ui.discover(make_checkout(Path(tmp)))
            self.assertEqual(
                sorted(FIXTURE_RUNS + (EMPTY_RUN,)),
                [run["run"] for run in discovery["runs"]],
            )
            by_run = {run["run"]: run for run in discovery["runs"]}
            self.assertEqual([], by_run[EMPTY_RUN]["tickets"])
            self.assertEqual(
                ["A1", "A2"], [t["id"] for t in by_run["run-alpha"]["tickets"]]
            )


class TestIndexPage(unittest.TestCase):
    """The objective: one page listing every run and its tickets."""

    def test_index_lists_every_run_with_each_ticket_id_status_and_executor(self):
        with tempfile.TemporaryDirectory() as tmp:
            main = make_checkout(Path(tmp))
            status, page = ui.render_route(main, "/")

            self.assertEqual(200, status)
            for run in FIXTURE_RUNS + (EMPTY_RUN,):
                self.assertNotEqual("", section_for(page, run), run)
            alpha_one = row_for(page, "A1")
            self.assertIn("complete", alpha_one)
            self.assertIn("orch-tdd", alpha_one)
            alpha_two = row_for(page, "A2")
            self.assertIn("claimed", alpha_two)
            self.assertIn("orch-verify", alpha_two)
            self.assertNotIn("orch-tdd", alpha_two)

    def test_unknown_route_is_404_with_the_requested_path_escaped(self):
        with tempfile.TemporaryDirectory() as tmp:
            main = make_checkout(Path(tmp))
            status, page = ui.render_route(main, "/<script>x</script>")

            self.assertEqual(404, status)
            self.assertNotIn("<script>x</script>", page)
            self.assertIn("&lt;script&gt;x&lt;/script&gt;", page)


class TestEscaping(unittest.TestCase):
    """Spec criterion 9 and the `rules/visibility.md` §6 untrusted-data law."""

    def test_untrusted_objective_reaches_the_page_escaped_never_as_markup(self):
        source = (FIXTURES / "run-alpha" / "A2.md").read_text(encoding="utf-8")
        self.assertIn(PAYLOAD, source)

        with tempfile.TemporaryDirectory() as tmp:
            main = make_checkout(Path(tmp))
            _, page = ui.render_route(main, "/")

            self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", row_for(page, "A2"))
            self.assertNotIn(PAYLOAD, page)

    def test_the_detail_page_escapes_the_same_payload(self):
        with tempfile.TemporaryDirectory() as tmp:
            main = make_checkout(Path(tmp))
            status, page = ui.render_route(main, detail_url("run-alpha", "A2"))

            self.assertEqual(200, status)
            self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", page)
            self.assertNotIn(PAYLOAD, page)


class TestEmptyStates(unittest.TestCase):
    """Spec criterion 13."""

    def test_root_with_no_orch_directory_renders_a_named_empty_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            bare = Path(tmp) / "bare"
            (bare / ".git").mkdir(parents=True)

            status, page = ui.render_route(bare, "/")

            self.assertEqual(200, status)
            self.assertIn("no .orch directory under this root", page)

    def test_orch_directory_with_no_tickets_tree_renders_a_named_empty_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "friction-only"
            (root / ".git").mkdir(parents=True)
            (root / ".orch" / "friction").mkdir(parents=True)

            status, page = ui.render_route(root, "/")

            self.assertEqual(200, status)
            self.assertIn("no runs under .orch/tickets", page)

    def test_run_directory_with_zero_tickets_renders_a_named_empty_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            main = make_checkout(Path(tmp))
            _, page = ui.render_route(main, "/")

            self.assertIn("no tickets in this run", section_for(page, EMPTY_RUN))
            self.assertNotIn("no tickets in this run", section_for(page, "run-alpha"))

    def test_ticket_omitting_optional_data_renders_named_empty_states(self):
        with tempfile.TemporaryDirectory() as tmp:
            main = make_checkout(Path(tmp))
            _, page = ui.render_route(main, "/")

            degenerate = row_for(page, "B1")
            self.assertIn("no objective recorded", degenerate)
            self.assertIn("unset", degenerate)
            self.assertNotIn("unset", row_for(page, "A1"))
            self.assertNotIn("no objective recorded", row_for(page, "A1"))


class TestStatusPresentation(unittest.TestCase):
    """Spec criterion 14 and the colour law of `lane-ui-patterns.md` §2,
    sourced to Airflow 2.10.5 `airflow/utils/state.py`."""

    def test_the_map_covers_exactly_the_contract_status_set(self):
        statuses = contract_statuses()

        self.assertEqual(8, len(statuses), statuses)
        self.assertEqual(set(statuses), set(ui.STATUS_PRESENTATION))
        self.assertEqual(set(statuses), set(tickets_mod.VALID_STATUSES))

    def test_every_status_resolves_to_a_populated_distinct_triple(self):
        statuses = contract_statuses()
        seen = [ui.status_presentation(status) for status in statuses]

        for status, presentation in zip(statuses, seen):
            self.assertTrue(presentation.glyph, status)
            self.assertTrue(presentation.word, status)
            self.assertTrue(presentation.hue.startswith("--st-"), status)
            self.assertTrue(presentation.border, status)
        triples = [(p.glyph, p.word, p.hue) for p in seen]
        self.assertEqual(len(triples), len(set(triples)))
        # The word alone would make every triple unique, so the channel that
        # has to carry the state on its own is also checked on its own.
        self.assertEqual(8, len({p.glyph for p in seen}))
        self.assertEqual(8, len({p.word for p in seen}))

    def test_an_unknown_status_maps_to_the_named_fallback_and_never_raises(self):
        for value in ("", "fabulous", "COMPLETE", "<script>", "3", "complete "):
            self.assertEqual(ui.STATUS_FALLBACK, ui.status_presentation(value), value)
        self.assertEqual("unknown", ui.STATUS_FALLBACK.word)
        # The fallback keeps its own hue: an unrecognized status that
        # borrowed a real state's colour would read as that state.
        self.assertNotIn(
            ui.STATUS_FALLBACK.hue,
            [ui.status_presentation(status).hue for status in contract_statuses()],
        )

    def test_eight_statuses_collapse_onto_exactly_six_hues_two_of_them_shared(self):
        statuses = contract_statuses()
        hues = [ui.status_presentation(status).hue for status in statuses]

        self.assertEqual(6, len(set(hues)))
        shared = sorted(hue for hue in set(hues) if hues.count(hue) > 1)
        self.assertEqual(2, len(shared), shared)
        for hue in shared:
            pair = [s for s in statuses if ui.status_presentation(s).hue == hue]
            self.assertEqual(2, len(pair), pair)
            # A shared hue is legible only because the other channels differ.
            self.assertEqual(2, len({ui.status_presentation(s).glyph for s in pair}), pair)
            self.assertEqual(2, len({ui.status_presentation(s).border for s in pair}), pair)

    def test_blocked_is_amber_and_failed_owns_red_alone(self):
        blocked = ui.status_presentation("blocked")
        failed = ui.status_presentation("failed")

        self.assertNotEqual(blocked.hue, failed.hue)
        self.assertEqual("amber", ui.HUE_TOKENS[blocked.hue])
        self.assertEqual("red", ui.HUE_TOKENS[failed.hue])
        self.assertEqual(
            [failed.hue], [t for t, family in ui.HUE_TOKENS.items() if family == "red"]
        )

    def test_in_flight_never_shares_the_hue_of_done_well(self):
        hues = [ui.status_presentation(s).hue for s in ("claimed", "ready", "complete")]

        self.assertEqual(3, len(set(hues)), hues)
        self.assertEqual("green", ui.HUE_TOKENS[ui.status_presentation("complete").hue])

    def test_every_hue_token_names_a_declared_colour_family(self):
        used = {ui.status_presentation(s).hue for s in contract_statuses()}
        used.add(ui.STATUS_FALLBACK.hue)

        self.assertEqual(used, set(ui.HUE_TOKENS))
        for token, family in ui.HUE_TOKENS.items():
            self.assertTrue(token.startswith("--st-"), token)
            self.assertTrue(family, token)

    def test_no_glyph_is_an_emoji_presentation_character(self):
        # Windows is a first-class CI leg and the page ships no icon font,
        # so each glyph must be a single text-presentation code point the
        # system font stack already carries. The rejected set is the
        # obvious-but-wrong choice for four of these states.
        rejected = ("⛔", "⏸", "✅", "❌", "⚠", "\U0001f534")
        glyphs = [p.glyph for p in ui.STATUS_PRESENTATION.values()]
        glyphs.append(ui.STATUS_FALLBACK.glyph)

        for glyph in glyphs:
            # One code point: a trailing variation selector is what turns a
            # text mark into an emoji, and it would fail this length check.
            self.assertEqual(1, len(glyph), ascii(glyph))
            self.assertLess(ord(glyph), 0x1F000, ascii(glyph))
            self.assertNotIn(glyph, rejected, ascii(glyph))
            self.assertFalse(0x2600 <= ord(glyph) <= 0x26FF, ascii(glyph))


class TestStatusRendering(unittest.TestCase):
    """The ticket objective: every rendered ticket carries its status as a
    glyph, a word and a hue token."""

    def index(self) -> str:
        with tempfile.TemporaryDirectory() as tmp:
            main = make_checkout(Path(tmp))
            status, page = ui.render_route(main, "/")
            self.assertEqual(200, status)
            return page

    def test_each_row_carries_the_glyph_the_word_and_the_status_class(self):
        page = self.index()

        for ticket_id, status in (("A1", "complete"), ("G2", "blocked"), ("G7", "suspended")):
            row = row_for(page, ticket_id)
            presentation = ui.status_presentation(status)
            self.assertIn(presentation.glyph, row, ticket_id)
            self.assertIn(presentation.word, row, ticket_id)
            self.assertIn("st-{0}".format(status), row, ticket_id)

    def test_every_status_class_in_the_markup_has_a_stylesheet_rule(self):
        page = self.index()

        used = set(re.findall(r'class="st (st-[a-z]+)"', page))
        styled = set(re.findall(r"\.(st-[a-z]+) \{", page))
        self.assertTrue(used)
        self.assertEqual(set(), used - styled)

    def test_every_hue_token_the_page_references_is_declared_on_the_page(self):
        # A `var()` with no declaration and no fallback resolves to nothing,
        # so a dangling token silently drops the whole border.
        page = self.index()

        referenced = set(re.findall(r"var\((--st-[a-z-]+)\)", page))
        declared = set(re.findall(r"(--st-[a-z-]+):\s*[^;]+;", page))
        self.assertTrue(referenced)
        self.assertEqual(set(), referenced - declared)

    def test_an_unknown_status_is_named_unknown_and_still_shown_escaped(self):
        source = (FIXTURES / "run-gamma" / "G6.md").read_text(encoding="utf-8")
        self.assertIn("status: side<b>ways", source)

        page = self.index()

        row = row_for(page, "G6")
        self.assertIn(ui.STATUS_FALLBACK.word, row)
        self.assertIn("st-unknown", row)
        self.assertIn("side&lt;b&gt;ways", row)
        self.assertNotIn("side<b>ways", page)


class TestVerificationParsing(unittest.TestCase):
    """Spec criterion 8 at the parser seam. Two shapes exist in the corpus;
    only one is machine-readable, and saying so is the whole feature."""

    def parsed(self, fixture: str) -> dict:
        text = (FIXTURES / "run-gamma" / fixture).read_text(encoding="utf-8")
        return ui.parse_verification(ui.split_sections(text)["Verification"])

    def test_the_five_column_table_yields_populated_rows(self):
        parsed = self.parsed("G1.md")

        self.assertEqual(ui.VERIFICATION_ROWS, parsed["state"])
        self.assertEqual(3, len(parsed["rows"]))
        for row in parsed["rows"]:
            self.assertEqual(set(ui.VERIFICATION_COLUMNS), set(row))
            for column, value in row.items():
                self.assertTrue(value, column)
        self.assertEqual("PASS", parsed["rows"][0]["verdict"])
        self.assertEqual("FAIL", parsed["rows"][2]["verdict"])
        # A `\|` inside a cell is escaped content, not a column boundary:
        # the real corpus carries regexes in its evidence column.
        self.assertIn("(?:src|href)", parsed["rows"][1]["evidence"])

    def test_the_numbered_prose_list_is_unparsed_and_never_zero_rows(self):
        parsed = self.parsed("G2.md")

        self.assertEqual(ui.VERIFICATION_UNPARSED, parsed["state"])
        self.assertEqual([], parsed["rows"])

    def test_a_header_with_no_data_rows_is_unparsed_rather_than_zero_rows(self):
        parsed = ui.parse_verification(
            "| # | verdict | oracle | class | evidence |\n| --- | --- | --- | --- | --- |\n"
        )

        self.assertEqual(ui.VERIFICATION_UNPARSED, parsed["state"])

    def test_a_row_narrower_than_the_header_leaves_the_whole_section_unparsed(self):
        # Half a table read as rows would report a verdict count that is not
        # the ticket's. Showing the text verbatim loses nothing.
        parsed = ui.parse_verification(
            "| # | verdict | oracle | class | evidence |\n"
            "| --- | --- | --- | --- | --- |\n"
            "| 1 | PASS | the command | deterministic | exit 0 |\n"
            "| 2 | PASS | the command |\n"
        )

        self.assertEqual(ui.VERIFICATION_UNPARSED, parsed["state"])

    def test_an_absent_section_is_reported_as_absent_not_as_unparsed(self):
        text = (FIXTURES / "run-gamma" / "G7.md").read_text(encoding="utf-8")

        self.assertNotIn("Verification", ui.split_sections(text))


class TestTicketDetail(unittest.TestCase):
    """The reading axis: one ticket, its state, its verdicts and its body."""

    def detail(self, main: Path, run: str, ticket_id: str) -> str:
        status, page = ui.render_route(main, detail_url(run, ticket_id))
        self.assertEqual(200, status, ticket_id)
        return page

    def test_the_index_links_every_ticket_to_a_detail_page_that_serves(self):
        with tempfile.TemporaryDirectory() as tmp:
            main = make_checkout(Path(tmp))
            _, index = ui.render_route(main, "/")

            self.assertIn('href="/ticket?run=run-gamma&amp;id=G1"', row_for(index, "G1"))
            page = self.detail(main, "run-gamma", "G1")
            self.assertIn("G1", page)
            self.assertIn("orch-tdd", page)
            self.assertIn(ui.status_presentation("complete").glyph, page)

    def test_the_table_shape_renders_every_verdict_row_with_a_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            main = make_checkout(Path(tmp))

            block = block_for(self.detail(main, "run-gamma", "G1"), "verification")

            for value in ("PASS", "FAIL", "deterministic", "tools/validate.py"):
                self.assertIn(value, block, value)
            self.assertIn("3 entries", block)
            self.assertNotIn(ui.VERIFICATION_UNPARSED, block)

    def test_the_prose_shape_renders_unparsed_verbatim_and_carries_no_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            main = make_checkout(Path(tmp))

            page = self.detail(main, "run-gamma", "G2")
            block = block_for(page, "verification")

            self.assertIn(ui.VERIFICATION_UNPARSED, block)
            self.assertNotIn('class="count"', block)
            self.assertNotIn("0 entries", page)
            # Unparsed is not unshown: the prose itself still reaches the page.
            self.assertIn("comm -23", block)

    def test_an_unresolvable_ticket_is_404_with_both_values_escaped(self):
        with tempfile.TemporaryDirectory() as tmp:
            main = make_checkout(Path(tmp))

            status, page = ui.render_route(main, detail_url("run-gamma", "<script>x"))

            self.assertEqual(404, status)
            self.assertIn("&lt;script&gt;x", page)
            self.assertNotIn("<script>x", page)

    def test_a_query_that_climbs_out_of_the_tickets_tree_resolves_to_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            main = make_checkout(Path(tmp))
            outside = main / ".orch" / "secret.md"
            outside.write_text(
                "---\nid: secret\n---\n\n## Objective\n\nOUTSIDE-THE-TICKETS-TREE\n",
                encoding="utf-8",
            )

            for url in (
                "/ticket",
                "/ticket?run=..&id=secret",
                "/ticket?run=run-gamma%2F..%2F..&id=secret",
                "/ticket?run=.&id=secret",
                detail_url("run-gamma", "..%2F..%2Fsecret"),
            ):
                status, page = ui.render_route(main, url)

                self.assertEqual(404, status, url)
                self.assertNotIn("OUTSIDE-THE-TICKETS-TREE", page, url)


# Names a client can send that the path layer refuses outright rather than
# answering "no such file": NUL raises `ValueError: embedded null byte` out
# of `Path.resolve`, and a component over `NAME_MAX` raises `OSError`
# ENAMETOOLONG out of the stat. Neither is caught by
# `BaseHTTPRequestHandler`, so before the guard the client got no HTTP
# response at all and `socketserver` printed the absolute tickets path.
REFUSED_NAMES = (
    "\x00",
    "lead\x00ing",
    "\x00trailing",
    "\x1f",
    "b" * 300,
    # 253 clears the ceiling on its own and fails it once `.md` is appended,
    # which is the name the lookup actually uses.
    "c" * 253,
)


class TestRefusedNames(unittest.TestCase):
    """The query-to-path boundary. `find_ticket` answers a ticket or
    ``None``, `run_tickets` tickets or ``None`` and `render_route` a
    ``(status, html)`` pair -- for every string a client can send, not only
    for the ones this filesystem happens to tolerate."""

    def urls(self) -> tuple:
        return tuple(
            url
            for name in REFUSED_NAMES
            for url in (
                graph_url(quote(name, safe="")),
                detail_url(quote(name, safe=""), "G1"),
                detail_url("run-gamma", quote(name, safe="")),
            )
        )

    def test_a_refused_name_is_a_named_empty_answer_never_an_exception(self):
        with tempfile.TemporaryDirectory() as tmp:
            main = make_checkout(Path(tmp))

            for name in REFUSED_NAMES:
                self.assertIsNone(ui.find_ticket(main, name, "G1"), ascii(name))
                self.assertIsNone(ui.find_ticket(main, "run-gamma", name), ascii(name))
                self.assertIsNone(ui.run_tickets(main, name), ascii(name))
                self.assertIsNone(ui.read_events(main, name), ascii(name))
            # Non-vacuity: the same three calls still resolve a real name,
            # so `None` above is a rejection rather than a lookup that
            # stopped working.
            self.assertIsNotNone(ui.find_ticket(main, "run-gamma", "G1"))
            self.assertTrue(ui.run_tickets(main, "run-gamma"))

    def test_every_refused_name_renders_a_404_page(self):
        with tempfile.TemporaryDirectory() as tmp:
            main = make_checkout(Path(tmp))

            for url in self.urls():
                status, page = ui.render_route(main, url)

                self.assertEqual(404, status, url)
                self.assertIn("not found", page, url)

    def test_a_refused_name_answers_over_the_socket_rather_than_dropping_it(self):
        # The inline poll loop catches a network error and retries, so a
        # parked browser re-triggers this every second; and a traceback out
        # of `socketserver` discloses the absolute tickets path the
        # silenced `log_message` exists to withhold.
        with tempfile.TemporaryDirectory() as tmp:
            main = make_checkout(Path(tmp))
            with serving(main) as server:
                for url in self.urls():
                    status, _headers, page = fetch(server, url)

                    self.assertEqual(404, status, url)
                    self.assertTrue(page, url)

    def test_the_guard_admits_every_name_the_corpus_actually_uses(self):
        # A ceiling set too low, or a character class drawn too wide, would
        # make this suite's own fixtures unreachable.
        for name in FIXTURE_RUNS + (EMPTY_RUN, "G1", "run-gamma", "a-z_0.9"):
            self.assertEqual(name, ui._safe_name(name), name)


class TestSectionRendering(unittest.TestCase):
    """A ticket body is whatever its author wrote: `contracts/work-item.md`
    fixes eight section names, requires only some of them, and lets a domain
    add its own. The reader shows what is there and invents nothing."""

    def detail(self, main: Path, run: str, ticket_id: str) -> str:
        status, page = ui.render_route(main, detail_url(run, ticket_id))
        self.assertEqual(200, status, ticket_id)
        return page

    def test_a_heading_inside_a_fenced_block_is_content_not_a_section(self):
        text = (FIXTURES / "run-gamma" / "G7.md").read_text(encoding="utf-8")

        sections = ui.split_sections(text)

        # The fenced line names a section the contract does fix, so nothing
        # about the name itself can rescue this: only the fence can.
        self.assertIn("Handoff", contract_sections())
        self.assertNotIn("Handoff", sections)
        # The line is not lost -- it belongs to the section it sits in.
        self.assertIn("## Handoff", sections["Notes on the wire"])

    def test_only_the_sections_the_ticket_carries_are_rendered(self):
        with tempfile.TemporaryDirectory() as tmp:
            main = make_checkout(Path(tmp))

            page = self.detail(main, "run-gamma", "G5")

            self.assertIn("<h2>Objective</h2>", page)
            for absent in ("Verification", "Result", "Risks", "Feedback"):
                self.assertNotIn("<h2>{0}</h2>".format(absent), page, absent)

    def test_a_section_name_outside_the_contract_set_is_still_rendered(self):
        with tempfile.TemporaryDirectory() as tmp:
            main = make_checkout(Path(tmp))

            page = self.detail(main, "run-gamma", "G7")

            self.assertNotIn("Notes on the wire", contract_sections())
            self.assertIn("<h2>Notes on the wire</h2>", page)
            self.assertIn("fixes eight section names", page)

    def test_a_present_but_empty_section_is_named_rather_than_blank(self):
        with tempfile.TemporaryDirectory() as tmp:
            main = make_checkout(Path(tmp))

            page = self.detail(main, "run-gamma", "G7")
            after = page.split("<h2>Result</h2>")[1].split("</section>")[0]

            self.assertIn(ui.EMPTY_SECTION, after)

    def test_sections_render_in_the_order_the_ticket_carries_them(self):
        with tempfile.TemporaryDirectory() as tmp:
            main = make_checkout(Path(tmp))

            page = self.detail(main, "run-gamma", "G7")

            self.assertEqual(
                ["Objective", "Notes on the wire", "Result", "Risks"],
                re.findall(r"<h2>(.*?)</h2>", page),
            )


class TestElapsedMeter(unittest.TestCase):
    """Spec criterion 9: `bound` is prose on real data, and a meter drawn
    from a substituted default would be a fiction."""

    NOW = datetime(2026, 1, 1, 1, 0, 0, tzinfo=timezone.utc)

    def test_only_the_ticket_duration_grammar_yields_minutes(self):
        self.assertEqual(90, ui.bound_minutes("90m"))
        self.assertEqual(120, ui.bound_minutes("2h"))
        for value in ("one session", "", "90", "90 m", "1d", "m90", "-5m", None):
            self.assertIsNone(ui.bound_minutes(value), value)

    def test_this_module_refuses_the_default_bound_its_sibling_substitutes(self):
        # Non-vacuity: the sibling really does default, so `None` here is a
        # decision rather than an accident of the same code path.
        self.assertEqual(
            tickets_mod.DEFAULT_BOUND_MINUTES,
            tickets_mod._parse_bound_minutes("one session"),
        )
        self.assertIsNone(ui.bound_minutes("one session"))

    def test_a_live_claim_with_both_operands_measures_elapsed_against_bound(self):
        meter = ui.claim_meter(
            {"status": "claimed", "bound": "90m", "claimed_at": "2026-01-01T00:00:00Z"},
            self.NOW,
        )

        self.assertEqual(60, meter["elapsed_minutes"])
        self.assertEqual(90, meter["bound_minutes"])
        self.assertEqual(67, meter["percent"])
        self.assertFalse(meter["over"])

    def test_a_claim_past_its_bound_caps_at_full_and_says_so(self):
        meter = ui.claim_meter(
            {"status": "suspended", "bound": "30m", "claimed_at": "2026-01-01T00:00:00Z"},
            self.NOW,
        )

        self.assertEqual(100, meter["percent"])
        self.assertTrue(meter["over"])

    def test_nothing_is_measured_without_two_operands_and_a_live_claim(self):
        for front in (
            {"status": "claimed", "bound": "one session", "claimed_at": "2026-01-01T00:00:00Z"},
            {"status": "claimed", "bound": "90m"},
            {"status": "claimed", "bound": "90m", "claimed_at": "yesterday"},
            {"status": "complete", "bound": "90m", "claimed_at": "2026-01-01T00:00:00Z"},
            {"status": "pending", "bound": "90m", "claimed_at": "2026-01-01T00:00:00Z"},
            {},
        ):
            self.assertIsNone(ui.claim_meter(front, self.NOW), front)

    def claim_line(self, ticket_id: str) -> tuple:
        with tempfile.TemporaryDirectory() as tmp:
            main = make_checkout(Path(tmp))
            status, page = ui.render_route(main, detail_url("run-gamma", ticket_id))
            self.assertEqual(200, status, ticket_id)
            return block_for(page, "claim", "</p>"), page

    def test_a_non_duration_bound_renders_no_meter_and_no_default(self):
        claim, page = self.claim_line("G3")

        self.assertIn("one session", claim)
        self.assertIn(ui.EMPTY_NO_METER, claim)
        self.assertNotIn("<progress", page)
        self.assertNotIn("%", claim)
        # The sibling's 60-minute lease default must not appear as a bound.
        self.assertNotIn("60", claim)

    def test_a_duration_bound_with_a_claim_time_renders_a_meter(self):
        claim, _ = self.claim_line("G4")

        self.assertIn("<progress", claim)
        self.assertIn("%", claim)
        self.assertIn("90m", claim)
        self.assertNotIn(ui.EMPTY_NO_METER, claim)

    def test_claimed_with_no_claim_time_renders_no_meter_and_does_not_raise(self):
        claim, page = self.claim_line("G5")

        self.assertIn(ui.EMPTY_UNSET, claim)
        self.assertIn(ui.EMPTY_NO_METER, claim)
        self.assertNotIn("<progress", page)
        self.assertNotIn("%", claim)


def coordinates(layout: dict) -> bytes:
    """The layout's coordinates as bytes, so "identical" is byte identity
    rather than a comparison that a float's repr could paper over."""

    return "\n".join(
        "{0} {1} {2} {3} {4}".format(node.id, node.layer, node.order, node.x, node.y)
        for node in layout["nodes"]
    ).encode("utf-8")


def fan_graph(width: int) -> tuple:
    """One root, ``width`` middles, one sink: the shape whose within-layer
    ordering has the most ties, and so the most room to come out unstable."""

    ids = ("R",) + tuple("M{0}".format(i) for i in range(width)) + ("S",)
    edges = tuple(("R", "M{0}".format(i)) for i in range(width))
    edges += tuple(("M{0}".format(i), "S") for i in range(width))
    return ids, edges


class TestGraphLayout(unittest.TestCase):
    """Spec criterion 6. A layered layout with a Coffman-Graham sorter, the
    shape Argo Workflows ships hand-rolled in 56 + 48 lines with zero
    dependencies (`lane-ui-patterns.md` §3), computed in Python so a layout
    bug is a failing unit test rather than a visual regression."""

    IDS = ("D1", "D2", "D3", "D4", "D5")
    EDGES = (("D1", "D2"), ("D1", "D3"), ("D2", "D4"), ("D3", "D4"), ("D4", "D5"))

    def test_two_calls_on_equal_input_return_byte_equal_coordinates(self):
        first = ui.graph_layout(self.IDS, self.EDGES)
        second = ui.graph_layout(self.IDS, self.EDGES)

        self.assertTrue(coordinates(first))
        self.assertEqual(coordinates(first), coordinates(second))
        # Byte equality is only meaningful because every coordinate is an
        # integer: a float would make it a fact about repr, not about layout.
        for node in first["nodes"]:
            for value in (node.layer, node.order, node.x, node.y):
                self.assertIsInstance(value, int, node)

    def test_input_order_does_not_move_a_single_node(self):
        # Set and dict iteration is where a layout loses determinism, and it
        # loses it silently: the same call in one process keeps agreeing.
        forward = ui.graph_layout(self.IDS, self.EDGES)
        reversed_input = ui.graph_layout(
            tuple(reversed(self.IDS)), tuple(reversed(self.EDGES))
        )

        self.assertEqual(coordinates(forward), coordinates(reversed_input))

    def test_a_wide_graph_with_every_tie_still_lays_out_identically_twice(self):
        ids, edges = fan_graph(9)

        first = ui.graph_layout(ids, edges)
        second = ui.graph_layout(tuple(reversed(ids)), tuple(reversed(edges)))

        self.assertEqual(coordinates(first), coordinates(second))
        self.assertEqual(len(ids), len(first["nodes"]))

    def test_every_edge_runs_from_a_strictly_lower_layer_to_a_strictly_higher_one(self):
        layout = ui.graph_layout(self.IDS, self.EDGES)
        layer = {node.id: node.layer for node in layout["nodes"]}

        self.assertEqual([], layout["diagnostics"])
        for source, target in layout["edges"]:
            self.assertLess(layer[source], layer[target], (source, target))
        # Non-vacuity: a layout that dropped every edge, or collapsed the
        # graph onto one layer, would satisfy the loop above and nothing else.
        self.assertEqual(len(self.EDGES), len(layout["edges"]))
        self.assertEqual(4, len(set(layer.values())))
        self.assertEqual(0, layer["D1"])

    def test_the_layer_law_survives_a_graph_wider_than_the_layer_bound(self):
        ids, edges = fan_graph(9)

        layout = ui.graph_layout(ids, edges)
        layer = {node.id: node.layer for node in layout["nodes"]}

        self.assertGreater(9, ui.LAYER_WIDTH)
        for source, target in layout["edges"]:
            self.assertLess(layer[source], layer[target], (source, target))
        counts = {}
        for value in layer.values():
            counts[value] = counts.get(value, 0) + 1
        self.assertTrue(counts)
        for value, count in counts.items():
            self.assertLessEqual(count, ui.LAYER_WIDTH, (value, count))

    def test_no_two_nodes_share_a_coordinate(self):
        ids, edges = fan_graph(9)

        for layout in (ui.graph_layout(*fan_graph(9)), ui.graph_layout(self.IDS, self.EDGES)):
            points = [(node.x, node.y) for node in layout["nodes"]]
            self.assertEqual(len(points), len(set(points)), points)

    def test_an_empty_graph_lays_out_to_nothing_rather_than_raising(self):
        layout = ui.graph_layout((), ())

        self.assertEqual([], layout["nodes"])
        self.assertEqual([], layout["edges"])
        self.assertEqual([], layout["diagnostics"])


class TestGraphDiagnostics(unittest.TestCase):
    """Spec criterion 7. Nothing on the write path proves a `depends_on` set
    is a DAG, and `.orch/` is untrusted data, so the layout is total over
    every edge set: it terminates, it never raises, and what it cannot
    honour it names."""

    CYCLE = (("E3", "E1"), ("E1", "E2"), ("E2", "E3"))
    IDS = ("E1", "E2", "E3")

    def layer_law_holds(self, layout: dict):
        layer = {node.id: node.layer for node in layout["nodes"]}
        for source, target in layout["edges"]:
            self.assertLess(layer[source], layer[target], (source, target))

    def test_a_cycle_is_reported_as_a_named_diagnostic_and_never_raised(self):
        layout = ui.graph_layout(self.IDS, self.CYCLE)

        self.assertEqual(3, len(layout["nodes"]))
        self.assertEqual(1, len(layout["diagnostics"]), layout["diagnostics"])
        diagnostic = layout["diagnostics"][0]
        self.assertTrue(diagnostic.startswith(ui.DIAGNOSTIC_CYCLE), diagnostic)
        for node_id in self.IDS:
            self.assertIn(node_id, diagnostic, diagnostic)

    def test_breaking_the_cycle_leaves_every_remaining_edge_obeying_the_layer_law(self):
        layout = ui.graph_layout(self.IDS, self.CYCLE)

        self.layer_law_holds(layout)
        # Exactly one arc is withheld: dropping the whole cycle would lose
        # two true dependencies to report one false one.
        self.assertEqual(len(self.CYCLE) - 1, len(layout["edges"]))

    def test_the_diagnostic_does_not_depend_on_the_order_the_edges_arrive_in(self):
        first = ui.graph_layout(self.IDS, self.CYCLE)
        shuffled = ui.graph_layout(
            tuple(reversed(self.IDS)), (self.CYCLE[1], self.CYCLE[2], self.CYCLE[0])
        )

        self.assertEqual(first["diagnostics"], shuffled["diagnostics"])
        self.assertEqual(coordinates(first), coordinates(shuffled))

    def test_a_ticket_depending_on_itself_is_named_rather_than_drawn(self):
        layout = ui.graph_layout(("X", "Y"), (("X", "X"), ("X", "Y")))

        self.assertEqual([("X", "Y")], layout["edges"])
        self.assertEqual(1, len(layout["diagnostics"]))
        self.assertIn(ui.DIAGNOSTIC_CYCLE, layout["diagnostics"][0])

    def test_a_dependency_on_a_ticket_outside_the_run_is_named_and_dropped(self):
        layout = ui.graph_layout(("E1", "E4"), (("ZZ9", "E4"), ("E1", "E4")))

        self.assertEqual(["E1", "E4"], [node.id for node in layout["nodes"]])
        self.assertEqual([("E1", "E4")], layout["edges"])
        self.assertEqual(1, len(layout["diagnostics"]), layout["diagnostics"])
        self.assertTrue(layout["diagnostics"][0].startswith(ui.DIAGNOSTIC_DANGLING))
        self.assertIn("ZZ9", layout["diagnostics"][0])

    def test_a_graph_that_is_nothing_but_cycles_still_terminates(self):
        # Every ordered pair of eight nodes, so every edge sits on a cycle
        # and a naive "drop one edge and retry" that picked a chord would
        # never converge. The suite's own runtime is the timeout.
        ids = tuple("N{0}".format(i) for i in range(8))
        edges = tuple((a, b) for a in ids for b in ids if a != b)

        layout = ui.graph_layout(ids, edges)

        self.assertEqual(8, len(layout["nodes"]))
        self.assertTrue(layout["diagnostics"])
        self.layer_law_holds(layout)

    def test_both_diagnostics_can_be_reported_at_once(self):
        layout = ui.graph_layout(("A", "B"), (("A", "B"), ("B", "A"), ("GONE", "A")))

        named = " ".join(layout["diagnostics"])
        self.assertIn(ui.DIAGNOSTIC_CYCLE, named)
        self.assertIn(ui.DIAGNOSTIC_DANGLING, named)


class TestGraphView(unittest.TestCase):
    """The graph route: coordinates from the server, rendered as inline SVG.
    No canvas and no external asset -- `install.py`'s `SCRIPT_NAMES` ships
    flat filenames, so a sidecar asset would never reach `~/.orchflows/bin`
    even if the no-network law allowed one."""

    def graph(self, main: Path, run: str) -> str:
        status, page = ui.render_route(main, graph_url(run))
        self.assertEqual(200, status, run)
        return page

    def test_a_ticket_carries_its_dependencies_and_its_claimant(self):
        ticket = ui.read_ticket(FIXTURES / SETTLED_RUN / "D4.md")

        self.assertEqual(("D2", "D3"), ticket["depends_on"])
        self.assertEqual("fixture-agent", ticket["claimed_by"])
        # Both `depends_on` spellings the frontmatter parser accepts reach
        # the graph identically; only the fixtures know which is which.
        self.assertEqual(
            ("D1",), ui.read_ticket(FIXTURES / SETTLED_RUN / "D2.md")["depends_on"]
        )
        self.assertEqual((), ui.read_ticket(FIXTURES / SETTLED_RUN / "D1.md")["depends_on"])

    def test_the_graph_draws_one_node_per_ticket_and_one_edge_per_dependency(self):
        with tempfile.TemporaryDirectory() as tmp:
            main = make_checkout(Path(tmp))

            page = self.graph(main, SETTLED_RUN)

            self.assertIn("<svg", page)
            self.assertNotIn("<canvas", page)
            self.assertEqual(5, len(re.findall(r'<g class="nd', page)), page)
            self.assertEqual(5, len(re.findall(r'<line class="edge"', page)))
            for ticket_id in ("D1", "D2", "D3", "D4", "D5"):
                self.assertIn(">{0}<".format(ticket_id), page, ticket_id)

    def test_every_drawn_edge_points_downward_on_the_canvas(self):
        # The layer law is a fact about integers; this is the fact about the
        # picture, and one sign error separates them.
        with tempfile.TemporaryDirectory() as tmp:
            main = make_checkout(Path(tmp))

            page = self.graph(main, SETTLED_RUN)

            drawn = re.findall(r'<line class="edge" x1="\d+" y1="(\d+)" x2="\d+" y2="(\d+)"', page)
            self.assertEqual(5, len(drawn))
            for y1, y2 in drawn:
                self.assertLess(int(y1), int(y2), (y1, y2))

    def test_each_node_carries_its_status_and_links_to_its_ticket(self):
        with tempfile.TemporaryDirectory() as tmp:
            main = make_checkout(Path(tmp))

            page = self.graph(main, SETTLED_RUN)

            self.assertIn('href="/ticket?run=run-delta&amp;id=D3"', page)
            self.assertIn("nd-failed", page)
            self.assertIn(ui.status_presentation("failed").glyph, page)

    def test_a_cyclic_run_displays_the_named_diagnostic_and_still_draws(self):
        with tempfile.TemporaryDirectory() as tmp:
            main = make_checkout(Path(tmp))

            page = self.graph(main, CYCLIC_RUN)

            diagnostics = block_for(page, "diagnostics", "</ul>")
            self.assertIn(ui.DIAGNOSTIC_CYCLE, diagnostics)
            self.assertIn(ui.DIAGNOSTIC_DANGLING, diagnostics)
            self.assertIn("ZZ9", diagnostics)
            # Named, not fatal: the four nodes are still on the page.
            self.assertEqual(4, len(re.findall(r'<g class="nd', page)))

    def test_a_run_with_no_dependencies_draws_nodes_and_no_edges(self):
        with tempfile.TemporaryDirectory() as tmp:
            main = make_checkout(Path(tmp))

            page = self.graph(main, "run-beta")

            self.assertIn("<svg", page)
            self.assertIn('<g class="nd', page)
            self.assertNotIn('<line class="edge"', page)
            self.assertEqual("", block_for(page, "diagnostics", "</ul>"))

    def test_a_run_with_no_tickets_names_the_empty_state_instead_of_drawing(self):
        with tempfile.TemporaryDirectory() as tmp:
            main = make_checkout(Path(tmp))

            page = self.graph(main, EMPTY_RUN)

            self.assertIn(ui.EMPTY_NO_TICKETS, page)
            self.assertNotIn("<svg", page)

    def test_an_unresolvable_run_is_404_with_the_value_escaped(self):
        with tempfile.TemporaryDirectory() as tmp:
            main = make_checkout(Path(tmp))

            for url in ("/graph", graph_url("no-such-run"), graph_url("..")):
                status, page = ui.render_route(main, url)
                self.assertEqual(404, status, url)

            status, page = ui.render_route(main, graph_url("%3Cscript%3Ex"))
            self.assertEqual(404, status)
            self.assertIn("&lt;script&gt;x", page)
            self.assertNotIn("<script>x", page)

    def test_an_out_of_contract_status_is_drawn_from_the_closed_set(self):
        # G6's `status` carries markup. The graph never interpolates a raw
        # status at all -- it draws the presentation the closed set maps to
        # -- so the fact worth holding is that the fallback was drawn, on
        # G6's own node, rather than that markup is missing from the page.
        with tempfile.TemporaryDirectory() as tmp:
            page = self.graph(make_checkout(Path(tmp)), "run-gamma")

            self.assertEqual(
                "nd-{0}".format(ui.STATUS_FALLBACK.word), node_for(page, "G6")
            )
            self.assertIn(ui.STATUS_FALLBACK.glyph, page)
            self.assertNotIn("side<b>ways", page)

    def test_every_untrusted_value_the_graph_interpolates_reaches_it_escaped(self):
        # A run name and a ticket id are directory and file names, so the
        # payload has to be one a filesystem will accept: `&` is legal on
        # every platform this runs on, and is exactly the character that
        # ends an href's query parameter early if it is not escaped.
        run = "run&sub"
        with tempfile.TemporaryDirectory() as tmp:
            root = make_checkout(Path(tmp), runs=())
            run_dir = root / ".orch" / "tickets" / run
            write_ticket(run_dir, "T&1", status="done")
            write_ticket(run_dir, "T&2", status="ready", depends_on="T&1")

            status, page = ui.render_route(
                root, "/graph?run={0}".format(quote(run, safe=""))
            )
            self.assertEqual(200, status)

            self.assertIn('aria-label="dependency graph for run&amp;sub"', page)
            self.assertIn('href="/ticket?run=run%26sub&amp;id=T%261"', page)
            self.assertIn('<text class="nd-id" x="10" y="19">T&amp;1</text>', page)
            self.assertNotIn("run&sub", page)
            self.assertNotIn(">T&1<", page)

    def test_a_dependency_naming_markup_reaches_the_diagnostic_escaped(self):
        # `depends_on` is the one untrusted value that reaches the page as
        # free text rather than as a name the corpus vouches for: a dangling
        # target is reported verbatim and need never have been a filename.
        with tempfile.TemporaryDirectory() as tmp:
            root = make_checkout(Path(tmp), runs=())
            write_ticket(
                root / ".orch" / "tickets" / "run-ghost",
                "H1",
                status="ready",
                depends_on="<b>ghost</b>",
            )

            page = self.graph(root, "run-ghost")

            diagnostics = block_for(page, "diagnostics", "</ul>")
            self.assertIn(ui.DIAGNOSTIC_DANGLING, diagnostics)
            self.assertIn("&lt;b&gt;ghost&lt;/b&gt;", diagnostics)
            self.assertNotIn("<b>ghost</b>", page)

    def test_the_index_offers_a_graph_for_every_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            main = make_checkout(Path(tmp))

            _, index = ui.render_route(main, "/")

            for run in FIXTURE_RUNS + (EMPTY_RUN,):
                self.assertIn('href="/graph?run={0}"'.format(run), index, run)


def write_raw_ticket(run_dir: Path, file_name: str, declared_id: str, **fields) -> Path:
    """A ticket whose file name and declared ``id:`` are set separately, for
    the case ``write_ticket`` cannot express: the two disagreeing."""

    run_dir.mkdir(parents=True, exist_ok=True)
    lines = ["---", "id: {0}".format(declared_id)]
    lines.extend("{0}: {1}".format(key, value) for key, value in fields.items())
    lines.extend(["---", ""])
    path = run_dir / file_name
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


class TestTicketIdentity(unittest.TestCase):
    """A ticket carries two identities: the frontmatter `id:` the page
    displays and links, and the file name every lookup resolves. Nothing on
    the write path keeps them equal -- a ticket copied or renamed between
    runs keeps the id it was written with -- and where they differ every
    link the page emits for that ticket is dead. The reader names what it
    cannot honour everywhere else; this is the last place it went silent."""

    RUN = "run-identity"

    def checkout(self, tmp: str, tickets) -> Path:
        root = make_checkout(Path(tmp), runs=(), friction=False, events=False)
        for file_name, declared_id in tickets:
            write_raw_ticket(
                root / ".orch" / "tickets" / self.RUN,
                file_name,
                declared_id,
                status="ready",
            )
        return root

    def diagnostics(self, page: str) -> str:
        return block_for(page, "diagnostics", "</ul>")

    def test_a_declared_id_that_is_not_its_file_name_is_named_on_the_index(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.checkout(tmp, (("C1.md", "renamed"),))

            page = ui.render_route(root, "/")[1]

            named = self.diagnostics(section_for(page, self.RUN))
            self.assertNotEqual("", named)
            self.assertIn(ui.DIAGNOSTIC_ID_MISMATCH, named)
            self.assertIn("renamed", named)
            self.assertIn("C1.md", named)

    def test_the_same_mismatch_is_named_on_the_graph(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.checkout(tmp, (("C1.md", "renamed"),))

            page = ui.render_route(root, graph_url(self.RUN))[1]

            self.assertIn(ui.DIAGNOSTIC_ID_MISMATCH, self.diagnostics(page))
            # Named, not fatal: the node is still drawn.
            self.assertIn(">renamed<", page)

    def test_the_diagnostic_names_a_link_that_really_is_dead(self):
        # Without this the diagnostic could be true of nothing: the row,
        # the node and the band all link the declared id, and that is the
        # id no lookup resolves.
        with tempfile.TemporaryDirectory() as tmp:
            root = self.checkout(tmp, (("C1.md", "renamed"),))

            page = ui.render_route(root, "/")[1]

            self.assertIn('href="/ticket?run=run-identity&amp;id=renamed"', page)
            self.assertEqual(404, ui.render_route(root, detail_url(self.RUN, "renamed"))[0])
            self.assertEqual(200, ui.render_route(root, detail_url(self.RUN, "C1"))[0])

    def test_two_files_declaring_one_id_are_named_and_one_node_is_drawn(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.checkout(tmp, (("C1.md", "dup"), ("C2.md", "dup")))

            page = ui.render_route(root, graph_url(self.RUN))[1]

            named = self.diagnostics(page)
            self.assertIn(ui.DIAGNOSTIC_ID_COLLISION, named)
            self.assertIn("C1.md", named)
            self.assertIn("C2.md", named)
            # The collapse the diagnostic exists for: two tickets, one node.
            self.assertEqual(2, len(ui.run_tickets(root, self.RUN)))
            self.assertEqual(1, len(re.findall(r'<g class="nd', page)))

    def test_a_declared_id_carrying_markup_reaches_the_diagnostic_escaped(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.checkout(tmp, (("C1.md", "<b>x</b>"),))

            page = ui.render_route(root, graph_url(self.RUN))[1]

            self.assertIn("&lt;b&gt;x&lt;/b&gt;", self.diagnostics(page))
            self.assertNotIn("<b>x</b>", page)

    def test_a_run_whose_ids_all_match_their_files_says_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            main = make_checkout(Path(tmp))

            self.assertEqual([], ui.identity_diagnostics(ui.run_tickets(main, "run-gamma")))
            index = ui.render_route(main, "/")[1]
            for run in FIXTURE_RUNS:
                self.assertNotIn(
                    ui.DIAGNOSTIC_ID_MISMATCH, self.diagnostics(section_for(index, run)), run
                )

    def test_an_unreadable_frontmatter_falls_back_to_the_file_name_silently(self):
        # A ticket with no `id:` at all already resolves both ways, so it
        # must not be reported as a disagreement.
        with tempfile.TemporaryDirectory() as tmp:
            root = make_checkout(Path(tmp), runs=(), friction=False, events=False)
            run_dir = root / ".orch" / "tickets" / self.RUN
            run_dir.mkdir(parents=True)
            (run_dir / "C9.md").write_text("no frontmatter at all\n", encoding="utf-8")

            tickets = ui.run_tickets(root, self.RUN)

            self.assertEqual(["C9"], [ticket["id"] for ticket in tickets])
            self.assertEqual([], ui.identity_diagnostics(tickets))


class TestLayoutCache(unittest.TestCase):
    """`lane-ui-patterns.md` §6(3): re-laying out a graph on a refresh that
    moved no node is a live defect in a shipped orchestrator, whose own fix
    sits in the source commented out. At a one-second poll the cost is paid
    once per second forever, so the guard is the feature."""

    def setUp(self):
        ui.LAYOUT_CACHE.clear()
        self.addCleanup(ui.LAYOUT_CACHE.clear)

    @contextlib.contextmanager
    def counting(self):
        with patch.object(ui, "graph_layout", side_effect=ui.graph_layout) as computed:
            yield computed

    def test_two_requests_over_an_unchanged_ticket_set_lay_out_exactly_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            main = make_checkout(Path(tmp))

            with self.counting() as computed:
                first = ui.render_route(main, graph_url(SETTLED_RUN))[1]
                second = ui.render_route(main, graph_url(SETTLED_RUN))[1]

            self.assertEqual(1, computed.call_count)
            self.assertEqual(first, second)
            # The counter can reach two, so one is a measurement rather than
            # a mock that was never wired to anything.
            with self.counting() as recomputed:
                ui.LAYOUT_CACHE.clear()
                ui.render_route(main, graph_url(SETTLED_RUN))
                ui.LAYOUT_CACHE.clear()
                ui.render_route(main, graph_url(SETTLED_RUN))
            self.assertEqual(2, recomputed.call_count)

    def test_a_status_change_repaints_without_laying_the_graph_out_again(self):
        with tempfile.TemporaryDirectory() as tmp:
            main = make_checkout(Path(tmp))
            ticket = main / ".orch" / "tickets" / SETTLED_RUN / "D3.md"

            with self.counting() as computed:
                before = ui.render_route(main, graph_url(SETTLED_RUN))[1]
                ticket.write_text(
                    ticket.read_text(encoding="utf-8").replace(
                        "status: failed", "status: complete"
                    ),
                    encoding="utf-8",
                )
                after = ui.render_route(main, graph_url(SETTLED_RUN))[1]

            self.assertEqual(1, computed.call_count)
            self.assertEqual("nd-failed", node_for(before, "D3"))
            self.assertEqual("nd-complete", node_for(after, "D3"))

    def test_a_node_or_an_edge_appearing_does_lay_the_graph_out_again(self):
        with tempfile.TemporaryDirectory() as tmp:
            main = make_checkout(Path(tmp))
            run_dir = main / ".orch" / "tickets" / SETTLED_RUN

            with self.counting() as computed:
                ui.render_route(main, graph_url(SETTLED_RUN))
                (run_dir / "D6.md").write_text(
                    "---\nid: D6\nstatus: ready\ndepends_on: [D5]\n---\n", encoding="utf-8"
                )
                ui.render_route(main, graph_url(SETTLED_RUN))
                edged = run_dir / "D2.md"
                edged.write_text(
                    edged.read_text(encoding="utf-8").replace("  - D1", "  - D3"),
                    encoding="utf-8",
                )
                page = ui.render_route(main, graph_url(SETTLED_RUN))[1]

            self.assertEqual(3, computed.call_count)
            self.assertIn(">D6<", page)

    def test_two_runs_never_serve_each_other_a_cached_layout(self):
        with tempfile.TemporaryDirectory() as tmp:
            main = make_checkout(Path(tmp))

            delta = ui.render_route(main, graph_url(SETTLED_RUN))[1]
            epsilon = ui.render_route(main, graph_url(CYCLIC_RUN))[1]

            self.assertIn(">D5<", delta)
            self.assertNotIn(">D5<", epsilon)
            self.assertIn(">E4<", epsilon)
            self.assertEqual(2, len(ui.LAYOUT_CACHE))

    def test_the_cache_is_bounded_so_a_long_lived_viewer_cannot_grow_forever(self):
        for index in range(ui.LAYOUT_CACHE_LIMIT * 2):
            ui.cached_layout(("N{0}".format(index),), ())

        self.assertEqual(ui.LAYOUT_CACHE_LIMIT, len(ui.LAYOUT_CACHE))

    def test_a_cache_hit_returns_the_layout_that_was_computed_for_that_key(self):
        ids, edges = fan_graph(5)

        computed = ui.graph_layout(ids, edges)
        first = ui.cached_layout(ids, edges)
        second = ui.cached_layout(tuple(reversed(ids)), tuple(reversed(edges)))

        self.assertEqual(coordinates(computed), coordinates(first))
        self.assertIs(first, second)


BAND_ID_RE = re.compile(r'<li class="claim">.*?<a [^>]*>([^<]+)</a>')


def band_ids(page: str) -> list:
    return BAND_ID_RE.findall(block_for(page, "band", "</ul>"))


def band_entry(page: str, ticket_id: str) -> str:
    """The band entry for ``ticket_id``, so a field is proved to sit with
    its own claim rather than with some other executor's."""

    for fragment in block_for(page, "band", "</ul>").split('<li class="claim">')[1:]:
        entry = fragment.split("</li>")[0]
        if ">{0}</a>".format(ticket_id) in entry:
            return entry
    return ""


class TestActiveBand(unittest.TestCase):
    """`U3` completion test 6, for the band the spec's view scope names.
    Which executors are at work right now is the question an orchestrator
    asks between polls, and reading it off the run tables costs a scan of
    every ticket in every run."""

    def index(self, tmp: str, runs=FIXTURE_RUNS) -> str:
        return ui.render_route(make_checkout(Path(tmp), runs=runs), "/")[1]

    def test_the_band_lists_exactly_the_tickets_whose_status_is_claimed(self):
        with tempfile.TemporaryDirectory() as tmp:
            page = self.index(tmp)

            self.assertEqual(["A2", "G3", "G4", "G5"], band_ids(page))
            # G7 is suspended and G2 blocked: both hold a claim, neither is
            # an executor at work, and the meter's wider notion of live is
            # not this band's.
            self.assertNotIn("G7", band_ids(page))
            self.assertNotIn("G2", band_ids(page))

    def test_the_band_is_absent_when_nothing_is_claimed(self):
        with tempfile.TemporaryDirectory() as tmp:
            page = self.index(tmp, runs=(SETTLED_RUN,))

            self.assertEqual("", block_for(page, "band", "</ul>"))
            self.assertNotIn('<ul class="band"', page)
            # The page itself still rendered, so the band's absence is not
            # the absence of the index.
            self.assertIn(">D1<", page)

    def test_each_entry_names_its_run_ticket_executor_and_claimant(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_checkout(Path(tmp), runs=())
            write_ticket(
                root / ".orch" / "tickets" / "run-one",
                "K1",
                status="claimed",
                executor="orch-tdd",
                claimed_by="agent-one",
            )
            write_ticket(
                root / ".orch" / "tickets" / "run-two",
                "K2",
                status="claimed",
                executor="orch-verify",
                claimed_by="agent-two",
            )
            page = ui.render_route(root, "/")[1]

            self.assertEqual(["K1", "K2"], band_ids(page))
            for wanted in ("run-one", "K1", "orch-tdd", "agent-one"):
                self.assertIn(wanted, band_entry(page, "K1"), wanted)
            for wanted in ("run-two", "K2", "orch-verify", "agent-two"):
                self.assertIn(wanted, band_entry(page, "K2"), wanted)
            # Each claimant sits with its own claim rather than anywhere.
            self.assertNotIn("agent-two", band_entry(page, "K1"))

    def test_an_entry_links_to_the_ticket_it_names(self):
        with tempfile.TemporaryDirectory() as tmp:
            entry = band_entry(self.index(tmp), "G3")

            self.assertIn('href="/ticket?run=run-gamma&amp;id=G3"', entry)

    def test_a_claim_that_can_be_measured_carries_its_meter(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIn("<progress", band_entry(self.index(tmp), "G4"))

    def test_a_claim_with_nothing_to_measure_is_listed_without_a_meter(self):
        # G5 is claimed and carries no `claimed_at`; G3's bound is not a
        # duration. Both are real shapes, and a band that dropped either
        # would hide a working executor.
        with tempfile.TemporaryDirectory() as tmp:
            page = self.index(tmp)

            for ticket_id in ("G3", "G5"):
                entry = band_entry(page, ticket_id)
                self.assertNotIn("<progress", entry, ticket_id)
                self.assertIn(ui.EMPTY_NO_METER, entry, ticket_id)

    def test_an_unset_executor_or_claimant_is_named_rather_than_left_blank(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_checkout(Path(tmp), runs=())
            write_ticket(root / ".orch" / "tickets" / "run-one", "K1", status="claimed")
            entry = band_entry(ui.render_route(root, "/")[1], "K1")

            self.assertEqual(2, entry.count(ui.EMPTY_UNSET), entry)

    def test_an_untrusted_claimant_reaches_the_band_escaped(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_checkout(Path(tmp), runs=())
            write_ticket(
                root / ".orch" / "tickets" / "run-one",
                "K1",
                status="claimed",
                claimed_by="<b>agent</b>",
            )
            page = ui.render_route(root, "/")[1]

            self.assertIn("&lt;b&gt;agent&lt;/b&gt;", page)
            self.assertNotIn("<b>agent</b>", page)

    def test_the_band_sits_above_the_runs_it_summarises(self):
        with tempfile.TemporaryDirectory() as tmp:
            page = self.index(tmp)

            self.assertLess(page.index('class="band"'), page.index('class="run"'))


SCRIPT_RE = re.compile(r"<script>(.*?)</script>", re.S)
LIVE_RE = re.compile(r'<main data-live="([a-z]+)">')


class TestPolling(unittest.TestCase):
    """`U3` completion test 8. `lane-ui-patterns.md` §4: stdlib
    `http.server` never speaks HTTP/2, so the browser's six-connection cap
    applies in full and one held stream would deadlock a serial server.
    Interval polling is the transport, and the interval is the whole
    design."""

    def script(self, page: str) -> str:
        found = SCRIPT_RE.findall(page)
        self.assertEqual(1, len(found), "expected exactly one inline script")
        return found[0]

    def live(self, root: Path, route: str) -> str:
        return LIVE_RE.search(ui.render_route(root, route)[1]).group(1)

    def test_every_polling_constant_the_spec_names_is_bound_in_the_emitted_js(self):
        # Each interval is bound to its own name. A bare substring search
        # cannot tell these three apart -- "1000" is inside "15000" and
        # "5000" is inside "15000" too -- so a page that emitted only the
        # hidden interval would satisfy all three.
        with tempfile.TemporaryDirectory() as tmp:
            source = self.script(ui.render_route(make_checkout(Path(tmp)), "/")[1])

            for name, milliseconds in (
                ("LIVE_MS", ui.POLL_LIVE_MS),
                ("IDLE_MS", ui.POLL_IDLE_MS),
                ("HIDDEN_MS", ui.POLL_HIDDEN_MS),
            ):
                bound = re.compile(
                    r"\b{0}\s*=\s*{1}\b".format(name, milliseconds)
                )
                self.assertRegex(source, bound, name)
            self.assertIn("document.hidden", source)

    def test_the_binding_test_can_tell_the_three_intervals_apart(self):
        # The discrimination the assertion above rests on, made explicit:
        # against a page emitting one interval under all three names, two of
        # the three patterns must fail.
        source = "  var LIVE_MS = 15000, IDLE_MS = 15000, HIDDEN_MS = 15000;\n"

        matched = [
            re.search(r"\b{0}\s*=\s*{1}\b".format(name, milliseconds), source)
            for name, milliseconds in (
                ("LIVE_MS", ui.POLL_LIVE_MS),
                ("IDLE_MS", ui.POLL_IDLE_MS),
                ("HIDDEN_MS", ui.POLL_HIDDEN_MS),
            )
        ]

        self.assertEqual([None, None], matched[:2])
        self.assertIsNotNone(matched[2])

    def test_those_constants_are_the_module_s_own(self):
        self.assertEqual(
            (1000, 5000, 15000),
            (ui.POLL_LIVE_MS, ui.POLL_IDLE_MS, ui.POLL_HIDDEN_MS),
        )

    def test_no_route_emits_setinterval(self):
        # `setInterval` queues a second request behind a slow first one; on a
        # serial stdlib server that is how a poll becomes a pile-up.
        with tempfile.TemporaryDirectory() as tmp:
            main = make_checkout(Path(tmp))
            for route in every_route():
                page = ui.render_route(main, route)[1]
                self.assertNotIn("setInterval", page, route)
                self.assertIn("setTimeout", page, route)

    def test_the_poll_revalidates_with_the_tag_it_was_given(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = self.script(ui.render_route(make_checkout(Path(tmp)), "/")[1])

            self.assertIn("If-None-Match", source)
            self.assertIn("304", source)

    def test_the_script_is_inline_and_names_no_remote_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            main = make_checkout(Path(tmp))
            for route in every_route():
                page = ui.render_route(main, route)[1]
                self.assertNotIn("<script src", page, route)
                self.assertNotIn("<script ", page, route)

    def test_a_run_with_work_under_way_polls_at_the_live_interval(self):
        with tempfile.TemporaryDirectory() as tmp:
            main = make_checkout(Path(tmp))

            # run-gamma holds claimed tickets; run-epsilon holds a ready one.
            self.assertEqual("yes", self.live(main, graph_url("run-gamma")))
            self.assertEqual("yes", self.live(main, graph_url(CYCLIC_RUN)))

    def test_a_run_whose_every_ticket_is_terminal_polls_at_the_idle_interval(self):
        with tempfile.TemporaryDirectory() as tmp:
            main = make_checkout(Path(tmp))

            self.assertEqual("no", self.live(main, graph_url(SETTLED_RUN)))
            self.assertEqual("no", self.live(main, graph_url(EMPTY_RUN)))

    def test_the_index_is_live_while_any_run_is(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual("yes", self.live(make_checkout(Path(tmp)), "/"))
        with tempfile.TemporaryDirectory() as tmp:
            settled = make_checkout(Path(tmp), runs=(SETTLED_RUN,))
            self.assertEqual("no", self.live(settled, "/"))

    def test_a_ticket_page_is_live_only_while_its_own_ticket_is(self):
        with tempfile.TemporaryDirectory() as tmp:
            main = make_checkout(Path(tmp))

            self.assertEqual("yes", self.live(main, detail_url("run-gamma", "G3")))
            self.assertEqual("no", self.live(main, detail_url("run-gamma", "G1")))
            # `suspended` holds the lease with nobody at the keyboard: the
            # meter keeps running, the page has nothing to wait for.
            self.assertEqual("no", self.live(main, detail_url("run-gamma", "G7")))

    def test_a_page_with_no_ticket_in_view_polls_at_the_idle_interval(self):
        with tempfile.TemporaryDirectory() as tmp:
            main = make_checkout(Path(tmp))

            self.assertEqual("no", self.live(main, ui.FRICTION_ROUTE))
            self.assertEqual("no", self.live(main, "/no-such-route"))


TS_RE = re.compile(r'<span class="ts">([^<]*)</span>')


class TestFrictionFeed(unittest.TestCase):
    """`U3` completion test 7. The friction law says a session that hit
    friction and logged nothing failed silently; a feed that dies on one
    half-written line is the same failure one layer up."""

    def feed(self, tmp: str, friction=True) -> str:
        root = make_checkout(Path(tmp), friction=friction)
        status, page = ui.render_route(root, ui.FRICTION_ROUTE)
        self.assertEqual(200, status)
        return page

    def test_every_well_formed_entry_from_every_log_is_rendered(self):
        with tempfile.TemporaryDirectory() as tmp:
            page = self.feed(tmp)

            self.assertEqual(5, len(TS_RE.findall(page)))
            self.assertIn("tools/validate.py discovered no file under scripts/", page)
            self.assertIn("a route added by branching inside the dispatcher", page)

    def test_entries_are_newest_first_across_the_log_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            stamps = TS_RE.findall(self.feed(tmp))

            self.assertEqual(sorted(stamps, reverse=True), stamps)
            self.assertEqual("2026-08-03T11:00:00Z", stamps[0])
            self.assertEqual("2026-07-30T09:15:00Z", stamps[-1])

    def test_a_malformed_line_is_skipped_and_counted_rather_than_failing(self):
        with tempfile.TemporaryDirectory() as tmp:
            page = self.feed(tmp)

            # Two: a line that is not JSON, and an array that is JSON and
            # still not an entry.
            self.assertIn("2 unreadable", page)
            self.assertNotIn("an array is valid JSON", page)

    def test_a_blank_line_is_not_a_malformed_one(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_checkout(Path(tmp), friction=False)
            log = root / ".orch" / "friction" / "2026-09.jsonl"
            log.parent.mkdir(parents=True)
            log.write_text(
                '\n{"ts": "2026-09-01T00:00:00Z", "observed": "a", "expected": "b"}\n\n\n',
                encoding="utf-8",
            )
            read = ui.read_friction(root)

            self.assertEqual(0, read["skipped"])
            self.assertEqual(1, len(read["entries"]))

    def test_a_clean_log_carries_no_skip_note_at_all(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_checkout(Path(tmp), friction=False)
            log = root / ".orch" / "friction" / "2026-09.jsonl"
            log.parent.mkdir(parents=True)
            log.write_text(
                '{"ts": "2026-09-01T00:00:00Z", "observed": "a", "expected": "b"}\n',
                encoding="utf-8",
            )
            page = ui.render_route(root, ui.FRICTION_ROUTE)[1]

            self.assertNotIn("unreadable", page)
            self.assertIn("1 entry", page)

    def test_an_entry_missing_a_category_or_host_is_shown_rather_than_dropped(self):
        # An older logger wrote entries without them. Dropping the entry
        # would lose the observation the law exists to keep.
        with tempfile.TemporaryDirectory() as tmp:
            page = self.feed(tmp)

            self.assertIn("an entry written by an older logger", page)
            self.assertEqual(2, page.count(ui.EMPTY_UNSET))

    def test_an_untrusted_entry_reaches_the_feed_escaped(self):
        with tempfile.TemporaryDirectory() as tmp:
            page = self.feed(tmp)

            self.assertIn("&lt;b&gt;markup&lt;/b&gt;", page)
            self.assertNotIn("<b>markup</b>", page)

    def test_an_absent_friction_log_is_named_rather_than_an_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            page = self.feed(tmp, friction=False)

            self.assertIn(ui.EMPTY_NO_FRICTION, page)
            self.assertEqual([], TS_RE.findall(page))

    def test_the_index_links_to_the_feed(self):
        with tempfile.TemporaryDirectory() as tmp:
            page = ui.render_route(make_checkout(Path(tmp)), "/")[1]

            self.assertIn('href="{0}"'.format(ui.FRICTION_ROUTE), page)

    def test_an_entry_that_is_json_but_not_an_object_never_reaches_a_key_lookup(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_checkout(Path(tmp), friction=False)
            log = root / ".orch" / "friction" / "2026-09.jsonl"
            log.parent.mkdir(parents=True)
            log.write_text('"a bare string"\n42\nnull\n[]\n', encoding="utf-8")
            read = ui.read_friction(root)

            self.assertEqual({"entries": [], "skipped": 4}, read)


EVENT_RUN = "run-gamma"


class TestEventsSeam(unittest.TestCase):
    """The deferred hooks seam the spec's `binding_constraints` fix so v2 is
    additive: `.orch/events/<run>.jsonl`, one JSON object per line. No hook
    writes it in this version, so the reader has to hold both halves --
    render the file where it exists, say nothing at all where it does
    not."""

    def graph(self, root: Path, run: str) -> str:
        status, page = ui.render_route(root, graph_url(run))
        self.assertEqual(200, status, run)
        return page

    def test_a_run_with_an_event_log_renders_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            page = self.graph(make_checkout(Path(tmp)), EVENT_RUN)

            self.assertIn("<h2>events</h2>", page)
            block = block_for(page, "events")
            self.assertEqual(3, len(block.split('<li class="event">')) - 1, block)
            for kind in ("tool_pre", "tool_post", "subagent_stop"):
                self.assertIn(kind, block, kind)

    def test_a_run_with_no_event_log_says_nothing_at_all(self):
        # The silent half. A heading over an empty feed would promise a
        # stream nothing in this version produces.
        with tempfile.TemporaryDirectory() as tmp:
            main = make_checkout(Path(tmp))

            for run in (SETTLED_RUN, CYCLIC_RUN, EMPTY_RUN):
                page = self.graph(main, run)
                self.assertNotIn("<h2>events</h2>", page, run)
                self.assertEqual("", block_for(page, "events"), run)
            self.assertIsNone(ui.read_events(main, SETTLED_RUN))

    def test_an_absent_events_directory_is_the_same_silence(self):
        with tempfile.TemporaryDirectory() as tmp:
            main = make_checkout(Path(tmp), events=False)

            self.assertIsNone(ui.read_events(main, EVENT_RUN))
            self.assertNotIn("<h2>events</h2>", self.graph(main, EVENT_RUN))

    def test_every_key_the_seam_fixes_reaches_the_page(self):
        with tempfile.TemporaryDirectory() as tmp:
            block = block_for(self.graph(make_checkout(Path(tmp)), EVENT_RUN), "events")

            for value in (
                "2026-01-01T00:20:00Z",
                "run-gamma",
                "G4",
                "fixture-agent",
                "tool_pre",
                "Read",
                "scripts/ui.py",
            ):
                self.assertIn(value, block, value)

    def test_a_nullable_key_left_null_is_named_rather_than_blank(self):
        with tempfile.TemporaryDirectory() as tmp:
            block = block_for(self.graph(make_checkout(Path(tmp)), EVENT_RUN), "events")
            stop = block.split('<li class="event">')[1].split("</li>")[0]

            self.assertIn("subagent_stop", stop)
            # `ticket`, `tool` and `detail` are all null on that line.
            self.assertEqual(3, stop.count(ui.EMPTY_UNSET), stop)

    def test_events_are_newest_first(self):
        with tempfile.TemporaryDirectory() as tmp:
            main = make_checkout(Path(tmp))
            block = block_for(self.graph(main, EVENT_RUN), "events")

            stamps = TS_RE.findall(block)
            self.assertEqual(3, len(stamps))
            self.assertEqual(sorted(stamps, reverse=True), stamps)
            self.assertEqual("2026-01-01T00:21:00Z", stamps[0])

    def test_a_malformed_line_is_skipped_and_counted_as_the_friction_feed_does(self):
        with tempfile.TemporaryDirectory() as tmp:
            main = make_checkout(Path(tmp))

            read = ui.read_events(main, EVENT_RUN)

            # Two: a half-written line, and an array that is JSON and still
            # not an event. The blank line is neither.
            self.assertEqual(2, read["skipped"])
            self.assertEqual(3, len(read["entries"]))
            self.assertIn("2 unreadable lines", block_for(self.graph(main, EVENT_RUN), "events"))
            self.assertNotIn("a half-written line", self.graph(main, EVENT_RUN))

    def test_an_untrusted_event_reaches_the_page_escaped(self):
        with tempfile.TemporaryDirectory() as tmp:
            page = self.graph(make_checkout(Path(tmp)), EVENT_RUN)

            self.assertIn("&lt;b&gt;markup&lt;/b&gt;", page)
            self.assertNotIn("<b>markup</b>", page)

    def test_the_log_is_read_from_the_run_it_is_named_for_and_no_other(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_checkout(Path(tmp), events=False)
            logs = root / ".orch" / "events"
            logs.mkdir(parents=True)
            (logs / "{0}.jsonl".format(SETTLED_RUN)).write_text(
                '{"ts": "2026-01-01T00:00:00Z", "event": "tool_pre", "detail": "OWN-RUN"}\n',
                encoding="utf-8",
            )

            self.assertIn("OWN-RUN", self.graph(root, SETTLED_RUN))
            self.assertNotIn("OWN-RUN", self.graph(root, EVENT_RUN))

    def test_an_event_log_appearing_moves_the_validator(self):
        # `STATE_DIRS` omitted the directory, so a log written while a
        # viewer was open would never have been noticed.
        with tempfile.TemporaryDirectory() as tmp:
            root = make_checkout(Path(tmp), events=False)
            with frozen_clock():
                before = ui.state_digest(root)
                logs = root / ".orch" / "events"
                logs.mkdir(parents=True)
                (logs / "{0}.jsonl".format(SETTLED_RUN)).write_text(
                    '{"ts": "2026-01-01T00:00:00Z", "event": "tool_pre"}\n', encoding="utf-8"
                )
                after = ui.state_digest(root)

            self.assertNotEqual(before, after)
            self.assertIn(ui.EVENTS_DIR, ui.STATE_DIRS)


class TestValidatorObservesTheWholePage(unittest.TestCase):
    """The validator's whole job is to be a faithful function of the body it
    is served with. A tag that observes less than the page does turns the
    poll into a machine for showing a reader something that is no longer
    true, and does it silently: the response is a 304, which looks exactly
    like nothing having happened."""

    def live_root(self, tmp: str) -> Path:
        """One claim, 90m bound, claimed at `CLAIMED_AT` -- the shape whose
        rendering moves with the clock and nothing else."""

        root = make_checkout(Path(tmp), runs=(), friction=False, events=False)
        write_ticket(
            root / ".orch" / "tickets" / "run-live",
            "L1",
            status="claimed",
            bound="90m",
            claimed_at="2026-01-01T00:20:00Z",
        )
        return root

    def at(self, server, minutes: int, etag=None) -> tuple:
        headers = {"If-None-Match": etag} if etag else {}
        with frozen_clock(CLAIMED_AT + timedelta(minutes=minutes)):
            return fetch(server, "/", headers)

    def test_a_live_meter_advances_under_polling(self):
        with tempfile.TemporaryDirectory() as tmp:
            seen = []
            with serving(self.live_root(tmp)) as server:
                for minutes in (1, 75, 100):
                    status, headers, body = self.at(server, minutes)
                    self.assertEqual(200, status, minutes)
                    seen.append((headers.get("ETag"), body))

            for (tag, body), wanted in zip(
                seen, ("1m of 90m", "75m of 90m", "100m of 90m, over bound")
            ):
                self.assertIn(wanted, body, wanted)
                self.assertTrue(tag, wanted)
            # Three different pages, so three different validators.
            self.assertEqual(3, len({tag for tag, _ in seen}))

    def test_a_client_holding_last_minutes_tag_is_answered_rather_than_left(self):
        with tempfile.TemporaryDirectory() as tmp:
            with serving(self.live_root(tmp)) as server:
                stale = self.at(server, 1)[1].get("ETag")
                status, headers, body = self.at(server, 75, stale)

            self.assertEqual(200, status)
            self.assertNotEqual(stale, headers.get("ETag"))
            self.assertIn("75m of 90m", body)

    def test_a_bound_is_crossed_under_polling_rather_than_at_the_next_write(self):
        # Nothing writes to a ticket when its bound expires, so an overrun is
        # visible only if the clock alone can move the page.
        with tempfile.TemporaryDirectory() as tmp:
            with serving(self.live_root(tmp)) as server:
                inside = self.at(server, 89)
                status, _, body = self.at(server, 91, inside[1].get("ETag"))

            self.assertNotIn("over bound", inside[2])
            self.assertEqual(200, status)
            self.assertIn("over bound", body)

    def test_a_meter_that_has_not_moved_still_answers_304(self):
        # The 304 is not defeated: within one minute the page is identical
        # and the poll must stay cheap.
        with tempfile.TemporaryDirectory() as tmp:
            with serving(self.live_root(tmp)) as server:
                first = self.at(server, 30)[1].get("ETag")
                with frozen_clock(CLAIMED_AT + timedelta(minutes=30, seconds=59)):
                    status, headers, body = fetch(
                        server, "/", {"If-None-Match": first}
                    )

            self.assertEqual(304, status)
            self.assertEqual("", body)
            self.assertEqual(first, headers.get("ETag"))

    def test_a_settled_run_answers_304_across_an_hour_of_clock(self):
        # Criterion 10's own case, kept: where nothing is claimed there is
        # nothing for the clock to move, so the tag must not move either.
        with tempfile.TemporaryDirectory() as tmp:
            main = make_checkout(Path(tmp), runs=(SETTLED_RUN,))
            with serving(main) as server:
                first = self.at(server, 0)[1].get("ETag")
                status, headers, _ = self.at(server, 74, first)

            self.assertEqual(304, status)
            self.assertEqual(first, headers.get("ETag"))

    def test_a_meter_the_page_draws_is_a_digest_input(self):
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as other:
            live = self.live_root(tmp)
            settled = make_checkout(Path(other), runs=(SETTLED_RUN,))
            clock = [CLAIMED_AT + timedelta(minutes=minutes) for minutes in (1, 2, 3)]

            self.assertEqual(3, len({ui.state_digest(live, now) for now in clock}))
            # The clock is an input only where the page reads one.
            self.assertEqual(1, len({ui.state_digest(settled, now) for now in clock}))

    def test_the_two_empty_states_of_orch_never_share_one_digest(self):
        # `.orch/` absent and `.orch/` present-but-bare are two different
        # named pages, so they are two different validators.
        with tempfile.TemporaryDirectory() as tmp:
            bare = Path(tmp) / "bare"
            (bare / ".git").mkdir(parents=True)
            hollow = Path(tmp) / "hollow"
            (hollow / ".orch").mkdir(parents=True)
            tickets = Path(tmp) / "tickets"
            (tickets / ".orch" / "tickets").mkdir(parents=True)

            digests = [ui.state_digest(root) for root in (bare, hollow, tickets)]
            pages = [ui.render_route(root, "/")[1] for root in (bare, hollow, tickets)]

            self.assertEqual(3, len(set(digests)), digests)
            self.assertIn(ui.EMPTY_NO_ORCH, pages[0])
            self.assertIn(ui.EMPTY_NO_RUNS, pages[1])
            self.assertIn(ui.EMPTY_NO_RUNS, pages[2])

    def test_an_orch_directory_appearing_repaints_the_empty_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "bare"
            (root / ".git").mkdir(parents=True)
            with serving(root) as server:
                first = fetch(server, "/")
                (root / ".orch" / "tickets").mkdir(parents=True)
                status, headers, body = fetch(
                    server, "/", {"If-None-Match": first[1].get("ETag")}
                )

            self.assertIn(ui.EMPTY_NO_ORCH, first[2])
            self.assertEqual(200, status)
            self.assertNotEqual(first[1].get("ETag"), headers.get("ETag"))
            self.assertIn(ui.EMPTY_NO_RUNS, body)
            self.assertNotIn(ui.EMPTY_NO_ORCH, body)


class TestConditionalRequests(unittest.TestCase):
    """Spec criterion 10. A one-second poll that re-renders every page every
    second is the cost this view refuses to pay; the 304 is what makes the
    interval affordable."""

    def setUp(self):
        # These are tests about a directory that did or did not change. The
        # fixtures also carry a live meter, which honestly moves the tag at
        # each minute boundary, so an unpinned clock would make a handful of
        # them fail on the minute rather than never.
        freeze(self)

    def touch(self, path: Path):
        """A rewrite inside the same wall-clock second that leaves the size
        alone -- the case a mtime-only tag misses."""

        before = path.stat()
        os.utime(path, ns=(before.st_atime_ns, before.st_mtime_ns + 1000))
        after = path.stat()
        if after.st_mtime_ns == before.st_mtime_ns:
            self.skipTest("filesystem does not record sub-second mtime")
        self.assertEqual(before.st_size, after.st_size)
        self.assertEqual(int(before.st_mtime), int(after.st_mtime))

    def test_an_unchanged_ticket_directory_answers_304_to_every_data_route(self):
        with tempfile.TemporaryDirectory() as tmp:
            main = make_checkout(Path(tmp))
            with serving(main) as server:
                for route in every_route():
                    status, headers, body = fetch(server, route)
                    if status != 200:
                        continue
                    etag = headers.get("ETag")
                    self.assertTrue(etag, route)
                    again = fetch(server, route, {"If-None-Match": etag})
                    self.assertEqual(304, again[0], route)
                    self.assertEqual("", again[2], route)
                    self.assertEqual(etag, again[1].get("ETag"), route)
                    self.assertNotEqual("", body, route)

    def test_a_ticket_changing_size_answers_200_with_a_different_tag(self):
        with tempfile.TemporaryDirectory() as tmp:
            main = make_checkout(Path(tmp))
            ticket = main / ".orch" / "tickets" / SETTLED_RUN / "D1.md"
            with serving(main) as server:
                first = fetch(server, graph_url(SETTLED_RUN))[1].get("ETag")
                with ticket.open("a", encoding="utf-8") as handle:
                    handle.write("\nanother line\n")
                status, headers, _ = fetch(
                    server, graph_url(SETTLED_RUN), {"If-None-Match": first}
                )

            self.assertEqual(200, status)
            self.assertNotEqual(first, headers.get("ETag"))

    def test_a_same_second_rewrite_of_the_same_size_answers_200_with_a_new_tag(self):
        with tempfile.TemporaryDirectory() as tmp:
            main = make_checkout(Path(tmp))
            ticket = main / ".orch" / "tickets" / SETTLED_RUN / "D1.md"
            with serving(main) as server:
                first = fetch(server, "/")[1].get("ETag")
                self.touch(ticket)
                status, headers, body = fetch(server, "/", {"If-None-Match": first})

            self.assertEqual(200, status)
            self.assertNotEqual(first, headers.get("ETag"))
            self.assertNotEqual("", body)

    def test_a_tag_from_another_page_never_satisfies_this_one(self):
        with tempfile.TemporaryDirectory() as tmp:
            main = make_checkout(Path(tmp))
            with serving(main) as server:
                index = fetch(server, "/")[1].get("ETag")
                graph = fetch(server, graph_url(SETTLED_RUN))[1].get("ETag")
                status, _, _ = fetch(server, "/", {"If-None-Match": graph})

            self.assertNotEqual(index, graph)
            self.assertEqual(200, status)

    def test_a_stale_or_absent_validator_answers_the_whole_page(self):
        with tempfile.TemporaryDirectory() as tmp:
            main = make_checkout(Path(tmp))
            with serving(main) as server:
                for header in ({}, {"If-None-Match": '"not-a-real-tag"'}):
                    status, _, body = fetch(server, "/", header)
                    self.assertEqual(200, status)
                    self.assertIn("<main", body)

    def test_a_wildcard_or_weak_validator_is_honoured_as_rfc7232_requires(self):
        with tempfile.TemporaryDirectory() as tmp:
            main = make_checkout(Path(tmp))
            with serving(main) as server:
                etag = fetch(server, "/")[1].get("ETag")
                for sent in (
                    "*",
                    "W/{0}".format(etag),
                    '"other", {0}'.format(etag),
                ):
                    status, _, _ = fetch(server, "/", {"If-None-Match": sent})
                    self.assertEqual(304, status, sent)

    def test_a_404_carries_no_entity_tag_to_be_cached_against(self):
        with tempfile.TemporaryDirectory() as tmp:
            main = make_checkout(Path(tmp))
            with serving(main) as server:
                for route in ("/nope", detail_url(SETTLED_RUN, "ZZ9"), graph_url("nope")):
                    status, headers, _ = fetch(server, route)
                    self.assertEqual(404, status, route)
                    self.assertIsNone(headers.get("ETag"), route)

    def test_the_page_is_offered_for_revalidation_rather_than_not_stored(self):
        # `no-store` forbids keeping the response at all, so the browser has
        # nothing to revalidate and never sends `If-None-Match`: the 304 above
        # would be unreachable from a real client.
        with tempfile.TemporaryDirectory() as tmp:
            main = make_checkout(Path(tmp))
            with serving(main) as server:
                headers = fetch(server, "/")[1]

            self.assertEqual("no-cache", headers.get("Cache-Control"))

    def test_a_304_renders_nothing_at_all(self):
        with tempfile.TemporaryDirectory() as tmp:
            main = make_checkout(Path(tmp))
            etag = ui.respond(main, graph_url(SETTLED_RUN))[1]

            with patch.object(ui, "render_route") as rendered:
                status, echoed, body = ui.respond(main, graph_url(SETTLED_RUN), etag)

            self.assertEqual((304, etag, ""), (status, echoed, body))
            rendered.assert_not_called()


class TestLoopbackOnly(unittest.TestCase):
    """Spec `binding_constraints`: bind loopback only, never 0.0.0.0."""

    def test_server_binds_a_loopback_address_and_serves_there(self):
        with tempfile.TemporaryDirectory() as tmp:
            main = make_checkout(Path(tmp))
            with serving(main) as server:
                host = server.server_address[0]

                self.assertTrue(ipaddress.ip_address(host).is_loopback, host)
                self.assertNotEqual("0.0.0.0", host)
                status, page = get(server, "/")
                self.assertEqual(200, status)
                self.assertIn("orchflows runs", page)

    def test_an_unavailable_port_exits_2_with_a_message_not_a_traceback(self):
        # The bind failure is injected rather than provoked by holding the
        # port: Windows honours SO_REUSEADDR on a live listener, so a real
        # collision would bind there and serve_forever would hang CI.
        with tempfile.TemporaryDirectory() as tmp:
            main = make_checkout(Path(tmp))
            argv = ["--root", str(main), "--port", "8787"]
            stderr = io.StringIO()
            with patch.object(ui, "create_server", side_effect=OSError("in use")):
                with contextlib.redirect_stderr(stderr):
                    code = ui.main(argv)

            self.assertEqual(2, code)
            self.assertIn("8787", stderr.getvalue())
            self.assertIn("in use", stderr.getvalue())


class TestRouteCoverage(unittest.TestCase):
    """A guard that iterates the routes proves nothing about a route it
    never visits. U1 registered `/` alone; a route added later and left out
    of the examples silently shrinks both guards below, so the coverage is
    asserted rather than assumed."""

    def test_every_served_route_is_reached_by_a_concrete_example(self):
        for route in ui.ROUTES:
            self.assertIn(route, ROUTE_EXAMPLES, route)
            self.assertTrue(ROUTE_EXAMPLES[route], route)

    def test_the_examples_reach_a_rendered_ticket_not_only_its_error_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            main = make_checkout(Path(tmp))

            served = [ui.render_route(main, url)[0] for url in every_route()]

            self.assertIn(200, served)
            self.assertIn(404, served)


class TestReadOnly(unittest.TestCase):
    """Spec criterion 11."""

    def test_exercising_every_route_writes_nothing_under_orch(self):
        with tempfile.TemporaryDirectory() as tmp:
            main = make_checkout(Path(tmp))
            orch = main / ".orch"
            before = snapshot(orch)
            self.assertTrue(before)

            with serving(main) as server:
                for route in every_route():
                    status, page = get(server, route)
                    self.assertIn(status, (200, 404))
                    self.assertTrue(page)

            self.assertEqual(before, snapshot(orch))

    def test_revalidating_every_route_writes_nothing_either(self):
        # A 304 short-circuits before `render_route`, so the guard above
        # never walks that path -- and it is the path a poll takes almost
        # every second the viewer is open.
        freeze(self)
        with tempfile.TemporaryDirectory() as tmp:
            main = make_checkout(Path(tmp))
            orch = main / ".orch"
            before = snapshot(orch)
            revalidated = 0

            with serving(main) as server:
                for route in every_route():
                    etag = fetch(server, route)[1].get("ETag")
                    if etag is None:
                        continue
                    again = fetch(server, route, {"If-None-Match": etag})
                    self.assertEqual(304, again[0], route)
                    revalidated += 1

            self.assertEqual(before, snapshot(orch))
            self.assertGreaterEqual(revalidated, len(ui.ROUTES))


class TestNoNetworkAssets(unittest.TestCase):
    """Spec criterion 12."""

    def test_the_detector_catches_a_remote_asset(self):
        for markup in (
            '<script src="https://cdn.example/x.js"></script>',
            "<link rel=stylesheet href='//cdn.example/x.css'>",
            '<img src="http://cdn.example/x.png">',
        ):
            self.assertIsNotNone(REMOTE_ASSET_RE.search(markup), markup)

    def test_no_route_emits_a_remote_src_or_href(self):
        with tempfile.TemporaryDirectory() as tmp:
            main = make_checkout(Path(tmp))
            with serving(main) as server:
                for route in every_route():
                    _, page = get(server, route)
                    self.assertIsNone(REMOTE_ASSET_RE.search(page), route)


def first_import(source: str) -> tuple:
    """``(module, first name)`` of the earliest import statement, or ``()``."""

    for node in ast.parse(source).body:
        if isinstance(node, ast.ImportFrom):
            return (node.module, node.names[0].name)
        if isinstance(node, ast.Import):
            return (None, node.names[0].name)
    return ()


# The spec's `binding_constraints` list, as things an AST can be asked
# about. `zoneinfo` imports on 3.9 and is forbidden anyway: CPython on
# Windows ships no tz database.
FLOOR_MODULES = ("tomllib", "zoneinfo")
FLOOR_NAMES = {"datetime": ("UTC",), "typing": ("Self",), "itertools": ("batched",)}
FLOOR_NODES = tuple(
    (getattr(ast, attribute), spelling)
    for attribute, spelling in (("Match", "match"), ("TryStar", "except*"))
    if getattr(ast, attribute, None) is not None
)


def evaluated_nodes(tree) -> list:
    """Every node the interpreter actually runs.

    `from __future__ import annotations` makes an annotation a string that
    is never evaluated, so PEP 604 inside one is legal at the floor and a
    detector that flagged it would be reporting a violation that is not one.
    """

    postponed = []
    for node in ast.walk(tree):
        if isinstance(node, ast.AnnAssign):
            postponed.append(node.annotation)
        elif isinstance(node, ast.arg) and node.annotation is not None:
            postponed.append(node.annotation)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.returns is not None:
                postponed.append(node.returns)
    skip = set()
    for annotation in postponed:
        skip.update(id(child) for child in ast.walk(annotation))
    return [node for node in ast.walk(tree) if id(node) not in skip]


def above_the_floor(source: str) -> list:
    """Every construct in `source` that Python 3.9 cannot run.

    Parsing alone proves nothing here: a 3.13 interpreter parses all of
    these happily, and the module has already been imported by the time any
    test runs, so a `SyntaxError` would have failed collection rather than a
    test. What CI's 3.9 leg would refuse has to be asked of the tree.
    """

    found = set()
    for node in evaluated_nodes(ast.parse(source)):
        for kind, spelling in FLOOR_NODES:
            if isinstance(node, kind):
                found.add(spelling)
        if isinstance(node, ast.Import):
            found.update(
                alias.name
                for alias in node.names
                if alias.name.split(".")[0] in FLOOR_MODULES
            )
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module.split(".")[0] in FLOOR_MODULES:
                found.add(module)
            found.update(
                "{0}.{1}".format(module, alias.name)
                for alias in node.names
                if alias.name in FLOOR_NAMES.get(module, ())
            )
        elif isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
            if node.attr in FLOOR_NAMES.get(node.value.id, ()):
                found.add("{0}.{1}".format(node.value.id, node.attr))
        elif isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
            # `X | None` is the runtime PEP 604 the spec names; `a | None`
            # is not arithmetic anyone writes by accident.
            if any(
                isinstance(side, ast.Constant) and side.value is None
                for side in (node.left, node.right)
            ):
                found.add("X | None")
    return sorted(found)


class TestModuleFloor(unittest.TestCase):
    """Spec `binding_constraints`: the 3.9 floor and mandatory postponed
    annotations."""

    def test_the_module_reaches_for_nothing_above_the_floor(self):
        self.assertGreaterEqual(sys.version_info[:2], (3, 9))

        self.assertEqual([], above_the_floor(UI_PY.read_text(encoding="utf-8")))

    def test_the_detector_names_every_import_and_name_the_floor_forbids(self):
        # Every construct here parses on 3.9 and fails at import or call
        # there, which is exactly the class a parse check cannot catch.
        source = (
            "import tomllib\n"
            "from zoneinfo import ZoneInfo\n"
            "from typing import Self\n"
            "import datetime, itertools\n"
            "stamp = datetime.datetime.now(datetime.UTC)\n"
            "pairs = itertools.batched(stamp, 2)\n"
            "fallback = int | None\n"
        )

        self.assertEqual(
            [
                "X | None",
                "datetime.UTC",
                "itertools.batched",
                "tomllib",
                "typing.Self",
                "zoneinfo",
            ],
            above_the_floor(source),
        )

    def test_the_detector_names_the_syntax_the_floor_forbids(self):
        source = "match value:\n    case 1:\n        pass\n"

        if FLOOR_NODES:
            self.assertEqual(["match"], above_the_floor(source))
        else:
            # On the floor interpreter itself the syntax is a `SyntaxError`,
            # which is the same guarantee arrived at sooner.
            self.assertRaises(SyntaxError, ast.parse, source)

    def test_a_postponed_annotation_is_not_a_violation(self):
        # The detector has to be wrong in neither direction: this module's
        # own `X | None` annotations are strings under the mandatory
        # `__future__` import and must not be reported.
        source = (
            "from __future__ import annotations\n"
            "held: int | None = None\n"
            "def read(path: str | None = None) -> dict | None:\n"
            "    return None\n"
        )

        self.assertEqual([], above_the_floor(source))

    def test_future_annotations_is_the_first_import(self):
        self.assertEqual(
            ("__future__", "annotations"), first_import(UI_PY.read_text(encoding="utf-8"))
        )
        # The check discriminates: a module that imports anything first fails it.
        self.assertNotEqual(
            ("__future__", "annotations"),
            first_import("import os\nfrom __future__ import annotations\n"),
        )


if __name__ == "__main__":
    unittest.main()
