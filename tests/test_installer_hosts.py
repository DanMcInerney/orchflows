"""Installer host-planning cases exposed as an independent process shard."""

from tests import test_installer as _facade
from tests.test_installer_cases.planning.host_detection import DryRunOracleTest, TestHostAutoDetection
from tests.test_installer_cases.planning.scoped_hosts import (
    RoleProfileRefusalTest,
    TestScopedHostConfiguration,
)


DryRunOracleTest.__module__ = _facade.__name__
TestHostAutoDetection.__module__ = _facade.__name__
RoleProfileRefusalTest.__module__ = _facade.__name__
TestScopedHostConfiguration.__module__ = _facade.__name__
