"""Installer receipt and uninstall cases exposed as an independent shard."""

import sys

_facade = sys.modules.get("test_installer")
if _facade is None:
    from tests import test_installer as _facade
from tests.test_installer_cases.receipt.install_receipt import TestInstallReceipt
from tests.test_installer_cases.receipt.source_commit import TestSourceCommit, TestUnreadableReceipt
from tests.test_installer_cases.uninstall.conservative import TestConservativeUninstall


TestInstallReceipt.__module__ = _facade.__name__
TestSourceCommit.__module__ = _facade.__name__
TestUnreadableReceipt.__module__ = _facade.__name__
TestConservativeUninstall.__module__ = _facade.__name__
