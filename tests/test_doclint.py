"""scripts/doclint.py: the documentation oracle any repository can run.

Two findings and no third: a relative markdown link that resolves to
nothing, and a paragraph carried by two files. The fixture below is the
can-fail direction -- it is built beside the tree, never by mutating it
(rules/verification.md Section 8) -- and the library tiers are the
already-green direction.
"""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import scripts.doclint as doclint  # noqa: E402

DOCLINT_PY = ROOT / "scripts" / "doclint.py"

# One paragraph, two files. Long enough to clear the script's minimum: a
# short block -- a heading, a one-line note -- repeats across documents by
# function rather than by copying.
COPY = (
    "The join adjudicates one returned child result before anything "
    "downstream trusts it, and the blame rule routes each finding to the "
    "causal owner it belongs to.\n"
)

INDEX_MD = (
    "# Index\n\n"
    "This index points at [the guide](guide.md) and at "
    "[a page that was removed](missing.md).\n\n" + COPY
)

GUIDE_MD = (
    "# Guide\n\n"
    "Installing the toolchain takes one command, and the receipt it writes "
    "names every file that command placed.\n\n" + COPY
)


def write(path: Path, text: str) -> None:
    """LF on every host: a paragraph splitter graded against CRLF here
    would be graded against LF in CI."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode("utf-8"))


def build_fixture(root: Path) -> None:
    write(root / "index.md", INDEX_MD)
    write(root / "guide.md", GUIDE_MD)


class FixtureRootTest(unittest.TestCase):
    """One dangling link, one copied paragraph, and nothing else."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        build_fixture(self.root)

    def test_the_fixture_reports_exactly_the_two_findings(self):
        findings = doclint.report(self.root)["findings"]
        self.assertEqual(
            ["dangling-link", "near-duplicate"],
            sorted(finding["kind"] for finding in findings),
            findings,
        )

    def test_the_dangling_link_names_its_file_and_its_target(self):
        (finding,) = [
            f for f in doclint.report(self.root)["findings"] if f["kind"] == "dangling-link"
        ]
        self.assertEqual("index.md", finding["file"])
        self.assertEqual("missing.md", finding["target"])

    def test_the_near_duplicate_names_both_sites(self):
        (finding,) = [
            f for f in doclint.report(self.root)["findings"] if f["kind"] == "near-duplicate"
        ]
        self.assertEqual({"guide.md", "index.md"}, {finding["file"], finding["other"]})
        self.assertGreaterEqual(finding["ratio"], 0.99)

    def test_a_root_with_neither_reports_nothing(self):
        (self.root / "index.md").unlink()
        (self.root / "guide.md").unlink()
        write(self.root / "only.md", "# Only\n\nA file that links nowhere.\n")
        self.assertEqual([], doclint.report(self.root)["findings"])

    def test_the_threshold_is_the_reported_sets_parameter(self):
        """Above the copy's ratio nothing is a near-duplicate: the pair set
        is a function of the threshold, so the flag decides the verdict."""

        findings = doclint.report(self.root, threshold=1.01)["findings"]
        self.assertEqual(
            ["dangling-link"], sorted(finding["kind"] for finding in findings), findings
        )


class CommandLineTest(unittest.TestCase):
    """`doclint.py <root>` prints one JSON document and exits on findings."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        build_fixture(self.root)

    def run_cli(self, *args):
        return subprocess.run(
            [sys.executable, str(DOCLINT_PY), *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

    def test_the_run_prints_the_findings_and_exits_nonzero(self):
        done = self.run_cli(str(self.root))
        self.assertEqual(1, done.returncode, done.stderr)
        payload = json.loads(done.stdout)
        self.assertEqual(
            ["dangling-link", "near-duplicate"],
            sorted(finding["kind"] for finding in payload["findings"]),
            payload,
        )

    def test_the_threshold_flag_reaches_the_report(self):
        done = self.run_cli(str(self.root), "--near-duplicate-threshold", "1.01")
        payload = json.loads(done.stdout)
        self.assertEqual(
            ["dangling-link"],
            sorted(finding["kind"] for finding in payload["findings"]),
            payload,
        )

    def test_a_clean_root_exits_zero(self):
        (self.root / "index.md").unlink()
        (self.root / "guide.md").unlink()
        write(self.root / "only.md", "# Only\n\nA file that links nowhere.\n")
        done = self.run_cli(str(self.root))
        self.assertEqual(0, done.returncode, done.stderr)
        self.assertEqual([], json.loads(done.stdout)["findings"])


class LibraryTreeTest(unittest.TestCase):
    """The already-green direction. Graded tier by tier: `tests/fixtures`
    carries markdown written to be broken, and a link is resolved from the
    file that carries it, so scanning a tier still resolves the citations
    it makes into every other one."""

    TIERS = ("rules", "contracts", "docs", "skills", "packs", "compositions", "templates")

    def test_no_tier_carries_a_dangling_link(self):
        dangling = []
        for tier in self.TIERS:
            dangling += [
                f
                for f in doclint.report(ROOT / tier)["findings"]
                if f["kind"] == "dangling-link"
            ]
        self.assertEqual([], dangling)


if __name__ == "__main__":
    unittest.main()
