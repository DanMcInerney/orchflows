"""Compatibility selector for the partitioned coverage checks."""

from __future__ import annotations

import unittest

from tests.test_coverage_cases.artifact_review import (
    DepthReviewTest,
    ReviewArtifactTest,
    StepIdentityTest,
)
from tests.test_coverage_cases.depth_planning import DepthPlanTest
from tests.test_coverage_cases.documentation import ProtocolDocTest, SkillDocTest
from tests.test_coverage_cases.manifest_review import ReviewManifestTest
from tests.test_coverage_cases.no_io import NoIOTest


__all__ = [
    "DepthPlanTest",
    "DepthReviewTest",
    "NoIOTest",
    "ProtocolDocTest",
    "ReviewArtifactTest",
    "ReviewManifestTest",
    "SkillDocTest",
    "StepIdentityTest",
]


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
