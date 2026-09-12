"""Compatibility selector for the context suite, partitioned by behavioral seam."""

import unittest

from .test_context_cases.adapters import (
    AdapterCallBoundaryTest,
    AdapterDeclarationTest,
    FakeAdapterTest,
    RedditArchiveHydrationTest,
)
from .test_context_cases.lineage import (
    K4HybridNeverMergesTest,
    LineageGapIsTypedTest,
    WrongMergeLawTest,
)
from .test_context_cases.manifest import ManifestSchemaTest
from .test_context_cases.normalization import NormalizeTest
from .test_context_cases.routing import OutcomeReductionTest, RouteConstantOwnershipTest
from .test_context_cases.staging import RunTest


if __name__ == "__main__":  # pragma: no cover - convenience runner
    unittest.main()
