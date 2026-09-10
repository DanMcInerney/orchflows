"""Stable discovery facade for the partitioned transport test collection."""

from .test_transport_cases.common import NETWORK_SEAM_MODULES, ROUTE_OWNING_MODULES
from .test_transport_cases.credential_cases import (
    CredentialApplicationTest,
    CredentialStaysInsideTransportTest,
    CredentialThreatTest,
    PublicClientCredentialTest,
)
from .test_transport_cases.credential_guest import GuestMintIsOnePacedRecordedCallTest
from .test_transport_cases.network_seam import (
    ChannelVerdictTest,
    FetchedChannelVerdictTest,
    InterceptionOracleCanFailTest,
    InterceptionReachesTheArtifactTest,
    InterceptionReachesThePageTest,
    OracleCanFailTest,
    OriginBehaviorSurvivesTest,
)
from .test_transport_cases.policy_cases import (
    AbsentMachineryTest,
    NoWriteIsReachableTest,
    RefusalThreatTest,
    ThreatRemapTest,
    ThreatTableIsReadOffTheDocumentTest,
    UntrustedContentOracleCanFailTest,
    UntrustedContentTest,
)
from .test_transport_cases.request_cases import (
    GuestActivationRouteTest,
    OutboundRequestTest,
    TheAnswerCarriesWhatTheOriginSaidTest,
    TheOpenerReadsARealHTTPErrorTest,
    WriteVerbRefusalTest,
)
from .test_transport_cases.route_ownership import (
    RouteOwnershipIsStatedTrulyTest,
    RouteOwnershipScanTest,
)
