"""Typed Fixed-input records and pack adapter acceptance."""

from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts import cutcheck_ticket, tickets_dispatch, tickets_input_producers, tickets_inputs


def canonical(value) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def ticket(inputs, *, ticket_id="T", run="run", depends="[]", status="pending",
           cohort="v1:ticket:T", executor="orch-tdd", pack="") -> str:
    pack_line = f"pack: {pack}\n" if pack else ""
    return f"""---
id: {ticket_id}
run: {run}
status: {status}
cohort: {cohort}
executor: {executor}
{pack_line}admission: v1:pending
depends_on: {depends}
---

## Objective

Exercise the resolver.

## Fixed inputs

{inputs}

## Completion test

- resolver output is exact

## Return fields

status; result

## Result

payload
"""


def record(name, *, value=None, identity=None) -> str:
    value = ({"identity": identity, "name": name, "type": "identity"}
             if identity is not None else
             {"name": name, "type": "literal", "value": value})
    return "- input: " + canonical(value)


class InputRecordTest(unittest.TestCase):
    def grade(self, lines, adapter="plain-artifact", **context):
        text = ticket(lines)
        return tickets_inputs.grade_inputs(
            ticket_id="T", text=text, siblings={"T": text},
            adapter_id=adapter, context=context,
        )

    def test_literals_preserve_json_values_and_fingerprint_portably(self):
        lines = "\n".join((
            record("question", value={"audience": ["a", "b"], "open": True}),
            record("source-policy", value=None),
        ))
        first = self.grade(lines)
        second = self.grade(lines, project_root="C:/different/host")
        self.assertEqual([], first["findings"])
        self.assertEqual(first["fingerprint"], second["fingerprint"])
        self.assertRegex(first["fingerprint"], r"^inputs:sha256:[0-9a-f]{64}$")

    def test_record_grammar_rejects_prose_duplicates_and_noncanonical_json(self):
        cases = {
            "non-identity": "- prose is not an identity",
            "input-name-duplicate": "\n".join((record("same", value=1), record("same", value=2))),
            "input-name-invalid": record("Not_Kebab", value=1),
            "input-json-noncanonical": '- input: {"type": "literal", "name":"x","value":1}',
            "input-record-shape": '- input: {"name":"x","type":"literal"}',
        }
        for expected, lines in cases.items():
            with self.subTest(expected=expected):
                codes = [item["code"] for item in self.grade(lines)["findings"]]
                self.assertIn(expected, codes)

    def test_producer_rejects_duplicate_keys_nonfinite_numbers_and_rendered_placeholders(self):
        for encoded in (
            '{"name":"x","name":"y","type":"literal","value":1}',
            '{"name":"x","type":"literal","value":NaN}',
        ):
            with self.subTest(encoded=encoded):
                _, error = tickets_input_producers.render_inputs("- input: " + encoded, {"run": "run"}, [], "")
                self.assertIn("invalid JSON", error)
        source = ticket(record("question", value="{{answer}}"))
        _, error = tickets_input_producers.render_stub(source, {"run": "run", "answer": "{{still-missing}}"})
        self.assertIn("unfilled placeholder", error)

    def test_dependency_carriage_compares_the_whole_ticket_section_identity(self):
        wrong = record("dependency-completion", identity={
            "kind": "ticket-section", "run": "run", "section": "Completion test", "ticket": "P",
        })
        rendered, error = tickets_input_producers.render_inputs(wrong, {"run": "run"}, ["P"], "")
        self.assertIsNone(error)
        records = tickets_inputs.parse_input_records(ticket(rendered))["records"]
        identities = [item["identity"] for item in records if item.get("type") == "identity"]
        self.assertIn({"kind": "ticket-section", "run": "run", "section": "Result", "ticket": "P"}, identities)

    def test_identity_payload_requires_a_known_exact_schema(self):
        malformed = record("thing", identity={"kind": "artifact", "locator": "sink:x"})
        unknown = record("thing", identity={"kind": "future-kind"})
        self.assertIn("identity-schema", [x["code"] for x in self.grade(malformed)["findings"]])
        self.assertIn("identity-kind-unsupported", [x["code"] for x in self.grade(unknown)["findings"]])

    def test_exact_fourteen_historical_sections_replay_only_as_non_identity(self):
        fixture = Path("tests/fixtures/final_specs/04/historical.json")
        cases = json.loads(fixture.read_text(encoding="utf-8"))
        self.assertEqual(14, len(cases))
        for case in cases:
            with self.subTest(ticket=case["ticket"]):
                section = case["fixed_inputs"]
                self.assertEqual(case["sha256"], hashlib.sha256(section.encode("utf-8")).hexdigest())
                codes = {
                    item["code"] for item in self.grade(section)["findings"]
                }
                self.assertEqual({"non-identity"}, codes)

    def test_composition_producers_use_only_canonical_records(self):
        roots = (
            "benchmaker", "drift-canary", "evolve", "fix", "renovate", "self-improve", "skill-tournament",
        )
        for root in roots:
            paths = ((Path("compositions") / root / "00-run.md",) if root == "drift-canary"
                     else sorted((Path("compositions") / root).glob("[0-9]*.md")))
            for path in paths:
                with self.subTest(path=str(path)):
                    parsed = tickets_inputs.parse_input_records(path.read_text(encoding="utf-8"))
                    self.assertEqual([], parsed["findings"])
                    self.assertTrue(parsed["records"])
                    for item in parsed["records"]:
                        self.assertFalse(item["name"].startswith("contract-"))
                        value = item.get("value")
                        if isinstance(value, str) and "{{" in value:
                            self.assertRegex(value, r"^\{\{[a-z_]+\}\}$")
                        if isinstance(value, str):
                            self.assertNotRegex(value, r"(?:^|\s)\.\.?/.*\.md(?:#|:|$)")

    def test_routing_objectives_are_observable_states_not_embedded_procedures(self):
        for relative in (
            "compositions/drift-canary/00-run.md",
            "compositions/skill-tournament/00-benchmark.md",
            "compositions/skill-tournament/01-campaign.md",
        ):
            text = Path(relative).read_text(encoding="utf-8")
            objective = tickets_inputs.section_body(text, "Objective")
            for activity in ("Instantiate ", "Place ", "Supply ", "Drain ", "Run "):
                with self.subTest(relative=relative, activity=activity):
                    self.assertNotIn(activity, objective)

    def test_pack_producers_supply_portable_adapter_roots(self):
        cases = (
            ("orch-content-pack", {"workspace": "docs/guide"}, "document-root", "project:docs/guide/"),
            ("orch-research-pack", {"package": "evidence/run"}, "evidence-store-root", "sink:evidence/run/"),
        )
        for pack, values, name, expected in cases:
            with self.subTest(pack=pack):
                source = record(next(iter(values)), value=f"{{{{{next(iter(values))}}}}}")
                rendered, error = tickets_input_producers.render_inputs(source, {**values, "run": "run"}, [], pack)
                self.assertIsNone(error)
                parsed = tickets_inputs.parse_input_records(ticket(rendered))
                roots = {item["name"]: item.get("value") for item in parsed["records"]}
                self.assertEqual(expected, roots[name])
        _, error = tickets_input_producers.render_inputs(
            record("package", value="{{package}}"), {"package": "C:\\host\\evidence", "run": "run"},
            [], "orch-research-pack",
        )
        self.assertIn("portable", error)

    def test_generated_git_gate_carries_exactly_one_baseline(self):
        sections = [
            ("Objective", "Inspect."), ("Fixed inputs", record("question", value="exact")),
            ("Completion test", "- exact | oracle: result | oracle_class: deterministic | provenance: pre-existing"),
            ("Return fields", "status; result"),
        ]
        rendered = tickets_dispatch._gate_stub(
            "run", "root.gate.critique-code", "orch-critique", [], [], sections,
            "orch-code-pack",
        )
        parsed = tickets_inputs.parse_input_records(rendered)
        baselines = [item for item in parsed["records"] if item["name"] == "baseline"]
        self.assertEqual(1, len(baselines))
        self.assertEqual("git-tree", baselines[0]["identity"]["kind"])
        content = tickets_dispatch._gate_stub(
            "run", "root.gate.critique-content", "orch-critique", [], [], sections,
            "orch-content-pack", inherited_inputs=record("document-root", value="sink:documents/run/"),
        )
        literals = {
            item["name"]: item.get("value") for item in tickets_inputs.parse_input_records(content)["records"]
            if item["type"] == "literal"
        }
        self.assertEqual("sink:documents/run/", literals["document-root"])

    def test_the_harvest_reads_a_roots_last_record_under_trailing_prose(self):
        """`input_groups` attaches every later non-blank line to the group the
        last `- ` opened, so a root whose `## Fixed inputs` ends in a line of
        prose delivers its final record inside a two-line group. Judging that
        group by its length drops the record -- and when it is the one naming
        the document or evidence-store root, the rendering refuses a root that
        plainly states it. `tickets_dispatch_gate._is_record` owns the
        corrected law; this is its twin in the harvest, and it is asserted at
        this function rather than through the gate because the gate also
        inherits the record verbatim and so masks the defect there.
        """

        child = ticket(record("question", value="exact"), pack="orch-content-pack",
                       executor="orch-draft")
        inherited = record("document-root", value="sink:documents/run/")

        for label, body in (("lone record", inherited),
                            ("record under prose", inherited + "\n\nReading order follows.")):
            with self.subTest(label):
                text, error = tickets_input_producers.render_ticket_inputs(
                    child, "run", body)

                self.assertIsNone(error, label)
                literals = {
                    item["name"]: item.get("value")
                    for item in tickets_inputs.parse_input_records(text)["records"]
                    if item["type"] == "literal"
                }
                self.assertEqual("sink:documents/run/", literals.get("document-root"))

    def test_cutcheck_renders_the_shared_input_codes_unchanged(self):
        revision = tickets_input_producers.git_head()
        inputs = "\n".join((
            record("baseline", identity={"kind": "git-tree", "repo": "run-project", "revision": revision}),
            record("missing", identity={"kind": "git-path", "path": "absent-input-identity", "repo": "run-project", "revision": revision}),
        ))
        text = ticket(inputs, pack="orch-code-pack")
        expected = [item["code"] for item in tickets_inputs.grade_inputs(
            ticket_id="T", text=text, siblings={"T": text}, adapter_id="git",
        )["findings"]]
        rendered = cutcheck_ticket._policy_findings("T", text, {"T": text}, revision, revision)
        actual = [item[2] for item in rendered if item[2] in expected]
        self.assertEqual(expected, actual)

    def test_cutcheck_reports_pending_dependency_as_advisory(self):
        revision = tickets_input_producers.git_head()
        predecessor = ticket("", ticket_id="P")
        dependent = ticket(
            record("predecessor", identity={
                "kind": "ticket-section", "run": "run", "section": "Result", "ticket": "P",
            }),
            ticket_id="D", depends="[P]",
        )
        rendered = cutcheck_ticket._policy_findings(
            "D", dependent, {"D": dependent, "P": predecessor}, revision, revision,
        )
        codes = [item[2] for item in rendered]
        self.assertIn("ticket-result-not-terminal", codes)
        self.assertIn("ticket-result-not-terminal", cutcheck_ticket._contract.ADVISORY)


