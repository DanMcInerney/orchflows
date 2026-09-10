"""Bound and record one B1.4 check, retaining children until observed exit."""
import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--seconds", type=int, required=True)
parser.add_argument("--record", type=Path, required=True)
parser.add_argument("command", nargs=argparse.REMAINDER)
args = parser.parse_args()
command = [sys.executable] + args.command
started = time.monotonic()
process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           start_new_session=os.name != "nt")
timed_out = False
try:
    stdout, _ = process.communicate(timeout=args.seconds)
except subprocess.TimeoutExpired:
    timed_out = True
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], check=True, timeout=30)
    else:
        os.killpg(process.pid, signal.SIGKILL)
    stdout, _ = process.communicate(timeout=30)
record = {
    "assigned_name": "B1.4", "dispatch_id": "B1.4:d1",
    "assignment_seal": "sha256:4e6322a841b9994f0e29b3c9abefdd35595c2ebf0279f81f147d6cc389cca8a8",
    "command": command, "timeout_seconds": args.seconds, "timed_out": timed_out,
    "exit_code": process.returncode, "wall_seconds": time.monotonic() - started,
    "stdout": stdout.decode("utf-8", "replace"),
}
args.record.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
print(record["stdout"])
print(json.dumps({key: value for key, value in record.items() if key != "stdout"}))
raise SystemExit(124 if timed_out else process.returncode)
