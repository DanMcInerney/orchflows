"""Discovery seam for the lint subcommand's cases.

The behavioural cases live in ``tests.test_tickets_lint_cases``; keeping
their TestCase classes on this module preserves the runner seam every other
ticket-script shard uses.
"""

import unittest

from tests.test_tickets_lint_cases.table_cases import CommandTableTest
from tests.test_tickets_lint_cases.lint_cases import (
    LintDraftTest,
    LintFixTest,
    LintTicketTest,
)


if __name__ == "__main__":
    unittest.main()
