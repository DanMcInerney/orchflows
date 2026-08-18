"""Compatibility seam for the partitioned benchmaker regression tests."""

import unittest

from tests.test_benchmaker_cases.fixture import TestBenchmarkFixture
from tests.test_benchmaker_cases.protocol import TestCanonicalBenchmaker
from tests.test_benchmaker_cases.retirement import TestCanonicalSurface

__all__ = (
    "TestBenchmarkFixture",
    "TestCanonicalBenchmaker",
    "TestCanonicalSurface",
)


if __name__ == "__main__":
    unittest.main()
