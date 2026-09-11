"""Compatibility selector for the cache suite's behavioral partitions."""

from .test_cache_cases.cacheability import CacheabilityTest
from .test_cache_cases.failure import OracleCanFailTest, RunLocalTest
from .test_cache_cases.footprint import (
    BoundedCacheTest,
    FootprintLawTest,
    MeasuredBodyTest,
    RouteCommentTest,
)
from .test_cache_cases.key import CacheKeyTest
from .test_cache_cases.ttl import RouteTtlTableTest, TtlServeTest


__all__ = (
    "BoundedCacheTest",
    "CacheKeyTest",
    "CacheabilityTest",
    "FootprintLawTest",
    "MeasuredBodyTest",
    "OracleCanFailTest",
    "RouteCommentTest",
    "RouteTtlTableTest",
    "RunLocalTest",
    "TtlServeTest",
)
