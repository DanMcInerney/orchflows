"""Index, escaping, status, verification, and detail rendering regressions."""

from tests.test_ui_cases._web import *  # noqa: F401,F403
class TestIndexPage(unittest.TestCase):
    """The objective: one page listing every run and its tickets."""

    def test_index_lists_every_run_with_each_ticket_id_status_and_executor(self):
        with tempfile.TemporaryDirectory() as tmp:
            main = make_sink(Path(tmp))
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
            main = make_sink(Path(tmp))
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
            main = make_sink(Path(tmp))
            _, page = ui.render_route(main, "/")

            self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", row_for(page, "A2"))
            self.assertNotIn(PAYLOAD, page)

    def test_the_detail_page_escapes_the_same_payload(self):
        with tempfile.TemporaryDirectory() as tmp:
            main = make_sink(Path(tmp))
            status, page = ui.render_route(main, detail_url("run-alpha", "A2"))

            self.assertEqual(200, status)
            self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", page)
            self.assertNotIn(PAYLOAD, page)


class TestEmptyStates(unittest.TestCase):
    """Spec criterion 13."""

    def test_absent_sink_renders_a_named_empty_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            absent = Path(tmp) / "no-sink-here"

            status, page = ui.render_route(absent, "/")

            self.assertEqual(200, status)
            self.assertIn("no state sink at this root", page)

    def test_sink_with_no_tickets_tree_renders_a_named_empty_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "friction-only"
            (root / "friction").mkdir(parents=True)

            status, page = ui.render_route(root, "/")

            self.assertEqual(200, status)
            self.assertIn("no runs under this sink", page)

    def test_run_directory_with_zero_tickets_renders_a_named_empty_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            main = make_sink(Path(tmp))
            _, page = ui.render_route(main, "/")

            self.assertIn("no tickets in this run", section_for(page, EMPTY_RUN))
            self.assertNotIn("no tickets in this run", section_for(page, "run-alpha"))

    def test_ticket_omitting_optional_data_renders_named_empty_states(self):
        with tempfile.TemporaryDirectory() as tmp:
            main = make_sink(Path(tmp))
            _, page = ui.render_route(main, "/")

            degenerate = row_for(page, "B1")
            self.assertIn("no goal recorded", degenerate)
            self.assertIn("unset", degenerate)
            self.assertNotIn("unset", row_for(page, "A1"))
            self.assertNotIn("no goal recorded", row_for(page, "A1"))


class TestStatusPresentation(unittest.TestCase):
    """Spec criterion 14 and the colour law of `lane-ui-patterns.md` §2,
    sourced to Airflow 2.10.5 `airflow/utils/state.py`."""

    def test_the_map_covers_exactly_the_contract_status_set(self):
        statuses = contract_statuses()

        self.assertEqual(9, len(statuses), statuses)
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
        self.assertEqual(9, len({p.glyph for p in seen}))
        self.assertEqual(9, len({p.word for p in seen}))

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

    def test_nine_statuses_collapse_onto_exactly_six_hues_two_of_them_shared(self):
        statuses = contract_statuses()
        hues = [ui.status_presentation(status).hue for status in statuses]

        self.assertEqual(6, len(set(hues)))
        shared = sorted(hue for hue in set(hues) if hues.count(hue) > 1)
        self.assertEqual(2, len(shared), shared)
        for hue in shared:
            group = [s for s in statuses if ui.status_presentation(s).hue == hue]
            self.assertGreater(len(group), 1, group)
            # A shared hue is legible only because the other channels differ,
            # so every state on it differs from every other on both.
            self.assertEqual(
                len(group),
                len({ui.status_presentation(s).glyph for s in group}),
                group,
            )
            self.assertEqual(
                len(group),
                len({ui.status_presentation(s).border for s in group}),
                group,
            )

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
            main = make_sink(Path(tmp))
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
            main = make_sink(Path(tmp))
            _, index = ui.render_route(main, "/")

            self.assertIn('href="/ticket?run=run-gamma&amp;id=G1"', row_for(index, "G1"))
            page = self.detail(main, "run-gamma", "G1")
            self.assertIn("G1", page)
            self.assertIn("orch-tdd", page)
            self.assertIn(ui.status_presentation("complete").glyph, page)

    def test_the_table_shape_renders_every_verdict_row_with_a_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            main = make_sink(Path(tmp))

            block = block_for(self.detail(main, "run-gamma", "G1"), "verification")

            for value in ("PASS", "FAIL", "deterministic", "tools/validate.py"):
                self.assertIn(value, block, value)
            self.assertIn("3 entries", block)
            self.assertNotIn(ui.VERIFICATION_UNPARSED, block)

    def test_the_prose_shape_renders_unparsed_verbatim_and_carries_no_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            main = make_sink(Path(tmp))

            page = self.detail(main, "run-gamma", "G2")
            block = block_for(page, "verification")

            self.assertIn(ui.VERIFICATION_UNPARSED, block)
            self.assertNotIn('class="count"', block)
            self.assertNotIn("0 entries", page)
            # Unparsed is not unshown: the prose itself still reaches the page.
            self.assertIn("comm -23", block)

    def test_an_unresolvable_ticket_is_404_with_both_values_escaped(self):
        with tempfile.TemporaryDirectory() as tmp:
            main = make_sink(Path(tmp))

            status, page = ui.render_route(main, detail_url("run-gamma", "<script>x"))

            self.assertEqual(404, status)
            self.assertIn("&lt;script&gt;x", page)
            self.assertNotIn("<script>x", page)

    def test_a_query_that_climbs_out_of_the_tickets_tree_resolves_to_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            main = make_sink(Path(tmp))
            outside = main / "secret.md"
            outside.write_text(
                "---\nid: secret\n---\n\n## Goal\n\nOUTSIDE-THE-TICKETS-TREE\n\n## Context\n\n[]\n",
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
