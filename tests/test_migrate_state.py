"""Discover the migrate-state regression collection through one stable seam.

The cases are partitioned by plan, collision, and apply behavior. Every case
sets ``ORCHFLOWS_STATE_HOME`` for its own sink and uses only fixture trees in
the OS temporary directory.
"""
from __future__ import annotations

from .test_migrate_state_cases.apply import (
    TestLegacyFriction,
    TestMigrationApply,
    TestMigrationIdempotent,
)
from .test_migrate_state_cases.collision import TestMigrationCollision
from .test_migrate_state_cases.plan import (
    TestMigrationPlan,
    TestUnreadableDestination,
    TestUsage,
)

__all__ = [
    "TestLegacyFriction",
    "TestMigrationApply",
    "TestMigrationCollision",
    "TestMigrationIdempotent",
    "TestMigrationPlan",
    "TestUnreadableDestination",
    "TestUsage",
]


if __name__ == "__main__":
    import unittest

    unittest.main()
