"""Installer planning cases exposed as an independent process shard."""

import sys

_facade = sys.modules.get("test_installer")
if _facade is None:
    from tests import test_installer as _facade
from tests.test_installer_cases.planning.private_runtime import RuntimeVenvTests


RuntimeVenvTests.__module__ = _facade.__name__
