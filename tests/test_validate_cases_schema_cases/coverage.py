"""Post-qualification field coverage checks."""

import unittest

from tests.test_validate_cases_schema import CASES, vc


class CoverageCensusTest(unittest.TestCase):
    """Field-to-case census checks."""

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
        gap = (
            "manifest field coverage: no case probes 'incomparability' — run "
            "20260809T021408Z-benchmaker-unseal found no angle that reaches it"
        )
        self.assertEqual([], vc.census_errors(thin, [gap]))

    def test_a_case_that_probes_no_field_is_refused(self):
        thin = dict(self.FULL)
        thin["cs-e"] = {}
        found = vc.census_errors(thin, [])
        self.assertTrue(any("cs-e probes no field" in e for e in found), found)

    def test_a_case_that_probes_no_field_recorded_as_a_gap_is_accepted(self):
        thin = dict(self.FULL)
        thin["cs-e"] = {}
        gap = (
            "manifest field coverage: cs-e probes no field — its angle produces no "
            "package, so no manifest field is reachable"
        )
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
    """A declaration is only worth its mutation; these run real probes."""

    def probe_against(self, case, mutate):
        return vc.probe_a_mutated_target(CASES / case, mutate)

    def test_a_declared_none_anchor_with_a_reason_passes_and_silence_fails(self):
        def plant(manifest):
            manifest["anchors"]["s1"] = "   "
            manifest["anchors"]["s2"] = "none"

        code, detail = self.probe_against("cs-sparse-fresh", plant)
        self.assertNotEqual(0, code)
        with self.subTest("silence"):
            self.assertIn("anchors['s1'] is silent", detail)
        with self.subTest("a declared none with no reason"):
            self.assertIn("anchors['s2'] declares 'none' with no reason", detail)
        with self.subTest("a declared none with a reason"):
            code, detail = self.probe_against(
                "cs-sparse-fresh",
                lambda manifest: manifest["anchors"].__setitem__(
                    "s1",
                    "none — the spec exhibits no example, so nothing outside "
                    "the package pins this behavior",
                ),
            )
            self.assertEqual(0, code, detail)

    def test_a_reference_audit_rate_fails_where_a_count_passes(self):
        def plant(manifest):
            manifest["reference_audit"]["defect_count"] = 0.125
            manifest["reference_audit"]["defect_rate"] = "1 defect per 8 cases"

        code, detail = self.probe_against("cs-contradiction-fresh", plant)
        self.assertNotEqual(0, code)
        with self.subTest("a rate in place of the count"):
            self.assertIn("never a rate", detail)
        with self.subTest("a rate beside the count"):
            self.assertIn("states a rate ('defect_rate')", detail)

    def test_a_declared_field_no_probe_enforces_is_refused(self):
        found = vc.coverage_probe_errors(
            CASES / "cs-cli-fresh", {"incomparability": "constrained"}
        )
        self.assertTrue(
            any("still passes with 'incomparability' removed" in e for e in found), found
        )
