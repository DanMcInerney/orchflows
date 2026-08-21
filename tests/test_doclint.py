"""scripts/doclint.py: the documentation oracle any repository can run.

Two findings and no third: a relative markdown link that resolves to
nothing, and a paragraph carried by two files. The fixture below is the
can-fail direction -- it is built beside the tree, never by mutating it
(rules/verification.md Section 8) -- and the library tiers are the
already-green direction.
"""

import ast
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import scripts.doclint as doclint  # noqa: E402
from tools import validate  # noqa: E402  (needs the sys.path insert above)

DOCLINT_PY = ROOT / "scripts" / "doclint.py"
VALIDATE_PY = ROOT / "tools" / "validate.py"

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

    def test_link_shapes_the_library_never_writes_are_still_read_as_links(self):
        """A project's markdown: a destination in angle brackets, a
        root-relative path, a title after the path. Each is graded by
        where it points, not by its spelling."""

        write(self.root / "docs" / "has space.md", "# Spaced\n")
        write(
            self.root / "docs" / "shapes.md",
            "[a](<has space.md>) [b](/guide.md) [c](/gone.md) "
            "[d](../guide.md \"Guide\") [e]({{root}}/x.md)\n",
        )
        findings = [
            (f["file"], f["target"])
            for f in doclint.report(self.root)["findings"]
            if f["kind"] == "dangling-link"
        ]
        self.assertEqual([("docs/shapes.md", "/gone.md"), ("index.md", "missing.md")], findings)

    def test_a_target_the_path_layer_refuses_is_reported_missing_not_skipped(self):
        """`resolve_link` returns None for a link that is not the
        repository's to resolve -- an external URL, a bare anchor. A name
        the path layer itself will not answer for is a different thing: the
        reader cannot follow it either, so it is a dangling link and not a
        link the check has no business grading. Sharing one None sent it
        through documentation.md law 5 unread -- and an embedded null, which
        the path layer refuses with a ValueError rather than an OSError,
        did not reach that None at all: it came out of the check as a
        traceback."""

        source = self.root / "index.md"
        refused = "bad\x00name.md"

        self.assertIsNotNone(doclint.resolve_link(source, refused))
        self.assertEqual([refused], doclint.dangling_links(source, "[x]({0})".format(refused)))

        with mock.patch.object(Path, "resolve", side_effect=OSError("refused")):
            self.assertEqual(
                ["missing.md"], doclint.dangling_links(source, "[m](missing.md)")
            )

    def test_a_link_that_is_not_ours_to_resolve_is_still_skipped(self):
        # The other half of the same None, unchanged: an external URL, a
        # bare anchor and a templated path are graded by nobody here.
        source = self.root / "index.md"

        self.assertEqual(
            [], doclint.dangling_links(source, "[a](https://x/y) [b](#anchor) [c]({{root}}/x.md)")
        )

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


def imported_modules(path: Path) -> set:
    """Every module `path` imports and every name it imports from one, at
    any nesting depth -- a lazy import inside a function counts."""

    names = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            names.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            names.add((node.module or "").split(".")[0])
            names.update(alias.name for alias in node.names)
    return names


