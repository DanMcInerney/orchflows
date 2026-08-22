"""Admission boundaries unique to sealed v2 assignments."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts import tickets_admission as admission
from scripts import tickets_generations as generations
from scripts.tickets_dispatch import _dispatch
from scripts.tickets_format import _parse_frontmatter
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

    def test_generation_pair_and_durable_seal_record_are_both_required(self):
        current = snapshot()
        draft = generations.draft_snapshot("00-root", current)
        sealed = generations.seal_assignments("00-root", current, draft, generations.validate_draft("00-root", current, draft))
        text = sealed["00-root.01"].replace("v2:cut:00-root:1:", "v2:cut:other-root:2:")
        text = generations._set_frontmatter_field(text, "assignment_seal", generations.assignment_digest("00-root.01", text))
        grade = admission.grade_admission("00-root.01", text, {**sealed, "00-root.01": text})
        self.assertIn("generation-pair-mismatch", {item["code"] for item in grade["findings"]})

        with tempfile.TemporaryDirectory() as directory:
            with mock.patch.dict(os.environ, {"ORCHFLOWS_STATE_HOME": directory}):
                run_dir = Path(directory) / "tickets" / "run"
                run_dir.mkdir(parents=True)
                for ticket_id, value in current.items(): (run_dir / f"{ticket_id}.md").write_text(value, encoding="utf-8")
                cut = _dispatch(["draft-validate", "run", "00-root"])["draft_validation"]["cut_generation"]
                _dispatch(["seal", "run", "00-root", "--cut-generation", cut])
                sealed_path = next((Path(directory) / "runs" / "run" / "generations").glob("*.sealed.json"))
                sealed_path.write_text('{"state":"sealed"}\n', encoding="utf-8")
                ready = _dispatch(["ready", "--run", "run"])
                refused = next(item for item in ready["skipped"] if item["id"] == "00-root.01")
                self.assertIn("seal-state-mismatch", {item["code"] for item in refused["findings"]})


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

    def test_mutators_refuse_unsafe_paths_and_non_v2_history(self):
        self.assertIn("unsafe run id", _dispatch(["draft-validate", "..\\escape", "00-root"])["error"])
        self.assertIn("unsafe ticket id", _dispatch(["amendment-request", "run", "..\\escape", "--record", "{}"])["error"])
        with tempfile.TemporaryDirectory() as directory:
            with mock.patch.dict(os.environ, {"ORCHFLOWS_STATE_HOME": directory}):
                run_dir = Path(directory) / "tickets" / "run"
                run_dir.mkdir(parents=True)
                legacy = snapshot()["00-root.01"].replace("admission: v2:pending", "admission: v1:git:sha256:" + "0" * 64).replace("ownership_regions: []\n", "").replace("status: pending", "status: complete")
                (run_dir / "00-root.01.md").write_text(legacy, encoding="utf-8")
                refusal = _dispatch(["amendment-request", "run", "00-root.01", "--record", "{}"])
                self.assertIn("claimed sealed v2 worker", refusal["error"])


class SealedAuthorityAndOutputTest(unittest.TestCase):
    def test_v2_grant_and_result_replace_are_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            with mock.patch.dict(os.environ, {"ORCHFLOWS_STATE_HOME": directory}):
                run_dir = Path(directory) / "tickets" / "run"
                run_dir.mkdir(parents=True)
                for ticket_id, value in snapshot().items(): (run_dir / f"{ticket_id}.md").write_text(value, encoding="utf-8")
                cut = _dispatch(["draft-validate", "run", "00-root"])["draft_validation"]["cut_generation"]
                _dispatch(["seal", "run", "00-root", "--cut-generation", cut])
                _dispatch(["claim", "run", "00-root.01", "--by", "worker"])
                grant = _dispatch(["grant", "run", "00-root.01", "--write-scope", "extra.py", "--by", "caller"])
                self.assertIn("cannot widen authority", grant["error"])
                self.assertNotIn("error", _dispatch(["result", "run", "00-root.01", "--section", "Result", "--text", "first"]))
                replace = _dispatch(["result", "run", "00-root.01", "--section", "Result", "--text", "second", "--replace"])
                self.assertIn("append-only", replace["error"])


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

    def test_amend_invalidates_the_seal_and_validates_a_successor(self):
        with tempfile.TemporaryDirectory() as directory:
            with mock.patch.dict(os.environ, {"ORCHFLOWS_STATE_HOME": directory}):
                run_dir = Path(directory) / "tickets" / "run"
                run_dir.mkdir(parents=True)
                for ticket_id, text in snapshot().items():
                    (run_dir / f"{ticket_id}.md").write_text(text, encoding="utf-8")
                first = _dispatch(["draft-validate", "run", "00-root"])["draft_validation"]
                self.assertNotIn("error", _dispatch(["seal", "run", "00-root", "--cut-generation", first["cut_generation"]]))
                amended = _dispatch(["amend", "run", "00-root.01", "--section", "Objective", "--text", "successor assignment"])
                self.assertNotIn("error", amended)
                data = _parse_frontmatter((run_dir / "00-root.01.md").read_text(encoding="utf-8"))
                self.assertEqual("v2:pending", data["admission"])
                self.assertNotIn("assignment_seal", data)
                second = _dispatch(["draft-validate", "run", "00-root"])["draft_validation"]
                self.assertIn(":2:sha256:", second["cut_generation"])


if __name__ == "__main__":
    unittest.main()
