"""run_capped: caps, process-tree reaping, cancel, files instead of pipes."""
from __future__ import annotations

import _thread
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from benchkit import launch  # noqa: E402

# The child starts a grandchild at once. The grandchild records its pid, then writes `done` after `delay` seconds.
GRANDCHILD = ("import os, sys, time, pathlib\n"
              "root = pathlib.Path(sys.argv[1])\n"
              "(root / 'grandchild.pid').write_text(str(os.getpid()))\n"
              "time.sleep(float(sys.argv[2]))\n"
              "(root / 'done').write_text('x')\n")
CHILD = ("import os, subprocess, sys, time, pathlib\n"
         f"grandchild = subprocess.Popen([sys.executable, '-c', {GRANDCHILD!r}, sys.argv[1], sys.argv[2]])\n"
         "pathlib.Path(sys.argv[1], 'child.pid').write_text(str(os.getpid()))\n"
         "mode = sys.argv[3]\n"
         "if mode == 'wait':\n"
         "    grandchild.wait()\n"
         "elif mode == 'sleep':\n"
         "    time.sleep(60)\n"
         "else:\n"
         "    while not pathlib.Path(sys.argv[1], 'grandchild.pid').exists():\n"
         "        time.sleep(0.02)\n")


def alive(pid: int) -> bool:
    if os.name == "nt":
        import ctypes
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.OpenProcess.restype = ctypes.c_void_p
        kernel.OpenProcess.argtypes = [ctypes.c_uint32, ctypes.c_int, ctypes.c_uint32]
        kernel.CloseHandle.argtypes = [ctypes.c_void_p]
        handle = kernel.OpenProcess(0x1000, False, pid)
        if not handle:
            return ctypes.get_last_error() == 5
        code = ctypes.c_uint32()
        kernel.GetExitCodeProcess.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint32)]
        kernel.GetExitCodeProcess(handle, ctypes.byref(code))
        kernel.CloseHandle(handle)
        return code.value == 259  # STILL_ACTIVE
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    try:
        return Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()[0] != "Z"
    except OSError:
        return True


def wait_for(condition, seconds=10.0):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        if condition():
            return True
        time.sleep(0.02)
    return condition()


class LaunchTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def run_py(self, *args, code=None, **options):
        options.setdefault("timeout", 30)
        return launch.run_capped([sys.executable, "-c", code, *map(str, args)], cwd=self.tmp,
                                 stdout=self.tmp / "out.txt", stderr=self.tmp / "err.txt", **options)

    def pid(self, name):
        return int((self.tmp / name).read_text())

    def test_cap_stops_a_grandchild_started_at_once(self):
        began = time.monotonic()
        outcome = self.run_py(self.tmp, 0.8, "sleep", code=CHILD, timeout=0.5)
        self.assertEqual(outcome.status, "timeout")
        self.assertLess(time.monotonic() - began, 5)
        time.sleep(1.0)  # past the moment the grandchild would have written its marker
        self.assertFalse((self.tmp / "done").exists())
        if (self.tmp / "grandchild.pid").exists():
            self.assertFalse(alive(self.pid("grandchild.pid")))

    def test_the_grandchild_finishes_when_nothing_stops_it(self):
        outcome = self.run_py(self.tmp, 0.2, "wait", code=CHILD)
        self.assertEqual((outcome.status, outcome.exit_code, outcome.left_running), ("completed", 0, False))
        self.assertTrue((self.tmp / "done").exists())

    def test_descendants_left_after_exit_are_reported_and_stopped(self):
        outcome = self.run_py(self.tmp, 60, "exit", code=CHILD)
        self.assertEqual((outcome.status, outcome.exit_code, outcome.left_running), ("completed", 0, True))
        self.assertIn("left running", outcome.reason)
        self.assertTrue(wait_for((self.tmp / "grandchild.pid").exists, 5))
        self.assertTrue(wait_for(lambda: not alive(self.pid("grandchild.pid")), 5))

    def test_a_clean_exit_leaves_nothing_running(self):
        outcome = self.run_py(code="print('hello')")
        self.assertEqual((outcome.status, outcome.exit_code, outcome.left_running, outcome.reason), ("completed", 0, False, ""))

    def test_cancel_stops_the_tree(self):
        cancel = threading.Event()
        threading.Timer(0.5, cancel.set).start()
        began = time.monotonic()
        outcome = self.run_py(self.tmp, 60, "sleep", code=CHILD, cancel=cancel)
        self.assertEqual(outcome.status, "canceled")
        self.assertLess(time.monotonic() - began, 10)
        self.assertTrue(wait_for((self.tmp / "child.pid").exists, 5))
        self.assertTrue(wait_for(lambda: not alive(self.pid("child.pid")), 5))
        if (self.tmp / "grandchild.pid").exists():
            self.assertTrue(wait_for(lambda: not alive(self.pid("grandchild.pid")), 5))

    def test_an_already_set_cancel_launches_then_cancels(self):
        cancel = threading.Event()
        cancel.set()
        outcome = self.run_py(code="import time; time.sleep(60)", cancel=cancel)
        self.assertEqual(outcome.status, "canceled")
        self.assertLess(outcome.seconds, 5)

    def test_exit_codes(self):
        failed = self.run_py(code="import sys; sys.exit(3)")
        self.assertEqual((failed.status, failed.exit_code, failed.reason), ("error", 3, "exit code 3"))
        self.assertEqual(self.run_py(code="pass").exit_code, 0)

    def test_output_and_input_travel_through_files(self):
        code = ("import sys\n"
                "sys.stdout.buffer.write(b'o' * 3_000_000)\n"
                "sys.stderr.buffer.write(b'e' * 3_000_000)\n"
                "sys.stdout.buffer.write(sys.stdin.buffer.read())\n")
        outcome = self.run_py(code=code, stdin=b"typed input", timeout=60)
        self.assertEqual(outcome.status, "completed")
        self.assertEqual((self.tmp / "out.txt").read_bytes(), b"o" * 3_000_000 + b"typed input")
        self.assertEqual((self.tmp / "err.txt").stat().st_size, 3_000_000)

    def test_no_stdin_means_end_of_input(self):
        self.assertEqual(self.run_py(code="import sys; sys.exit(len(sys.stdin.read()))").exit_code, 0)

    def test_environment_and_working_directory_are_the_callers(self):
        env = {**os.environ, "BENCHKIT_PROBE": "seen"}
        self.run_py(code="import os; print(os.environ['BENCHKIT_PROBE'], os.getcwd())", env=env)
        printed = (self.tmp / "out.txt").read_text().split(maxsplit=1)
        self.assertEqual(printed[0], "seen")
        self.assertEqual(Path(printed[1].strip()).resolve(), self.tmp.resolve())

    def test_a_missing_program_is_an_error_outcome(self):
        outcome = launch.run_capped(["no-such-program-benchkit"], cwd=self.tmp, stdout=self.tmp / "o", stderr=self.tmp / "e",
                                    timeout=5)
        self.assertEqual((outcome.status, outcome.exit_code), ("error", None))
        self.assertTrue(outcome.reason.startswith("launch failed"))

    def test_ctrl_c_stops_the_tree_and_propagates(self):
        def interrupt_when_started():
            wait_for((self.tmp / "grandchild.pid").exists, 10)
            _thread.interrupt_main()
        threading.Thread(target=interrupt_when_started, daemon=True).start()
        with self.assertRaises(KeyboardInterrupt):
            self.run_py(self.tmp, 60, "sleep", code=CHILD, timeout=60)
        self.assertTrue(wait_for(lambda: not alive(self.pid("grandchild.pid")), 5))
        self.assertTrue(wait_for(lambda: not alive(self.pid("child.pid")), 5))


@unittest.skipUnless(os.name == "nt", "job objects are Windows only")
class WindowsJobTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def test_killing_the_runner_kills_the_attempt_tree(self):
        runner = ("import sys\n"
                  f"sys.path.insert(0, {str(SCRIPTS)!r})\n"
                  "from pathlib import Path\n"
                  "from benchkit import launch\n"
                  "root = Path(sys.argv[1])\n"
                  f"launch.run_capped([sys.executable, '-c', {CHILD!r}, str(root), '60', 'sleep'], cwd=root,\n"
                  "                  stdout=root / 'o', stderr=root / 'e', timeout=120)\n")
        process = subprocess.Popen([sys.executable, "-c", runner, str(self.tmp)])
        self.addCleanup(process.wait)
        self.assertTrue(wait_for((self.tmp / "grandchild.pid").exists, 15))
        pids = [int((self.tmp / name).read_text()) for name in ("child.pid", "grandchild.pid")]
        self.assertTrue(all(alive(pid) for pid in pids))
        process.kill()
        process.wait()
        for pid in pids:
            self.assertTrue(wait_for(lambda pid=pid: not alive(pid), 10), f"process {pid} outlived its runner")

    def test_a_process_started_suspended_is_resumed_by_the_thread_fallback(self):
        marker = self.tmp / "ran"
        process = subprocess.Popen([sys.executable, "-c", f"open({str(marker)!r}, 'w').write('x')"],
                                   creationflags=0x4)  # CREATE_SUSPENDED
        self.addCleanup(process.kill)
        time.sleep(0.5)
        self.assertFalse(marker.exists())
        launch._resume_threads(process.pid)
        self.assertEqual(process.wait(timeout=10), 0)
        self.assertTrue(marker.exists())


if __name__ == "__main__":
    unittest.main()
