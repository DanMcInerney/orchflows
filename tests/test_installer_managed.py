"""Installer application and managed-text cases without shared installs."""

import sys

_facade = sys.modules.get("test_installer")
if _facade is None:
    from tests import test_installer as _facade
from tests.test_installer_cases.application.partial_apply import TestPartialApplyAfterRmtree
from tests.test_installer_cases.managed_text.host_block import (
    TestHostBlockDemands,
    TestHostBlockDispatchFlags,
    TestHostBlockRendering,
)
from tests.test_installer_cases.managed_text.markers import (
    TestConservativeBlockRemoval,
    TestHostConfigLimitRemoval,
    TestMarkerEngineMisuse,
)
from tests.test_installer_cases.managed_text.roles import TestRoleAgentInstructions


TestPartialApplyAfterRmtree.__module__ = _facade.__name__
TestHostBlockDemands.__module__ = _facade.__name__
TestHostBlockDispatchFlags.__module__ = _facade.__name__
TestHostBlockRendering.__module__ = _facade.__name__
TestConservativeBlockRemoval.__module__ = _facade.__name__
TestHostConfigLimitRemoval.__module__ = _facade.__name__
TestMarkerEngineMisuse.__module__ = _facade.__name__
TestRoleAgentInstructions.__module__ = _facade.__name__
