"""Structural discovery facade for the partitioned pipeline behavioral suite."""

from tests.test_pipeline_cases.common import GITHUB_REST_BUDGET, REDDIT_FEED_BUDGET
from tests.test_pipeline_cases.acquisition import (
    AStepMayDeclareItsOwnPageBoundTest,
    LanesOverlapAndTheCoreOwnsPagingTest,
    PagingIsTheCoresTest,
)
from tests.test_pipeline_cases.artifact import (
    CacheHitOnTheRecordTest,
    FusedModeTest,
    WorkLedgerTest,
)
from tests.test_pipeline_cases.failure import (
    AStepThatGotNoAnswerIsTypedTest,
    AdapterBranchTest,
    OracleCanFailTest,
)
from tests.test_pipeline_cases.ordering import OrderingContractTest
from tests.test_pipeline_cases.scheduling import (
    BurstAndCooldownTest,
    FakeClockOnlyTest,
    OriginStatedCooldownTest,
    RateBudgetTest,
    TheDocumentedPathPacesAndRemembersTest,
    VolatileIdentifierTest,
)
