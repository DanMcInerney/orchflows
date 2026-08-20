"""V1 admission receipt and authority-policy cases."""

import types
import subprocess

from .common import *  # noqa: F401,F403
from scripts import tickets_format, tickets_lifecycle


V1_TICKET = """---
id: {tid}
run: testrun
status: pending
admission: v1:pending
cohort: {cohort}
executor: {executor}
pack: {pack}
independence: gate
depends_on: {deps}
write_scope: [scratch/{tid}.txt]
mutations: [change:scratch/{tid}.txt]
excluded_actions: {excluded}
isolation: {isolation}
bound: 30m
claimed_by:
claimed_at:
---

## Objective

Change one observable artifact.

## Fixed inputs

- input: {{"identity":{{"kind":"git-tree","repo":"run-project","revision":"{baseline}"}},"name":"baseline","type":"identity"}}
- input: {{"name":"question","type":"literal","value":"fixed"}}

## Completion test

- the artifact has the requested value | oracle: `python -m unittest` | oracle_class: deterministic | provenance: pre-existing

## Return fields

status; result; changed_artifacts; verification; feedback; risks

## Result

## Verification

## Feedback

[]

## Risks

[]
"""


def v1_ticket(tid="T1", *, cohort=None, executor="orch-tdd",
              pack="orch-code-pack", deps="[]", isolation="required",
              excluded="[vcs.integrate, vcs.push, vcs.open-pr]", baseline=None):
    return V1_TICKET.format(
        tid=tid,
        cohort=cohort or f"v1:ticket:{tid}",
        executor=executor,
        pack=pack,
        deps=deps,
        isolation=isolation,
        excluded=excluded,
        baseline=baseline or subprocess.check_output(
            ["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True
        ).strip(),
    )


def initialize_git_fixture(root):
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.email", "test@example.invalid"], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.name", "Test"], check=True)
    subprocess.run(["git", "-C", str(root), "commit", "--allow-empty", "-qm", "baseline"], check=True)
    return subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()


class AdmissionPrimitiveTest(unittest.TestCase):
    def test_closed_snapshot_rejects_new_members_and_read_failures(self):
        with tempfile.TemporaryDirectory() as raw:
            run_dir = Path(raw)
            (run_dir / "T1.md").write_text("one", encoding="utf-8")
            snapshot, failures = tickets_lifecycle._run_snapshot(run_dir)
            self.assertEqual([], failures)
            (run_dir / "T2.md").write_text("two", encoding="utf-8")
            self.assertFalse(tickets_lifecycle._snapshot_matches(run_dir, snapshot))
            with mock.patch.object(tickets_lifecycle, "_run_snapshot", return_value=(snapshot, [{"id": "T2"}])):
                self.assertFalse(tickets_lifecycle._snapshot_matches(run_dir, snapshot))

    def test_cohort_identities_are_deterministic_and_order_independent(self):
        self.assertEqual("v1:ticket:T1", tickets_mod.ticket_cohort("T1"))
        self.assertEqual("v1:root:R", tickets_mod.root_cohort("R"))
        self.assertEqual(
            tickets_mod.batch_cohort(["B", "A"]),
            tickets_mod.batch_cohort(["A", "B"]),
        )
        self.assertRegex(
            tickets_mod.batch_cohort(["A", "B"]),
            r"^v1:batch:[0-9a-f]{12}$",
        )

    def test_receipt_is_portable_and_ignores_lifecycle_and_host_fields(self):
        text = v1_ticket()
        grade = tickets_mod.grade_admission("T1", text, {"T1": text})
        self.assertEqual([], grade["findings"])
        self.assertRegex(grade["receipt"], r"^v1:git:sha256:[0-9a-f]{64}$")
        moved = tickets_mod._set_frontmatter_field(text, "claimed_by", "agent-a")
        moved = tickets_mod._set_frontmatter_field(moved, "claimed_at", "2099-01-01T00:00:00Z")
        moved = tickets_mod._set_frontmatter_field(moved, "workspace_branch", "host-only")
        self.assertEqual(
            grade["receipt"],
            tickets_mod.grade_admission("T1", moved, {"T1": moved})["receipt"],
        )

    def test_tdd_authority_matrix_is_closed(self):
        valid = v1_ticket()
        self.assertEqual([], tickets_mod.grade_admission("T1", valid, {"T1": valid})["findings"])
        cases = {
            "vcs-adapter-required": v1_ticket(pack="orch-content-pack"),
            "vcs-isolation-required": v1_ticket(isolation="none"),
            "vcs-action-excluded": v1_ticket(excluded="[vcs.commit]"),
            "vcs-exclusion-not-tokenized": v1_ticket(excluded="do not commit this branch"),
        }
        for code, text in cases.items():
            with self.subTest(code=code):
                self.assertIn(
                    code,
                    [finding["code"] for finding in tickets_mod.grade_admission("T1", text, {"T1": text})["findings"]],
                )

    def test_every_stable_pack_binding_is_closed(self):
        cases = {
            "orch-code-pack": "orch-tdd",
            "orch-content-pack": "orch-draft",
            "orch-design-pack": "orch-render",
            "orch-research-pack": "orch-investigate",
        }
        for pack, executor in cases.items():
            with self.subTest(pack=pack):
                text = v1_ticket(pack=pack, executor=executor, isolation="none", excluded="[]")
                self.assertNotIn(
                    "executor-pack-mismatch",
                    [item["code"] for item in tickets_mod.grade_admission("T1", text, {"T1": text})["findings"]],
                )
                wrong = v1_ticket(pack=pack, executor="orch-fixture", isolation="none", excluded="[]")
                self.assertIn(
                    "executor-pack-mismatch",
                    [item["code"] for item in tickets_mod.grade_admission("T1", wrong, {"T1": wrong})["findings"]],
                )
        unknown = v1_ticket(pack="orch-unknown-pack", executor="orch-fixture", isolation="none", excluded="[]")
        self.assertIn(
            "executor-pack-mismatch",
            [item["code"] for item in tickets_mod.grade_admission("T1", unknown, {"T1": unknown})["findings"]],
        )


