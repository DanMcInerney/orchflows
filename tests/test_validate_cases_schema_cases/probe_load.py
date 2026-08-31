"""Host-contention semantics of the probe wall-clock cap.

A probe that finishes in seconds alone starved past its 60 s tier under the
full parallel suite (twice, 2026-08-30): wall clock counted every sibling
worker's CPU as if it were the probe's. The cap therefore scales by the
worker count the dispatching runner declares, and only by that — an
undeclared host keeps the exact tier bound.
"""

import contextlib
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tests.test_validate_cases_schema import vc


@contextlib.contextmanager
def declared_workers(value):
    """Pin the dispatching runner's declared worker count for one check."""
    with mock.patch.dict(os.environ):
        os.environ.pop(vc.HOST_PARALLELISM_ENV_VAR, None)
        if value is not None:
            os.environ[vc.HOST_PARALLELISM_ENV_VAR] = value
        yield


class ProbeHostLoadTest(unittest.TestCase):
    """Sibling-worker starvation must not fail a probe the tier admits."""

    def run_sleeper(self, seconds, timeout):
        command = '"{}" -c "import time; time.sleep({})"'.format(
            sys.executable.replace("\\", "/"), seconds
        )
        with tempfile.TemporaryDirectory() as tmp:
            case_dir = Path(tmp)
            impl = case_dir / "target"
            impl.mkdir()
            return vc.run_probe_output(case_dir, command, "", impl, timeout)

    def test_a_declared_parallel_dispatch_scales_the_kill_cap(self):
        with declared_workers("16"):
            code, output = self.run_sleeper(1.2, 0.5)
        self.assertEqual(0, code, output)

    def test_an_undeclared_host_keeps_the_exact_tier_bound(self):
        with declared_workers(None):
            code, output = self.run_sleeper(5, 0.5)
        self.assertIsNone(code)
        self.assertEqual("probe exceeded 0.5 s", output)

    def test_a_scaled_kill_names_its_derivation(self):
        with declared_workers("2"):
            code, output = self.run_sleeper(5, 0.5)
        self.assertIsNone(code)
        self.assertEqual(
            "probe exceeded 1.0 s (0.5 s tier x 2 declared workers)", output
        )

    def test_the_declaration_reads_as_an_integer_with_floor_one(self):
        cases = (("6", 6), ("1", 1), ("0", 1), ("-3", 1), ("many", 1), ("", 1), (None, 1))
        for raw, expected in cases:
            with declared_workers(raw):
                self.assertEqual(expected, vc.host_parallelism(), raw)
