"""Archive reflection and lineage search-plan checks."""

from tests.test_search_plan import (
    admitted_outcome,
    canonical_bytes,
    copy,
    ineligible_outcome,
    json,
    no_candidate_outcome,
    reverse_object_keys,
    run_advance,
    settled_request,
    tagged_identity,
    two_dimension_request,
    unittest,
)

class TestParetoReflection(unittest.TestCase):
    def run_ok(self, request):
        result = run_advance(request)
        self.assertEqual(0, result.returncode, result.stderr.decode())
        self.assertEqual(b"", result.stderr)
        return json.loads(result.stdout)

    def settled_fixture(self, resolution="0.1"):
        initial_request = two_dimension_request(resolution=resolution)
        initial = self.run_ok(initial_request)
        slots = initial["plan"]["slots"]
        outcomes = [
            admitted_outcome(slots[0], "candidate:a", "0.8", "0.6", "a"),
            admitted_outcome(slots[1], "candidate:b", "0.4", "0.2", "b"),
            admitted_outcome(slots[2], "candidate:dominated", "0.3", "0.8", "d"),
        ]
        request = settled_request(
            initial_request["policy"],
            initial,
            list(reversed(outcomes)),
            "candidate:dominated",
        )
        return request, outcomes

    def assert_pareto_response(self, response):
        projection = response["projection"]
        self.assertEqual(
            {"candidate:origin", "candidate:a", "candidate:b"},
            set(projection["archive"]),
        )
        self.assertEqual(4, len(projection["nodes"]))
        first = response["plan"]["slots"][0]
        self.assertEqual("reflect", first["kind"])
        self.assertEqual(["candidate:dominated"], first["parent_identities"])
        self.assertIn(
            first["focus_dimension_identity"],
            {"dimension:quality", "dimension:cost"},
        )
        self.assertTrue(first["feedback"])
        self.assertTrue(
            all(
                item["dimension_identity"] == first["focus_dimension_identity"]
                for item in first["feedback"]
            )
        )

    def test_resolution_aware_archive_reflection_and_replay(self):
        request, _ = self.settled_fixture()
        response = self.run_ok(request)
        replay = run_advance(reverse_object_keys(request))
        self.assertEqual(0, replay.returncode, replay.stderr.decode())
        self.assertEqual(canonical_bytes(response) + b"\n", replay.stdout)
        self.assert_pareto_response(response)

    def test_feedback_changes_the_reflection_packet_identity(self):
        request, outcomes = self.settled_fixture()
        original = self.run_ok(request)
        changed = copy.deepcopy(request)
        dominated = next(
            item
            for item in changed["settled"]["outcomes"]
            if item.get("candidate_identity") == "candidate:dominated"
        )
        original_slot = original["plan"]["slots"][0]
        focused_feedback = next(
            item
            for item in dominated["feedback"]
            if item["dimension_identity"]
            == original_slot["focus_dimension_identity"]
        )
        focused_feedback["reference_identity"] += "-v2"
        revised = self.run_ok(changed)
        revised_slot = revised["plan"]["slots"][0]
        self.assertNotEqual(original_slot["feedback"], revised_slot["feedback"])
        self.assertNotEqual(original_slot["identity"], revised_slot["identity"])
        self.assertEqual(
            revised_slot["identity"],
            tagged_identity(
                "search-slot/v1",
                {
                    key: value
                    for key, value in revised_slot.items()
                    if key != "identity"
                },
            ),
        )

    def test_comparison_exceeds_decimal_context_precision(self):
        resolution = "0.123456789012345678901234567890123456789"
        request, _ = self.settled_fixture(resolution=resolution)
        for outcome in request["settled"]["outcomes"]:
            if outcome["candidate_identity"] == "candidate:a":
                outcome["dimension_vector"] = [
                    {"identity": "dimension:quality", "value": resolution},
                    {"identity": "dimension:cost", "value": "0"},
                ]
            elif outcome["candidate_identity"] == "candidate:b":
                outcome["dimension_vector"] = [
                    {"identity": "dimension:quality", "value": "0"},
                    {"identity": "dimension:cost", "value": resolution},
                ]
            else:
                outcome["dimension_vector"] = [
                    {"identity": "dimension:quality", "value": "0"},
                    {"identity": "dimension:cost", "value": "1"},
                ]
        response = self.run_ok(request)
        self.assertNotIn("candidate:dominated", response["projection"]["archive"])

    def test_width_one_focus_rotates_across_generations(self):
        initial_request = two_dimension_request(width=1, merge_slots=0)
        generation_one = self.run_ok(initial_request)
        first_slot = generation_one["plan"]["slots"][0]
        generation_two = self.run_ok(
            settled_request(
                initial_request["policy"],
                generation_one,
                [admitted_outcome(first_slot, "candidate:best", "0.8", "0.2")],
                "candidate:origin",
            )
        )
        second_slot = generation_two["plan"]["slots"][0]
        generation_three = self.run_ok(
            settled_request(
                initial_request["policy"],
                generation_two,
                [no_candidate_outcome(second_slot, "generation-two")],
                "candidate:origin",
            )
        )
        self.assertEqual(
            ["dimension:quality", "dimension:cost", "dimension:quality"],
            [
                first_slot["focus_dimension_identity"],
                second_slot["focus_dimension_identity"],
                generation_three["plan"]["slots"][0]["focus_dimension_identity"],
            ],
        )


