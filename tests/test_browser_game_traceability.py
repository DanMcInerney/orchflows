"""PJ-21 structural traceability for the browser-game composition."""

from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from tools.validate_support import browser_game
from tools.validate_support.packages import Diagnostics
import tools.validate as validate


ROOT = Path(__file__).resolve().parents[1]

# BGW-TRACE[traceability|PJ-21]
# BGW-TRACE[program-record|PJ-03,PJ-07]
# BGW-TRACE[question-authority|PJ-06,PJ-09,PJ-10]
# BGW-TRACE[checkpoint-disposition|PJ-05]
# BGW-TRACE[experiment-validity|PJ-16,PJ-17]
# BGW-TRACE[kind-separation|AUTH-05,PJ-18,PJ-28]
# BGW-TRACE[closed-surface|PJ-20]
# BGW-TRACE[decision-safety|PJ-22]
# BGW-TRACE[conditional-fidelity|PJ-23]
# BGW-TRACE[evidence-identity|PJ-08,PJ-24]
# BGW-TRACE[revalidation|PJ-25]
# BGW-TRACE[migration|PJ-01,PJ-26,U-03]


class BrowserGameTraceabilityTests(unittest.TestCase):
    def _copy_tree(self) -> Path:
        temporary = Path(tempfile.mkdtemp(prefix="browser-game-trace-"))
        self.addCleanup(shutil.rmtree, temporary, True)
        for relative in (
            Path("compositions/browser-game"),
            Path("compositions/references/browser-game-program-record.schema.json"),
            Path("tests/test_browser_game_traceability.py"),
        ):
            source = ROOT / relative
            target = temporary / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            if source.is_dir():
                shutil.copytree(source, target, dirs_exist_ok=True)
            else:
                shutil.copy2(source, target)
        return temporary

    def _findings(self, root: Path) -> list[str]:
        diag = Diagnostics()
        browser_game.validate_browser_game_traceability(diag, root=root)
        return [line for line in diag.lines() if line.startswith("ERROR")]

    def test_real_composition_has_a_closed_traceability_seam(self):
        self.assertEqual([], self._findings(ROOT))

    def test_implemented_behavior_without_a_normative_identity_is_rejected(self):
        root = self._copy_tree()
        manifest_path = root / "compositions/browser-game/traceability.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["behaviors"][0]["identities"] = []
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

        findings = self._findings(root)

        self.assertTrue(any("normative identity" in line for line in findings), findings)

    def test_test_or_help_identity_disagreement_is_rejected(self):
        root = self._copy_tree()
        test_path = root / "tests/test_browser_game_traceability.py"
        text = test_path.read_text(encoding="utf-8")
        test_path.write_text(
            text.replace(
                "BGW-TRACE[" + "checkpoint-disposition|PJ-05]",
                "BGW-TRACE[" + "checkpoint-disposition|PJ-24]",
            ),
            encoding="utf-8",
        )

        findings = self._findings(root)

        self.assertTrue(any("checkpoint-disposition" in line and "test" in line for line in findings), findings)

    def test_governed_minimum_schema_field_cannot_be_removed(self):
        root = self._copy_tree()
        schema_path = root / "compositions/references/browser-game-program-record.schema.json"
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        required = schema["$defs"]["releaseContractRevision"]["required"]
        required.remove("recovery")
        schema_path.write_text(json.dumps(schema, indent=2) + "\n", encoding="utf-8")

        findings = self._findings(root)

        self.assertTrue(any("release_contracts" in line and "recovery" in line for line in findings), findings)

    def test_governing_identity_on_schema_row_cannot_drift(self):
        root = self._copy_tree()
        schema_path = root / "compositions/references/browser-game-program-record.schema.json"
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        schema["$defs"]["qaOracleRevision"]["x-governing-identities"] = ["PJ-24"]
        schema_path.write_text(json.dumps(schema, indent=2) + "\n", encoding="utf-8")

        findings = self._findings(root)

        self.assertTrue(any("qa_oracle_map" in line and "governing identities" in line for line in findings), findings)

    def test_repository_validator_runs_the_browser_game_audit(self):
        root = self._copy_tree()
        schema_path = root / "compositions/references/browser-game-program-record.schema.json"
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        schema["$defs"]["releaseContractRevision"]["required"].remove("recovery")
        schema_path.write_text(json.dumps(schema, indent=2) + "\n", encoding="utf-8")
        saved = validate.ROOT
        try:
            validate.ROOT = root
            findings = validate.run_validation().lines()
        finally:
            validate.ROOT = saved

        self.assertTrue(any("release_contracts" in line and "recovery" in line for line in findings), findings)


if __name__ == "__main__":
    unittest.main()
