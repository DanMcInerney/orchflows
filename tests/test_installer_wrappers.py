"""Installer wrapper-contract cases exposed as an independent shard."""

import sys

_facade = sys.modules.get("test_installer")
if _facade is None:
    from tests import test_installer as _facade
from tests.test_installer_cases.planning.wrappers import (
    TestBootstrapWrappers,
    TestDeclaredPythonFloor,
    TestPluginSubsystemRemoved,
)


TestBootstrapWrappers.__module__ = _facade.__name__
TestDeclaredPythonFloor.__module__ = _facade.__name__
TestPluginSubsystemRemoved.__module__ = _facade.__name__
