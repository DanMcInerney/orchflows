"""Failability proof for the case schema's execution-bound rules, and
the guard that keeps the retired seal out of the case set.

``bound`` used to carry two quantities in one string — the construction
run's builder-context allocation and the candidate-facing probe tier. The
first told a candidate how the case was authored; only the second was
measurable. ``exec_bound`` carries the second alone, and these tests
prove the validator refuses the conflation rather than accepting it
silently.

The full flagless sweep over ``cases/`` stays the acceptance oracle; this
suite runs ``check_schema`` over dicts, so it costs nothing.
"""

from __future__ import annotations

import json
import re
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TOOL_DIR = REPO_ROOT / "benchmarks" / "benchmaker" / "tools"
if str(TOOL_DIR) not in sys.path:
    sys.path.insert(0, str(TOOL_DIR))

import deseal_cases as dc  # noqa: E402
import validate_cases as vc  # noqa: E402

CASES = REPO_ROOT / "benchmarks" / "benchmaker" / "cases"

CLEAN = {
    "id": "cs-cli-fresh",
    "angle": "deterministic-cli",
    "outcome": "an outcome",
    "target": "target",
    "probe": "python probe/check.py {impl}",
    "port": "cli-dedupe",
    "tests": "one line",
    "provenance": "synthesis@41ee9ea2 claims 1",
    "evidence": ["evidence/spec.md"],
    "expected_qualification": ["schema-valid"],
    "exec_bound": "probe within small tier",
    "negative": False,
    "size": "small",
    "parallel_safe": True,
}


def errors(**overrides):
    data = dict(CLEAN)
    data.update(overrides)
    found = []
    vc.check_schema(data, data["id"], found.append)
    return found


class ExecBoundTest(unittest.TestCase):
    def test_clean_case_has_no_errors(self):
        self.assertEqual([], errors())

    def test_bound_is_no_longer_a_schema_key(self):
        data = dict(CLEAN)
        data["bound"] = data.pop("exec_bound")
        found = []
        vc.check_schema(data, data["id"], found.append)
        self.assertTrue(any("missing required key 'exec_bound'" in e for e in found))
        self.assertTrue(any("carries key 'bound'" in e for e in found))

    def test_builder_context_in_exec_bound_is_refused(self):
        found = errors(exec_bound="one BC1 share; probe within small tier")
        self.assertTrue(any("names a builder context" in e for e in found), found)

    def test_every_builder_context_token_is_caught(self):
        for n in range(1, 7):
            found = errors(exec_bound="one BC%d share; probe within small tier" % n)
            self.assertTrue(any("names a builder context" in e for e in found), n)

    def test_tier_disagreeing_with_size_is_refused(self):
        found = errors(size="small", exec_bound="probe within large tier")
        self.assertTrue(any("names a probe tier other than" in e for e in found), found)

    def test_tier_agreeing_with_size_passes(self):
        self.assertEqual([], errors(size="large", exec_bound="probe within large tier"))

    def test_trial_budgets_survive_alongside_the_tier(self):
        self.assertEqual(
            [],
            errors(size="medium", exec_bound="probe within medium tier; 3 trials budgeted"),
        )

    def test_empty_exec_bound_is_refused(self):
        found = errors(exec_bound="")
        self.assertTrue(any("'exec_bound' must be" in e for e in found), found)

    def test_integer_exec_bound_is_allowed(self):
        self.assertEqual([], errors(exec_bound=60))

    def test_zero_exec_bound_is_refused(self):
        found = errors(exec_bound=0)
        self.assertTrue(any("'exec_bound' must be" in e for e in found), found)


class CaseSetTest(unittest.TestCase):
    """The live set must already satisfy the rule this pass introduced."""

    def test_no_case_leaks_its_builder_context(self):
        for toml in sorted(CASES.glob("*/case.toml")):
            text = toml.read_text(encoding="utf-8")
            self.assertNotIn("bound = \"one BC", text, toml.name)
            self.assertIn("exec_bound = ", text, toml.name)


# --------------------------------------------------------------------
# the retired seal, and the case set's own guard against its return
# --------------------------------------------------------------------

