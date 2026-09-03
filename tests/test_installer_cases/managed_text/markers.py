"""Installer regression cases grouped by behavioral seam."""

from __future__ import annotations

from ..support import *  # noqa: F403

from installer import managed_text


class TestMarkerEngineMisuse(unittest.TestCase):
    """Marker matching is line equality on ``rstrip("\\r\\n")``. Duplicate,
    unbalanced, and out-of-order markers must raise ``ValueError`` naming the
    offending marker, for ``upsert_marked_block`` and ``without_owned_block``
    alike, and for CRLF line endings too."""

    # -- upsert_marked_block -------------------------------------------

    def test_upsert_marked_block_duplicate_begin_raises(self):
        text = "# BEGIN\nold\n# BEGIN\nold2\n# END\n"
        with self.assertRaisesRegex(ValueError, "duplicate"):
            install.upsert_marked_block(text, "new\n", "# BEGIN", "# END")

    def test_upsert_marked_block_duplicate_end_raises(self):
        text = "# BEGIN\nold\n# END\nold2\n# END\n"
        with self.assertRaisesRegex(ValueError, "duplicate"):
            install.upsert_marked_block(text, "new\n", "# BEGIN", "# END")

    def test_upsert_marked_block_begin_without_end_raises(self):
        text = "# BEGIN\nold\n"
        with self.assertRaisesRegex(ValueError, "unbalanced"):
            install.upsert_marked_block(text, "new\n", "# BEGIN", "# END")

    def test_upsert_marked_block_end_without_begin_raises(self):
        text = "old\n# END\n"
        with self.assertRaisesRegex(ValueError, "unbalanced"):
            install.upsert_marked_block(text, "new\n", "# BEGIN", "# END")

    def test_upsert_marked_block_out_of_order_raises(self):
        text = "# END\nold\n# BEGIN\n"
        with self.assertRaisesRegex(ValueError, "out of order"):
            install.upsert_marked_block(text, "new\n", "# BEGIN", "# END")

    def test_upsert_marked_block_duplicate_begin_raises_with_crlf(self):
        text = "# BEGIN\r\nold\r\n# BEGIN\r\nold2\r\n# END\r\n"
        with self.assertRaisesRegex(ValueError, "duplicate"):
            install.upsert_marked_block(text, "new\n", "# BEGIN", "# END")

    def test_upsert_marked_block_unbalanced_raises_with_crlf(self):
        text = "# BEGIN\r\nold\r\n"
        with self.assertRaisesRegex(ValueError, "unbalanced"):
            install.upsert_marked_block(text, "new\n", "# BEGIN", "# END")

    def test_upsert_marked_block_out_of_order_raises_with_crlf(self):
        text = "# END\r\nold\r\n# BEGIN\r\n"
        with self.assertRaisesRegex(ValueError, "out of order"):
            install.upsert_marked_block(text, "new\n", "# BEGIN", "# END")

    # -- without_owned_block --------------------------------------------
    #
    # The one surviving reader of the span. ``_owned`` claims every line, so
    # what is graded here is the marker reading and nothing about ownership.

    @staticmethod
    def _owned(line):
        return True

    def test_without_owned_block_duplicate_begin_raises(self):
        text = "# BEGIN\nold\n# BEGIN\nold2\n# END\n"
        with self.assertRaisesRegex(ValueError, "invalid"):
            managed_text.without_owned_block(text, "# BEGIN", "# END", self._owned)

    def test_without_owned_block_duplicate_end_raises(self):
        text = "# BEGIN\nold\n# END\nold2\n# END\n"
        with self.assertRaisesRegex(ValueError, "invalid"):
            managed_text.without_owned_block(text, "# BEGIN", "# END", self._owned)

    def test_without_owned_block_begin_without_end_raises(self):
        text = "# BEGIN\nold\n"
        with self.assertRaisesRegex(ValueError, "invalid"):
            managed_text.without_owned_block(text, "# BEGIN", "# END", self._owned)

    def test_without_owned_block_end_without_begin_raises(self):
        text = "old\n# END\n"
        with self.assertRaisesRegex(ValueError, "invalid"):
            managed_text.without_owned_block(text, "# BEGIN", "# END", self._owned)

    def test_without_owned_block_out_of_order_raises(self):
        text = "# END\nold\n# BEGIN\n"
        with self.assertRaisesRegex(ValueError, "invalid"):
            managed_text.without_owned_block(text, "# BEGIN", "# END", self._owned)

    def test_without_owned_block_out_of_order_raises_with_crlf(self):
        text = "# END\r\nold\r\n# BEGIN\r\n"
        with self.assertRaisesRegex(ValueError, "invalid"):
            managed_text.without_owned_block(text, "# BEGIN", "# END", self._owned)

    def test_without_owned_block_absent_markers_is_a_no_op(self):
        # Contrast case: no markers at all is not misuse -- text passes through.
        text = "plain content\n"
        self.assertEqual(
            text, managed_text.without_owned_block(text, "# BEGIN", "# END", self._owned)
        )