class SharedPolicyFormatTest(unittest.TestCase):
    def test_mutation_plan_parser_is_exact_and_path_safe(self):
        parsed, defects = tickets_mod.parse_mutations({
            "mutations": ["create:scripts/tool.py", "write:web/src/", "delete:old.txt"],
        })
        self.assertEqual([], defects)
        self.assertEqual(
            [
                {"operation": "create", "path": "scripts/tool.py"},
                {"operation": "write", "path": "web/src/"},
                {"operation": "delete", "path": "old.txt"},
            ],
            parsed,
        )
        for entry in (
            "write:file.txt", "change:folder/", "create:../escape.py",
            "change:scripts/*.py", "rename:a.py", "change:C:\\host.py",
            "change:C:/host.py",
        ):
            with self.subTest(entry=entry):
                _, defects = tickets_mod.parse_mutations({"mutations": [entry]})
                self.assertTrue(defects)

    def test_return_size_clause_result_line_and_counters_have_one_parser(self):
        clause = (
            'status; result; verification\n'
            'return-size: {"counter":"words-v1","maximum":3,'
            '"minimum-complete":"return-fixture","target":"result"}'
        )
        parsed, defects = tickets_mod.parse_return_size(clause)
        self.assertEqual([], defects)
        self.assertEqual("words-v1", parsed["counter"])
        self.assertEqual(3, tickets_mod.count_return_text(" one\ttwo\nthree ", "words-v1"))
        self.assertEqual(2, tickets_mod.count_return_text("one\ntwo\n", "lines-v1"))
        identity, defects = tickets_mod.parse_result_identity(
            'result: {"kind":"artifact","locator":"sink:results/T1.txt","sha256":"' + "a" * 64 + '"}'
        )
        self.assertEqual([], defects)
        self.assertEqual("artifact", identity["kind"])

    def test_return_size_rejects_noncanonical_or_duplicated_constraints(self):
        malformed = [
            'return-size: {"maximum":3,"counter":"words-v1","minimum-complete":"fixture","target":"result"}',
            'return-size: {"counter":"tokens","maximum":3,"minimum-complete":"fixture","target":"result"}',
            'return-size: {"counter":"words-v1","maximum":0,"minimum-complete":"fixture","target":"result"}',
        ]
        for line in malformed:
            with self.subTest(line=line):
                _, defects = tickets_mod.parse_return_size(line)
                self.assertTrue(defects)
        text = v1_ticket().replace(
            "status; result; changed_artifacts; verification; feedback; risks",
            'status; result; verification\nreturn-size: {"counter":"words-v1","maximum":3,"minimum-complete":"fixture","target":"result"}',
        ).replace("Change one observable artifact.", "Change one observable artifact in 3 words.")
        self.assertTrue(any("numeric" in defect for defect in tickets_mod.ticket_defects(text)))
        scalar = text.replace("Change one observable artifact in 3 words.", "Change one observable artifact.")
        scalar = scalar.replace("excluded_actions: [vcs.integrate, vcs.push, vcs.open-pr]", "excluded_actions: limit result to 3 lines")
        self.assertTrue(any("numeric" in defect for defect in tickets_mod.ticket_defects(scalar)))

    def test_authority_duplicates_lowercase_sections_and_nonfinite_json_fail_closed(self):
        duplicate = v1_ticket().replace("status: pending", "status: pending\nstatus: claimed")
        self.assertTrue(any("frontmatter repeats 'status'" in defect for defect in tickets_mod.ticket_defects(duplicate)))
        lowercase = v1_ticket().replace("## Fixed inputs", "## fixed inputs").replace("## Return fields", "## return fields")
        self.assertIn("Fixed inputs", tickets_mod._sections(lowercase))
        self.assertIn("Return fields", tickets_mod._sections(lowercase))
        for encoded in ('{"value":NaN}', '{"value":Infinity}', '{"value":-Infinity}'):
            with self.subTest(encoded=encoded), self.assertRaises(ValueError):
                tickets_format.parse_canonical_json(encoded)


