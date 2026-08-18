"""Installer regression cases grouped by behavioral seam."""

from __future__ import annotations

from ..support import *  # noqa: F403


class TestRoleAgentInstructions(unittest.TestCase):
    """The instruction every child of every role loads before it has read its
    own ticket. It used to open by sending that child to read rules/roles.md
    (149 words) 'before acting' -- and the two clauses a child acts on are in
    the rendered text itself, while folding roles.md's own clauses in instead
    would be 105 words against an 80-word body. So the sentence is cut, and
    pinned cut: nothing else in the tree counts these words (D-2).

    The pin covers the whole rendered file, not only its instruction: the
    ``description`` is listed to every context holding the Agent tool --
    the dispatcher and every child alike -- on every turn, so a contract
    pointer left there is still a roles.md read the file names."""

    BODY_CEILING = 80

    def test_role_instructions_send_no_child_to_read_the_role_contract(self):
        self.assertNotIn("roles.md", install.ROLE_INSTRUCTIONS)
        self.assertNotIn("before acting", install.ROLE_INSTRUCTIONS)
        self.assertIn("delegated scope", install.ROLE_INSTRUCTIONS)

    def test_claude_agent_file_names_no_contract_read_and_stays_under_the_ceiling(self):
        profile = install.load_role_profiles()["orch-worker"]

        rendered = install.render_claude_agent("orch-worker", profile)

        self.assertNotIn("roles.md", rendered)
        _frontmatter, body = install.split_frontmatter(rendered)
        self.assertLessEqual(validate.body_words(body), self.BODY_CEILING)

    def test_codex_agent_file_names_no_contract_read(self):
        profile = install.load_role_profiles()["orch-worker"]

        rendered = install.render_codex_agent("orch-worker", profile)

        self.assertNotIn("roles.md", rendered)
        line = next(
            line for line in rendered.splitlines() if line.startswith("developer_instructions")
        )
        self.assertLessEqual(validate.body_words(line), self.BODY_CEILING)

    def test_role_description_is_the_role_name_and_nothing_to_follow(self):
        # The name is the routing fact. "follow the role contract at <path>"
        # was an imperative with no addressee in a field every context reads,
        # and the dispatcher's law already lives in rules/roles.md section 4
        # by way of contracts/work-item.md and orch-frontier.
        self.assertEqual("Orchflows child role orch-worker.", install._role_description("orch-worker"))