# A benchmark's version is its git revision. Nothing in the case set asks
# a candidate to mint a whole-package identity or to record a digest
# beside a component's locator. Evidence identity is a different
# discipline with a different owner and is deliberately not caught here:
# ``evidence@sha256:`` case provenance, provenance-chain link identities
# and the held-back store's identity all survive.
RETIRED_TOKENS = ("benchmark_identity", "covered_set_digest")
COMPONENT_DIGEST_KEYS = ("sha256", "identity")
# Both case dialects: a ``sha256:``-prefixed value, and the bare
# lowercase hex some contracts specified instead.
DIGEST_RE = re.compile(r"(?:sha256:[0-9a-f]{8,}|\b[0-9a-f]{64}\b)")
# Six components, in every case dialect.
COMPONENTS = (
    "evaluation_design",
    "runnable_cases",
    "runner",
    "scoring",
    "provenance",
    "qualification",
)
# A canonicalization recipe is the seal's construction rule. Any of these
# in an interchange contract hands a candidate the retired law as its
# spec.
RETIRED_RECIPE_PHRASES = (
    "canonical payload",
    "canonical json",
    "ensure_ascii",
    "keys sorted",
    "sorted keys",
    "mints a successor",
    "successor identity",
    "successor benchmark",
)


def case_files():
    for path in sorted(CASES.rglob("*")):
        if path.is_file() and "__pycache__" not in path.parts:
            yield path


def case_json():
    for path in sorted(CASES.rglob("*.json")):
        if "__pycache__" not in path.parts:
            yield path


def walk_objects(node):
    if isinstance(node, dict):
        yield node
        for value in node.values():
            for found in walk_objects(value):
                yield found
    elif isinstance(node, list):
        for value in node:
            for found in walk_objects(value):
                yield found


class RetiredSealTest(unittest.TestCase):
    """T05a criterion 2: no case demands a sealed package."""

    def test_no_case_file_names_a_retired_seal_field(self):
        offenders = []
        for path in case_files():
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            for line_number, line in enumerate(text.splitlines(), 1):
                for token in RETIRED_TOKENS:
                    if token in line:
                        offenders.append(
                            "%s:%d %s"
                            % (path.relative_to(REPO_ROOT), line_number, line.strip()[:110])
                        )
        self.assertEqual([], offenders, "%d line(s) name a retired seal field" % len(offenders))

    def test_no_component_reference_carries_a_digest_beside_its_locator(self):
        offenders = []
        for path in case_json():
            data = json.loads(path.read_text(encoding="utf-8"))
            for obj in walk_objects(data):
                if not isinstance(obj.get("locator"), str):
                    continue
                for key in COMPONENT_DIGEST_KEYS:
                    value = obj.get(key)
                    if isinstance(value, str) and DIGEST_RE.search(value):
                        offenders.append(
                            "%s: {%r: %r} beside locator %r"
                            % (path.relative_to(REPO_ROOT), key, value[:24], obj["locator"])
                        )
        self.assertEqual([], offenders, "%d component digest(s) survive" % len(offenders))

    def test_no_qualification_cover_addresses_a_component_by_digest(self):
        offenders = []
        for path in case_json():
            data = json.loads(path.read_text(encoding="utf-8"))
            for obj in walk_objects(data):
                covers = obj.get("covers")
                if covers is None:
                    continue
                values = []
                if isinstance(covers, str):
                    values = [covers]
                elif isinstance(covers, list):
                    values = [v for v in covers if isinstance(v, str)]
                elif isinstance(covers, dict):
                    values = [v for v in covers.values() if isinstance(v, str)]
                for value in values:
                    if DIGEST_RE.search(value):
                        offenders.append(
                            "%s: covers %r" % (path.relative_to(REPO_ROOT), value[:70])
                        )
        self.assertEqual([], offenders, "%d cover(s) address a component by digest" % len(offenders))

    def test_every_interchange_states_the_surviving_manifest_schema(self):
        """T05a criterion 3.

        The contract a candidate builds against names each component's
        locator and no digest, and hands over no canonicalization recipe
        and no successor rule.
        """
        contracts = sorted(CASES.glob("*/evidence/interchange.md"))
        self.assertEqual(13, len(contracts), "the interchange contract set moved")
        offenders = []
        for path in contracts:
            text = path.read_text(encoding="utf-8")
            lowered = text.lower()
            name = path.relative_to(CASES).parts[0]
            if "manifest" not in lowered:
                continue
            for phrase in RETIRED_RECIPE_PHRASES:
                if phrase in lowered:
                    offenders.append("%s: states %r" % (name, phrase))
            if "locator" not in lowered:
                offenders.append("%s: names no component locator" % name)
            for component in COMPONENTS:
                if component not in text:
                    offenders.append("%s: omits component %r" % (name, component))
        self.assertEqual([], offenders, "%d interchange defect(s)" % len(offenders))


