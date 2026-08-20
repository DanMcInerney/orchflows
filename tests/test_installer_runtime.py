"""Installer runtime-planning cases exposed as an independent shard."""

import sys

_facade = sys.modules.get("test_installer")
if _facade is None:
    from tests import test_installer as _facade
from tests.test_installer_cases.planning.runtime import TestClaudeAdapterSet, TestRuntimeDirsSeedTheSink


TestClaudeAdapterSet.__module__ = _facade.__name__
TestRuntimeDirsSeedTheSink.__module__ = _facade.__name__
