"""Cross-layer contract for the rendered observability experience substrate."""

import hashlib
import json

from reader.tests.test_ui_cases._web import *  # noqa: F401,F403

import reader.scripts.ui_experience as experience
import reader.scripts.ui_readiness as readiness
from reader.scripts.ui_sessions import DIAGNOSTIC_UNDECODABLE_SLUG


class ExperienceFoundationContractTests(unittest.TestCase):
    def test_modularization_spec_is_the_accepted_content_with_locator_repairs(self):
        path = ROOT / "docs" / "ui" / "modularization.md"
        implemented = path.read_bytes()

        self.assertNotIn(
            b"../../web/src/features/session-graph/index.tsx)", implemented
        )
        self.assertEqual(
            "A2B5BDABC873C3B376DC9A339AE0AAA441C7EDB94FFBDEA435A500AA6D5CF13E",
            hashlib.sha256(implemented).hexdigest().upper(),
        )

    def test_workflows_spec_preserves_accepted_content_with_locator_repairs(self):
        path = ROOT / "docs" / "ui" / "workflows.md"
        implemented = path.read_bytes()

        self.assertNotIn(b"](../../web/src/api/schema.ts)", implemented)
        self.assertNotIn(b"](../../web/src/state/location.ts)", implemented)
        reconstructed = implemented.replace(
            b"`ExperienceSnapshot` schema (`web/src/api/schema.ts`)",
            b"[`ExperienceSnapshot` schema](../../web/src/api/schema.ts)",
        ).replace(
            b"current routes (`web/src/state/location.ts`)",
            b"[current routes](../../web/src/state/location.ts)",
        ).replace(
            b"schema (`web/src/api/schema.ts`)",
            b"[schema](../../web/src/api/schema.ts)",
        )
        self.assertEqual(
            "700B76400D43D796249C343902D0AE153B99E9967FDCCC56499DE9FD0C7D167C",
            hashlib.sha256(reconstructed).hexdigest().upper(),
        )

    def test_architecture_names_live_ui_owners_and_workflow_routes(self):
        architecture = (ROOT / "ARCHITECTURE.md").read_text(encoding="utf-8")

        for deleted in (
            "web/src/api",
            "web/src/state",
            "web/src/graph",
            "web/src/testing",
            "Workflows remains a route-free",
        ):
            self.assertNotIn(deleted, architecture)
        for owner in (
            "[`reader/`](reader/) owns the Observe browser",
            "reader/web/src/features/workflows/view/SummaryFlow.tsx",
            "reader/scripts/ui_api.py",
        ):
            self.assertIn(owner, architecture)

    def test_session_slug_diagnostic_keeps_legacy_identity_but_api_is_path_safe(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            root = make_sink(tmp)
            transcripts = make_transcripts(tmp)
            raw = experience.read_sessions(transcripts)["diagnostics"]
            projected = experience.project_experience(root, transcripts)["sessions"]["diagnostics"]

        diagnostic = DIAGNOSTIC_UNDECODABLE_SLUG
        self.assertIn("{0}: {1}".format(diagnostic, UNDECODABLE_PROJECT), raw)
        self.assertIn(diagnostic, projected)
        self.assertNotIn(UNDECODABLE_PROJECT, json.dumps(projected, sort_keys=True))

    def test_safe_projection_tokens_shell_and_manifest_form_one_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            root = make_sink(tmp)
            transcripts = make_transcripts(tmp)
            before = snapshot(root)
            projected = experience.project_experience(
                root,
                transcripts,
                {
                    "view": "ticket",
                    "run": "run-gamma",
                    "ticket": "G1",
                    "state": "raw-escaped",
                },
            )
            expected_readiness = readiness.explain_run(
                experience.run_tickets(root, "run-gamma")
            )["G1"]
            self.assertEqual(before, snapshot(root))

        self.assertEqual("orchflows.experience.v1", projected["schema"])
        self.assertEqual(
            ["now", "run-map", "create", "sessions", "friction"],
            [item["id"] for item in projected["navigation"]],
        )
        self.assertEqual(
            ["Now", "Workflows", "Create", "Sessions", "Friction"],
            [item["label"] for item in projected["navigation"]],
        )
        create = projected["navigation"][2]
        self.assertTrue(create["disabled"])
        self.assertIn("future", create["explanation"].lower())
        self.assertEqual(
            {"view": "ticket", "run": "run-gamma", "ticket": "G1", "session": ""},
            projected["selection"],
        )
        selected = projected["ticket"]
        self.assertEqual("G1", selected["id"])
        self.assertEqual("rows", selected["verification"]["state"])
        self.assertEqual(["PASS", "PASS", "FAIL"], [row["verdict"] for row in selected["verification"]["rows"]])
        self.assertEqual(
            expected_readiness,
            {key: selected["readiness"][key] for key in expected_readiness},
        )
        self.assertEqual("none", selected["readiness"]["cause"])
        self.assertEqual([], selected["readiness"]["causal_chain"])
        encoded = json.dumps(projected, sort_keys=True)
        self.assertNotIn(TRANSCRIPT_SENTINEL, encoded)
        self.assertNotIn(str(root), encoded)
        self.assertNotIn(str(transcripts), encoded)
        self.assertNotIn("not-an-encoded-path", encoded)
        self.assertNotIn("toolu_alpha_01", encoded)
        self.assertNotIn("file-history", encoded)

        manifest = json.loads((ROOT / "reader" / "docs" / "view-manifest.json").read_text(encoding="utf-8"))
        states = {
            "now": ["mixed-live", "needs-attention", "no-active-runs", "unreadable-data", "live-paused", "empty"],
            "run-map": ["summary-active", "full-collapsed", "full-expanded", "blocked-causal", "completed", "malformed-topology"],
            "ticket": ["running-overview", "proof-pass", "proof-fail", "friction-present", "history-unavailable", "raw-escaped"],
            "sessions": ["populated", "empty", "diagnostic"],
            "session-graph": ["populated", "diagnostic"],
            "friction": ["populated", "empty"],
            "workflow-catalog": ["populated", "empty"],
            "workflow-detail": ["unreadable", "complex-loop", "callable"],
            "workflow-source": ["missing-source", "unreadable-source"],
        }
        expected = {
            "{0}--{1}--{2}".format(view, state, breakpoint)
            for view, view_states in states.items()
            for state in view_states
            for breakpoint in ("wide", "compact")
        }
        self.assertEqual("orchflows.view-manifest.v1", manifest["schema"])
        self.assertEqual({"wide": [1440, 1024], "compact": [1024, 768]}, manifest["breakpoints"])
        self.assertEqual(expected, {item["identity"] for item in manifest["views"]})
        self.assertEqual(64, len(manifest["views"]))
        for item in manifest["views"]:
            self.assertEqual(item["identity"], "{view}--{state}--{breakpoint}".format(**item))
            self.assertTrue(item["path"].startswith("/"))
            self.assertIn("fixture=" + item["state"], item["path"])

        tokens = (ROOT / "reader" / "web" / "src" / "styles" / "tokens.css").read_text(encoding="utf-8")
        for token in (
            "--canvas: #090b10", "--surface-1: #11151d", "--space-1: 4px",
            "--space-4: 16px", "--radius-card: 12px", "--row-compact: 44px",
            "--status-running: #22d3ee", "--status-failed: #fb7185",
            "--type-2xs: 10px", "--type-base: 14px", "--type-display: clamp(26px, 3vw, 40px)",
            "--privacy-border: #293b43", "--status-border-attention: #92400e",
        ):
            self.assertIn(token, tokens)
        self.assertNotIn("linear-gradient", tokens)
        self.assertNotIn("backdrop-filter", tokens)

        sessions_css = (ROOT / "reader" / "web" / "src" / "features" / "sessions" / "sessions.css").read_text(encoding="utf-8")
        now_css = (ROOT / "reader" / "web" / "src" / "features" / "now" / "now.css").read_text(encoding="utf-8")
        self.assertIn("background: var(--attention-surface)", sessions_css)
        self.assertNotIn("color-mix", sessions_css)
        self.assertNotIn("border-radius: 8px", now_css)
        self.assertGreaterEqual(now_css.count("border-radius: var(--radius-control)"), 3)

        app = (ROOT / "reader" / "web" / "src" / "ObserveApp.tsx").read_text(encoding="utf-8")
        shell = (ROOT / "reader" / "web" / "src" / "app" / "shell" / "Shell.tsx").read_text(encoding="utf-8")
        composition = (ROOT / "reader" / "web" / "src" / "app" / "shell" / "featureCatalog.ts").read_text(encoding="utf-8")
        application_catalog = (ROOT / "reader" / "web" / "src" / "app" / "catalog.ts").read_text(encoding="utf-8")
        harness = (ROOT / "reader" / "tools" / "ui_frontend.py").read_text(encoding="utf-8")
        experience_harness = (ROOT / "reader" / "web" / "src" / "smoke.spec.ts").read_text(encoding="utf-8")
        self.assertEqual('import { Shell } from "./app/shell/Shell";\n\nexport function ObserveApp() {\n  return <Shell />;\n}\n', app)
        self.assertIn('data-mode="observe"', shell)
        self.assertIn("read only", shell.lower())
        self.assertIn('import { featureCatalog } from "./featureCatalog"', shell)
        self.assertNotIn("FALLBACK", shell)
        for removed in (
            ROOT / "reader" / "web" / "src" / "app" / "registry.ts",
            ROOT / "reader" / "web" / "src" / "state" / "location.ts",
            ROOT / "reader" / "web" / "src" / "api" / "schema.ts",
            ROOT / "reader" / "web" / "src" / "api" / "client.ts",
            ROOT / "reader" / "web" / "src" / "feed.ts",
        ):
            self.assertFalse(removed.exists(), str(removed))
        self.assertNotIn("import.meta.glob", composition)
        self.assertEqual('export { featureCatalog } from "../catalog";\n', composition)
        self.assertIn("export const featureCatalog = defineCatalog([", application_catalog)
        self.assertEqual(9, application_catalog.count("defineFeature({"))
        self.assertNotIn("bindWorkflowDefinitions", application_catalog)
        self.assertIn('navigation: { label: "Workflows", home: { fixture: "" } }', application_catalog)
        for path in (
            "/workflows",
            "/workflows/evolve",
            "/workflows/evolve/sources/src_campaign",
        ):
            self.assertTrue(experience.is_spa_path(path), path)
        for command in ('add_parser("capture")', 'add_parser("audit")', 'add_parser("diff")'):
            self.assertIn(command, harness)
        for scenario in ("200% zoom-equivalent reflow", "forced-colors: active", "prefers-reduced-motion: reduce", "expectKeyboardParity"):
            self.assertIn(scenario, experience_harness)


class ExperienceProjectionTest(unittest.TestCase):
    def test_execution_provenance_requires_explicit_associations_and_mechanical_judgment(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_sink(Path(tmp), runs=(), friction=False, events=False)
            associated = root / "tickets" / "run-associated"
            inferred = root / "tickets" / "evolve-by-name"
            ticket = write_ticket(
                associated,
                "01-judge",
                status="complete",
                executor="orch-critique",
                depends_on="[]",
            )
            ticket.write_text(
                ticket.read_text(encoding="utf-8")
                + "\n## Result\n\naccepted revision deadbeef\n\n"
                + "## Verification\n\n"
                + "| # | Verdict | Oracle | Class | Evidence |\n"
                + "| --- | --- | --- | --- | --- |\n"
                + "| 1 | PASS | code craft lens | judged | review:42 |\n\n"
                + "## Feedback\n\n[]\n\n"
                + "## Risks\n\n[]\n",
                encoding="utf-8",
            )
            rationale_id = "art_" + "a" * 43
            rationale_ticket = write_ticket(
                associated,
                "02-rationale",
                status="complete",
                executor="orch-critique",
                depends_on="[01-judge]",
            )
            rationale_ticket.write_text(
                rationale_ticket.read_text(encoding="utf-8")
                + "\n## Rationale\n\n"
                + json.dumps({"kind": "artifact", "id": rationale_id})
                + "\n",
                encoding="utf-8",
            )
            write_ticket(
                inferred,
                "01-evolve",
                status="claimed",
                executor="orch-evolve",
                depends_on="[]",
            )
            identity = root / "runs" / "run-associated" / "run.json"
            identity.parent.mkdir(parents=True)
            identity.write_text(
                json.dumps({
                    "run": "run-associated",
                    "workflow": "evolve",
                    "project": {"root": "C:/private/project"},
                    "workspaces": [{"path": "C:/private/worktree"}],
                }),
                encoding="utf-8",
            )

            projected = experience.project_experience(
                root,
                query={"view": "ticket", "run": "run-associated", "ticket": "01-judge"},
            )
            with_rationale = experience.project_experience(
                root,
                query={"view": "ticket", "run": "run-associated", "ticket": "02-rationale"},
            )

        runs = {run["id"]: run for run in projected["runs"]}
        self.assertEqual(
            {"state": "available", "id": "evolve"},
            runs["run-associated"]["workflow"],
        )
        self.assertEqual(
            {"state": "unavailable", "id": ""},
            runs["evolve-by-name"]["workflow"],
        )
        judgment = projected["ticket"]["judgment"]
        self.assertEqual(
            [{
                "criterion": "1",
                "verdict": "PASS",
                "oracle": "code craft lens",
                "oracle_class": "judged",
                "evidence": "review:42",
            }],
            judgment["criteria"],
        )
        self.assertEqual("accepted revision deadbeef", judgment["result"])
        self.assertEqual("[]", judgment["feedback"])
        self.assertEqual("[]", judgment["risks"])
        self.assertEqual(
            {"state": "unavailable", "identity": None},
            judgment["rationale"],
        )
        self.assertEqual(
            {"state": "available", "identity": {"kind": "artifact", "id": rationale_id}},
            with_rationale["ticket"]["judgment"]["rationale"],
        )
        encoded = json.dumps(projected, sort_keys=True)
        self.assertNotIn("C:/private/project", encoded)
        self.assertNotIn("C:/private/worktree", encoded)


if __name__ == "__main__":
    unittest.main()
