"""Compatibility selector for the partitioned CLI behavioral collection."""

from .test_cli_cases.failure_seam import (
    InterceptionDegradesNothingTest,
    SmokeSubcommandTest,
    StaleSmokeDegradesTest,
    WrongImplementationsAreRejectedTest,
)
from .test_cli_cases.ledger import (
    AReadThatHappenedIsNotNeverSmokedTest,
    AdaptersSubcommandTest,
    NothingTheRunHoldsReachesTheOutputTest,
    SmokeLedgerTest,
)
from .test_cli_cases.liveness import (
    StatusSaysWhatWasReadTest,
    StatusSubcommandTest,
    TheRecordedLivenessReplaysTest,
    TheRecoveryLineFitsTheLossTest,
)
from .test_cli_cases.smoke import (
    ASmokeIsOneReadTest,
    SmokeAssertsTheRosterFieldSetTest,
    SmokeProbeTableTest,
    TheOperationSetIsClosedTest,
    TheSuiteReachesNoNetworkTest,
)