# --------------------------------------------------------------------
# the de-sealing tool
# --------------------------------------------------------------------

SEALED_MANIFEST = """{
  "benchmark_identity": "sha256:%s",
  "evaluation_design": {
    "identity": "sha256:%s",
    "locator": "provenance/design.md"
  },
  "gaps": [],
  "runnable_cases": {
    "locator": "cases/cases.json",
    "sha256": "%s"
  }
}
""" % ("a" * 64, "b" * 64, "c" * 64)

SEALED_QUALIFICATION = """{
  "entries": [
    {
      "covers": [
        "runnable_cases sha256:%s"
      ],
      "criterion": "schema-valid",
      "evidence": {
        "summary": "benchmark_identity recomputed equal; six component digests verified over shipped bytes"
      },
      "oracle": "manifest canonicalization audit: recompute benchmark_identity and every component digest over the shipped bytes"
    }
  ]
}
""" % ("c" * 64)

CLEAN_SIBLING = """{
 "cases": [
  {"id": "one", "provenance": "evidence@sha256:b933dcd4a99f560b factors table"}
 ]
}
"""


class DesealToolTest(unittest.TestCase):
    """T05a criterion 1: the mechanical edit is a tested tool, not 118
    hand edits."""

    def setUp(self):
        self.manifest = json.loads(SEALED_MANIFEST)
        self.locators = dc.digest_to_locator(self.manifest)

    def test_locator_map_reads_both_dialects(self):
        self.assertEqual(
            {"b" * 64: "provenance/design.md", "c" * 64: "cases/cases.json"},
            self.locators,
        )

    def test_an_already_clean_file_is_returned_unchanged(self):
        self.assertEqual(
            CLEAN_SIBLING, dc.deseal_text(CLEAN_SIBLING, self.locators, "clean.json")
        )

    def test_evidence_identity_is_not_a_component_digest(self):
        """The non-goal, pinned: a case's evidence citation survives."""
        out = dc.deseal_text(CLEAN_SIBLING, self.locators, "clean.json")
        self.assertIn("evidence@sha256:b933dcd4a99f560b", out)

    def test_a_sealed_manifest_loses_its_identity_and_every_digest(self):
        out = dc.deseal_text(SEALED_MANIFEST, self.locators, "manifest.json")
        self.assertNotIn("benchmark_identity", out)
        self.assertNotIn("sha256", out)
        self.assertEqual(
            {
                "evaluation_design": {"locator": "provenance/design.md"},
                "gaps": [],
                "runnable_cases": {"locator": "cases/cases.json"},
            },
            json.loads(out),
        )

    def test_formatting_outside_the_deleted_lines_survives(self):
        out = dc.deseal_text(SEALED_MANIFEST, self.locators, "manifest.json")
        kept = [line for line in SEALED_MANIFEST.splitlines() if "sha256" not in line]
        # Only the trailing comma of a member left last by a deletion moves.
        self.assertEqual(
            [line.rstrip(",") for line in kept], [line.rstrip(",") for line in out.splitlines()]
        )
        self.assertTrue(out.endswith("}\n"))

    def test_a_cover_addresses_its_component_by_locator(self):
        """The digest gives way to the locator; the label it carried stays."""
        out = dc.deseal_text(SEALED_QUALIFICATION, self.locators, "qualification.json")
        self.assertEqual(
            ["runnable_cases cases/cases.json"], json.loads(out)["entries"][0]["covers"]
        )

    def test_a_held_back_store_identity_is_not_a_component_digest(self):
        """No locator beside it, so no rule reaches it."""
        store = '{\n "protected_evidence": {\n  "identity": "sha256:%s",\n  "visibility": "held"\n }\n}\n' % (
            "e" * 64
        )
        self.assertEqual(store, dc.deseal_text(store, self.locators, "manifest.json"))

    def test_retired_audit_prose_is_replaced_not_left(self):
        out = dc.deseal_text(SEALED_QUALIFICATION, self.locators, "qualification.json")
        self.assertNotIn("benchmark_identity", out)
        self.assertNotIn("canonicalization", out)
        entry = json.loads(out)["entries"][0]
        self.assertIn("component locator", entry["oracle"])
        self.assertIn("nine schema fields present", entry["evidence"]["summary"])

    def test_malformed_json_is_refused_not_skipped(self):
        with self.assertRaises(dc.DesealError) as caught:
            dc.deseal_text('{"gaps": [,]}\n', self.locators, "broken.json")
        self.assertIn("does not parse as JSON", str(caught.exception))

    def test_a_cover_no_component_claims_is_refused_not_left(self):
        orphan = SEALED_QUALIFICATION.replace("c" * 64, "d" * 64)
        with self.assertRaises(dc.DesealError) as caught:
            dc.deseal_text(orphan, self.locators, "qualification.json")
        self.assertIn("no component of this package claims", str(caught.exception))

    def test_an_uncovered_retired_token_is_refused_not_left(self):
        surviving = SEALED_QUALIFICATION.replace(
            "manifest canonicalization audit: recompute benchmark_identity and every "
            "component digest over the shipped bytes",
            "a phrase no rule knows, naming benchmark_identity",
        )
        with self.assertRaises(dc.DesealError) as caught:
            dc.deseal_text(surviving, self.locators, "qualification.json")
        self.assertIn("no rule covers", str(caught.exception))

    def test_a_package_without_a_manifest_is_refused(self):
        with self.assertRaises(dc.DesealError) as caught:
            dc.deseal_package(REPO_ROOT / "benchmarks", write=False)
        self.assertIn("no manifest.json", str(caught.exception))

    def test_the_live_set_is_already_de_sealed(self):
        """Idempotence, read as the tool's own --check."""
        self.assertEqual(0, dc.main(["--check", "--cases-dir", str(CASES)]))


