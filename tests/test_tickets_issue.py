"""Compatibility seam for ticket issue, amend, template, and refusal tests.

The behavioral cases live in ``tests.test_tickets_issue_cases``. Keeping
their TestCase classes on this module preserves the established runner seam.
"""

import unittest
from pathlib import Path

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
from tests.test_tickets_issue_cases.admission_producers import (
    ProducerStampingTest,
    V1ProducerTest,
)
from tests.test_tickets_issue_cases.admission_recut import RecutAndCohortTest
from tests.test_tickets_issue_cases.generation_lifecycle import (
    CorrectionGenerationPolicyTest,
    DraftValidateSealLifecycleTest,
    GenerationIdentityTest,
)


ROOT = Path(__file__).resolve().parent.parent


class PublicRouteLifecycleTest(unittest.TestCase):
    """The scaled route produces one decomposable root lifecycle."""

    def text(self, relative: str) -> str:
        return (ROOT / relative).read_text(encoding="utf-8")

    def test_spec_never_emits_an_undecomposable_direct_executor_root(self):
        spec = self.text("skills/workflows/orch-spec/SKILL.md")
        self.assertNotIn("bind that executor in the root itself", spec)
        self.assertIn("--executor orch-decompose", spec)

    def test_retired_ad_hoc_set_is_not_a_public_routing_artifact(self):
        vocabulary = self.text("docs/vocabulary.md")
        topology = self.text("rules/topology.md")
        self.assertNotIn("**ad-hoc set**", vocabulary)
        self.assertNotIn("An ad-hoc set is a cut", topology)

    def test_root_cut_acceptance_is_explicitly_nonterminal(self):
        vocabulary = self.text("docs/vocabulary.md")
        integration = self.text("skills/kernel/orch-integrate/SKILL.md")
        self.assertIn("cut-accepted", vocabulary)
        self.assertIn("cut-accepted", integration)


if __name__ == "__main__":
    unittest.main()