class ResultGradeLifecycleTest(unittest.TestCase):
    def bounded(self, *, maximum=3):
        text = v1_ticket().replace(
            "status; result; changed_artifacts; verification; feedback; risks",
            'status; result; verification\nreturn-size: '
            f'{{"counter":"words-v1","maximum":{maximum},"minimum-complete":"return-fixture","target":"result"}}',
        )
        identity = '{"kind":"artifact","locator":"sink:results/T1.txt","sha256":"' + "a" * 64 + '"}'
        return text.replace("## Result\n", f"## Result\n\nresult: {identity}\n")

    def resolver(self, content):
        module = types.ModuleType("scripts.tickets_inputs")
        module.resolve_identity_payload = lambda **kwargs: {
            "findings": [], "fingerprint": "artifact:a", "bytes": content,
        }
        return module

    def test_result_grade_and_complete_share_exact_findings(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            (tmp / ".git").mkdir()
            run_dir = use_sink(tmp) / "tickets" / "testrun"
            run_dir.mkdir(parents=True)
            path = run_dir / "T1.md"
            path.write_text(self.bounded(), encoding="utf-8")
            with mock.patch.dict(sys.modules, {"scripts.tickets_inputs": self.resolver(b"one two three four")}):
                grade = run_cmd(tmp, "result-grade", "testrun", "T1")
                refused = run_cmd(tmp, "set-status", "testrun", "T1", "complete")
            self.assertEqual(grade["result_grade"]["findings"], refused["findings"])
            self.assertEqual("result-too-large", grade["result_grade"]["findings"][0]["code"])
            self.assertIn("status: pending", path.read_text(encoding="utf-8"))

    def test_exact_maximum_completes_and_failure_status_stays_available(self):
        for status, content in (("complete", b"one two three"), ("limited", b"one two three four")):
            with self.subTest(status=status), tempfile.TemporaryDirectory() as raw:
                tmp = Path(raw)
                (tmp / ".git").mkdir()
                run_dir = use_sink(tmp) / "tickets" / "testrun"
                run_dir.mkdir(parents=True)
                path = run_dir / "T1.md"
                path.write_text(self.bounded(), encoding="utf-8")
                with mock.patch.dict(sys.modules, {"scripts.tickets_inputs": self.resolver(content)}):
                    payload = run_cmd(tmp, "set-status", "testrun", "T1", status)
                self.assertNotIn("error", payload)
                self.assertIn(f"status: {status}", path.read_text(encoding="utf-8"))


class PendingClaimAdmissionTest(unittest.TestCase):
    def test_pending_v1_claim_is_one_atomic_transition(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            baseline = initialize_git_fixture(tmp)
            run_dir = use_sink(tmp) / "tickets" / "testrun"
            run_dir.mkdir(parents=True)
            path = run_dir / "T1.md"
            path.write_text(v1_ticket(baseline=baseline), encoding="utf-8")
            payload = run_cmd(tmp, "claim", "testrun", "T1", "--by", "agent-a")
            self.assertEqual("agent-a", payload["claimed"]["claimed_by"])
            final = path.read_text(encoding="utf-8")
            self.assertIn("status: claimed", final)
            self.assertRegex(final, r"admission: v1:git:sha256:[0-9a-f]{64}")
            self.assertNotIn("status: ready", final)

    def test_ready_and_claim_report_identical_portable_findings(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            baseline = initialize_git_fixture(tmp)
            run_dir = use_sink(tmp) / "tickets" / "testrun"
            run_dir.mkdir(parents=True)
            malformed = v1_ticket(excluded="[vcs.commit]", baseline=baseline)
            (run_dir / "T1.md").write_text(malformed, encoding="utf-8")
            ready = run_cmd(tmp, "ready", "--run", "testrun")
            claim = run_cmd(tmp, "claim", "testrun", "T1", "--by", "agent-a")
            self.assertEqual(ready["skipped"][0]["findings"], claim["findings"])
            self.assertEqual(malformed, (run_dir / "T1.md").read_text(encoding="utf-8"))


class PacketAdmissionBoundaryTest(unittest.TestCase):
    def fixture(self, tmp: Path):
        baseline = initialize_git_fixture(tmp)
        run_dir = use_sink(tmp) / "tickets" / "testrun"
        run_dir.mkdir(parents=True)
        path = run_dir / "T1.md"
        path.write_text(v1_ticket(baseline=baseline), encoding="utf-8")
        return path

    def test_v1_packet_requires_claimed_with_a_current_receipt(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            path = self.fixture(tmp)
            pending = run_cmd(tmp, "packet", "testrun", "T1", "--reply-to", "main")
            self.assertIn("claimed", pending["error"])
            run_cmd(tmp, "claim", "testrun", "T1", "--by", "agent-a")
            admitted = run_cmd(tmp, "packet", "testrun", "T1", "--reply-to", "main")
            self.assertRegex(admitted["packet"]["admission"], r"^v1:git:sha256:[0-9a-f]{64}$")
            tampered = path.read_text(encoding="utf-8").replace(
                "Change one observable artifact.", "Tampered cut-time objective."
            )
            path.write_text(tampered, encoding="utf-8")
            stale = run_cmd(tmp, "packet", "testrun", "T1", "--reply-to", "main")
            self.assertIn("current admission receipt", stale["error"])

    def test_only_an_already_live_v0_claim_gets_the_legacy_marker(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            (tmp / ".git").mkdir()
            run_dir = use_sink(tmp) / "tickets" / "testrun"
            run_dir.mkdir(parents=True)
            legacy = v1_ticket().replace("status: pending", "status: ready")
            legacy = legacy.replace("admission: v1:pending\n", "").replace("cohort: v1:ticket:T1\n", "")
            (run_dir / "T1.md").write_text(legacy, encoding="utf-8")
            refused = run_cmd(tmp, "packet", "testrun", "T1", "--reply-to", "main")
            self.assertIn("re-cut", refused["error"])
            text = (run_dir / "T1.md").read_text(encoding="utf-8")
            text = tickets_mod._set_frontmatter_field(text, "status", "claimed")
            text = tickets_mod._set_frontmatter_field(text, "claimed_by", "legacy-agent")
            text = tickets_mod._set_frontmatter_field(text, "claimed_at", "2026-08-19T00:00:00Z")
            (run_dir / "T1.md").write_text(text, encoding="utf-8")
            packet = run_cmd(tmp, "packet", "testrun", "T1", "--reply-to", "main")
            self.assertEqual("legacy-unadmitted", packet["packet"]["admission"])

    def test_set_status_cannot_bypass_ready_or_claimed(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            path = self.fixture(tmp)
            before = path.read_text(encoding="utf-8")
            for status in ("ready", "claimed"):
                with self.subTest(status=status):
                    payload = run_cmd(tmp, "set-status", "testrun", "T1", status)
                    self.assertIn("admission", payload["error"])
                    self.assertEqual(before, path.read_text(encoding="utf-8"))

    def test_checked_and_suspended_ticket_keeps_its_portable_resume_packet(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            path = self.fixture(tmp)
            path.write_text(path.read_text(encoding="utf-8").replace("independence: gate", "independence: checker"), encoding="utf-8")
            run_cmd(tmp, "claim", "testrun", "T1", "--by", "agent-a")
            checked = run_cmd(tmp, "check", "testrun", "T1", "--by", "checker-a")
            self.assertEqual("checker-a", checked["check"]["checked_by"])
            suspended = run_cmd(tmp, "set-status", "testrun", "T1", "suspended")
            self.assertNotIn("error", suspended)
            packet = run_cmd(tmp, "packet", "testrun", "T1", "--reply-to", "main")
            self.assertNotIn("error", packet)
            self.assertIn("checked_by: checker-a", path.read_text(encoding="utf-8"))
