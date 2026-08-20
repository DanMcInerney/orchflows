"""Regression for the shared projection seam consumed by feature views."""

from tests.test_ui_cases._web import *  # noqa: F401,F403

from scripts.ui_experience import project_experience


class TestExperienceFoundationGap(unittest.TestCase):
    def test_observe_smoke_defaults_to_the_mounted_experience_feed(self):
        smoke = (ROOT / "web" / "src" / "smoke.spec.ts").read_text(encoding="utf-8")
        self.assertIn('process.env.ORCHFLOWS_UI_EXPERIENCE === "1"', smoke)
        self.assertNotIn("const experienceMode = true", smoke)
        start = smoke.index('test("Observe ')
        end = smoke.index('test("compiled experience', start)
        default_contract = smoke[start:end]
        self.assertIn('"/api/v1/experience"', default_contract)
        self.assertIn('`${origin}/runs/run-gamma`', default_contract)
        self.assertIn("status === 304", default_contract)
        self.assertNotIn("revision [0-9a-f]{64}", default_contract)

    def test_ticket_inputs_scope_and_raw_share_the_host_path_boundary(self):
        with tempfile.TemporaryDirectory() as raw:
            root = make_sink(Path(raw), runs=("run-gamma",))
            ticket_path = root / "tickets" / "run-gamma" / "G1.md"
            private_path = r"C:\Users\private\source\input.md"
            ticket_text = ticket_path.read_text(encoding="utf-8").replace(
                "  - scratch/g1.txt", "  - {0}".format(private_path), 1
            )
            ticket_path.write_text(
                ticket_text + "\n## Fixed inputs\n\n- {0}\n".format(private_path),
                encoding="utf-8",
            )

            selected = project_experience(
                root,
                query={"view": "ticket", "run": "run-gamma", "ticket": "G1"},
            )

        ticket = selected["ticket"]
        self.assertEqual(["[redacted-host-path]"], ticket["inputs"])
        self.assertEqual(["[redacted-host-path]"], ticket["write_scope"])
        self.assertNotIn(private_path, ticket["raw"])
        self.assertIn("[redacted-host-path]", ticket["raw"])

    def test_ticket_inputs_redact_host_paths_like_raw_ticket_text(self):
        with tempfile.TemporaryDirectory() as raw:
            root = make_sink(Path(raw), runs=("run-gamma",))
            ticket_path = root / "tickets" / "run-gamma" / "G1.md"
            private_path = r"C:\Users\private\source\input.md"
            ticket_path.write_text(
                ticket_path.read_text(encoding="utf-8")
                + "\n## Fixed inputs\n\n- {0}\n".format(private_path),
                encoding="utf-8",
            )

            selected = project_experience(
                root,
                query={"view": "ticket", "run": "run-gamma", "ticket": "G1"},
            )

        self.assertEqual(["[redacted-host-path]"], selected["ticket"]["inputs"])
        self.assertNotIn(private_path, selected["ticket"]["raw"])

    def test_feature_entries_and_safe_live_fields_share_one_contract(self):
        composition = (
            ROOT / "web" / "src" / "app" / "catalog.ts"
        ).read_text(encoding="utf-8")
        expected_packages = {
            "friction": "friction",
            "inspector": "inspector",
            "now": "now",
            "runMap": "run-map",
            "sessionGraph": "session-graph",
            "sessions": "sessions",
            "workflows": "workflows",
        }
        for alias, package in expected_packages.items():
            self.assertIn(
                'import * as {0} from "../features/{1}"'.format(alias, package),
                composition,
            )
            index = (
                ROOT / "web" / "src" / "features" / package / "index.ts"
            ).read_text(encoding="utf-8")
            self.assertNotIn("defineFeature", index)
            self.assertNotIn("featureCatalog", index)
        self.assertEqual(1, composition.count("defineCatalog(["))
        self.assertNotIn("import.meta.glob", composition)
        shell_reexport = (
            ROOT / "web" / "src" / "app" / "shell" / "featureCatalog.ts"
        ).read_text(encoding="utf-8")
        self.assertEqual(
            'export { featureCatalog } from "../catalog";',
            shell_reexport.strip(),
        )
        self.assertNotIn("import ", shell_reexport)
        self.assertNotIn("defineCatalog", shell_reexport)

        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            root = make_sink(tmp)
            transcripts = make_transcripts(tmp)
            ticket_path = root / "tickets" / "run-gamma" / "G1.md"
            private_paths = (
                str(root),
                r"C:\Users\private\source\ticket.md",
                "/Users/private/source/ticket.md",
            )
            ticket_path.write_text(
                ticket_path.read_text(encoding="utf-8")
                + "\n## Handoff\n\nprivate paths: {0}\n".format(
                    " ".join(private_paths)
                ),
                encoding="utf-8",
            )
            unselected = root / "tickets" / "run-gamma" / "G2.md"
            unselected.write_text(
                unselected.read_text(encoding="utf-8")
                + "\n## Result\n\nunselected-ticket-body-sentinel\n",
                encoding="utf-8",
            )
            before = snapshot(root)

            selected = project_experience(
                root,
                transcripts,
                {
                    "view": "ticket",
                    "run": "run-gamma",
                    "ticket": "G1",
                    "session": TITLED_SESSION,
                },
            )
            history = project_experience(
                root,
                transcripts,
                {"view": "ticket", "run": "run-gamma", "ticket": "G4"},
            )
            malformed = project_experience(
                root,
                transcripts,
                {"view": "run-map", "run": "run-epsilon"},
            )
            self.assertEqual(before, snapshot(root))

        run_keys = {
            "id", "ticket_count", "active", "objective", "repository", "client",
            "last_activity", "unreadable", "tickets",
        }
        self.assertTrue(selected["runs"])
        for run in selected["runs"]:
            self.assertEqual(run_keys, set(run))
            self.assertIsInstance(run["objective"], str)
            self.assertIsInstance(run["repository"], str)
            self.assertIsInstance(run["client"], str)
            self.assertIsInstance(run["last_activity"], str)
            self.assertIsInstance(run["unreadable"], bool)
            self.assertIsInstance(run["tickets"], list)

        readiness_causes = {
            "pending_dependency", "suspended_handoff", "failed_upstream",
            "blocked_upstream", "stale_claim", "malformed_topology", "none",
        }
        self.assertTrue(malformed["run"]["diagnostics"])
        for diagnostic in malformed["run"]["diagnostics"]:
            self.assertEqual({"kind", "ticket_ids", "message"}, set(diagnostic))
            self.assertIn(
                diagnostic["kind"],
                {"cycle", "dangling", "duplicate", "unreadable", "inferred_session_edge"},
            )
            self.assertIsInstance(diagnostic["ticket_ids"], list)
        for ticket in malformed["run"]["tickets"]:
            readiness = ticket["readiness"]
            self.assertEqual(
                {"state", "dependencies", "explanation", "cause", "causal_chain"},
                set(readiness),
            )
            self.assertIn(readiness["cause"], readiness_causes)
            self.assertIsInstance(readiness["causal_chain"], list)

        ticket = selected["ticket"]
        self.assertEqual(["scratch/g1.txt"], ticket["write_scope"])
        self.assertIsInstance(ticket["inputs"], list)
        self.assertIsInstance(ticket["pack"], str)
        self.assertIsInstance(ticket["history"], list)
        self.assertIn("## Objective", ticket["raw"])
        self.assertNotIn("unselected-ticket-body-sentinel", ticket["raw"])
        for private_path in private_paths:
            self.assertNotIn(private_path, ticket["raw"])
        self.assertIn("[redacted-host-path]", ticket["raw"])
        proof_rows = ticket["verification"]["rows"]
        self.assertTrue(proof_rows)
        self.assertTrue(
            all(
                set(row) == {"#", "verdict", "oracle", "class", "evidence"}
                for row in proof_rows
            )
        )

        self.assertEqual(
            ["tool_post", "tool_pre"],
            [item["event"] for item in history["ticket"]["history"]],
        )
        for item in history["ticket"]["history"]:
            self.assertEqual({"ts", "event", "agent", "detail"}, set(item))

        for session in selected["sessions"]["items"]:
            self.assertIsInstance(session["client"], str)
            self.assertIsInstance(session["project"], str)
            self.assertFalse(any(mark in session["project"] for mark in ("/", "\\", ":")))
            self.assertIsInstance(session["modified"], str)

        session = selected["session"]
        self.assertEqual(
            {"id", "title", "modified", "agent_count", "diagnostics", "agents"},
            set(session),
        )
        for agent in session["agents"]:
            self.assertEqual(
                {"id", "type", "depth", "parent", "modified", "state", "evidence", "unreadable"},
                set(agent),
            )

        friction = selected["friction"]
        self.assertEqual({"items", "skipped", "unreadable"}, set(friction))
        for item in friction["items"]:
            self.assertTrue(
                set(item).issubset(
                    {"ts", "host", "observed", "expected", "run", "ticket"}
                )
            )


if __name__ == "__main__":
    unittest.main()
