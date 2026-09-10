"""Canonical self-improve has one identity and four generated host entries."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import install
from installer.doctor import _planned_files
from installer.packages import split_frontmatter
from scripts import rings
from tests.test_installer_cases.support import mock_host_clis
from tests.test_installer_cases.node_tooling import offline_node_preparation
from tests.test_rings import _item, _world


class SelfImproveEntryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="self-improve-entry-")
        self.addCleanup(self.temporary.cleanup)
        self.home = Path(self.temporary.name).resolve()
        home_patch = patch.object(Path, "home", return_value=self.home)
        home_patch.start()
        self.addCleanup(home_patch.stop)
        environment_patch = patch.dict(os.environ, {
            "CLAUDE_CONFIG_DIR": str(self.home / "claude"),
            "CODEX_HOME": str(self.home / "codex"),
            "GROK_HOME": str(self.home / "grok"),
        })
        environment_patch.start()
        self.addCleanup(environment_patch.stop)
        hosts_patch = mock_host_clis("claude", "codex", "grok")
        hosts_patch.start()
        self.addCleanup(hosts_patch.stop)
        self.plan = install.build_plan()

    def entries(self, plan):
        return {
            path: (kind, text)
            for _, kind, path, _, text in _planned_files(plan)
            if kind in {"adapter", "prompt", "codex-skill", "grok-skill"} and (path.stem == "orch-self-improve" or path.parent.name == "orch-self-improve")
        }

    def test_plan_preserves_surfaces_arguments_and_one_canonical_identity(self):
        entries = self.entries(self.plan)
        expected = {
            self.home / "claude/skills/orch-self-improve/SKILL.md": "adapter",
            self.home / "codex/prompts/orch-self-improve.md": "prompt",
            self.home / "codex/skills/orch-self-improve/SKILL.md": "codex-skill",
            self.home / "grok/skills/orch-self-improve/SKILL.md": "grok-skill",
        }
        self.assertEqual(expected, {path: kind for path, (kind, _) in entries.items()})
        target = self.plan.lib_home / "example-workflows/orch-self-improve/SKILL.md"
        for path, (kind, text) in entries.items():
            self.assertIn(str(target), text)
            self.assertNotIn("--workflow self-improve", text)
            if kind == "prompt":
                self.assertIn("$ARGUMENTS", text)
            else:
                head, _ = split_frontmatter(text)
                host = {"adapter": "claude", "codex-skill": "codex", "grok-skill": "grok"}[kind]
                fields = {line.partition(":")[0] for line in head.splitlines() if ":" in line}
                self.assertLessEqual(fields, set(install.load_host_adapters()[host]["frontmatter"]["legal_keys"]))
                self.assertIn("name: orch-self-improve", head)
                self.assertNotIn("role:", head)
                if host == "claude":
                    self.assertIn("disable-model-invocation: true", head)
        self.assertEqual(entries, self.entries(install.build_plan()))
        for surface in (self.plan.claude_adapters, self.plan.codex_prompts,
                        self.plan.codex_skills, self.plan.grok_skills):
            self.assertFalse(any(p.stem == "self-improve" or p.parent.name == "self-improve" for p, _ in surface))
        self.assertTrue(any(p.parent.name == "orch-self-improve" for p, _ in self.plan.by_name))
        inventory = rings.inventory(("workflow",), home=self.home / "ring", lib=install.REPO_ROOT)
        names = [r["name"] for r in inventory]
        self.assertEqual(1, names.count("orch-self-improve"))
        self.assertNotIn("self-improve", names)
        resolved = rings.resolve("workflow", "orch-self-improve", home=self.home / "ring", lib=install.REPO_ROOT)
        self.assertEqual("lib", resolved["ring"])
        self.assertEqual("orch-self-improve", resolved["name"])

    def test_receipt_reinstall_stale_cleanup_and_uninstall_own_entries(self):
        # Apply only the generated seam, avoiding runtime/frontend installation.
        plan = install.Plan(lib_home=self.plan.lib_home, scope_home=self.plan.scope_home,
                            bin_dir=self.plan.bin_dir, receipt_path=self.plan.receipt_path)
        for field in ("claude_adapters", "codex_prompts", "codex_skills", "grok_skills"):
            setattr(plan, field, [(p, t) for p, t in getattr(self.plan, field)
                                 if p in self.entries(self.plan)])
        expected = self.entries(plan)
        receipt = install.apply_plan(plan, accepted_source=install.resolve_source_commit())
        self.assertEqual({str(p) for p in expected}, {r["path"] for r in receipt["files"]})
        install.apply_plan(plan, accepted_source=install.resolve_source_commit())
        self.assertTrue(all(p.is_file() for p in expected))
        empty = install.Plan(lib_home=plan.lib_home, scope_home=plan.scope_home,
                             bin_dir=plan.bin_dir, receipt_path=plan.receipt_path)
        install.apply_plan(empty, accepted_source=install.resolve_source_commit())
        self.assertTrue(all(not p.exists() for p in expected))
        install.apply_plan(plan, accepted_source=install.resolve_source_commit())
        install.run_uninstall("user", None, dry_run=False)
        self.assertTrue(all(not p.exists() for p in expected))

    def test_custom_reserved_workflow_names_still_refuse(self):
        for ring in ("home", "project"):
            for name in ("orch-self-improve", "orch-arbitrary"):
                with self.subTest(ring=ring, name=name), _world() as world:
                    root = world[ring] if ring == "home" else world[ring] / ".orchflows"
                    _item(root / "workflows", "workflow", name)
                    with self.assertRaises(rings.RingError) as caught:
                        rings.resolve("workflow", name, home=world["home"],
                                      project=world["project"], lib=world["lib"])
                    self.assertEqual("reserved-name", caught.exception.code)

    def test_upgrade_retires_managed_skills_without_deleting_custom_files(self):
        old = install.Plan(lib_home=self.plan.lib_home, scope_home=self.plan.scope_home,
                           bin_dir=self.plan.bin_dir, receipt_path=self.plan.receipt_path)
        fields = ("claude_adapters", "codex_prompts", "codex_skills", "grok_skills")
        retired = ("review-delivery", "browser-game", "self-improve")
        for field in fields:
            entries = [(p, t) for p, t in getattr(self.plan, field) if p in self.entries(self.plan)]
            setattr(old, field, [(Path(str(p).replace("orch-self-improve", name)), t)
                                for p, t in entries for name in retired])
        install.apply_plan(old, accepted_source=install.resolve_source_commit())
        keep = self.home / "codex/skills/self-improve/custom.md"
        keep.write_text("user-owned content", encoding="utf-8")
        current = install.Plan(lib_home=old.lib_home, scope_home=old.scope_home,
                               bin_dir=old.bin_dir, receipt_path=old.receipt_path)
        for field in fields:
            setattr(current, field, [(p, t) for p, t in getattr(self.plan, field)
                                     if p in self.entries(self.plan)])
        install.apply_plan(current, accepted_source=install.resolve_source_commit())
        for field in fields:
            self.assertTrue(all(not path.exists() for path, _ in getattr(old, field)))
        self.assertFalse((self.home / "codex/skills/review-delivery").exists())
        self.assertFalse((self.home / "codex/skills/browser-game").exists())
        self.assertEqual("user-owned content", keep.read_text(encoding="utf-8"))
        self.assertTrue(all(path.is_file() for path in self.entries(current)))

    def test_installed_collection_resolves_public_trace_facade(self):
        import json
        import subprocess
        import sys

        self.plan.runtime_action = None
        with offline_node_preparation():
            install.apply_plan(self.plan, accepted_source=install.resolve_source_commit())
        source = self.home / 'session.jsonl'
        source.write_text(json.dumps({
            'timestamp': '2026-09-07T10:00:00Z', 'type': 'session_meta',
            'payload': {'id': 'installed-session', 'cwd': str(self.home)}}) + '\n' + json.dumps({
            'timestamp': '2026-09-07T10:01:00Z', 'type': 'response_item',
            'payload': {'type': 'message', 'role': 'assistant',
                        'content': [{'type': 'output_text', 'text': 'nearby success'}]}}) + '\n',
            encoding='utf-8')
        selection = self.home / 'selection.json'
        selection.write_text(json.dumps({
            'mode': 'review', 'timezone': 'America/Indianapolis',
            'timezone_provenance': 'fixed offset fixture',
            'as_of': '2026-09-07T07:00:00-04:00',
            'start': '2026-09-07T10:00:00Z', 'end': '2026-09-07T11:00:00Z',
            'sources': [{'kind': 'codex', 'path': str(source)}],
            'projects': [], 'sessions': [], 'runs': [], 'descendants': True,
            'repair_bound': 2}), encoding='utf-8')
        command = self.plan.lib_home / 'example-workflows/orch-self-improve/scripts/self_improve.py'
        environment = dict(os.environ, ORCHFLOWS_STATE_HOME=str(self.home / 'sink'))
        result = subprocess.run([sys.executable, str(command), 'collect', '--selection', str(selection)],
                                env=environment, capture_output=True, text=True, timeout=30)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        collected = json.loads(result.stdout)
        self.assertEqual('complete', collected['coverage'])
