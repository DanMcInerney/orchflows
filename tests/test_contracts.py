"""Compatibility seam for the contract regression collection.

Cases live by contract seam under :mod:`tests.test_contracts_cases`; these
explicit imports preserve ``tests.test_contracts`` as the complete discovery
target used by local and CI runners.
"""

from tests.test_contracts_cases.register import (  # noqa: F401
    TestContractRegister,
    TestResultContract,
    TestTemplateAndStub,
    TestVerdictContract,
    TestWorklogContract,
)
from tests.test_contracts_cases.rules import (  # noqa: F401
    ChainRoleLawTest,
    TestSkillDescriptions,
    TestVerificationHomelessLaws,
    TestVisibilityChannelLaw,
    TestVocabularyDefinesShapeChange,
    V2LifecycleRuleContractTest,
    VocabularyCutTermsTest,
)
from tests.test_contracts_cases.topology import TopologyAtomTest  # noqa: F401
from tests.test_contracts_cases.work_item import (  # noqa: F401
    TestWorkItemCitationLaws,
    TestWorkItemContract,
    TestV1AdmissionContract,
)


if __name__ == "__main__":
    import unittest

    unittest.main()
