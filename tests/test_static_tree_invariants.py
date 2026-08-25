"""Compatibility seam for the static-tree invariant collection.

The cases are partitioned by their invariant owner while this module keeps the
historic ``tests.test_static_tree_invariants`` discovery target intact.
"""
import unittest

from tests.test_static_tree_invariants_cases.benchmark_architecture import (
    TestBenchmarkArchitecture,
)
from tests.test_static_tree_invariants_cases.compositions import (
    TestCompositionLinks,
    TestCompositionTemplates,
)
from tests.test_static_tree_invariants_cases.cut_rules import (
    TestCutGoalAnchors,
    TestDependencyOrderedOverlap,
)
from tests.test_static_tree_invariants_cases.repository_shape import (
    TestEveryCaseClassIsRegistered,
    TestNoTempTreeIsDeletedWhileItIsTheCwd,
    TestRootShellEntryPointsAreExecutable,
)
from tests.test_static_tree_invariants_cases.skill_packages import (
    TestFrozenRoleTable,
    TestPackageNamesMatchFolders,
    TestSkillAnatomyOrder,
    TestTierDirectoriesExist,
)


if __name__ == "__main__":
    unittest.main()
