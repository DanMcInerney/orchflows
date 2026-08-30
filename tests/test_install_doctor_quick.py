"""``install.py doctor --quick`` grades freshness without building the plan.

The full sweep in `tests/test_install_doctor.py` compares a whole desired
plan with disk. The quick verdict compares two facts -- the receipt's
`source_commit` and the installed instruction block -- so its cases fake
exactly those two and patch `build_plan` to raise: a quick path that needed
a plan fails here rather than quietly costing what the sweep costs.
"""

from __future__ import annotations

import hashlib
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

import install
from installer import doctor


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()



class TestQuickDoctor(unittest.TestCase):
    """``doctor --quick`` answers freshness without building the plan.

    The two facts it grades are the receipt's ``source_commit`` and the
    installed instruction block, so every case here fakes exactly those two
    and nothing else: a quick verdict that needed a plan would fail here by
    raising out of the patched ``build_plan``.
    """

    BLOCK = "<!-- BEGIN ORCHFLOWS -->\nbody\n<!-- END ORCHFLOWS -->\n"

    def _installed(self, *, commit="abc123", block=None, receipt_block=None):
        directory = tempfile.TemporaryDirectory(prefix="quick-doctor-")
        self.addCleanup(directory.cleanup)
        home = Path(directory.name)
        block_path = home / "host-block.md"
        block_path.write_text(self.BLOCK if block is None else block, encoding="utf-8")
        entries = []
        if receipt_block is not False:
            entries.append(
                {
                    "path": str(block_path),
                    "kind": "host-block",
                    "sha256": _sha256(block_path) if receipt_block is None else receipt_block,
                }
            )
        (home / "receipt.json").write_text(
            json.dumps({"version": 4, "source_commit": commit, "files": entries}),
            encoding="utf-8",
        )
        return home

    def _report(self, home: Path, *, commit="abc123", rendered=None):
        with patch(
            "installer.doctor._scope_home", return_value=home
        ), patch(
            "installer.doctor._host_block_content",
            return_value=(self.BLOCK if rendered is None else rendered, "s", "e"),
        ):
            return doctor.quick_report(commit)

    def test_a_matching_receipt_and_host_block_read_as_current(self):
        report = self._report(self._installed())
        self.assertEqual("coherent", report["status"])
        self.assertEqual([], report["findings"])
        self.assertIn("is current", report["summary"])

    def test_a_moved_source_commit_is_stale_and_names_the_reinstall(self):
        report = self._report(self._installed(commit="old111"))
        self.assertEqual("drift", report["status"])
        self.assertEqual(["receipt.source-commit"], [item["id"] for item in report["findings"]])
        self.assertIn(doctor.QUICK_REINSTALL, report["summary"])
        self.assertEqual(1, len(report["summary"].splitlines()))

    def test_a_checkout_whose_host_block_moved_is_stale(self):
        report = self._report(self._installed(), rendered=self.BLOCK + "one more law\n")
        self.assertEqual(["configuration.content"], [item["id"] for item in report["findings"]])

    def test_an_edited_installed_block_is_caught_by_the_receipt_hash(self):
        home = self._installed(receipt_block="0" * 64)
        self.assertEqual(
            ["receipt.hash"], [item["id"] for item in self._report(home)["findings"]]
        )

    def test_a_deleted_block_and_a_missing_receipt_each_report_themselves(self):
        home = self._installed()
        (home / "host-block.md").unlink()
        self.assertEqual(
            ["configuration.missing"], [item["id"] for item in self._report(home)["findings"]]
        )
        (home / "receipt.json").unlink()
        self.assertEqual(
            ["receipt.missing"], [item["id"] for item in self._report(home)["findings"]]
        )

    def test_a_receipt_that_never_recorded_the_block_is_named(self):
        home = self._installed(receipt_block=False)
        self.assertEqual(
            ["receipt.missing-entry"], [item["id"] for item in self._report(home)["findings"]]
        )

    def test_the_cli_exits_by_verdict_without_building_the_plan_or_writing(self):
        home = self._installed(commit="old111")
        before = sorted((path.name, path.read_bytes()) for path in home.iterdir())
        with patch.object(
            install, "resolve_source_commit", return_value="abc123"
        ), patch.object(
            install, "build_plan", side_effect=AssertionError("quick must not build the plan")
        ), patch(
            "installer.doctor._scope_home", return_value=home
        ), patch(
            "installer.doctor._host_block_content", return_value=(self.BLOCK, "s", "e")
        ):
            output = io.StringIO()
            with redirect_stdout(output):
                exit_code = install.main(["doctor", "--quick"])

        self.assertEqual(1, exit_code)
        printed = output.getvalue().splitlines()
        self.assertEqual(1, len(printed), printed)
        self.assertIn(doctor.QUICK_REINSTALL, printed[0])
        self.assertEqual(before, sorted((path.name, path.read_bytes()) for path in home.iterdir()))

    def test_the_quick_flag_alone_still_means_doctor(self):
        with patch.object(
            install, "resolve_source_commit", return_value="abc123"
        ), patch.object(
            install, "build_plan", side_effect=AssertionError("quick must not build the plan")
        ), patch(
            "installer.doctor._scope_home", return_value=self._installed()
        ), patch(
            "installer.doctor._host_block_content", return_value=(self.BLOCK, "s", "e")
        ):
            with redirect_stdout(io.StringIO()):
                self.assertEqual(0, install.main(["--quick"]))



if __name__ == "__main__":
    unittest.main()