class TestConservativeBlockRemoval(unittest.TestCase):
    """``without_owned_block`` lifts a managed block out of a file whose own
    host also edits it. The marker pair is not a safe identity there: a TOML
    editor appending a table at the end of the document body lands it ahead of
    a trailing END comment, which is *inside* the span. Only the run of lines
    the caller owns, from the BEGIN marker down, is the installer's."""

    @staticmethod
    def _owned(line):
        return line.lstrip().startswith("owned")

    def test_a_foreign_line_the_host_appended_inside_the_block_survives(self):
        text = "# BEGIN\nowned = 1\nowned = 2\n[marketplace]\nkey = true\n# END\n"

        self.assertEqual(
            "[marketplace]\nkey = true\n",
            managed_text.without_owned_block(text, "# BEGIN", "# END", self._owned),
        )

    def test_an_owned_looking_line_below_the_first_foreign_one_survives_too(self):
        # Under `[marketplace]` a bare `owned = 3` is the host's key, not the
        # installer's: the installer writes its own lines first and contiguously.
        text = "# BEGIN\nowned = 1\n[marketplace]\nowned = 3\n# END\n"

        self.assertEqual(
            "[marketplace]\nowned = 3\n",
            managed_text.without_owned_block(text, "# BEGIN", "# END", self._owned),
        )

    def test_a_block_holding_only_owned_lines_lifts_out_whole(self):
        text = "before\n# BEGIN\nowned = 1\nowned = 2\n# END\nafter\n"

        self.assertEqual(
            "before\nafter\n",
            managed_text.without_owned_block(text, "# BEGIN", "# END", self._owned),
        )

    def test_blank_lines_between_owned_ones_do_not_strand_them(self):
        text = "# BEGIN\nowned = 1\n\nowned = 2\n# END\n"

        self.assertEqual(
            "", managed_text.without_owned_block(text, "# BEGIN", "# END", self._owned)
        )

    def test_absent_markers_pass_the_text_through(self):
        text = "owned = 1\n"

        self.assertEqual(
            text, managed_text.without_owned_block(text, "# BEGIN", "# END", self._owned)
        )

    def test_duplicate_markers_raise_the_shared_marker_error(self):
        text = "# BEGIN\nowned = 1\n# BEGIN\n# END\n"

        with self.assertRaisesRegex(ValueError, "invalid"):
            managed_text.without_owned_block(text, "# BEGIN", "# END", self._owned)

    def test_crlf_line_endings_are_preserved_on_what_survives(self):
        text = "# BEGIN\r\nowned = 1\r\n[marketplace]\r\nkey = true\r\n# END\r\n"

        self.assertEqual(
            "[marketplace]\r\nkey = true\r\n",
            managed_text.without_owned_block(text, "# BEGIN", "# END", self._owned),
        )


class TestHostConfigLimitRemoval(unittest.TestCase):
    """Each host's TOML config removal, read as one contract rather than two.

    Both hosts fence a fixed set of keys inside one table of a file their own
    CLI also writes, so both removals have to be keyed on the lines the
    installer wrote rather than on the marked span. Every case here is written
    once and run per host, so a removal that regressed to a span lift on
    either side fails. The observed appended table is Grok's, but nothing
    about the hazard is -- and the Codex side had no check saying so.
    """

    def _hosts(self):
        return (
            (
                "codex",
                managed_text.without_codex_agent_limits,
                managed_text.render_codex_agent_limits,
                install.CODEX_LIMITS_START,
                install.CODEX_LIMITS_END,
                ("agents.max_threads = 20\n", "agents.max_depth = 1\n"),
            ),
            (
                "grok",
                managed_text.without_grok_subagent_limits,
                managed_text.render_grok_subagent_limits,
                install.GROK_LIMITS_START,
                install.GROK_LIMITS_END,
                (
                    "subagents.max_concurrent = 20\n",
                    "subagents.max_depth = 1\n",
                    'subagents.limit_behavior = "queue"\n',
                ),
            ),
        )

    def test_a_table_the_host_appended_inside_the_block_survives_removal(self):
        for host, remove, _render, start, end, keys in self._hosts():
            with self.subTest(host=host):
                text = f"{start}\n" + "".join(keys) + f"[marketplace]\nkey = true\n{end}\n"

                self.assertEqual("[marketplace]\nkey = true\n", remove(text))

    def test_a_block_holding_only_the_installers_keys_lifts_out_whole(self):
        for host, remove, _render, start, end, keys in self._hosts():
            with self.subTest(host=host):
                text = f"before\n{start}\n" + "".join(keys) + f"{end}\nafter\n"

                self.assertEqual("before\nafter\n", remove(text))

    def test_absent_markers_pass_the_config_through(self):
        for host, remove, _render, _start, _end, _keys in self._hosts():
            with self.subTest(host=host):
                text = '[permission]\nmode = "ask"\n'

                self.assertEqual(text, remove(text))

    @requires_tomllib
    def test_removing_the_rendered_block_restores_the_config_it_merged_into(self):
        """The removal is the merge run backwards, read as TOML.

        Byte equality is the wrong reading: the merge writes a blank line
        above the first table and the removal leaves that separator behind,
        which is whitespace and not a key. What must come back exactly is the
        document -- every table the user had, and none of the installer's.
        """

        for host, remove, render, _start, _end, _keys in self._hosts():
            for original in ('[permission]\nmode = "ask"\n', "seed = 1\n", ""):
                with self.subTest(host=host, original=original):
                    merged, _details = render(original)

                    restored = remove(merged)

                    self.assertEqual(
                        foundation.tomllib.loads(original),
                        foundation.tomllib.loads(restored),
                    )
