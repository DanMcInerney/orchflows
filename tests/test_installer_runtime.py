"""Installer runtime-planning cases exposed as an independent shard."""

from tests import test_installer as _facade
from tests.test_installer_cases.planning.runtime import TestClaudeAdapterSet, TestRuntimeDirsSeedTheSink


TestClaudeAdapterSet.__module__ = _facade.__name__
TestRuntimeDirsSeedTheSink.__module__ = _facade.__name__