class TestMergeLineage(unittest.TestCase):
    def run_ok(self, request):
        result = run_advance(request)
        self.assertEqual(0, result.returncode, result.stderr.decode())
        self.assertEqual(b"", result.stderr)
        return json.loads(result.stdout)

    def assert_rejected(self, request):
        result = run_advance(request)
        self.assertEqual(2, result.returncode)
        self.assertEqual(b"", result.stdout)

    def merge_fixture(self):
        initial_request = two_dimension_request()
        initial = self.run_ok(initial_request)
        slots = initial["plan"]["slots"]
        outcomes = [
            admitted_outcome(slots[0], "candidate:a", "0.8", "0.6", "a"),
            admitted_outcome(slots[1], "candidate:b", "0.4", "0.2", "b"),
            admitted_outcome(slots[2], "candidate:dominated", "0.3", "0.8", "d"),
        ]
        request = settled_request(
            initial_request["policy"],
            initial,
            outcomes,
            "candidate:dominated",
        )
        return initial_request["policy"], self.run_ok(request)

    def test_complementary_merge_and_complete_fresh_lineage(self):
        policy, generation_two = self.merge_fixture()
        slots = generation_two["plan"]["slots"]
        self.assertEqual(["reflect", "reflect", "merge"], [s["kind"] for s in slots])
        merge = slots[-1]
        self.assertEqual(2, len(merge["parent_identities"]))
        self.assertEqual(
            {"dimension:quality", "dimension:cost"},
            set(merge["complementary_dimension_identities"]),
        )

        outcomes = [
            admitted_outcome(slots[0], "candidate:reflected", "0.7", "0.4", "r"),
            ineligible_outcome(slots[1], "candidate:ineligible", "i"),
            admitted_outcome(merge, "candidate:merged", "0.9", "0.1", "m"),
        ]
        request = settled_request(
            policy, generation_two, outcomes, "candidate:merged"
        )
        advanced = self.run_ok(request)
        nodes = advanced["projection"]["nodes"]
        self.assertEqual(7, len(nodes))
        self.assertIn("candidate:ineligible", [node["candidate_identity"] for node in nodes])
        self.assertNotIn("candidate:ineligible", advanced["projection"]["archive"])
        seen = set()
        for node in nodes:
            self.assertTrue(set(node["parent_identities"]) <= seen)
            self.assertNotIn(node["candidate_identity"], seen)
            seen.add(node["candidate_identity"])

        merged = next(node for node in nodes if node["candidate_identity"] == "candidate:merged")
        parents = [
            node for node in nodes if node["candidate_identity"] in merged["parent_identities"]
        ]
        for field in (
            "candidate_identity",
            "result_identity",
            "evidence_identity",
            "eligibility_verdict_identity",
            "score_card_identity",
        ):
            self.assertNotIn(merged[field], [parent[field] for parent in parents])

        for slot in generation_two["plan"]["slots"]:
            self.assertEqual(
                slot["identity"],
                tagged_identity(
                    "search-slot/v1",
                    {key: value for key, value in slot.items() if key != "identity"},
                ),
            )
            self.assertNotIn("plan_identity", slot)
        self.assertEqual(
            generation_two["plan"]["identity"],
            tagged_identity(
                "search-plan/v1",
                {
                    key: value
                    for key, value in generation_two["plan"].items()
                    if key != "identity"
                },
            ),
        )
        projection = advanced["projection"]
        self.assertEqual(
            projection["identity"],
            tagged_identity(
                "search-projection/v1",
                {key: value for key, value in projection.items() if key != "identity"},
            ),
        )

    def test_settlement_is_exact_and_atomic(self):
        policy, generation_two = self.merge_fixture()
        slots = generation_two["plan"]["slots"]
        partial = settled_request(
            policy,
            generation_two,
            [admitted_outcome(slots[0], "candidate:partial", "0.6", "0.4", "p")],
            "candidate:dominated",
        )
        pending = self.run_ok(partial)
        self.assertEqual("pending", pending["status"])
        self.assertEqual(generation_two["projection"], pending["projection"])
        self.assertEqual(
            generation_two["projection"]["identity"],
            pending["output_projection_identity"],
        )
        self.assertIsNone(pending["plan"])
        self.assertEqual([slot["identity"] for slot in slots[1:]], pending["missing_slot_identities"])

        malformed = copy.deepcopy(partial)
        malformed["settled"]["atomic"] = True
        self.assert_rejected(malformed)

        changed_incumbent = copy.deepcopy(partial)
        changed_incumbent["settled"][
            "preferred_incumbent_identity"
        ] = "candidate:partial"
        self.assert_rejected(changed_incumbent)

    def test_cycle_dangling_reuse_and_inherited_score_are_rejected(self):
        policy, generation_two = self.merge_fixture()
        slots = generation_two["plan"]["slots"]
        outcomes = [
            admitted_outcome(slots[0], "candidate:reflected", "0.7", "0.4", "r"),
            ineligible_outcome(slots[1], "candidate:ineligible", "i"),
            admitted_outcome(slots[2], "candidate:merged", "0.9", "0.1", "m"),
        ]

        reused = settled_request(policy, generation_two, outcomes, "candidate:merged")
        reused["settled"]["outcomes"][0]["candidate_identity"] = "candidate:origin"
        self.assert_rejected(reused)

        inherited = settled_request(policy, generation_two, outcomes, "candidate:merged")
        merge_outcome = inherited["settled"]["outcomes"][2]
        parent_identity = merge_outcome["parent_identities"][0]
        parent = next(
            node
            for node in inherited["projection"]["nodes"]
            if node["candidate_identity"] == parent_identity
        )
        merge_outcome["score_card_identity"] = parent["score_card_identity"]
        self.assert_rejected(inherited)

        valid = settled_request(policy, generation_two, outcomes, "candidate:merged")
        advanced = self.run_ok(valid)
        for replacement in ("candidate:missing", "candidate:merged"):
            broken = copy.deepcopy(advanced)
            broken_node = broken["projection"]["nodes"][1]
            broken_node["parent_identities"] = [replacement]
            payload = {
                key: value
                for key, value in broken["projection"].items()
                if key != "identity"
            }
            broken["projection"]["identity"] = tagged_identity(
                "search-projection/v1", payload
            )
            next_request = settled_request(
                policy, broken, [], "candidate:merged"
            )
            self.assert_rejected(next_request)



