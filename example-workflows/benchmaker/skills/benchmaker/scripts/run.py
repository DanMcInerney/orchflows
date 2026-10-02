"""Benchmark runner: python run.py <command> ...; benchkit/INTERFACE.md describes the commands."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from benchkit.cli import main  # noqa: E402

sys.exit(main(ROOT, sys.argv[1:]))
