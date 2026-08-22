"""Admission boundaries unique to sealed v2 assignments."""

import unittest

from scripts import tickets_admission as admission
from scripts import tickets_generations as generations
from tests.test_tickets_issue_cases.generation_lifecycle import snapshot


class SealedAdmissionTest(unittest.TestCase):
    def test_unsealed_and_stale_seals_are_refused(self):
        current = snapshot()
        unsealed = admission.grade_admission("00-root.01", current["00-root.01"], current)
        self.assertIn("assignment-unsealed", {item["code"] for item in unsealed["findings"]})
        draft = generations.draft_snapshot("00-root", current)
        receipt = generations.validate_draft("00-root", current, draft)
        sealed = generations.seal_assignments("00-root", current, draft, receipt)
        stale = dict(sealed)
        stale["00-root.01"] = stale["00-root.01"].replace("deliver", "changed after seal")
        grade = admission.grade_admission("00-root.01", stale["00-root.01"], stale)
        self.assertIn("assignment-seal-mismatch", {item["code"] for item in grade["findings"]})


class ParentAmendmentRequestTest(unittest.TestCase):
    def test_worker_appends_one_typed_request_without_editing_parent(self):
        current = snapshot()
        parent_before = current["00-root"]
        draft = generations.draft_snapshot("00-root", current)
        record = {
            "bound-state": "available", "change-kind": "authority",
            "cut-generation": draft["cut_generation"], "evidence-identities": ["artifact:failure"],
            "parent-ticket": "00-root", "reason": "required file omitted", "request-id": "req-1",
            "requester-ticket": "00-root.01", "root-generation": draft["root_generation"],
            "target-fields": ["write_scope"],
        }
        amended = generations.append_amendment_request(current["00-root.01"], record)
        self.assertIn("- amendment-request: " + generations.canonical_json(record), amended)
        self.assertEqual(parent_before, current["00-root"])
        with self.assertRaises(generations.GenerationError):
            generations.append_amendment_request(amended, {**record, "request-id": "req-2"})


class PostSealAssignmentGenerationTest(unittest.TestCase):
    def test_post_seal_assignment_change_requires_a_new_generation(self):
        current = snapshot()
        draft = generations.draft_snapshot("00-root", current)
        sealed = generations.seal_assignments("00-root", current, draft, generations.validate_draft("00-root", current, draft))
        changed = dict(sealed)
        changed["00-root.01"] = changed["00-root.01"].replace("deliver", "new assignment")
        grade = admission.grade_admission("00-root.01", changed["00-root.01"], changed)
        self.assertIn("assignment-seal-mismatch", {item["code"] for item in grade["findings"]})
        successor = generations.draft_snapshot("00-root", changed, ordinal=2)
        self.assertIn(":2:sha256:", successor["cut_generation"])
        self.assertNotEqual(draft["cut_generation"], successor["cut_generation"])


if __name__ == "__main__":
    unittest.main()
