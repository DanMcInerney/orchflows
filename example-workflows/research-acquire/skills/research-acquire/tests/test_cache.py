"""Compatibility selector for the cache suite's behavioral partitions."""

from .test_cache_cases.cacheability import CacheabilityTest
from .test_cache_cases.failure import OracleCanFailTest, RunLocalTest
from .test_cache_cases.footprint import (
    BoundedCacheTest,
    BodySizeBoundaryTest,
)
from .test_cache_cases.key import CacheKeyTest
from .test_cache_cases.ttl import RouteTtlTableTest, TtlServeTest


__all__ = (
    "BoundedCacheTest",
    "CacheKeyTest",
    "CacheabilityTest",
    "BodySizeBoundaryTest",
    "OracleCanFailTest",
    "RouteTtlTableTest",
    "RunLocalTest",
    "TtlServeTest",
)
