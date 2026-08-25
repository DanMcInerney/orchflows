"""Compatibility seam for the validation regression collection."""
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import tools.validate as validate  # noqa: E402

from tests.test_validate_cases.contract_pins import (  # noqa: F401
    ContractPinIsNewlineInsensitiveTest,
)
from tests.test_validate_cases.sink_contracts import (
    TestContractsNameTheSink,
    TestWorkItemLocationInvariant,
    TestWorklogStatesRunIdentity,
)
from tests.test_validate_cases.sink_law import (
    TestFrictionFallbackNamesTheSink,
    TestOnlyCanaryAndBinMentionsSurvive,
    TestOneProseOwnerForThePath,
    TestRepositoryKeepsTwoSubdirectories,
    TestSelfImproveSelectsByScopeAndProject,
    TestTheLawNamesTheSinkRoot,
    TestVocabularyResolvesToTheSink,
)
from tests.test_validate_cases.validator_ownership import (
    CrossTierDuplicationTest,
    FrictionLocationSyncTest,
    TestPackAdmissionRegistryAgainstPacks,
    TestPackWorkspaceTableAgainstPacks,
    TestSyncCheckIsGone,
)

class TestDocumentedPathsResolveInTheInstalledTree(unittest.TestCase):
    """Every backticked library-internal path in shipped prose names a file
    the installer actually produces.

    Six friction entries across three sessions record executors walking from
    shipped prose into `~/.orchflows/lib/scripts/tickets.py` and `lib/tests`
    -- paths the prose names and the installed tree does not carry, because
    scripts land flat in `bin/` and the repository's own `tools/` and
    `tests/` ship nowhere. The reader was not wrong; the doc was. This is
    `validate_names`' law one namespace over: backticks are a reference that
    has to resolve, plain text is how prose mentions without pointing.
    """

    def _tree(self, doc_body: str) -> Path:
        root = Path(tempfile.mkdtemp(prefix="worker-opus-c01-"))
        self.addCleanup(shutil.rmtree, root, True)
        # ARCHITECTURE.md is the marker that says "this tree is the library",
        # the same guard validate_names uses to skip an isolated fixture.
        (root / "ARCHITECTURE.md").write_text("# marker\n", encoding="utf-8")
        (root / "rules").mkdir()
        (root / "rules" / "verification.md").write_text("# rules\n", encoding="utf-8")
        (root / "scripts").mkdir()
        (root / "scripts" / "tickets.py").write_text("# script\n", encoding="utf-8")
        (root / "tools").mkdir()
        (root / "tools" / "validate.py").write_text("# compiler\n", encoding="utf-8")
        (root / "docs").mkdir()
        (root / "docs" / "probe.md").write_text(doc_body, encoding="utf-8")
        return root

    def _findings(self, doc_body: str):
        root = self._tree(doc_body)
        saved = validate.ROOT
        try:
            validate.ROOT = root
            diag = validate.Diagnostics()
            validate.validate_documented_paths(diag)
        finally:
            validate.ROOT = saved
        return [line for line in diag.lines() if line.startswith("ERROR")]

    def test_a_path_the_installer_never_produces_is_an_error(self):
        """The compiler lives in the checkout, not under lib/. A shipped doc
        that backticks it sends every installed reader to a dead path."""

        findings = self._findings("The oracle is `tools/validate.py`.\n")
        self.assertTrue(
            any("tools/validate.py" in line for line in findings),
            f"expected a finding for the uninstalled path, got {findings}",
        )

    def test_the_test_directory_is_an_error(self):
        """`lib/tests` is the second path the friction record names."""

        findings = self._findings("Canonical bytes live in `tests/pins.json`.\n")
        self.assertTrue(
            any("tests/pins.json" in line for line in findings),
            f"expected a finding for the uninstalled tests path, got {findings}",
        )

    def test_an_installed_library_path_resolves(self):
        self.assertEqual([], self._findings("See `rules/verification.md` for the law.\n"))

    def test_a_script_resolves_through_the_installers_bin_mapping(self):
        """`scripts/<name>.py` installs flat at `bin/<name>.py`; the check
        carries the installer's mapping rather than convicting the prose."""

        self.assertEqual([], self._findings("The sink `scripts/tickets.py` resolves.\n"))

    def test_plain_text_mentions_nothing(self):
        """Same escape hatch validate_names gives a name: drop the backticks
        and the prose is mentioning, not pointing."""

        self.assertEqual([], self._findings("The oracle is tools/validate.py itself.\n"))

    def test_a_tree_without_the_marker_is_skipped_not_failed(self):
        root = self._tree("The oracle is `tools/validate.py`.\n")
        (root / "ARCHITECTURE.md").unlink()
        saved = validate.ROOT
        try:
            validate.ROOT = root
            diag = validate.Diagnostics()
            validate.validate_documented_paths(diag)
        finally:
            validate.ROOT = saved
        self.assertFalse(diag.has_errors)
        self.assertTrue(any(line.startswith("WARN") for line in diag.lines()))

    def test_the_exemption_is_one_live_site_and_not_a_blanket(self):
        """An exemption that outlives its sentence is a hole. Each pair names
        a file that still carries that token, and `tests/pins.json` erroring
        in the fixture above is the proof the pass is per-file, not per-name.

        Per-file is the honest word: the key is (file, token), so this guard
        catches the exemption outliving its sentence entirely, and does not
        catch a second sentence in the same file reusing the token.
        """

        for where, token in validate.DOC_PATH_EXEMPT_SITES:
            source = _ROOT / where
            self.assertTrue(source.is_file(), f"exempt site {where} is gone")
            self.assertIn(
                f"`{token}`",
                source.read_text(encoding="utf-8"),
                f"{where} no longer carries `{token}`; drop the exemption",
            )

    def test_the_real_library_tree_carries_no_dead_documented_path(self):
        diag = validate.Diagnostics()
        saved = validate.ROOT
        try:
            validate.ROOT = _ROOT
            validate.validate_documented_paths(diag)
        finally:
            validate.ROOT = saved
        self.assertEqual(
            [], [line for line in diag.lines() if line.startswith("ERROR")]
        )


if __name__ == "__main__":
    unittest.main()