# --------------------------------------------------------------------
# post-qualification field coverage
# --------------------------------------------------------------------

# The census below is arithmetic over declarations and costs nothing. The
# last two cases run real probes against a mutated copy of a case, because
# a declaration that no probe enforces is the only failure mode worth
# testing and no cheaper oracle sees it.


class CoverageCensusTest(unittest.TestCase):
    """Field -> covering cases, and what makes the census refuse."""

    FULL = {
        "cs-a": {"anchors": "constrained", "builders": "constrained"},
        "cs-b": {"reference_audit": "constrained", "attack_audit": "constrained"},
        "cs-c": {"measurement": "constrained", "resolution": "constrained"},
        "cs-d": {"retirement_trigger": "constrained", "incomparability": "presence-only"},
    }

    def test_a_covering_declaration_set_is_accepted(self):
        self.assertEqual([], vc.census_errors(self.FULL, []))

    def test_the_census_reports_every_field_and_its_covering_cases(self):
        census = vc.coverage_census(self.FULL)
        self.assertEqual(sorted(vc.POST_QUALIFICATION_FIELDS), sorted(census))
        self.assertEqual(["cs-a"], census["anchors"])

    def test_a_field_no_case_probes_is_refused(self):
        thin = dict(self.FULL)
        thin["cs-d"] = {"retirement_trigger": "constrained"}
        found = vc.census_errors(thin, [])
        self.assertTrue(any("no case probes 'incomparability'" in e for e in found), found)

    def test_an_uncovered_field_recorded_as_a_gap_is_accepted(self):
        thin = dict(self.FULL)
        thin["cs-d"] = {"retirement_trigger": "constrained"}
        gap = ("manifest field coverage: no case probes 'incomparability' — run "
               "20260809T021408Z-benchmaker-unseal found no angle that reaches it")
        self.assertEqual([], vc.census_errors(thin, [gap]))

    def test_a_case_that_probes_no_field_is_refused(self):
        thin = dict(self.FULL)
        thin["cs-e"] = {}
        found = vc.census_errors(thin, [])
        self.assertTrue(any("cs-e probes no field" in e for e in found), found)

    def test_a_case_that_probes_no_field_recorded_as_a_gap_is_accepted(self):
        thin = dict(self.FULL)
        thin["cs-e"] = {}
        gap = ("manifest field coverage: cs-e probes no field — its angle produces no "
               "package, so no manifest field is reachable")
        self.assertEqual([], vc.census_errors(thin, [gap]))

    def test_a_field_outside_the_eight_is_refused(self):
        broken = dict(self.FULL)
        broken["cs-a"] = {"benchmark_identity": "constrained"}
        found = vc.census_errors(broken, [])
        self.assertTrue(
            any("'benchmark_identity' is not a post-qualification field" in e for e in found),
            found,
        )

    def test_a_coverage_class_outside_the_two_is_refused(self):
        broken = dict(self.FULL)
        broken["cs-a"] = {"anchors": "probably"}
        found = vc.census_errors(broken, [])
        self.assertTrue(any("coverage class 'probably'" in e for e in found), found)


