"""Compatibility seam for ticket issue, amend, template, and refusal tests.

The behavioral cases live in ``tests.test_tickets_issue_cases``. Keeping
their TestCase classes on this module preserves the established runner seam.
"""

import unittest

from tests.test_tickets_issue_cases.amend_cases import AmendTest, InstructionCeilingTest
from tests.test_tickets_issue_cases.console_cases import NarrowConsoleTest
from tests.test_tickets_issue_cases.criterion_cases import CriterionDefectsTest
from tests.test_tickets_issue_cases.defect_cases import (
    CriterionNestingTest,
    PacketGradesEveryCriterionTest,
    TicketDefectsTest,
)
from tests.test_tickets_issue_cases.encoding_cases import NonUtf8BytesTest
from tests.test_tickets_issue_cases.frontmatter_cases import InlineListSeparatorTest
from tests.test_tickets_issue_cases.new_cases import NewTest
from tests.test_tickets_issue_cases.refusal_cases import RefusalTextTest
from tests.test_tickets_issue_cases.root_spec_cases import RootStubSpecFieldsTest
from tests.test_tickets_issue_cases.surface_cases import SurfaceTest
from tests.test_tickets_issue_cases.template_cases import InstantiateTest


if __name__ == "__main__":
    unittest.main()
