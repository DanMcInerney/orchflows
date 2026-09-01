"""Installer regression cases grouped by behavioral seam."""

from __future__ import annotations

from ..support import *  # noqa: F403

from installer import managed_text, packages

# This module declares exactly one class, and every case below is a method of
# it. `test_installer_cases/managed_text/*.py` is collected by nothing: the one
# door is the explicit class-name import block at `tests/test_installer_managed
# .py`, which is outside this ticket's write scope, so a second top-level
# `TestCase` here would be imported by no shard and would report green without
# ever running. A mixin folded into the imported class is not the way out
# either: `tests/test_run_tests.py` holds every class name DECLARED under this
# tree against the class name each case LOADS under, and a mixin declares its
# methods under one name and loads them under another.

_GROK_WORKER_FRONTMATTER = (
    "---\n"
    "name: orch-tdd\n"
    "description: Implement one code ticket through red-green slices.\n"
    "role: worker\n"
    "pack: orch-code-pack\n"
    "---\n"
)
_GROK_GLUE_FRONTMATTER = (
    "---\n"
    "name: orch-integrate\n"
    "description: Adjudicate one returned child result at the join.\n"
    "role: none\n"
    "---\n"
)
_GROK_LIB_SKILL_MD = Path("/lib/orchflows/skills/units/orch-tdd/SKILL.md")


