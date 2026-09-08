"""Publication admission preserves operator bytes and active runtime dependencies."""

import json
import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from installer import application, runtime
from installer.models import Plan


class PublicationAdmissionTests(unittest.TestCase):
    def fixture(self, root):
        home = root / 'home'
        source = root / 'source.py'
        source.write_text('VALUE = 1\n')
        plan = Plan(lib_home=home / 'lib', scope_home=home, bin_dir=home / 'bin',
                    receipt_path=home / 'receipt.json',
                    lib_copies=[(source, home / 'lib/module.py')],
                    scripts=[(source, home / 'bin/module.py')])
        application.apply_plan(plan, 'old')
        return plan, source

    def active(self, plan):
        ticket = plan.scope_home / 'state/tickets/r/B1.md'
        ticket.parent.mkdir(parents=True)
        ticket.write_text('---\nid: B1\nrun: r\nstatus: claimed\n'
                          'executor: orch-do\nprofile: orch-worker\n---\n')
        return ticket

    def test_unowned_collision_refuses_without_changing_live_bytes_or_receipt(self):
        with tempfile.TemporaryDirectory() as raw:
            plan, source = self.fixture(Path(raw))
            helper = plan.bin_dir / 'new_helper.py'
            helper.write_bytes(b'USER_HELPER = 42\r\n')
            before = helper.read_bytes(), plan.receipt_path.read_bytes()
            plan.scripts.append((source, helper))
            source.write_text('VALUE = 2\n')
            with self.assertRaisesRegex(RuntimeError, re.escape(str(helper))):
                application.apply_plan(plan, 'collision')
            self.assertEqual(before, (helper.read_bytes(), plan.receipt_path.read_bytes()))
            self.assertEqual('VALUE = 1\n', (plan.lib_home / 'module.py').read_text())
            self.assertEqual([], list(plan.scope_home.glob('.install-transaction-*')))

    def test_owned_replacement_preserves_noncolliding_unknown_helper(self):
        with tempfile.TemporaryDirectory() as raw:
            plan, source = self.fixture(Path(raw))
            helper = plan.bin_dir / 'operator.py'
            helper.write_bytes(b'USER_HELPER = 42\r\n')
            before = helper.read_bytes()
            source.write_text('VALUE = 2\n')
            receipt = application.apply_plan(plan, 'updated')
            self.assertEqual(before, helper.read_bytes())
            self.assertEqual('VALUE = 2\n', (plan.bin_dir / 'module.py').read_text())
            self.assertNotIn(str(helper), {entry['path'] for entry in receipt['files']})

    def runtime_fixture(self, root):
        plan, source = self.fixture(root)
        home = plan.scope_home / 'runtime'
        home.mkdir()
        (home / 'dependency.txt').write_text('OLD ACTIVE DEPENDENCY')
        plan.runtime_action = 'reuse'  # deliberately stale planning input
        return plan, source, home

    def test_active_runtime_repair_refuses_actual_swap_from_stale_reuse_plan(self):
        with tempfile.TemporaryDirectory() as raw:
            plan, source, home = self.runtime_fixture(Path(raw))
            self.active(plan)
            before = plan.receipt_path.read_bytes()
            built = []
            def build(stage):
                built.append(stage)
                (stage / 'dependency.txt').write_text('NEW DEPENDENCY')
            with patch.object(runtime, 'private_runtime_home', return_value=home), patch.object(
                runtime, 'private_runtime_action', return_value='repair'
            ), patch.object(runtime, '_build_private_runtime', side_effect=build), patch.object(
                runtime, 'private_runtime_is_healthy', return_value=True
            ):
                with self.assertRaisesRegex(RuntimeError, 'protected by active references'):
                    application.apply_plan(plan, 'repair')
            self.assertEqual([], built)
            self.assertEqual('OLD ACTIVE DEPENDENCY', (home / 'dependency.txt').read_text())
            self.assertEqual(before, plan.receipt_path.read_bytes())
            self.assertEqual([], list(plan.scope_home.glob('.runtime-*')))

    def test_verified_runtime_reuse_does_not_enter_mutating_ensure(self):
        with tempfile.TemporaryDirectory() as raw:
            plan, _, home = self.runtime_fixture(Path(raw))
            self.active(plan)
            plan.runtime_action = 'repair'  # current observation wins
            with patch.object(runtime, 'private_runtime_home', return_value=home), patch.object(
                runtime, 'private_runtime_action', return_value='reuse'
            ), patch.object(application, '_create_private_runtime', side_effect=AssertionError('mutating ensure')):
                receipt = application.apply_plan(plan, 'reuse')
            self.assertEqual('reuse', receipt['source_commit'])
            self.assertEqual('OLD ACTIVE DEPENDENCY', (home / 'dependency.txt').read_text())

    def test_quiescent_runtime_repair_uses_real_swap_and_retires_backup(self):
        with tempfile.TemporaryDirectory() as raw:
            plan, _, home = self.runtime_fixture(Path(raw))
            def build(stage):
                (stage / 'dependency.txt').write_text('NEW DEPENDENCY')
            with patch.object(runtime, 'private_runtime_home', return_value=home), patch.object(
                runtime, 'private_runtime_action', return_value='repair'
            ), patch.object(runtime, '_build_private_runtime', side_effect=build), patch.object(
                runtime, 'private_runtime_is_healthy', return_value=True
            ):
                receipt = application.apply_plan(plan, 'repair')
            self.assertEqual('repair', receipt['source_commit'])
            self.assertEqual('NEW DEPENDENCY', (home / 'dependency.txt').read_text())
            self.assertEqual([], list(plan.scope_home.glob('.runtime-*')))

    def test_legacy_lifecycle_writer_requires_quiet_window_for_runtime_only_repair(self):
        with tempfile.TemporaryDirectory() as raw:
            plan, _, home = self.runtime_fixture(Path(raw))
            for name in ('tickets.py', 'tickets_install_guard.py', 'tickets_issue.py',
                         'tickets_attempts.py', 'tickets_dispatch_facade.py', 'tickets_mint.py',
                         'tickets_frame.py', 'tickets_seal.py'):
                (plan.bin_dir / name).write_text('# installation_lock\n')
            (plan.bin_dir / 'tickets_lifecycle.py').write_text('# legacy lifecycle writer\n')
            before = plan.receipt_path.read_bytes()
            with patch.object(runtime, 'private_runtime_home', return_value=home), patch.object(
                runtime, 'private_runtime_action', return_value='repair'
            ), patch.object(application, '_create_private_runtime') as create:
                with self.assertRaisesRegex(RuntimeError, 'old bytes retained'):
                    application.apply_plan(plan, 'repair')
                create.assert_not_called()
            self.assertEqual(before, plan.receipt_path.read_bytes())
            self.assertEqual('OLD ACTIVE DEPENDENCY', (home / 'dependency.txt').read_text())
