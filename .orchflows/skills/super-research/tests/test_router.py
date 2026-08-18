"""Compatibility selector for the router suite's behavioral partitions."""

from .test_router_cases.archive import ThirdPartyArchiveTest
from .test_router_cases.public_client import PublicClientCredentialTest
from .test_router_cases.refusal import OracleCanFailTest, UnclassedDescriptorTest
from .test_router_cases.routing import AccessClassDeclarationTest, KeylessCapabilityTest


__all__ = (
    "AccessClassDeclarationTest",
    "KeylessCapabilityTest",
    "OracleCanFailTest",
    "PublicClientCredentialTest",
    "ThirdPartyArchiveTest",
    "UnclassedDescriptorTest",
)