def function_names(path: Path) -> set:
    return {
        node.name
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8")))
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


class OneImplementationTest(unittest.TestCase):
    """`tools/validate.py` asks doclint the two questions instead of
    carrying its own answers. Two copies of a near-duplicate method are two
    definitions of what a copy is."""

    def test_validate_reaches_difflib_only_through_doclint(self):
        modules = imported_modules(VALIDATE_PY)
        self.assertIn("doclint", modules)
        self.assertNotIn("difflib", modules)

    def test_validate_keeps_no_link_resolver_or_pair_index_of_its_own(self):
        self.assertEqual(
            set(),
            function_names(VALIDATE_PY) & {"_resolve_link", "_cross_tier_candidates"},
        )

    def test_the_near_duplicate_ratio_validate_reports_is_doclints(self):
        """The verdict, not the wiring: the cross-tier check, run over two
        clauses of two tiers, reports the one pair at doclint's ratio and
        names both sites. Fails if the compiler ever grades a copy by a
        method of its own, whatever that method imports."""

        left, right = "the join adjudicates one returned child result", "the join adjudicates one returned result"
        entries = [("rules", "rules/a.md", "A: " + left, left), ("docs", "docs/b.md", "B: " + right, right)]
        original = validate._cross_tier_clauses
        validate._cross_tier_clauses = lambda packages: entries
        self.addCleanup(setattr, validate, "_cross_tier_clauses", original)
        diag = validate.Diagnostics()
        validate.validate_cross_tier_duplication([], diag)
        (item,) = diag.items
        _, label, message = item
        self.assertEqual("rules/a.md", label)
        self.assertIn("with docs/b.md:", message)
        self.assertIn(f"at {doclint.similarity(right, left):.2f} with", message)


class ValidateLinkCheckTest(unittest.TestCase):
    """The library tree carries no dangling link, so the can-fail direction
    is a tree built beside it (rules/verification.md Section 8): the same
    check, the same call, one broken link."""

    def graded(self, link: str) -> list:
        """What the compiler's link check says about a tree whose one
        document carries `link`."""

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for tier in validate.LINKED_MD_ROOTS:
                (root / tier).mkdir()
            write(root / "docs" / "guide.md", "See [a link](%s).\n" % link)
            write(root / "docs" / "here.md", "# Here\n")
            original = validate.ROOT
            validate.ROOT = root
            self.addCleanup(setattr, validate, "ROOT", original)
            diag = validate.Diagnostics()
            validate.validate_markdown_links(diag)
            return diag.items

    def test_a_dangling_link_in_a_graded_tier_is_an_error(self):
        self.assertEqual(
            [("ERROR", "docs/guide.md", "markdown link does not resolve: missing.md")],
            self.graded("missing.md"),
        )

    def test_a_link_that_resolves_is_not(self):
        self.assertEqual([], self.graded("here.md"))

    def test_an_external_url_is_not_the_repositorys_to_resolve(self):
        self.assertEqual([], self.graded("https://example.invalid/page"))


class FactoryTableTest(unittest.TestCase):
    """docs/documentation.md Section 7 names the oracle that grades each
    factory's output. A project gets no `tools/validate.py`, so the
    documentation row names what it does get."""

    def test_the_documentation_row_names_this_script_as_its_oracle(self):
        rows = [
            line
            for line in (ROOT / "docs" / "documentation.md")
            .read_text(encoding="utf-8")
            .split("\n")
            if line.startswith("| documentation |")
        ]
        self.assertEqual(1, len(rows), rows)
        self.assertIn("doclint.py", rows[0].rsplit("|", 2)[1])


class InstallationScopeDocumentationTest(unittest.TestCase):
    INSTALL_DOCS = (
        "README.md",
        "ARCHITECTURE.md",
        "DESIGN.md",
        "docs/documentation.md",
        "docs/ui/platform.md",
        "skills/workflows/orch-build/references/scopes.md",
    )

    def test_maintained_installation_docs_name_user_scope_and_no_project_install(self):
        texts = {
            name: (ROOT / name).read_text(encoding="utf-8")
            for name in self.INSTALL_DOCS
        }
        forbidden = re.compile(r"\bproject(?:-scope)? install(?:ation|s)?\b", re.IGNORECASE)
        for name, text in texts.items():
            with self.subTest(name=name):
                self.assertNotIn("install.py --project", text)
                self.assertIsNone(forbidden.search(text))
        for name in self.INSTALL_DOCS[:-1]:
            with self.subTest(user_anchor=name):
                self.assertRegex(texts[name].lower(), r"\buser(?:-level|-scope)? install")

    def test_live_routing_cases_teach_user_install_and_keep_project_custom_builds(self):
        cases = json.loads((ROOT / "benchmarks" / "routing" / "cases.json").read_text())
        by_id = {case["id"]: case for case in cases}
        self.assertNotIn("answer-project-scope", by_id)
        self.assertIn("user install", by_id["answer-install-scope"]["prompt"].lower())
        self.assertEqual("answer", by_id["answer-install-scope"]["expected"])

        project_build = by_id["build-project-custom-skill"]
        self.assertIn("project-scope custom skill", project_build["prompt"])
        self.assertEqual("ticket", project_build["expected"])

    def test_project_build_scope_remains_a_distinct_custom_item_landing_zone(self):
        scopes = (
            ROOT / "skills" / "workflows" / "orch-build" / "references" / "scopes.md"
        ).read_text(encoding="utf-8")
        self.assertIn("## Project build scope", scopes)
        project_row = next(
            line for line in scopes.splitlines() if line.startswith("| project |")
        )
        self.assertIn("<repo>/.orchflows/skills/<name>/SKILL.md", project_row)
        self.assertIn("repo's `AGENTS.md`", project_row)


if __name__ == "__main__":
    unittest.main()
