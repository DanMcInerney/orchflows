"""Cross-layer contract for the rendered observability experience substrate."""

import hashlib

from tests.test_ui_cases._web import *  # noqa: F401,F403

import scripts.ui_experience as experience
import scripts.ui_readiness as readiness
from scripts.ui_sessions import DIAGNOSTIC_UNDECODABLE_SLUG


class ExperienceFoundationContractTests(unittest.TestCase):
    def test_modularization_spec_is_the_accepted_content_with_locator_repairs(self):
        path = ROOT / "docs" / "ui" / "modularization.md"
        implemented = path.read_bytes()

        self.assertNotIn(
            b"../../web/src/features/session-graph/index.tsx)", implemented
        )
        self.assertEqual(
            "6AEF8758EBEC2DCB6C117A6A566FB0843B6061AF6CE3441278869E7A462AF303",
            hashlib.sha256(implemented).hexdigest().upper(),
        )

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

        manifest = json.loads((ROOT / "docs" / "ui" / "view-manifest.json").read_text(encoding="utf-8"))
        states = {
            "now": ["mixed-live", "needs-attention", "no-active-runs", "unreadable-data", "live-paused"],
            "run-map": ["summary-active", "full-collapsed", "full-expanded", "blocked-causal", "completed", "malformed-topology"],
            "ticket": ["running-overview", "proof-pass", "proof-fail", "friction-present", "history-unavailable", "raw-escaped"],
            "sessions": ["populated", "empty", "diagnostic"],
            "session-graph": ["populated", "diagnostic"],
            "friction": ["populated", "empty"],
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
        self.assertEqual(48, len(manifest["views"]))
        for item in manifest["views"]:
            self.assertEqual(item["identity"], "{view}--{state}--{breakpoint}".format(**item))
            self.assertTrue(item["path"].startswith("/"))
            self.assertIn("fixture=" + item["state"], item["path"])

        tokens = (ROOT / "web" / "src" / "styles" / "tokens.css").read_text(encoding="utf-8")
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

        sessions_css = (ROOT / "web" / "src" / "features" / "sessions" / "sessions.css").read_text(encoding="utf-8")
        now_css = (ROOT / "web" / "src" / "features" / "now" / "now.css").read_text(encoding="utf-8")
        self.assertIn("background: var(--attention-surface)", sessions_css)
        self.assertNotIn("color-mix", sessions_css)
        self.assertNotIn("border-radius: 8px", now_css)
        self.assertGreaterEqual(now_css.count("border-radius: var(--radius-control)"), 3)

        app = (ROOT / "web" / "src" / "ObserveApp.tsx").read_text(encoding="utf-8")
        shell = (ROOT / "web" / "src" / "app" / "shell" / "Shell.tsx").read_text(encoding="utf-8")
        composition = (ROOT / "web" / "src" / "app" / "shell" / "featureCatalog.ts").read_text(encoding="utf-8")
        harness = (ROOT / "tools" / "ui_frontend.py").read_text(encoding="utf-8")
        experience_harness = (ROOT / "web" / "src" / "smoke.spec.ts").read_text(encoding="utf-8")
        self.assertEqual('import { Shell } from "./app/shell/Shell";\n\nexport function ObserveApp() {\n  return <Shell />;\n}\n', app)
        self.assertIn('data-mode="observe"', shell)
        self.assertIn("read only", shell.lower())
        self.assertIn('import { featureCatalog } from "./featureCatalog"', shell)
        self.assertNotIn("FALLBACK", shell)
        for removed in (
            ROOT / "web" / "src" / "app" / "registry.ts",
            ROOT / "web" / "src" / "state" / "location.ts",
            ROOT / "web" / "src" / "api" / "schema.ts",
            ROOT / "web" / "src" / "api" / "client.ts",
            ROOT / "web" / "src" / "feed.ts",
        ):
            self.assertFalse(removed.exists(), str(removed))
        self.assertNotIn("import.meta.glob", composition)
        self.assertEqual(6, composition.count("defineFeature({"))
        for command in ('add_parser("capture")', 'add_parser("audit")', 'add_parser("diff")'):
            self.assertIn(command, harness)
        for scenario in ("200% zoom-equivalent reflow", "forced-colors: active", "prefers-reduced-motion: reduce", "expectKeyboardParity"):
            self.assertIn(scenario, experience_harness)


if __name__ == "__main__":
    unittest.main()
