"""Installer regression cases grouped by behavioral seam."""

from __future__ import annotations

from ..support import *  # noqa: F403


class TestClaudeAlwaysOnImport(unittest.TestCase):
    """Criteria 3-4: the always-on layer is one appended import line in
    CLAUDE.md pointing at an installer-owned ``~/.orchflows/host-block.md``;
    Codex keeps the proven inline marker block (import expansion was probed
    against the installed CLI and does not resolve in AGENTS.md)."""

    def test_upsert_import_line_is_idempotent(self):
        updated, action = install.upsert_import_line("", "@/x/host-block.md", "<!-- BEGIN -->", "<!-- END -->")
        self.assertEqual("@/x/host-block.md\n", updated)
        self.assertEqual("created-file", action)

        updated2, action2 = install.upsert_import_line(
            updated, "@/x/host-block.md", "<!-- BEGIN -->", "<!-- END -->"
        )
        self.assertEqual(updated, updated2)
        self.assertEqual("already-present", action2)

    def test_upsert_import_line_migrates_legacy_inline_block(self):
        legacy = "before\n<!-- BEGIN -->\nold managed content\n<!-- END -->\nafter\n"

        updated, action = install.upsert_import_line(legacy, "@/x/host-block.md", "<!-- BEGIN -->", "<!-- END -->")

        self.assertEqual("migrated-from-block", action)
        self.assertNotIn("<!-- BEGIN -->", updated)
        self.assertNotIn("old managed content", updated)
        self.assertIn("before\n", updated)
        self.assertIn("after\n", updated)
        self.assertIn("@/x/host-block.md\n", updated)

    def test_upsert_import_line_appends_to_existing_file_without_block(self):
        updated, action = install.upsert_import_line(
            "# My CLAUDE.md\nsome instructions\n", "@/x/host-block.md", "<!-- BEGIN -->", "<!-- END -->"
        )

        self.assertEqual("added-import", action)
        self.assertTrue(updated.startswith("# My CLAUDE.md\nsome instructions\n"))
        self.assertTrue(updated.rstrip("\n").endswith("@/x/host-block.md"))

    def test_user_plan_renders_host_block_file_and_claude_import(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            (home / ".claude").mkdir(parents=True)
            (home / ".codex").mkdir(parents=True)
            with patch.object(install.Path, "home", return_value=home), mock_host_clis(
                "claude", "codex"
            ):
                plan = install.build_plan("user", None)

            self.assertEqual(home / ".orchflows" / "host-block.md", plan.host_block.dest)
            self.assertEqual("host-block", plan.host_block.kind)
            self.assertNotIn("{{ORCH_LIB}}", plan.host_block.content)
            self.assertIn("Friction law", plan.host_block.content)

            self.assertEqual(home / ".claude" / "CLAUDE.md", plan.claude_import.dest)
            self.assertEqual(plan.host_block.dest.resolve(), plan.claude_import.import_target)

            # Codex keeps the full inline block, never an import.
            self.assertEqual(1, len(plan.blocks))
            self.assertEqual(home / ".codex" / "AGENTS.md", plan.blocks[0].dest)
            self.assertIn("Friction law", plan.blocks[0].content)

    def test_apply_writes_host_block_file_and_appends_import_line(self):
        """What the apply put on disk. Which paths those are is graded by
        `test_user_plan_renders_host_block_file_and_claude_import` above,
        which needs no apply at all -- so this one reads the plan's own
        destinations and can share an install with three other tests."""

        plan, home, _claude_dir, _codex_dir = relocated_user_install()
        host_block_path = home / ".orchflows" / "host-block.md"
        self.assertEqual(host_block_path, plan.host_block.dest)
        self.assertTrue(host_block_path.is_file())
        self.assertIn("Friction law", host_block_path.read_text(encoding="utf-8"))

        claude_text = plan.claude_import.dest.read_text(encoding="utf-8")
        import_line = f"@{host_block_path.resolve()}"
        self.assertEqual(1, claude_text.count(import_line))

        # Codex AGENTS.md still carries the full inline block.
        agents_text = plan.blocks[0].dest.read_text(encoding="utf-8")
        self.assertIn("Friction law", agents_text)
        self.assertNotIn(import_line, agents_text)

    def test_reapply_does_not_duplicate_import_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            (home / ".claude").mkdir(parents=True)
            with patch.object(install.Path, "home", return_value=home), mock_host_clis("claude"):
                plan = install.build_plan("user", None)
                install.apply_plan(plan)
                plan2 = install.build_plan("user", None)
                install.apply_plan(plan2)

            claude_text = (home / ".claude" / "CLAUDE.md").read_text(encoding="utf-8")
            host_block_path = home / ".orchflows" / "host-block.md"
            import_line = f"@{host_block_path.resolve()}"
            self.assertEqual(1, claude_text.count(import_line))

    def test_apply_migrates_legacy_inline_block_in_claude_md(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            (home / ".claude").mkdir(parents=True)
            claude_md = home / ".claude" / "CLAUDE.md"
            template_text = install.HOST_BLOCK_TEMPLATE.read_text(encoding="utf-8")
            start_marker, end_marker = install.template_markers(template_text)
            claude_md.write_text(
                f"# personal notes\n{start_marker}\nold rendered block\n{end_marker}\n", encoding="utf-8"
            )

            with patch.object(install.Path, "home", return_value=home), mock_host_clis("claude"):
                plan = install.build_plan("user", None)
                install.apply_plan(plan)

            claude_text = claude_md.read_text(encoding="utf-8")
            self.assertIn("# personal notes", claude_text)
            self.assertNotIn(start_marker, claude_text)
            self.assertNotIn("old rendered block", claude_text)
            self.assertIn(f"@{(home / '.orchflows' / 'host-block.md').resolve()}", claude_text)

    def test_uninstall_reports_manual_cleanup_for_import_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            claude_md = project / "CLAUDE.md"
            claude_md.write_text("notes\n@/x/host-block.md\n", encoding="utf-8")
            receipt_path = project / ".orchflows" / "receipt.json"
            receipt_path.parent.mkdir(parents=True)
            receipt_path.write_text(
                json.dumps(
                    {
                        "files": [],
                        "blocks": [],
                        "imports": [
                            {
                                "path": str(claude_md),
                                "import_line": "@/x/host-block.md",
                                "install_action": "created-file",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            result = install.run_uninstall("project", project, dry_run=False)

            self.assertTrue(claude_md.exists())
            actions = "\n".join(entry["action"] for entry in result["manual_actions"])
            self.assertIn("@/x/host-block.md", actions)
