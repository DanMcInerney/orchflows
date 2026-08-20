"""Installer cases that share the expensive read-only installed trees."""

from tests import test_installer as _facade
from tests.test_installer_cases.application.configuration import (
    TestClaudeConfigDir,
    TestCodexHome,
    TestCodexHooksPreflight,
)
from tests.test_installer_cases.managed_text.claude_import import TestClaudeAlwaysOnImport
from tests.test_installer_cases.planning.script_inventory import TestScriptNames


TestClaudeConfigDir.__module__ = _facade.__name__
TestCodexHome.__module__ = _facade.__name__
TestCodexHooksPreflight.__module__ = _facade.__name__
TestClaudeAlwaysOnImport.__module__ = _facade.__name__
TestScriptNames.__module__ = _facade.__name__
