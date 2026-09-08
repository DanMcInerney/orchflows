"""Updates publish installer-owned bytes without interpreting ticket history."""
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

from installer import application, publication
from installer.models import Plan


class OrdinaryUpdateTests(unittest.TestCase):
    def fixture(self, root):
        home = root / 'home'
        source = root / 'writer.py'
        source.write_text('# legacy writer with no installation coordination\nVALUE = 1\n')
        plan = Plan(lib_home=home / 'lib', scope_home=home, bin_dir=home / 'bin',
                    receipt_path=home / 'receipt.json',
                    lib_copies=[(source, home / 'lib/module.py')],
                    scripts=[(source, home / 'bin/tickets.py')])
        application.apply_plan(plan, 'old')
        return plan, source

    def test_upgrade_ignores_old_writers_and_unreadable_ticket_history(self):
        with tempfile.TemporaryDirectory() as raw:
            plan, source = self.fixture(Path(raw))
            state = plan.scope_home / 'state'
            tickets = state / 'tickets/history'
            tickets.mkdir(parents=True)
            contents = {
                'malformed.md': b'\xff\x00not frontmatter',
                'legacy.md': b'---\nid: old\nstatus: working\n---\nold report\n',
                'active.md': b'---\nid: active\nrun: history\nstatus: claimed\nexecutor: orch-do\nprofile: orch-worker\nstandards: [old@sha256:bad]\n---\n',
            }
            for name, content in contents.items():
                (tickets / name).write_bytes(content)
            source.write_text('VALUE = 2\n')
            original = Path.open
            def no_state_access(path, *args, **kwargs):
                if path == state or state in path.parents:
                    raise AssertionError('installer accessed ticket state: ' + str(path))
                return original(path, *args, **kwargs)
            with mock.patch.object(Path, 'open', no_state_access):
                # Prove the read prohibition itself is live.
                with self.assertRaises(AssertionError):
                    (tickets / 'active.md').read_bytes()
                receipt = application.apply_plan(plan, 'new')
            self.assertEqual('new', receipt['source_commit'])
            self.assertEqual('VALUE = 2\n', (plan.bin_dir / 'tickets.py').read_text())
            self.assertEqual(contents, {path.name: path.read_bytes() for path in tickets.iterdir()})

    def test_fresh_install_and_update_need_no_state_directory(self):
        with tempfile.TemporaryDirectory() as raw:
            plan, source = self.fixture(Path(raw))
            self.assertFalse((plan.scope_home / 'state').exists())
            source.write_text('VALUE = 2\n')
            application.apply_plan(plan, 'new')
            self.assertFalse((plan.scope_home / 'state').exists())
            self.assertEqual('VALUE = 2\n', (plan.lib_home / 'module.py').read_text())

    def test_concurrent_installers_wait_before_staging_and_publish_in_order(self):
        with tempfile.TemporaryDirectory() as raw:
            plan, _ = self.fixture(Path(raw))
            entered, attempted, second_stage = threading.Event(), threading.Event(), threading.Event()
            stages, results, failures = [], [], []
            original = publication._stage
            def stage(*args):
                stages.append(threading.current_thread().name)
                if len(stages) == 1:
                    entered.set()
                    self.assertTrue(attempted.wait(5))
                    self.assertFalse(second_stage.wait(.1))
                else:
                    second_stage.set()
                return original(*args)
            def install(commit):
                try:
                    if commit == 'second': attempted.set()
                    results.append(application.apply_plan(plan, commit)['source_commit'])
                except BaseException as error:
                    failures.append(error)
            first = threading.Thread(target=install, args=('first',), name='first')
            second = threading.Thread(target=install, args=('second',), name='second')
            with mock.patch.object(publication, '_stage', stage):
                first.start()
                try:
                    self.assertTrue(entered.wait(5))
                    second.start()
                finally:
                    first.join(10)
                    if second.ident is not None: second.join(10)
            self.assertFalse(first.is_alive() or second.is_alive())
            self.assertEqual([], failures)
            self.assertEqual(['first', 'second'], stages)
            self.assertEqual(['first', 'second'], results)
