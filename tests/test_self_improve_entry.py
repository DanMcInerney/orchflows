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
            if path.stem == "orch-self-improve" or path.parent.name == "orch-self-improve"
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
        target = self.plan.lib_home / "example-workflows/self-improve/SKILL.md"
        for path, (kind, text) in entries.items():
            self.assertIn(str(target), text)
            self.assertIn("--workflow self-improve", text)
            self.assertNotIn("--workflow orch-self-improve", text)
            self.assertIn("arguments unchanged", text)
            self.assertIn("explicit user request", text)
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
            self.assertTrue(any(p.stem == "self-improve" or p.parent.name == "self-improve" for p, _ in surface))
        self.assertFalse(any(p.parent.name == "orch-self-improve" for p, _ in self.plan.by_name))
        inventory = rings.inventory(("workflow",), home=self.home / "ring", lib=install.REPO_ROOT)
        names = [r["name"] for r in inventory]
        self.assertEqual(1, names.count("self-improve"))
        self.assertNotIn("orch-self-improve", names)

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
        command = self.plan.lib_home / 'example-workflows/self-improve/scripts/self_improve.py'
        environment = dict(os.environ, ORCHFLOWS_STATE_HOME=str(self.home / 'sink'))
        result = subprocess.run([sys.executable, str(command), 'collect', '--selection', str(selection)],
                                env=environment, capture_output=True, text=True, timeout=30)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        collected = json.loads(result.stdout)
        self.assertEqual('complete', collected['coverage'])
