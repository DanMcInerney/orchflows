"""Behavioral cases imported by the ``tests.test_tickets_issue`` seam."""

from .common import *  # noqa: F401,F403

class InlineListSeparatorTest(unittest.TestCase):
    """An inline frontmatter list `[a, b]` splits on commas and on nothing
    else. A second separator would make one written shape read two ways
    depending on which reader saw it, so an entry that carries a comma —
    prose, which every `excluded_actions` is — takes the block form
    instead, and both shapes read back as one list."""

    def test_the_comma_is_the_only_separator(self):
        parsed = tickets_mod._parse_frontmatter(
            "---\nexcluded_actions: [pushing; forcing, editing]\n---\n"
        )
        self.assertEqual(["pushing; forcing", "editing"], parsed["excluded_actions"])

    def test_an_entry_with_a_comma_is_written_in_the_block_form(self):
        lines = tickets_mod._frontmatter_list(
            "excluded_actions", ["editing rules/, contracts/", "pushing"]
        )
        self.assertEqual(
            ["excluded_actions:", "- editing rules/, contracts/", "- pushing"], lines
        )
        parsed = tickets_mod._parse_frontmatter(
            "---\n" + "\n".join(lines) + "\n---\n"
        )
        self.assertEqual(
            ["editing rules/, contracts/", "pushing"], parsed["excluded_actions"]
        )

    def test_an_entry_with_a_semicolon_takes_the_block_form_too(self):
        """Not because the reader would split it — it would not — but
        because a reader meeting `[a.py; b.py]` cannot tell that from the
        list it looks like, and a scope misread is a scope granted."""

        lines = tickets_mod._frontmatter_list("write_scope", ["a.py; b.py"])
        self.assertEqual(["write_scope:", "- a.py; b.py"], lines)
        parsed = tickets_mod._parse_frontmatter(
            "---\n" + "\n".join(lines) + "\n---\n"
        )
        self.assertEqual(["a.py; b.py"], parsed["write_scope"])

    def test_a_plain_list_stays_inline(self):
        self.assertEqual(
            ["write_scope: [a.py, b.py]"],
            tickets_mod._frontmatter_list("write_scope", ["a.py", "b.py"]),
        )

    def test_the_rule_is_stated_where_the_writer_is(self):
        self.assertIn("block", tickets_mod._frontmatter_list.__doc__ or "")
        self.assertIn("semicolon", tickets_mod._frontmatter_list.__doc__ or "")