class CoverageDeclarationTest(unittest.TestCase):
    def test_every_live_case_declares_its_coverage_or_is_recorded(self):
        declared = vc.declared_coverage(CASES)
        self.assertEqual(16, len(declared))
        gaps = vc.recorded_gaps(CASES.parent)
        self.assertEqual([], vc.census_errors(declared, gaps))

    def test_a_probe_that_declares_nothing_reads_as_an_empty_declaration(self):
        self.assertEqual({}, vc.probed_fields_from_source("x = 1\n"))

    def test_a_declaration_that_is_not_a_literal_mapping_is_refused(self):
        with self.assertRaises(vc.CoverageError):
            vc.probed_fields_from_source("PROBED_MANIFEST_FIELDS = dict(a=1)\n")


class CoverageTeethTest(unittest.TestCase):
    """A declaration is only worth its mutation. These run real probes."""

    def probe_against(self, case, mutate):
        return vc.probe_a_mutated_target(CASES / case, mutate)

    def test_a_declared_none_anchor_with_a_reason_passes_and_silence_fails(self):
        with self.subTest("silence"):
            code, detail = self.probe_against(
                "cs-sparse-fresh",
                lambda manifest: manifest["anchors"].__setitem__("s1", "   "),
            )
            self.assertNotEqual(0, code)
            self.assertIn("anchors['s1'] is silent", detail)
        with self.subTest("a declared none with no reason"):
            code, detail = self.probe_against(
                "cs-sparse-fresh",
                lambda manifest: manifest["anchors"].__setitem__("s1", "none"),
            )
            self.assertNotEqual(0, code)
            self.assertIn("declares 'none' with no reason", detail)
        with self.subTest("a declared none with a reason"):
            code, _ = self.probe_against(
                "cs-sparse-fresh",
                lambda manifest: manifest["anchors"].__setitem__(
                    "s1", "none — the spec exhibits no example, so nothing outside "
                          "the package pins this behavior"
                ),
            )
            self.assertEqual(0, code)

    def test_a_reference_audit_rate_fails_where_a_count_passes(self):
        with self.subTest("a rate in place of the count"):
            code, detail = self.probe_against(
                "cs-contradiction-fresh",
                lambda manifest: manifest["reference_audit"].__setitem__(
                    "defect_count", 0.125
                ),
            )
            self.assertNotEqual(0, code)
            self.assertIn("never a rate", detail)
        with self.subTest("a rate beside the count"):
            code, detail = self.probe_against(
                "cs-contradiction-fresh",
                lambda manifest: manifest["reference_audit"].__setitem__(
                    "defect_rate", "1 defect per 8 cases"
                ),
            )
            self.assertNotEqual(0, code)
            self.assertIn("states a rate", detail)
        with self.subTest("the count the contract asks for"):
            code, _ = self.probe_against("cs-contradiction-fresh", lambda manifest: None)
            self.assertEqual(0, code)

    def test_a_declared_field_no_probe_enforces_is_refused(self):
        found = vc.coverage_probe_errors(
            CASES / "cs-cli-fresh", {"incomparability": "constrained"}
        )
        self.assertTrue(
            any("still passes with 'incomparability' removed" in e for e in found), found
        )


if __name__ == "__main__":
    unittest.main()