class ResolverFixture(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.project = self.root / "project"
        self.sink = self.root / "sink"
        self.project.mkdir()
        self.sink.mkdir()
        subprocess.run(["git", "init", "-q", str(self.project)], check=True)
        subprocess.run(["git", "-C", str(self.project), "config", "user.email", "test@example.invalid"], check=True)
        subprocess.run(["git", "-C", str(self.project), "config", "user.name", "Test"], check=True)
        (self.project / "src").mkdir()
        (self.project / "src" / "tool.py").write_text("def exact_symbol():\n    return 1\n", encoding="utf-8")
        (self.project / "capture.png").write_bytes(b"capture")
        subprocess.run(["git", "-C", str(self.project), "add", "."], check=True)
        subprocess.run(["git", "-C", str(self.project), "commit", "-qm", "fixture"], check=True)
        self.revision = subprocess.check_output(
            ["git", "-C", str(self.project), "rev-parse", "HEAD"], text=True
        ).strip()
        self.context = {"project_root": str(self.project), "sink_root": str(self.sink), "run": "run"}

    def tearDown(self):
        self.temporary.cleanup()

    def grade(self, records, adapter, *, siblings=None, ticket_text=None, **context):
        text = ticket_text or ticket("\n".join(records))
        return tickets_inputs.grade_inputs(
            ticket_id="T", text=text, siblings=siblings or {"T": text}, adapter_id=adapter,
            context={**self.context, **context},
        )

    def baseline(self):
        return record("baseline", identity={"kind": "git-tree", "repo": "run-project", "revision": self.revision})


class GitAdapterTest(ResolverFixture):
    def test_git_kinds_resolve_at_the_immutable_revision(self):
        records = [
            self.baseline(),
            record("source", identity={"kind": "git-path", "path": "src/tool.py", "repo": "run-project", "revision": self.revision}),
            record("callable", identity={"kind": "git-symbol", "path": "src/tool.py", "repo": "run-project", "revision": self.revision, "symbol": "exact_symbol"}),
        ]
        grade = self.grade(records, "git")
        self.assertEqual([], grade["findings"])
        self.assertNotIn(str(self.project), grade["fingerprint"])

    def test_git_adapter_reports_revision_path_symbol_and_baseline_failures(self):
        cases = {
            "git-baseline-cardinality": [],
            "git-revision-invalid": [record("baseline", identity={"kind": "git-tree", "repo": "run-project", "revision": "abc"})],
            "git-path-absent": [self.baseline(), record("missing", identity={"kind": "git-path", "path": "no.txt", "repo": "run-project", "revision": self.revision})],
            "git-symbol-absent": [self.baseline(), record("symbol", identity={"kind": "git-symbol", "path": "src/tool.py", "repo": "run-project", "revision": self.revision, "symbol": "not_there"})],
            "identity-path-invalid": [self.baseline(), record("escape", identity={"kind": "git-path", "path": "../x", "repo": "run-project", "revision": self.revision})],
        }
        for expected, records in cases.items():
            with self.subTest(expected=expected):
                self.assertIn(expected, [x["code"] for x in self.grade(records, "git")["findings"]])

    def test_git_remote_metadata_and_symbol_boundaries_are_exact(self):
        subprocess.run(
            ["git", "-C", str(self.project), "remote", "add", "origin", "https://example.test/repo.git"],
            check=True,
        )
        mismatched = self.grade([self.baseline()], "git", project_remote="https://else.test/repo")
        self.assertIn("git-remote-mismatch", [x["code"] for x in mismatched["findings"]])
        source = record("symbol", identity={
            "kind": "git-symbol", "path": "src/tool.py", "repo": "run-project",
            "revision": self.revision, "symbol": "exact",
        })
        grade = self.grade([self.baseline(), source], "git", project_remote="https://example.test/repo")
        self.assertIn("git-symbol-absent", [x["code"] for x in grade["findings"]])

    def test_git_plus_render_verifies_tuple_and_capture_bytes(self):
        digest = hashlib.sha256(b"capture").hexdigest()
        view = record("desktop", identity={
            "breakpoint": "1280x720", "capture": "capture.png", "kind": "view-identity",
            "repo": "run-project", "revision": self.revision, "sha256": digest,
            "state": "ready", "view": "home",
        })
        self.assertEqual([], self.grade([self.baseline(), view], "git-plus-render")["findings"])
        bad = view.replace(digest, "0" * 64)
        self.assertIn("identity-digest-mismatch", [x["code"] for x in self.grade([self.baseline(), bad], "git-plus-render")["findings"]])

    def test_git_plus_render_resolves_fresh_captures_only_from_the_sink(self):
        payload = b"fresh capture"
        capture = self.sink / "captures" / "home-ready.png"
        capture.parent.mkdir()
        capture.write_bytes(payload)
        identity = {
            "breakpoint": "1280x720", "kind": "capture-artifact",
            "locator": "sink:captures/home-ready.png",
            "sha256": hashlib.sha256(payload).hexdigest(), "state": "ready",
            "view": "home",
        }
        grade = self.grade(
            [self.baseline(), record("fresh-capture", identity=identity)],
            "git-plus-render",
        )
        self.assertEqual([], grade["findings"])
        self.assertNotIn(str(self.sink), grade["fingerprint"])

        identity["locator"] = "project:capture.png"
        in_scope = self.grade(
            [self.baseline(), record("fresh-capture", identity=identity)],
            "git-plus-render",
        )
        self.assertIn(
            "identity-locator-invalid",
            [item["code"] for item in in_scope["findings"]],
        )


class TreeAdapterTest(ResolverFixture):
    def test_document_and_evidence_roots_are_adapter_specific(self):
        (self.project / "docs").mkdir()
        (self.project / "docs" / "brief.md").write_bytes(b"brief")
        (self.sink / "evidence").mkdir()
        (self.sink / "evidence" / "packet.json").write_bytes(b"packet")
        document = [
            record("document-root", value="project:docs/"),
            record("brief", identity={"kind": "document-revision", "locator": "brief.md", "sha256": hashlib.sha256(b"brief").hexdigest()}),
        ]
        evidence = [
            record("evidence-store-root", value="sink:evidence/"),
            record("packet", identity={"kind": "evidence-packet", "locator": "packet.json", "sha256": hashlib.sha256(b"packet").hexdigest()}),
        ]
        self.assertEqual([], self.grade(document, "document-tree")["findings"])
        self.assertEqual([], self.grade(evidence, "evidence-store")["findings"])
        crossed = self.grade(document, "evidence-store")
        self.assertTrue(crossed["findings"])
        self.assertIn("adapter-kind-unsupported", [x["code"] for x in crossed["findings"]])

    def test_document_root_may_be_project_or_sink_but_evidence_is_sink_only(self):
        (self.sink / "documents").mkdir()
        (self.sink / "documents" / "brief.md").write_bytes(b"brief")
        digest = hashlib.sha256(b"brief").hexdigest()
        document = [
            record("document-root", value="sink:documents/"),
            record("brief", identity={"kind": "document-revision", "locator": "brief.md", "sha256": digest}),
        ]
        self.assertEqual([], self.grade(document, "document-tree")["findings"])
        invalid = [
            record("evidence-store-root", value="project:documents/"),
            record("packet", identity={"kind": "evidence-packet", "locator": "brief.md", "sha256": digest}),
        ]
        self.assertIn("adapter-root-invalid", [x["code"] for x in self.grade(invalid, "evidence-store")["findings"]])

    def test_store_resolution_stays_below_declared_root_and_matches_digest(self):
        records = [
            record("evidence-store-root", value="sink:evidence/"),
            record("packet", identity={"kind": "evidence-packet", "locator": "../outside", "sha256": "0" * 64}),
        ]
        codes = [x["code"] for x in self.grade(records, "evidence-store")["findings"]]
        self.assertIn("identity-path-invalid", codes)
        for root in ("C:/outside", "D:\\outside"):
            with self.subTest(root=root):
                drive = [
                    record("document-root", value="project:" + root),
                    record("document", identity={"kind": "document", "locator": "page.txt", "sha256": "0" * 64}),
                ]
                codes = [x["code"] for x in self.grade(drive, "document-tree")["findings"]]
                self.assertIn("adapter-root-invalid", codes)


class CommonIdentityTest(ResolverFixture):
    def test_artifact_locators_resolve_without_host_paths_in_the_fingerprint(self):
        path = self.sink / "records" / "one.txt"
        path.parent.mkdir()
        path.write_bytes(b"one")
        identity = {"kind": "artifact", "locator": "sink:records/one.txt", "sha256": hashlib.sha256(b"one").hexdigest()}
        grade = self.grade([record("record", identity=identity)], "plain-artifact")
        self.assertEqual([], grade["findings"])
        self.assertNotIn(str(self.sink), grade["fingerprint"])

    def test_same_run_dependency_result_uses_no_digest_and_must_be_terminal(self):
        predecessor = ticket("", ticket_id="P", status="complete", executor="orch-verify")
        identity = {"kind": "ticket-section", "run": "run", "section": "Result", "ticket": "P"}
        current = ticket(record("predecessor", identity=identity), depends="[P]")
        grade = self.grade([], "plain-artifact", siblings={"T": current, "P": predecessor}, ticket_text=current)
        self.assertEqual([], grade["findings"])
        prior = predecessor.replace("status: complete", "status: claimed")
        refused = self.grade([], "plain-artifact", siblings={"T": current, "P": prior}, ticket_text=current)
        self.assertIn("ticket-result-not-terminal", [x["code"] for x in refused["findings"]])

    def test_prior_run_ticket_section_requires_and_checks_digest(self):
        tickets_root = self.sink / "tickets"
        prior_dir = tickets_root / "prior"
        prior_dir.mkdir(parents=True)
        prior = ticket("", ticket_id="P", run="prior", status="complete", executor="orch-verify")
        (prior_dir / "P.md").write_text(prior, encoding="utf-8")
        section = tickets_inputs.section_body(prior, "Result").encode("utf-8")
        identity = {"kind": "ticket-section", "run": "prior", "section": "Result", "sha256": hashlib.sha256(section).hexdigest(), "ticket": "P"}
        grade = self.grade([record("prior-result", identity=identity)], "plain-artifact", tickets_root=str(tickets_root))
        self.assertEqual([], grade["findings"])
        identity["sha256"] = "0" * 64
        bad = self.grade([record("prior-result", identity=identity)], "plain-artifact", tickets_root=str(tickets_root))
        self.assertIn("identity-digest-mismatch", [x["code"] for x in bad["findings"]])

    def test_ticket_coordinates_cannot_escape_the_state_sink(self):
        identity = {
            "kind": "ticket-section", "run": "..", "section": "Result",
            "sha256": "0" * 64, "ticket": "outside",
        }
        grade = self.grade([record("prior", identity=identity)], "plain-artifact")
        self.assertIn("ticket-coordinate-invalid", [x["code"] for x in grade["findings"]])

    def test_result_payload_resolver_returns_exact_bytes(self):
        path = self.sink / "result.txt"
        path.write_bytes(b"one two")
        identity = {"kind": "artifact", "locator": "sink:result.txt", "sha256": hashlib.sha256(b"one two").hexdigest()}
        resolved = tickets_inputs.resolve_identity_payload(
            identity=identity, adapter_id="plain-artifact", context=self.context, mode="result"
        )
        self.assertEqual([], resolved["findings"])
        self.assertEqual(b"one two", resolved["bytes"])

    def test_migrated_historical_fixtures_keep_the_coordinate_and_reach_a_specific_resolver(self):
        fixture_root = Path("tests/fixtures/final_specs/04")
        historical = {
            item["ticket"]: item for item in json.loads((fixture_root / "historical.json").read_text(encoding="utf-8"))
        }
        migrated = json.loads((fixture_root / "migrated.json").read_text(encoding="utf-8"))
        self.assertEqual(14, len(migrated))
        (self.sink / "migrated.txt").write_bytes(b"actual")
        for case in migrated:
            with self.subTest(ticket=case["ticket"]):
                self.assertIn(case["evidence"], historical[case["ticket"]]["fixed_inputs"])
                expected = case["expected"]
                context = dict(self.context)
                if expected == "identity-digest-mismatch":
                    lines, adapter = [record("evidence", identity={"kind": "artifact", "locator": "sink:migrated.txt", "sha256": "0" * 64})], "plain-artifact"
                elif expected == "identity-digest-invalid":
                    lines, adapter = [record("evidence", identity={"kind": "artifact", "locator": "sink:migrated.txt", "sha256": "0" * 63})], "plain-artifact"
                elif expected == "identity-locator-absent":
                    lines, adapter = [record("evidence", identity={"kind": "artifact", "locator": "sink:absent.txt", "sha256": "0" * 64})], "plain-artifact"
                elif expected == "identity-locator-invalid":
                    lines, adapter = [record("evidence", identity={"kind": "artifact", "locator": "conversation:latest", "sha256": "0" * 64})], "plain-artifact"
                elif expected == "identity-schema":
                    lines, adapter = [record("evidence", identity={"kind": "artifact", "sha256": "0" * 64})], "plain-artifact"
                elif expected == "ticket-section-absent":
                    lines, adapter = [record("evidence", identity={"kind": "ticket-section", "run": "prior", "section": "Result", "sha256": "0" * 64, "ticket": "absent"})], "plain-artifact"
                elif expected == "git-remote-mismatch":
                    lines, adapter = [self.baseline()], "git"
                    context["project_remote"] = "https://wrong.invalid/project"
                else:
                    kind = "git-path" if expected == "git-path-absent" else "git-symbol"
                    identity = {"kind": kind, "path": "absent.py", "repo": "run-project", "revision": self.revision}
                    if kind == "git-symbol":
                        identity["path"], identity["symbol"] = "src/tool.py", "absent_symbol"
                    lines, adapter = [self.baseline(), record("evidence", identity=identity)], "git"
                grade = self.grade(lines, adapter, **context)
                self.assertIn(expected, [item["code"] for item in grade["findings"]])
                self.assertNotIn("non-identity", [item["code"] for item in grade["findings"]])


if __name__ == "__main__":
    unittest.main()