class TestRoleAgentInstructions(unittest.TestCase):
    """The role instruction and the three Grok text surfaces rendered around it.

    The instruction is what every child of every role loads before it has read
    its own ticket. It used to open by sending that child to read rules/roles.md
    (149 words) 'before acting' -- and the two clauses a child acts on are in
    the rendered text itself, while folding roles.md's own clauses in instead
    would be 105 words against an 80-word body. So the sentence is cut, and
    pinned cut: nothing else in the tree counts these words (D-2).

    The pin covers the whole rendered file, not only its instruction: the
    ``description`` is listed to every context holding the Agent tool --
    the dispatcher and every child alike -- on every turn, so a contract
    pointer left there is still a roles.md read the file names."""

    # One fact, not two: installer/packages.py's ROLE_INSTRUCTIONS is the
    # only content a role agent file ever carries (no separate un-rendered
    # source, unlike a SKILL.md body), so this ceiling and
    # rules/token-economy.md §11's "role agent file" number are the same
    # fact. Imported, not restated -- common.py is the owner
    # (tools/validate_support/common.py's ROLE_AGENT_BUDGET comment).
    BODY_CEILING = validate.ROLE_AGENT_BUDGET

    # A snake_case key -- `subagent_type`, `model_reasoning_effort` -- is the
    # exact mistake this catches: it is what the profile row and the Codex
    # column call these things, and Grok would ignore it silently.
    GROK_CAMEL_KEY_RE = re.compile(r"^[a-z]+(?:[A-Z][A-Za-z0-9]*)*$")
    GROK_UNBOUND_AGENT_FIELDS = (
        "completionRequirement",
        "capabilityMode",
        "maxTurns",
        "isolation",
    )

    # --- The role instruction itself -------------------------------------

    def test_role_instructions_send_no_child_to_read_the_role_contract(self):
        self.assertNotIn("roles.md", install.ROLE_INSTRUCTIONS)
        self.assertNotIn("before acting", install.ROLE_INSTRUCTIONS)
        self.assertIn("delegated scope", install.ROLE_INSTRUCTIONS)
        for anchor in (
            "exact primary skill",
            "each exact member",
            "launch-stated ordered sequence",
            "dispatch id, seal, and assigned name",
            "first record is your acceptance",
            "directly",
            "never redispatch",
        ):
            self.assertIn(anchor, install.ROLE_INSTRUCTIONS)

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
        # by way of contracts/work-item.md and contracts/dispatch.md.
        self.assertEqual("Orchflows child role orch-worker.", install._role_description("orch-worker"))

    # --- The rendered ``$GROK_HOME/agents/<role>.md`` ---------------------
    #
    # Grok parses an agent definition out of YAML frontmatter with camelCase
    # keys, and its ``AgentDefinition`` also accepts ``completionRequirement``,
    # ``capabilityMode``, ``maxTurns`` and ``isolation``. None of those is a
    # field the one role-profile table binds, so none is rendered. ``isolation``
    # in particular stays the decomposer's ticket field, established at dispatch
    # through ``spawn_subagent``'s own argument rather than frozen per role in a
    # file every dispatch of that role would inherit.

    def _grok_agent_frontmatter(self, rendered):
        frontmatter, _body = install.split_frontmatter(rendered)
        fields = {}
        for line in frontmatter.splitlines():
            if line.strip() == "---":
                continue
            key, separator, value = line.partition(":")
            self.assertTrue(separator, f"not a YAML mapping line: {line!r}")
            fields[key.strip()] = value.strip()
        return fields

    def test_grok_agent_is_yaml_frontmatter_with_camelcase_keys_only(self):
        profile = install.load_role_profiles()["orch-worker"]

        fields = self._grok_agent_frontmatter(managed_text.render_grok_agent("orch-worker", profile))

        self.assertEqual({"name", "description", "model", "effort"}, set(fields))
        for key in fields:
            self.assertRegex(key, self.GROK_CAMEL_KEY_RE)

    def test_grok_agent_carries_the_rows_censused_model_and_valid_effort(self):
        for name in ("orch-planner", "orch-worker"):
            with self.subTest(name=name):
                profile = install.load_role_profiles()[name]
                binding = profile["grok"]

                fields = self._grok_agent_frontmatter(managed_text.render_grok_agent(name, profile))

                self.assertEqual(binding["subagent_type"], fields["name"])
                self.assertEqual(binding["model"], fields["model"])
                self.assertEqual(binding["effort"], fields["effort"])
                self.assertIn(fields["model"], packages.GROK_MODEL_CENSUS)
                self.assertIn(fields["effort"], packages.GROK_EFFORTS)

    def test_grok_agent_binds_no_field_the_profile_row_does_not(self):
        rendered = managed_text.render_grok_agent(
            "orch-worker", install.load_role_profiles()["orch-worker"]
        )

        for field in self.GROK_UNBOUND_AGENT_FIELDS:
            self.assertNotIn(field, rendered)
        self.assertIn(install.ROLE_INSTRUCTIONS, rendered)
        self.assertNotIn("roles.md", rendered)

    def test_rendering_grok_leaves_the_claude_and_codex_agents_alone(self):
        profile = install.load_role_profiles()["orch-worker"]

        claude = install.render_claude_agent("orch-worker", profile)
        codex = install.render_codex_agent("orch-worker", profile)

        for rendered in (claude, codex):
            self.assertNotIn("spawn_subagent", rendered)
            self.assertNotIn(profile["grok"]["model"], rendered)
        self.assertIn("model_reasoning_effort", codex)
        self.assertIn(f"model: {profile['claude']['model']}", claude)

    # --- The rendered ``$GROK_HOME/skills/<name>/SKILL.md`` ---------------
    #
    # Two verified gaps own this shape. Grok does not expand ``@`` includes, so
    # every Claude adapter body reaching it through the compat scan is a literal
    # path and the canonical body never loads -- the Grok body names that body by
    # an explicit read instead. And ``context: fork`` / ``agent: <role>`` are
    # unknown skill keys on Grok and are ignored, so the role binding those keys
    # carry natively on Claude has to be stated in the body, as an explicit
    # dispatch gate.

    def _role_body(self):
        return managed_text.grok_skill_text(
            _GROK_WORKER_FRONTMATTER,
            _GROK_LIB_SKILL_MD,
            install.load_role_profiles()["orch-worker"],
        )

    def test_no_grok_body_is_an_at_include_and_every_one_reads_its_canonical_body(self):
        glue = managed_text.grok_skill_text(_GROK_GLUE_FRONTMATTER, _GROK_LIB_SKILL_MD)

        instruction = f"{_GROK_LIB_SKILL_MD} and follow it exactly"
        for label, text in (("glue", glue), ("role", self._role_body())):
            with self.subTest(surface=label):
                self.assertNotIn(f"@{_GROK_LIB_SKILL_MD}", text)
                self.assertEqual([], [l for l in text.splitlines() if l.startswith("@")])
                # Sentence-initial in the flat pointer, mid-sentence inside the
                # dispatch gate, exactly as the Codex gate words it. The
                # criterion is the explicit read instruction, not its casing.
                self.assertTrue(
                    f"Read {instruction}" in text or f"read {instruction}" in text,
                    f"{label} body must name its canonical body by an explicit read",
                )

    def test_the_role_bearing_grok_body_states_the_explicit_dispatch_gate(self):
        binding = install.load_role_profiles()["orch-worker"]["grok"]

        body = self._role_body()

        self.assertIn("spawn_subagent", body)
        self.assertIn(f"subagent_type `{binding['subagent_type']}`", body)
        self.assertIn("emitted launch prompt and exact named skill", body)
        self.assertIn("missing or mismatched", body)
        self.assertIn("no inline fallback", body)
        self.assertTrue(body.rstrip().endswith(install.FORK_ARRIVAL_CLAUSE))

    def test_a_role_none_grok_body_carries_neither_gate_nor_fork_clause(self):
        glue = managed_text.grok_skill_text(_GROK_GLUE_FRONTMATTER, _GROK_LIB_SKILL_MD)

        self.assertNotIn("spawn_subagent", glue)
        self.assertNotIn(install.FORK_ARRIVAL_CLAUSE, glue)

    def test_grok_frontmatter_drops_the_keys_grok_would_silently_ignore(self):
        frontmatter, _body = install.split_frontmatter(self._role_body())

        self.assertIn("name: orch-tdd", frontmatter)
        self.assertIn("description: Implement one code ticket", frontmatter)
        for ignored in ("role:", "pack:", "context:", "agent:"):
            self.assertNotIn(ignored, frontmatter)

    def test_a_declared_role_that_the_profile_contradicts_refuses(self):
        with self.assertRaisesRegex(ValueError, "declared role planner.*profile role worker"):
            managed_text.grok_role_adapter_body(
                "custom-planner",
                "planner",
                {"role": "worker", "grok": {"subagent_type": "orch-worker"}},
                _GROK_LIB_SKILL_MD,
            )

    # --- The managed ``[subagents]`` block in ``$GROK_HOME/config.toml`` --
    #
    # A user's config.toml is theirs; this owns three keys inside it and nothing
    # else, fenced by markers so a reinstall replaces its own block rather than
    # appending a second one. ``limit_behavior`` is ``queue`` on purpose: a spawn
    # past the concurrent cap waits its turn instead of becoming a lost lane,
    # which is what ``fail`` would make of it.

    def _rendered(self, text):
        updated, details = managed_text.render_grok_subagent_limits(text)
        again, _details = managed_text.render_grok_subagent_limits(updated)
        self.assertEqual(updated, again, "the managed block must be idempotent")
        if foundation.tomllib is not None:
            foundation.tomllib.loads(updated)
        return updated, details

    def test_an_absent_config_gains_the_three_managed_settings(self):
        updated, details = self._rendered("")

        self.assertIn(foundation.GROK_LIMITS_START, updated)
        self.assertIn(foundation.GROK_LIMITS_END, updated)
        self.assertEqual(
            {
                "subagents.max_concurrent": foundation.GROK_MAX_CONCURRENT,
                "subagents.max_depth": foundation.GROK_MAX_DEPTH,
                "subagents.limit_behavior": managed_text.GROK_LIMIT_BEHAVIOR,
            },
            details["settings"],
        )
        self.assertIn('limit_behavior = "queue"', updated)

    def test_an_existing_subagents_table_keeps_its_user_keys(self):
        text = (
            "[subagents]\n"
            "max_concurrent = 3\n"
            'user_key = "kept"\n'
            "\n"
            "[mcp_servers.example]\n"
            'command = "kept-too"\n'
        )

        updated, details = self._rendered(text)

        self.assertIn('user_key = "kept"', updated)
        self.assertIn("[mcp_servers.example]", updated)
        self.assertNotIn("max_concurrent = 3", updated)
        # The text assertions above run on every interpreter on purpose: 3.9
        # is the floor and the one leg without stdlib `tomllib`, so it is the
        # leg with no parser to catch a bad write. Only the reported previous
        # value is gated, because reading it requires the parser this leg
        # lacks -- it is None there, not 3.
        if foundation.tomllib is not None:
            self.assertEqual(3, details["previous"]["subagents.max_concurrent"])
            parsed = foundation.tomllib.loads(updated)
            self.assertEqual(foundation.GROK_MAX_CONCURRENT, parsed["subagents"]["max_concurrent"])
            self.assertEqual("queue", parsed["subagents"]["limit_behavior"])
            self.assertEqual("kept", parsed["subagents"]["user_key"])

    def test_a_config_with_no_subagents_table_gets_dotted_keys_above_the_first(self):
        updated, _details = self._rendered('[mcp_servers.example]\ncommand = "kept"\n')

        self.assertIn("subagents.max_concurrent = ", updated)
        self.assertIn("[mcp_servers.example]", updated)
        self.assertLess(updated.index("subagents.max_concurrent"), updated.index("[mcp_servers"))

    def test_a_reinstall_keeps_a_table_grok_appended_inside_the_block(self):
        """Grok adds ``[marketplace]`` to its own config within 0.2s of any
        subcommand, and a TOML editor lands it ahead of the trailing END
        comment -- inside the markers. A reinstall re-renders its three keys
        without carrying grok's table off with the old block. Planted, not
        provoked: nothing here may execute ``grok.exe``.

        The block also leaves EOF on the way out, which is what invited the
        append; grok's next table goes below ``[marketplace]``, outside the
        markers, so the file settles after one reinstall."""

        text = (
            "# BEGIN ORCHFLOWS SUBAGENT LIMITS\n"
            "subagents.max_concurrent = 20\n"
            "subagents.max_depth = 4\n"
            'subagents.limit_behavior = "queue"\n'
            "[marketplace]\n"
            "default_skills_installs_purged = true\n"
            "# END ORCHFLOWS SUBAGENT LIMITS\n"
        )

        updated, _details = self._rendered(text)

        self.assertIn("default_skills_installs_purged = true", updated)
        self.assertEqual(1, updated.count(foundation.GROK_LIMITS_START))
        self.assertEqual(1, updated.count(foundation.GROK_LIMITS_END))
        self.assertIn("subagents.max_concurrent = ", updated)
        self.assertLess(updated.index(foundation.GROK_LIMITS_END), updated.index("[marketplace]"))
        # 3.9 is the floor and the one leg without stdlib `tomllib`. What it
        # keeps is proved here rather than only on that leg of the matrix:
        # the parser gates the check, never the merge.
        self.assertEqual(
            updated, managed_text.render_grok_subagent_limits(text, toml_module=None)[0]
        )
        if foundation.tomllib is not None:
            parsed = foundation.tomllib.loads(updated)
            self.assertTrue(parsed["marketplace"]["default_skills_installs_purged"])
            self.assertEqual(foundation.GROK_MAX_CONCURRENT, parsed["subagents"]["max_concurrent"])

    def test_the_codex_agent_limits_block_is_untouched_by_the_grok_one(self):
        codex, _details = install._render_codex_agent_limits("")

        self.assertIn(foundation.CODEX_LIMITS_START, codex)
        self.assertNotIn(foundation.GROK_LIMITS_START, codex)
        self.assertNotIn("subagents", codex)

    # --- The managed ``[agents]`` block in ``~/.codex/config.toml`` --------
    #
    # Codex's block merges through the same owner as Grok's and answers to the
    # same law: a reinstall replaces its own block and leaves every other byte
    # alone. The dotted branch -- no ``[agents]`` table but some other table --
    # used to keep the whitespace-only prefix that removing the block left
    # behind, so each reinstall prepended one more blank line and the file grew
    # without bound. Reinstalling is the ordinary act, not the exotic one,
    # which is why every merge path is checked three renders deep.

    CODEX_CONFIGS = (
        ("an absent config", ""),
        ("a dotted branch above the first table", '[mcp_servers.example]\ncommand = "kept"\n'),
        ("an existing agents table", '[agents]\nmax_threads = 3\nkept = "yes"\n\n[o]\nv = true\n'),
        ("top-level keys and no table", 'model = "gpt-5-codex"\n'),
        ("top-level keys above a table", 'model = "gpt-5-codex"\n\n[mcp_servers.e]\nc = "k"\n'),
        ("top-level keys spaced off a table", 'model = "gpt-5-codex"\n\n\n[mcp_servers.e]\nc = "k"\n'),
        ("a comment above a table", '# mine\n\n[mcp_servers.e]\nc = "k"\n'),
        ("a whitespace-only config", "\n"),
    )

    def test_reinstalling_over_a_codex_config_leaves_the_block_byte_stable(self):
        for label, text in self.CODEX_CONFIGS:
            with self.subTest(config=label):
                once, _details = managed_text.render_codex_agent_limits(text)
                twice, _details = managed_text.render_codex_agent_limits(once)
                thrice, _details = managed_text.render_codex_agent_limits(twice)

                self.assertEqual(once, twice, "a reinstall must not change the rendered bytes")
                self.assertEqual(twice, thrice, "and the third reinstall must not either")
                self.assertIn(foundation.CODEX_LIMITS_START, once)
                self.assertIn(foundation.CODEX_LIMITS_END, once)
                if foundation.tomllib is not None:
                    foundation.tomllib.loads(once)

    def test_a_codex_reinstall_keeps_the_user_content_it_found(self):
        first, _details = managed_text.render_codex_agent_limits(
            '[mcp_servers.example]\ncommand = "kept"\n'
        )

        again, _details = managed_text.render_codex_agent_limits(first)

        self.assertFalse(again.startswith("\n"), "no blank line may accumulate above the block")
        self.assertIn('command = "kept"', again)
        self.assertLess(again.index("agents.max_threads"), again.index("[mcp_servers"))

    def test_a_codex_install_keeps_the_blank_lines_the_user_wrote(self):
        # The separator this branch takes back is its own, not any blank line
        # it finds. A first install has written none, so the two the user put
        # between their keys and their first table are still two afterwards --
        # and stay two through every reinstall.
        text = 'model = "gpt-5-codex"\n\n\n[mcp_servers.e]\nc = "k"\n'

        once, _details = managed_text.render_codex_agent_limits(text)
        twice, _details = managed_text.render_codex_agent_limits(once)

        self.assertTrue(once.startswith('model = "gpt-5-codex"\n\n\n'), once)
        self.assertEqual(once, twice)
