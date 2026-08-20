"""Specification 06: one witnessed return-size bound, separate from effort."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts import tickets_admission, tickets_format, tickets_lifecycle, tickets_result
from tests.test_tickets_cases.common import run_cmd


FIXTURES = Path(__file__).parent / "fixtures" / "final_specs" / "06"


def canonical(value) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def input_record(name, identity) -> str:
    return "- input: " + canonical({"identity": identity, "name": name, "type": "identity"})


def artifact(locator, content: bytes) -> dict:
    return {"kind": "artifact", "locator": locator, "sha256": hashlib.sha256(content).hexdigest()}


def ticket(*, inputs, maximum=3, counter="words-v1", result=None, status="claimed",
           objective="Return the result.", completion="the result satisfies `return-size`") -> str:
    clause = canonical({
        "counter": counter, "maximum": maximum,
        "minimum-complete": "return-fixture", "target": "result",
    })
    result_body = "" if result is None else f"result: {canonical(result)}"
    return f"""---
id: T
run: testrun
status: {status}
executor: orch-investigate
admission: v1:pending
cohort: v1:ticket:T
depends_on: []
write_scope: []
bound: 55m
---

## Objective

{objective}

## Fixed inputs

{inputs}

## Completion test

- {completion} | oracle: tickets.py result-grade | oracle_class: deterministic | provenance: authored-here

## Return fields

status; result
return-size: {clause}

## Result

{result_body}

## Verification


## Feedback

[]

## Risks

