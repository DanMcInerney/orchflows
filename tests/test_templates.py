"""Regression collection for the canonical ticket-template seams.

The case classes live in non-discoverable modules and are re-exported here so
the stable ``tests.test_templates`` seam remains the collection owner.
"""

import unittest

from tests.test_templates_cases.closure import (
    TestCanonicalTemplatesClose,
    TestProducerConsumerClosure,
    TestTemplateBudgets,
)
from tests.test_templates_cases.shape import (
    TestPlaceholders,
    TestStubExecutorResolves,
    TestStubGraph,
    TestStubShape,
    TestTemplateManifest,
    TestTheValidatorRefusesWhatTheOwnerRefuses,
)


if __name__ == "__main__":
    unittest.main()
