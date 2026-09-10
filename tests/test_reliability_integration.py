"""Joined publication boundaries, portable imports, and shared containment."""
from pathlib import Path
import os
import tempfile
import unittest
from unittest import mock

from scripts import tickets_issue


class RawIssuanceTests(unittest.TestCase):
    def test_nested_issue_reuses_locks_already_held_by_mint(self):
        with mock.patch.object(tickets_issue, "_run_lock") as run, mock.patch.object(tickets_issue, "ticket_defects", return_value=["control"]):
            self.assertIn("error", tickets_issue._issue_ticket("r", "T", "unused", _lock_held=True))
            run.assert_not_called()

class ReceiptPublicationTests(unittest.TestCase):
    @unittest.skipUnless(os.name == 'nt', 'Windows suspended-child boundary')
    def test_post_spawn_receipt_failure_reaps_unbound_suspended_child(self):
        import os
        import sys
        import time
        from scripts import tickets_done_evidence as evidence
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            marker = root / 'must-not-run'
            original = evidence._write
            calls = []
            def fail_after_spawn(path, record):
                if record.get('pid') and not calls:
                    calls.append(record['pid'])
                    raise PermissionError('injected post-spawn receipt failure')
                return original(path, record)
            with mock.patch.dict(os.environ, {'ORCHFLOWS_STATE_HOME': str(root / 'state')}), mock.patch.object(
                evidence, '_write', fail_after_spawn,
            ):
                started = time.monotonic()
                record, _, _ = evidence.run_command([
                    sys.executable, '-c', f'from pathlib import Path; Path({str(marker)!r}).write_text("escaped")',
                ], root, 1)
                elapsed = time.monotonic() - started
            self.assertEqual(1, len(calls))
            self.assertLess(elapsed, 5, record)
            self.assertEqual('supervision-failed', record['outcome'])
            self.assertIsNotNone(record['exit_status'])
            self.assertNotIn('cleanup_error', record)
            self.assertFalse(marker.exists())

    @unittest.skipUnless(os.name == 'nt', 'Windows transient replacement refusal')
    def test_receipt_replace_waits_out_transient_reader_refusal(self):
        from scripts import tickets_done_evidence as evidence
        with tempfile.TemporaryDirectory() as raw:
            target = Path(raw) / 'command.json'
            target.write_text('{}')
            original = Path.replace
            attempts = []
            def replace(path, destination):
                attempts.append(destination)
                if len(attempts) == 1:
                    raise PermissionError('injected concurrent reader')
                return original(path, destination)
            with mock.patch.object(Path, 'replace', replace):
                reference = evidence._write(target, {'outcome': 'running'})
            self.assertEqual(2, len(attempts))
            self.assertEqual(str(target), reference['path'])
            self.assertIn('running', target.read_text())

class InstalledCompositionTests(unittest.TestCase):
    def test_flat_and_reader_payloads_import_shared_process_owner(self):
        import shutil
        import subprocess
        import sys
        from installer.inventory import discover_script_names
        from installer.planning_support import SHARED_READER_MODULES
        repo = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            layouts = [(root / 'bin', discover_script_names(repo / 'scripts'),
                        'import tickets, workspace_process, process_job; assert callable(tickets.section_page)'),
                       (root / 'reader' / 'scripts', SHARED_READER_MODULES,
                        'from scripts import tickets_adapters, workspace_process, process_job')]
            for destination, names, imports in layouts:
                destination.mkdir(parents=True)
                for name in names:
                    if name != 'ui.py':
                        shutil.copyfile(repo / 'scripts' / name, destination / name)
                search = destination if destination.name == 'bin' else destination.parent
                code = f'import sys; sys.path.insert(0,{str(search)!r}); {imports}'
                result = subprocess.run([sys.executable, '-I', '-c', code], cwd=root,
                                        capture_output=True, text=True, timeout=20)
                self.assertEqual(0, result.returncode, result.stderr)
                (destination / 'process_job.py').unlink()
                refused = subprocess.run([sys.executable, '-I', '-c', code], cwd=root,
                                         capture_output=True, text=True, timeout=20)
                self.assertNotEqual(0, refused.returncode)
                self.assertIn('process_job', refused.stderr)

    def test_diagnostics_consumes_public_report_pages_and_refuses_bad_page(self):
        import subprocess
        import sys
        repo = Path(__file__).resolve().parents[1]
        code = '''import sys
from unittest import mock
sys.path[:0] = PATHS
import tickets, improve_sources
text = '---\\nrun: r\\nid: T\\n---\\n\\n## Report\\n\\n' + 'payload ' * 1600 + '\\n\\n## Other\\nexcluded\\n'
original = tickets.section_page
with mock.patch.object(tickets, 'section_page', wraps=original) as page:
    records = improve_sources.ticket_records(text)
    assert page.call_count >= 3
    assert [r['section_offset'] for r in records] == [0,4096,8192,12288]
    assert 'excluded' not in ''.join(r['content'] for r in records)
with mock.patch.object(tickets, 'section_page', return_value={'error':'control'}):
    try: improve_sources.ticket_records(text)
    except ValueError: pass
    else: raise AssertionError('bad facade page accepted')
'''.replace('PATHS', repr([str(repo / 'scripts'), str(repo / 'example-workflows' / 'orch-self-improve' / 'scripts')]))
        with tempfile.TemporaryDirectory() as raw:
            result = subprocess.run([sys.executable, '-I', '-c', code], cwd=raw,
                                    capture_output=True, text=True, timeout=20)
        self.assertEqual(0, result.returncode, result.stderr)
