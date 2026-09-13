"""Every retained route runs with an empty environment and no credential store."""

import unittest

from .test_keyless_cases.credentials import EnvironmentIsEmptyTest, OracleCanFailTest
from .test_keyless_cases.routes import KeylessRosterTest
from .test_keyless_cases.support import AUTH_REQUIRED, roster_manifest


__all__ = (
    "AUTH_REQUIRED",
    "EnvironmentIsEmptyTest",
    "KeylessRosterTest",
    "OracleCanFailTest",
    "roster_manifest",
)


if __name__ == "__main__":
    unittest.main()
