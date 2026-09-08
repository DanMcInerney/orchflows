"""Installer exclusion releases on failure and spans threads and processes."""
from pathlib import Path
import subprocess
import sys
import threading
import unittest
from installer.locking import installation_lock


class InstallationGuardTest(unittest.TestCase):
    def test_nested_lock_releases_after_failure_and_excludes_other_thread(self):
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            entered = threading.Event()
            def acquire():
                with installation_lock(directory):
                    entered.set()
            with installation_lock(directory):
                with installation_lock(directory):
                    worker = threading.Thread(target=acquire)
                    worker.start()
                    self.assertFalse(entered.wait(0.05))
            worker.join(5)
            self.assertFalse(worker.is_alive())
            self.assertTrue(entered.is_set())
            with self.assertRaises(ValueError):
                with installation_lock(directory):
                    raise ValueError("release")
            with installation_lock(directory):
                pass

    def test_process_cannot_enter_until_publication_lock_releases(self):
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            marker = Path(directory) / "entered"
            ready = Path(directory) / "ready"
            script = "from installer.locking import installation_lock; from pathlib import Path; import sys\nPath(sys.argv[3]).write_text('ready')\nwith installation_lock(sys.argv[1]): Path(sys.argv[2]).write_text('entered')"
            with installation_lock(directory):
                process = subprocess.Popen([sys.executable, "-c", script, directory, str(marker), str(ready)])
                try:
                    import time
                    deadline = time.monotonic() + 5
                    while not ready.exists() and time.monotonic() < deadline:
                        time.sleep(0.01)
                    self.assertTrue(ready.exists())
                    self.assertFalse(marker.exists())
                    with self.assertRaises(subprocess.TimeoutExpired):
                        process.wait(timeout=0.15)
                except BaseException:
                    process.kill()
                    process.wait(timeout=5)
                    raise
            try:
                self.assertEqual(0, process.wait(timeout=10))
            finally:
                if process.poll() is None:
                    process.kill()
                    process.wait(timeout=5)
            self.assertEqual("entered", marker.read_text())
