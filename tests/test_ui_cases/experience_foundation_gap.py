"""Regression for the shared projection seam consumed by feature views."""

from tests.test_ui_cases._base import *  # noqa: F401,F403

from scripts.ui_experience import project_experience


class TestExperienceFoundationGap(unittest.TestCase):
    def test_feature_entries_and_safe_live_fields_share_one_contract(self):
        registry = (ROOT / "web" / "src" / "app" / "registry.ts").read_text(
            encoding="utf-8"
        )
        self.assertIn(
            'import.meta.glob<ViewModule>("../views/*.tsx", { eager: true })',
            registry,
        )
        self.assertIn(
            'import.meta.glob<ViewModule>("../features/*/index.tsx", { eager: true })',
            registry,
        )

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
            {"id", "title", "client", "project", "modified", "agent_count", "diagnostics", "agents"},
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
                    {"ts", "category", "host", "observed", "expected", "run", "ticket"}
                )
            )


if __name__ == "__main__":
    unittest.main()
