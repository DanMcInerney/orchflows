"""Single-ticket mechanics after removal of the first-class errand seam."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts import tickets


class OrdinaryNewAuthoringTest(unittest.TestCase):
    def test_new_authors_one_generic_sequenced_code_ticket(self):
        criterion = (
            "The helper is covered | oracle: uv run --no-project python -m unittest "
            "tests.test_helper | oracle_class: deterministic | provenance: authored-here"
        )
        with tempfile.TemporaryDirectory() as directory:
            with mock.patch.dict(
                os.environ, {"ORCHFLOWS_STATE_HOME": directory}, clear=False
            ):
                payload = tickets._dispatch(
                    [
                        "new",
                        "run",
                        "job",
                        "--executor",
                        "orch-tdd",
                        "--sequence",
                        "orch-tdd,orch-build",
                        "--objective",
                        "Repair one bounded helper.",
                        "--criterion",
                        criterion,
                        "--write-scope",
                        "scripts/helper.py,tests/test_helper.py",
                        "--mutation",
                        "change:scripts/helper.py",
                        "--mutation",
                        "create:tests/test_helper.py",
                        "--bound",
                        "30m",
                        "--pack",
                        "orch-code-pack",
                        "--input",
                        '{"name":"request","type":"literal","value":"one ticket"}',
                        "--independence",
                        "checker",
                        "--isolation",
                        "required",
                    ]
                )

            self.assertNotIn("error", payload, payload)
            run_dir = Path(directory) / "tickets" / "run"
            self.assertEqual(["job.md"], sorted(path.name for path in run_dir.glob("*.md")))
            text = (run_dir / "job.md").read_text(encoding="utf-8")
            data = tickets._parse_frontmatter(text)
            self.assertEqual("orch-tdd", data["executor"])
            self.assertEqual(["orch-tdd", "orch-build"], data["sequence"])
            self.assertEqual("orch-code-pack", data["pack"])
            self.assertEqual(
                ["scripts/helper.py", "tests/test_helper.py"], data["write_scope"]
            )
            self.assertEqual("v1:pending", data["admission"])
            self.assertEqual("pending", data["status"])
            self.assertIn(criterion, text)


if __name__ == "__main__":
    unittest.main()
