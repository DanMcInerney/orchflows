"""Admission consumes and compares the complete sealed ancestry."""
from __future__ import annotations

import copy
import json

from scripts import tickets_admission as admission, tickets_lifecycle, tickets_mint, tickets_seal
from scripts.tickets_format import _set_frontmatter_field
from scripts.tickets_generations import assignment_digest
from tests.test_staleness_and_remedies import SealedRunTest


class AdmissionReliabilityTest(SealedRunTest):
    def child(self, ticket_id, parent):
        text = self.ticket_path("T").read_text(encoding="utf-8")
        for key, value in (("id", ticket_id), ("parent", parent), ("status", "pending"),
                           ("admission", "pending"), ("dispatch_v1", "")):
            text = _set_frontmatter_field(text, key, value)
        text = _set_frontmatter_field(text, "assignment_seal", assignment_digest(ticket_id, text))
        self.ticket_path(ticket_id).write_text(text, encoding="utf-8")
        return text

    def snapshot(self):
        return {p.stem: p.read_text(encoding="utf-8") for p in self.ticket_path("T").parent.glob("*.md")}

    def grade(self, ticket_id="T.1", snapshot=None):
        snapshot = self.snapshot() if snapshot is None else snapshot
        return admission.grade_admission(ticket_id, snapshot[ticket_id], snapshot,
                                         {"runs_root": self.home / "runs"})

    def state_path(self, state):
        return tickets_seal._state_path("run", self.frontmatter("T")["cut_generation"], state)

    def test_anchor_and_intermediate_bytes_are_validated(self):
        self.child("T.1", "T")
        self.child("T.1.1", "T.1")
        snapshot = self.snapshot()
        self.assertEqual([], self.grade("T.1.1", snapshot)["findings"])
        for child, parent in (("T.1", "T"), ("T.1.1", "T"), ("T.1.1", "T.1")):
            with self.subTest(child=child, parent=parent):
                changed = dict(snapshot)
                changed[parent] = changed[parent].replace("Deliver the behavior.", "Changed acceptance.")
                grade = self.grade(child, changed)
                self.assertTrue(grade["findings"])
                self.assertEqual("pending", grade["receipt"])
        self.assertEqual(["T", "T.1", "T.1.1"], self.grade("T.1.1", snapshot)["snapshot_ids"])

    def test_parent_generation_and_cycle_controls(self):
        self.child("T.1", "T")
        snapshot = self.snapshot()
        for field, value in (("parent", "T.1"), ("cut_generation", "cut:foreign:1:sha256:" + "0" * 64)):
            with self.subTest(field=field):
                changed = dict(snapshot)
                text = _set_frontmatter_field(changed["T.1"], field, value)
                changed["T.1"] = _set_frontmatter_field(text, "assignment_seal", assignment_digest("T.1", text))
                self.assertTrue(self.grade(snapshot=changed)["findings"])

    def test_consumed_ancestor_race_refuses_but_unread_sibling_moves(self):
        self.child("T.1", "T")
        self.child("T.1.1", "T.1")
        self.child("T.2", "T")
        snapshot = self.snapshot()
        grade = self.grade("T.1.1", snapshot)
        self.assertEqual([], grade["findings"])
        for changed_id in ("T", "T.1", "T.2"):
            self.ticket_path("T.1.1").write_text(snapshot["T.1.1"], encoding="utf-8")
            with self.subTest(changed_id=changed_id):
                path = self.ticket_path(changed_id)
                path.write_text(snapshot[changed_id] + "\nConcurrent Report movement\n", encoding="utf-8")
                result = tickets_lifecycle._admit_ready_cas("run", "T.1.1", snapshot["T.1.1"], snapshot, grade)
                if changed_id == "T.2":
                    self.assertNotIn("error", result, result)
                else:
                    self.assertIn("error", result)
                    self.assertEqual(snapshot["T.1.1"], self.ticket_path("T.1.1").read_text(encoding="utf-8"))
                path.write_text(snapshot[changed_id], encoding="utf-8")

    def test_malformed_sealed_containers_refuse(self):
        self.child("T.1", "T")
        path = self.state_path("sealed")
        original = json.loads(path.read_text(encoding="utf-8"))
        malformed = [None, [], 7, "bad"]
        malformed += [{**original, "assignment_seals": value} for value in (None, [], 7, "bad", {"T": []})]
        malformed += [{**original, "receipt": value} for value in (None, [], 7, "bad", {})]
        for value in malformed:
            with self.subTest(value=value):
                path.write_text(json.dumps(value), encoding="utf-8")
                grade = self.grade()
                self.assertTrue(grade["findings"])
                self.assertEqual("pending", grade["receipt"])
        path.write_text(json.dumps(original), encoding="utf-8")
        self.assertEqual([], self.grade()["findings"])

    def test_malformed_validation_refuses_before_sealing(self):
        path = self.state_path("validated")
        original = json.loads(path.read_text(encoding="utf-8"))
        malformed = [None, [], 7, "bad"]
        for field in ("draft", "receipt"):
            malformed += [{**original, field: value} for value in (None, [], 7, "bad", {})]
        for value in (None, {}, [None], [{"id": []}], "bad"):
            document = copy.deepcopy(original)
            document["draft"]["assignments"] = value
            malformed.append(document)
        before = self.snapshot()
        for value in malformed:
            with self.subTest(value=value):
                path.write_text(json.dumps(value), encoding="utf-8")
                self.assertTrue(self.grade("T")["findings"])
                result = tickets_seal._cmd_seal(["run", "T", "--cut-generation", self.frontmatter("T")["cut_generation"]])
                self.assertIn("error", result)
                self.assertTrue(result.get("findings"), result)
                self.assertEqual(before, self.snapshot())
        path.write_text(json.dumps(original), encoding="utf-8")
        self.assertEqual([], self.grade("T")["findings"])

    def test_mint_refuses_changed_parent_before_issuing(self):
        path = self.ticket_path("T")
        self.assertIsNone(tickets_mint._sealed_parent(path.parent, "T")[1])
        path.write_text(path.read_text(encoding="utf-8").replace("Deliver the behavior.", "Changed acceptance."), encoding="utf-8")
        data, refusal = tickets_mint._sealed_parent(path.parent, "T")
        self.assertIsNone(data)
        self.assertIn("error", refusal)
