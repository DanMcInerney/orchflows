"""Generation visibility and target-authority search-plan checks."""

from tests.test_search_plan import (
    ACTIVATION_ANCHOR,
    EVOLVE,
    EVOLVE_GENERATION,
    RECURSION_ANCHORS,
    TOURNAMENT,
    copy,
    generation_zero_request,
    json,
    plan_shape,
    read,
    recursive_target_errors,
    run_advance,
    tagged_identity,
    template_text,
    two_dimension_request,
    unittest,
)

class TestVisibilityAndSelfTarget(unittest.TestCase):
    def run_ok(self, request):
        result = run_advance(request)
        self.assertEqual(0, result.returncode, result.stderr.decode())
        self.assertEqual(b"", result.stderr)
        return json.loads(result.stdout)

    def assert_rejected(self, request):
        result = run_advance(request)
        self.assertEqual(2, result.returncode)
        self.assertEqual(b"", result.stdout)

    def test_closed_schema_rejects_protected_inputs(self):
        cases = []

        request_field = generation_zero_request()
        request_field["protected_locator"] = "protected:item"
        cases.append(request_field)

        policy_field = generation_zero_request()
        policy_field["policy"]["held_back_result_identity"] = "result:held-back"
        cases.append(policy_field)

        outcome_field = generation_zero_request()
        outcome_field["settled"]["outcomes"][0][
            "closing_verdict_identity"
        ] = "verdict:closing"
        cases.append(outcome_field)

        feedback_field = generation_zero_request()
        feedback_field["settled"]["outcomes"][0]["feedback"][0][
            "protected_derived"
        ] = True
        cases.append(feedback_field)

        for case in cases:
            with self.subTest(field=cases.index(case)):
                self.assert_rejected(case)

    def test_target_renaming_preserves_plan_shape(self):
        original_request = two_dimension_request()
        original = self.run_ok(original_request)

        renamed_request = copy.deepcopy(original_request)
        renamed_request["policy"]["target_owner_identity"] = "owner:self-target"
        renamed_request["policy"]["identity"] = tagged_identity(
            "search-policy/v1",
            {
                key: value
                for key, value in renamed_request["policy"].items()
                if key != "identity"
            },
        )
        renamed_request["settled"]["outcomes"][0][
            "target_owner_identity"
        ] = "owner:self-target"
        renamed = self.run_ok(renamed_request)

        self.assertEqual(plan_shape(original), plan_shape(renamed))
        self.assertNotEqual(original["plan"]["identity"], renamed["plan"]["identity"])

    def test_recursive_target_authority_and_activation_have_failure_controls(self):
        evolve = template_text(EVOLVE)
        generation = read(EVOLVE_GENERATION)
        tournament = template_text(TOURNAMENT)
        self.assertEqual([], recursive_target_errors(evolve, generation, tournament))

        for control, anchor in RECURSION_ANCHORS:
            with self.subTest(control=control):
                self.assertIn(
                    control,
                    recursive_target_errors(
                        evolve, generation.replace(anchor, ""), tournament
                    ),
                )
        # Each template's own clause, dropped one at a time.
        for name, evolve_text, tournament_text in (
            ("evolve", evolve.replace(ACTIVATION_ANCHOR, ""), tournament),
            ("tournament", evolve, tournament.replace(ACTIVATION_ANCHOR, "")),
        ):
            with self.subTest(control="activation", template=name):
                self.assertIn(
                    "activation",
                    recursive_target_errors(evolve_text, generation, tournament_text),
                )

