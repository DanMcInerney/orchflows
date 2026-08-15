"""Test package. Importing it installs the suite's platform guards.

Every runner that can load a test module imports this first, which is
why the guards live here rather than in one runner: `tools/run_tests.py`,
`unittest discover`, and a single `python -m unittest tests.test_x` all
get the same platform.
"""

from . import _windows_semantics

_windows_semantics.install()
