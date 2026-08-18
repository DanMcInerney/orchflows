"""Case-schema and live-set checks."""

import unittest

from tests.test_validate_cases_schema import CASES, CLEAN, errors, vc


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
