"""Installer regression cases grouped by behavioral seam."""

from __future__ import annotations

from ..support import *  # noqa: F403


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
