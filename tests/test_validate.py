"""Compatibility seam for the validation regression collection."""
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

from tests._repo_root import ROOT as _ROOT
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import tools.validate as validate  # noqa: E402

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
    TestTheLawNamesTheSinkRoot,
    TestVocabularyResolvesToTheSink,
)
from tests.test_validate_cases.validator_ownership import (
    CrossTierDuplicationTest,
    FrictionLocationSyncTest,
    TestPackAdmissionIsDomainBlind,
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

        findings = self._findings("The oracle is `tests/test_validate.py`.\n")
        self.assertTrue(
            any("tests/test_validate.py" in line for line in findings),
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

    def test_an_unknown_dead_path_head_is_an_error(self):
        findings = self._findings("See `unknown/tree/missing.md`.\n")
        self.assertTrue(any("unknown/tree/missing.md" in line for line in findings))

    def test_nested_contract_prose_is_checked(self):
        root = self._tree("No pointer here.\n")
        source = root / "contracts" / "nested" / "probe.md"
        source.parent.mkdir(parents=True)
        source.write_text("The oracle is `tools/validate.py`.\n", encoding="utf-8")
        saved = validate.ROOT
        try:
            validate.ROOT = root
            diag = validate.Diagnostics()
            validate.validate_documented_paths(diag)
        finally:
            validate.ROOT = saved
        self.assertTrue(any("contracts/nested/probe.md" in line for line in diag.lines()))

    def test_an_exemption_does_not_cover_a_second_occurrence(self):
        """The exemption is keyed by the sentence that carries the token, so
        the same token in another sentence is still graded.

        The site is synthetic rather than borrowed from the live roster: a
        case reading `sorted(DOC_PATH_EXEMPT_SITES)[0]` graded whichever
        entry happened to sort first, and stopped exercising the check at
        all once the entry that sorted first stopped naming a file the path
        check visits.
        """

        where, token, marker = "docs/probe.md", "tools/absent.py", "a roster entry"
        root = self._tree(
            f"The roster names `{token}` and {marker}.\n"
            + f"A new pointer names `{token}`.\n"
        )
        saved_root, saved_sites = validate.ROOT, validate.DOC_PATH_EXEMPT_SITES
        try:
            validate.ROOT = root
            validate.DOC_PATH_EXEMPT_SITES = frozenset({(where, token, marker)})
            diag = validate.Diagnostics()
            validate.validate_documented_paths(diag)
        finally:
            validate.ROOT = saved_root
            validate.DOC_PATH_EXEMPT_SITES = saved_sites
        findings = [line for line in diag.lines() if token in line]
        self.assertEqual(1, len(findings), findings)

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
        """Every exemption names one still-live sentence and token.

        Keyed by content rather than by line number: an insertion above an
        exempt site used to move the key off it silently, and the exemption
        then covered whichever line had taken the number.
        """

        for where, token, marker in validate.DOC_PATH_EXEMPT_SITES:
            source = _ROOT / where
            self.assertTrue(source.is_file(), f"exempt site {where} is gone")
            carrying = [
                line for line in source.read_text(encoding="utf-8").splitlines()
                if marker in line and f"`{token}`" in line
            ]
            self.assertEqual(
                1, len(carrying),
                f"{where} carries {marker!r} with `{token}` {len(carrying)} "
                "times; an exemption names exactly one live sentence",
            )

    def test_the_marker_and_not_the_line_number_decides(self):
        """The regression this keying exists for: a line inserted above an
        exempt site must not move the exemption onto another line.

        Synthetic, like its sibling above: the live roster is empty whenever
        no shipped sentence needs an exemption, and a case reading it would
        stop exercising the check the moment that happened.
        """

        where, token, marker = "docs/probe.md", "tools/absent.py", "a roster entry"
        root = self._tree("No pointer here.\n")
        source = root / where
        source.parent.mkdir(parents=True, exist_ok=True)
        body = f"The roster names `{token}` and {marker}.\n"
        saved_root, saved_sites = validate.ROOT, validate.DOC_PATH_EXEMPT_SITES
        try:
            validate.ROOT = root
            validate.DOC_PATH_EXEMPT_SITES = frozenset({(where, token, marker)})
            for prefix in ("", "An inserted line.\n\nAnd another.\n"):
                source.write_text(prefix + body, encoding="utf-8")
                diag = validate.Diagnostics()
                validate.validate_documented_paths(diag)
                found = [line for line in diag.lines() if token in line]
                self.assertEqual([], found, f"prefix={prefix!r}: {found}")
        finally:
            validate.ROOT = saved_root
            validate.DOC_PATH_EXEMPT_SITES = saved_sites

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
