"""Bounded projection and resume search-plan checks."""

from tests.test_search_plan import (
    EVOLVE_GENERATION,
    RESTART_ANCHORS,
    admitted_outcome,
    copy,
    generation_zero_request,
    json,
    load_search_module,
    no_candidate_outcome,
    read,
    run_advance,
    settled_request,
    tagged_identity,
    two_dimension_request,
    unittest,
    worklog_restart_errors,
)

class TestBoundedResume(unittest.TestCase):
    def run_ok(self, request):
        result = run_advance(request)
        self.assertEqual(0, result.returncode, result.stderr.decode())
        self.assertEqual(b"", result.stderr)
        return json.loads(result.stdout)

    def bounded_request(self, remaining):
        request = generation_zero_request()
        policy = request["policy"]
        policy["generation_width"] = 3
        policy["bound_unit_names"] = ["runs", "tokens"]
        policy["reservations"] = {
            "reflect": {"runs": 2, "tokens": 3},
            "merge": {"runs": 1, "tokens": 1},
        }
        policy["identity"] = tagged_identity(
            "search-policy/v1",
            {key: value for key, value in policy.items() if key != "identity"},
        )
        request["settled"]["outcomes"][0]["cost"] = {"runs": 0, "tokens": 0}
        request["remaining_bound"] = remaining
        return request

    def assert_within_bound(self, response, remaining):
        spent = {unit: 0 for unit in remaining}
        plan = response["plan"]
        if plan is not None:
            for slot in plan["slots"]:
                for unit in remaining:
                    spent[unit] += slot["reservation"][unit]
        self.assertTrue(
            all(spent[unit] <= remaining[unit] for unit in remaining),
            f"reservation {spent} exceeds {remaining}",
        )

    def test_componentwise_maximal_prefix_exact_fit_and_no_fit(self):
        for remaining in ({"runs": 4, "tokens": 100}, {"runs": 100, "tokens": 6}):
            with self.subTest(remaining=remaining):
                response = self.run_ok(self.bounded_request(remaining))
                self.assertEqual("planned", response["status"])
                self.assertEqual(2, len(response["plan"]["slots"]))
                self.assert_within_bound(response, remaining)
                reservation = response["plan"]["slots"][0]["reservation"]
                spent = {
                    unit: sum(slot["reservation"][unit] for slot in response["plan"]["slots"])
                    for unit in remaining
                }
                self.assertTrue(
                    any(spent[unit] + reservation[unit] > remaining[unit] for unit in remaining)
                )

        exact_bound = {"runs": 6, "tokens": 9}
        exact = self.run_ok(self.bounded_request(exact_bound))
        self.assertEqual(3, len(exact["plan"]["slots"]))
        self.assert_within_bound(exact, exact_bound)
        self.assertEqual(
            exact_bound,
            {
                unit: sum(slot["reservation"][unit] for slot in exact["plan"]["slots"])
                for unit in exact_bound
            },
        )

        no_fit = self.run_ok(self.bounded_request({"runs": 1, "tokens": 100}))
        self.assertEqual("no_fit", no_fit["status"])
        self.assertIsNone(no_fit["plan"])
        self.assertIsNone(no_fit["projection"]["last_plan"])
        self.assertEqual(["candidate:origin"], no_fit["projection"]["archive"])


    def test_partial_settlement_keeps_projection_and_complete_archive(self):
        initial_request = two_dimension_request()
        initial = self.run_ok(initial_request)
        slots = initial["plan"]["slots"]
        outcomes = [
            admitted_outcome(slots[0], "candidate:a", "0.8", "0.6", "a"),
            admitted_outcome(slots[1], "candidate:b", "0.4", "0.2", "b"),
            admitted_outcome(slots[2], "candidate:dominated", "0.3", "0.8", "d"),
        ]
        generation_two = self.run_ok(
            settled_request(
                initial_request["policy"], initial, outcomes, "candidate:origin"
            )
        )
        generation_two_slots = generation_two["plan"]["slots"]
        partial = settled_request(
            initial_request["policy"],
            generation_two,
            [
                admitted_outcome(
                    generation_two_slots[0], "candidate:partial", "0.7", "0.4", "p"
                )
            ],
            "candidate:origin",
        )
        pending = self.run_ok(partial)
        self.assertEqual("pending", pending["status"])
        self.assertIsNone(pending["plan"])
        self.assertEqual(generation_two["projection"], pending["projection"])
        self.assertEqual(
            generation_two["projection"]["archive"], pending["projection"]["archive"]
        )
        self.assertEqual(
            [slot["identity"] for slot in generation_two_slots[1:]],
            pending["missing_slot_identities"],
        )

        invalid_bound = copy.deepcopy(partial)
        invalid_bound["remaining_bound"] = {"unexpected": -1}
        result = run_advance(invalid_bound)
        self.assertEqual(2, result.returncode)
        self.assertEqual(b"", result.stdout)

    def test_first_no_fit_does_not_materialize_the_proposal_suffix(self):
        initial_request = two_dimension_request(width=5, merge_slots=0)
        initial = self.run_ok(initial_request)
        outcomes = [
            no_candidate_outcome(slot, f"generation-one-{index}")
            for index, slot in enumerate(initial["plan"]["slots"])
        ]
        request = settled_request(
            initial_request["policy"],
            initial,
            outcomes,
            "candidate:origin",
            remaining=0,
        )
        module = load_search_module()
        original_identified = module._identified
        produced_slots = []

        def tracking_identified(tag, payload):
            if tag == "search-slot/v1" and payload["generation"] == 2:
                produced_slots.append(payload["ordinal"])
            return original_identified(tag, payload)

        # The module instance is shared with every other test, so the patch
        # is undone whatever this one does.
        self.addCleanup(setattr, module, "_identified", original_identified)
        module._identified = tracking_identified
        response = module._advance(copy.deepcopy(request))
        self.assertEqual("no_fit", response["status"])
        self.assertEqual([0], produced_slots)

    def test_worklog_launch_and_restart_contract_has_failure_controls(self):
        """The restart controls a script can observe are pinned as behaviour:
        `test_partial_settlement_keeps_projection_and_complete_archive` shows
        the emitted projection carries the whole archive, and the `plan is
        None` it asserts beside the `pending` status is what "launches
        nothing" means to a caller. The three left here are the controller's
        own -- no script sees a live slot or a Worklog entry -- so each is
        pinned by the term that distinguishes its clause (RESTART_ANCHORS)."""
        generation = read(EVOLVE_GENERATION)
        self.assertEqual([], worklog_restart_errors(generation))

        for control, anchor in RESTART_ANCHORS:
            with self.subTest(control=control):
                self.assertIn(
                    control, worklog_restart_errors(generation.replace(anchor, ""))
                )
