"""Stable discovery facade for the partitioned transport test collection."""

from .test_transport_cases.common import NETWORK_SEAM_MODULES, ROUTE_OWNING_MODULES
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
    RefusalThreatTest,
    UntrustedContentOracleCanFailTest,
    UntrustedContentTest,
)
from .test_transport_cases.request_cases import (
    TheAnswerCarriesWhatTheOriginSaidTest,
    TheOpenerReadsARealHTTPErrorTest,
    WriteVerbRefusalTest,
)
from .test_transport_cases.route_ownership import (
    RouteOwnershipScanTest,
)