[]
"""


class ClauseAndCounterTest(unittest.TestCase):
    def test_exact_clause_and_result_identity_grammar_refuse_ambiguity(self):
        clause = 'return-size: {"counter":"words-v1","maximum":3,"minimum-complete":"return-fixture","target":"result"}'
        parsed, defects = tickets_format.parse_return_size(clause)
        self.assertEqual([], defects)
        self.assertEqual(3, parsed["maximum"])
        cases = (
            clause + "\n" + clause,
            'return-size: {"maximum":3,"counter":"words-v1","minimum-complete":"return-fixture","target":"result"}',
            'return-size: {"counter":"bytes-v1","maximum":3,"minimum-complete":"return-fixture","target":"result"}',
            'return-size: {"counter":"words-v1","maximum":true,"minimum-complete":"return-fixture","target":"result"}',
            'return-size: {"counter":"words-v1","maximum":3,"minimum-complete":"return-fixture","target":"packet"}',
        )
        for value in cases:
            with self.subTest(value=value):
                self.assertIsNone(tickets_format.parse_return_size(value)[0])
        identity = artifact("sink:result.txt", b"one")
        self.assertEqual(identity, tickets_format.parse_result_identity(f"result: {canonical(identity)}")[0])
        self.assertTrue(tickets_format.parse_result_identity("result: {}\nresult: {}")[1])

    def test_built_in_counters_have_frozen_edges(self):
        self.assertEqual(3, tickets_format.count_return_text(" alpha\u2003beta\n gamma ", "words-v1"))
        self.assertEqual(0, tickets_format.count_return_text("", "lines-v1"))
        self.assertEqual(2, tickets_format.count_return_text("alpha\r\nbeta\n", "lines-v1"))
        self.assertEqual(3, tickets_format.count_return_text("alpha\vbeta\fcharlie", "lines-v1"))

    def test_effort_bound_and_symbolic_oracle_survive_but_a_second_size_number_does_not(self):
        fixture = artifact("sink:fixture.txt", b"one")
        clean = ticket(inputs=input_record("return-fixture", fixture))
        self.assertNotIn("numeric word/line", " ".join(tickets_format.ticket_defects(clean)))
        for replacement in ("Return no more than 4 words.", "Return no more than 4 lines."):
            with self.subTest(replacement=replacement):
                defects = tickets_format.ticket_defects(clean.replace("Return the result.", replacement))
                self.assertTrue(any("numeric word/line" in item for item in defects), defects)


class MinimumCompleteFixtureTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.sink = Path(self.temporary.name)
        self.content = (FIXTURES / "minimum-complete.txt").read_bytes()
        (self.sink / "fixtures").mkdir()
        (self.sink / "fixtures" / "minimum-complete.txt").write_bytes(self.content)
        self.identity = artifact("sink:fixtures/minimum-complete.txt", self.content)

    def tearDown(self):
        self.temporary.cleanup()

    def grade(self, text):
        return tickets_result.grade_return_fixture(
            ticket_id="T", text=text, siblings={"T": text}, adapter_id="plain-artifact",
            context={"sink_root": str(self.sink), "run": "testrun"},
        )

    def test_frozen_witness_is_resolved_counted_and_fingerprinted(self):
        text = ticket(inputs=input_record("return-fixture", self.identity))
        grade = self.grade(text)
        self.assertEqual([], grade["findings"])
        self.assertEqual(3, grade["count"])
        self.assertRegex(grade["fingerprint"], r"^return-fixture:sha256:[0-9a-f]{64}$")

    def test_missing_mismatched_non_text_and_oversized_witnesses_are_refused(self):
        cases = {}
        cases["return-fixture-cardinality"] = ticket(inputs=input_record("another", self.identity))
        wrong_kind = {"kind": "git-path", "path": "x", "repo": "run-project", "revision": "a" * 40}
        cases["return-fixture-kind"] = ticket(inputs=input_record("return-fixture", wrong_kind))
        binary = b"\xff\xfe"
        (self.sink / "fixtures" / "binary.txt").write_bytes(binary)
        cases["return-fixture-not-text"] = ticket(
            inputs=input_record("return-fixture", artifact("sink:fixtures/binary.txt", binary))
        )
        cases["return-fixture-too-large"] = ticket(
            inputs=input_record("return-fixture", self.identity), maximum=2
        )
        for expected, text in cases.items():
            with self.subTest(expected=expected):
                codes = {item["code"] for item in self.grade(text)["findings"]}
                self.assertIn(expected, codes)

    def test_admission_consumes_the_same_fixture_grade(self):
        text = ticket(inputs=input_record("return-fixture", self.identity), maximum=2)
        grade = tickets_admission.grade_admission(
            "T", text, {"T": text}, context={"sink_root": str(self.sink), "run": "testrun"},
        )
        self.assertIn("return-fixture-too-large", {item["code"] for item in grade["findings"]})

    def test_malformed_clause_is_an_admission_finding(self):
        text = ticket(inputs=input_record("return-fixture", self.identity)).replace('"maximum":3', '"maximum":"three"')
        grade = tickets_admission.grade_admission(
            "T", text, {"T": text}, context={"sink_root": str(self.sink), "run": "testrun"},
        )
        self.assertIn("return-size-invalid", {item["code"] for item in grade["findings"]})


class ActualResultGradeTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.repo = self.root / "repo"
        (self.repo / ".git").mkdir(parents=True)
        self.sink = self.root / "sink"
        os.environ["ORCHFLOWS_STATE_HOME"] = str(self.sink)
        self.run_dir = self.sink / "tickets" / "testrun"
        self.run_dir.mkdir(parents=True)
        (self.sink / "results").mkdir()
        self.fixture = artifact("sink:fixtures/minimum-complete.txt", b"one two three")

    def tearDown(self):
        self.temporary.cleanup()

    def write_case(self, content: bytes, *, maximum=3, duplicate=False):
        path = self.sink / "results" / "actual.txt"
        path.write_bytes(content)
        identity = artifact("sink:results/actual.txt", content)
        text = ticket(
            inputs=input_record("return-fixture", self.fixture), maximum=maximum, result=identity,
        )
        if duplicate:
            text = text.replace(f"result: {canonical(identity)}", f"result: {canonical(identity)}\nresult: {canonical(identity)}")
        (self.run_dir / "T.md").write_text(text, encoding="utf-8")

    def test_result_grade_and_complete_share_findings_and_accept_the_boundary(self):
        self.write_case(b"one two three four")
        grade = run_cmd(self.repo, "result-grade", "testrun", "T")["result_grade"]
        refusal = run_cmd(self.repo, "set-status", "testrun", "T", "complete")
        self.assertEqual(grade["findings"], refusal["findings"])
        self.assertIn("result-too-large", {item["code"] for item in grade["findings"]})
        self.write_case(b"one two three")
        grade = run_cmd(self.repo, "result-grade", "testrun", "T")["result_grade"]
        self.assertEqual([], grade["findings"])
        self.assertNotIn("error", run_cmd(self.repo, "set-status", "testrun", "T", "complete"))

    def test_actual_result_refuses_duplicate_unresolved_and_non_text_targets(self):
        self.write_case(b"one", duplicate=True)
        self.assertIn("result-identity-invalid", {
            item["code"] for item in run_cmd(self.repo, "result-grade", "testrun", "T")["result_grade"]["findings"]
        })
        self.write_case(b"\xff")
        self.assertIn("result-not-text", {
            item["code"] for item in run_cmd(self.repo, "result-grade", "testrun", "T")["result_grade"]["findings"]
        })
        missing = artifact("sink:results/missing.txt", b"missing")
        text = ticket(inputs=input_record("return-fixture", self.fixture), result=missing)
        (self.run_dir / "T.md").write_text(text, encoding="utf-8")
        self.assertIn("identity-locator-absent", {
            item["code"] for item in run_cmd(self.repo, "result-grade", "testrun", "T")["result_grade"]["findings"]
        })

    def test_non_success_terminal_statuses_do_not_trust_the_target(self):
        missing = artifact("sink:results/missing.txt", b"missing")
        for status in ("limited", "failed"):
            with self.subTest(status=status):
                text = ticket(inputs=input_record("return-fixture", self.fixture), result=missing)
                (self.run_dir / "T.md").write_text(text, encoding="utf-8")
                self.assertNotIn("error", run_cmd(self.repo, "set-status", "testrun", "T", status))

    def test_result_resolver_receives_owner_siblings_run_and_literal_context(self):
        actual = artifact("sink:results/actual.txt", b"one")
        text = ticket(inputs="\n".join((
            input_record("return-fixture", self.fixture),
            '- input: {"name":"document-root","type":"literal","value":"sink:documents/"}',
        )), result=actual)
        captured = {}

        def resolve(**kwargs):
            captured.update(kwargs["context"])
            return {"findings": [], "fingerprint": "result:test", "bytes": b"one"}

        with mock.patch("scripts.tickets_inputs.resolve_identity_payload", side_effect=resolve):
            grade = tickets_admission.grade_result("T", text, {"T": text}, context={"tickets_root": str(self.sink)})
        self.assertEqual([], grade["findings"])
        self.assertEqual("T", captured["ticket_id"])
        self.assertEqual("testrun", captured["run"])
        self.assertEqual({"T": text}, captured["siblings"])
        self.assertEqual("sink:documents/", captured["input_literals"]["document-root"])

    def test_unbounded_result_does_not_read_an_unrelated_sibling(self):
        with tempfile.TemporaryDirectory() as raw:
            run_dir = Path(raw)
            target = run_dir / "T.md"
            sibling = run_dir / "U.md"
            unbounded = "\n".join(
                line for line in ticket(inputs="", result=None).splitlines()
                if not line.startswith("return-size: ")
            )
            target.write_text(unbounded, encoding="utf-8")
            sibling.write_text("unreadable in the injected seam", encoding="utf-8")
            real_read = tickets_lifecycle._read_utf8

            def read(path, *args, **kwargs):
                if Path(path) == sibling:
                    return None, {"error": "unreadable sibling"}
                return real_read(path, *args, **kwargs)

            with mock.patch.object(tickets_lifecycle, "_read_utf8", side_effect=read):
                _, snapshot, failure = tickets_lifecycle._result_grade_snapshot(target)
            self.assertIsNone(failure)
            self.assertEqual({"T"}, set(snapshot))


class ReplayFixtureTest(unittest.TestCase):
    def test_all_ten_open_ended_research_and_critique_tickets_drop_the_ceiling(self):
        recuts = json.loads((FIXTURES / "recuts.json").read_text(encoding="utf-8"))
        self.assertEqual(10, len(recuts))
        self.assertEqual(10, len({item["source"] for item in recuts}))
        self.assertTrue(all(item["return_size"] is None for item in recuts))
        self.assertTrue(all(len(item["source_sha256"]) == 64 for item in recuts))


class ContractAndJoinTest(unittest.TestCase):
    def test_result_contract_names_the_bounded_identity_and_grade(self):
        text = Path("contracts/result.md").read_text(encoding="utf-8")
        self.assertIn("`return-size`", text)
        self.assertIn("`result: <canonical JSON identity payload>`", text)
        self.assertIn("`tickets.py result-grade`", text)

    def test_join_grades_the_actual_result_before_acceptance(self):
        text = Path("skills/kernel/orch-integrate/SKILL.md").read_text(encoding="utf-8")
        self.assertEqual(1, text.count("`tickets.py result-grade"))
        self.assertIn("return-size", text)
        self.assertIn("reject(child)", text)


if __name__ == "__main__":
    unittest.main()
