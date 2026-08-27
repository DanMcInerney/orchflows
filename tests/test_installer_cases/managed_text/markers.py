"""Installer regression cases grouped by behavioral seam."""

from __future__ import annotations

from ..support import *  # noqa: F403

from installer import managed_text


class TestMarkerEngineMisuse(unittest.TestCase):
    """Marker matching is line equality on ``rstrip("\\r\\n")``. Duplicate,
    unbalanced, and out-of-order markers must raise ``ValueError`` naming the
    offending marker, for ``upsert_marked_block``, ``without_marked_block``,
    and ``upsert_import_line`` (which delegates legacy-marker stripping to
    ``without_marked_block``) alike, and for CRLF line endings too."""

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

    # -- without_marked_block -------------------------------------------

    def test_without_marked_block_duplicate_begin_raises(self):
        text = "# BEGIN\nold\n# BEGIN\nold2\n# END\n"
        with self.assertRaisesRegex(ValueError, "invalid"):
            install.without_marked_block(text, "# BEGIN", "# END")

    def test_without_marked_block_duplicate_end_raises(self):
        text = "# BEGIN\nold\n# END\nold2\n# END\n"
        with self.assertRaisesRegex(ValueError, "invalid"):
            install.without_marked_block(text, "# BEGIN", "# END")

    def test_without_marked_block_begin_without_end_raises(self):
        text = "# BEGIN\nold\n"
        with self.assertRaisesRegex(ValueError, "invalid"):
            install.without_marked_block(text, "# BEGIN", "# END")

    def test_without_marked_block_end_without_begin_raises(self):
        text = "old\n# END\n"
        with self.assertRaisesRegex(ValueError, "invalid"):
            install.without_marked_block(text, "# BEGIN", "# END")

    def test_without_marked_block_out_of_order_raises(self):
        text = "# END\nold\n# BEGIN\n"
        with self.assertRaisesRegex(ValueError, "invalid"):
            install.without_marked_block(text, "# BEGIN", "# END")

    def test_without_marked_block_out_of_order_raises_with_crlf(self):
        text = "# END\r\nold\r\n# BEGIN\r\n"
        with self.assertRaisesRegex(ValueError, "invalid"):
            install.without_marked_block(text, "# BEGIN", "# END")

    def test_without_marked_block_absent_markers_is_a_no_op(self):
        # Contrast case: no markers at all is not misuse -- text passes through.
        text = "plain content\n"
        self.assertEqual(text, install.without_marked_block(text, "# BEGIN", "# END"))

    # -- upsert_import_line (delegates legacy-marker stripping) ---------

    def test_upsert_import_line_duplicate_legacy_begin_raises(self):
        text = "<!-- BEGIN -->\nold\n<!-- BEGIN -->\nold2\n<!-- END -->\n"
        with self.assertRaisesRegex(ValueError, "invalid"):
            install.upsert_import_line(text, "@x", "<!-- BEGIN -->", "<!-- END -->")

    def test_upsert_import_line_legacy_begin_without_end_raises(self):
        text = "<!-- BEGIN -->\nold\n"
        with self.assertRaisesRegex(ValueError, "invalid"):
            install.upsert_import_line(text, "@x", "<!-- BEGIN -->", "<!-- END -->")

    def test_upsert_import_line_legacy_end_without_begin_raises(self):
        text = "old\n<!-- END -->\n"
        with self.assertRaisesRegex(ValueError, "invalid"):
            install.upsert_import_line(text, "@x", "<!-- BEGIN -->", "<!-- END -->")

    def test_upsert_import_line_legacy_out_of_order_raises(self):
        text = "<!-- END -->\nold\n<!-- BEGIN -->\n"
        with self.assertRaisesRegex(ValueError, "invalid"):
            install.upsert_import_line(text, "@x", "<!-- BEGIN -->", "<!-- END -->")

    def test_upsert_import_line_legacy_out_of_order_raises_with_crlf(self):
        text = "<!-- END -->\r\nold\r\n<!-- BEGIN -->\r\n"
        with self.assertRaisesRegex(ValueError, "invalid"):
            install.upsert_import_line(text, "@x", "<!-- BEGIN -->", "<!-- END -->")


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
            install.without_marked_block(text, "# BEGIN", "# END"),
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
