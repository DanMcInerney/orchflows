"""Stand-in for the claude CLI in tests: prints a recorded output file. Usage: fake_claude.py OUTPUT EXIT_CODE STDIN_CAPTURE [flags...]"""
import sys
from pathlib import Path

output, code, capture = sys.argv[1:4]
Path(capture).write_bytes(sys.stdin.buffer.read())
sys.stdout.buffer.write(Path(output).read_bytes())
sys.exit(int(code))
