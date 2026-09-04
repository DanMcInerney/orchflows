"""Protocol and public-boundary search-plan checks."""

from tests.test_search_plan import (
    EVOLVE,
    EVOLVE_GENERATION,
    EXECUTOR_RE,
    Path,
    ROOT,
    SEARCH_PROTOCOL,
    SEARCH_SCRIPT,
    TOURNAMENT,
    architecture_errors,
    canonical_bytes,
    copy,
    generation_zero_request,
    json,
    load_search_module,
    normalized,
    read,
    rehash_open_plan_slot,
    reverse_object_keys,
    run_advance,
    settled_request,
    spawn_advance,
    tagged_identity,
    template_text,
    tempfile,
    two_dimension_request,
    unittest,
)

class TestArchitecture(unittest.TestCase):
    def test_thin_evolve_owns_one_campaign_call_graph(self):
        for path in (EVOLVE, TOURNAMENT):
            self.assertTrue(path.is_dir(), f"missing campaign workflow: {path}")
            self.assertTrue((path / "SKILL.md").is_file(), f"{path} has no body")
        for path in (EVOLVE_GENERATION, SEARCH_PROTOCOL, SEARCH_SCRIPT):
            self.assertTrue(path.is_file(), f"missing search-planning surface: {path}")
        self.assertEqual(
            [], [str(path) for path in (ROOT / "skills").rglob("orch-search-plan")],
            "the search planner is a script, not a skill wrapping one command",
        )

        evolve = template_text(EVOLVE)
        generation = read(EVOLVE_GENERATION)
        tournament = template_text(TOURNAMENT)
        leaf = read(SEARCH_SCRIPT)
        self.assertEqual([], architecture_errors(evolve, generation, tournament, leaf))
        # One command, stated once, at the path the script now lives at.
        command = "python scripts/search_plan.py advance"
        self.assertEqual(1, leaf.count(command))
        self.assertIn("docs/search-plan-protocol.md", leaf)
        self.assertNotIn("operation registry", normalized(leaf))

    def test_the_campaign_prose_names_the_planner_it_selects_through(self):
        """The one caller of the search planner is the generations loop, and
        it names the script by bare filename -- the path moves when the
        script does, and a body that named the path would be stale the day
        it moved."""
        campaign = template_text(EVOLVE).partition("Generations,")[2]
        self.assertIn("search_plan.py advance", campaign)
        self.assertIn("do --standard orch-code", campaign)

    def test_planner_is_evaluation_mode_agnostic(self):
        protocol = read(SEARCH_PROTOCOL)
        script = read(SEARCH_SCRIPT)
        self.assertIn("evaluation_identity", protocol)
        self.assertIn('"evaluation_identity"', script)
        self.assertNotIn("benchmark_revision", protocol)
        self.assertNotIn('"benchmark_revision"', script)

    def test_known_wrong_ownership_fixtures_are_rejected(self):
        evolve = template_text(EVOLVE)
        generation = read(EVOLVE_GENERATION)
        tournament = template_text(TOURNAMENT)
        leaf = read(SEARCH_SCRIPT)

        closing = evolve + "\n**Wrap the campaign** with a further report.\n"
        self.assertIn(
            "closing-wrapper",
            architecture_errors(closing, generation, tournament, leaf),
        )
        direct_panel = tournament + "\nDirectly call `orch-panel`.\n"
        self.assertIn(
            "tournament-internal-call",
            architecture_errors(evolve, generation, direct_panel, leaf),
        )
        extra_leaf_call = leaf + "\nCall `orch-judge`.\n"
        self.assertIn(
            "leaf-call",
            architecture_errors(evolve, generation, tournament, extra_leaf_call),
        )
        readmitted_panel = generation + "\nScore the set through `orch-panel`.\n"
        self.assertIn(
            "judge-owner",
            architecture_errors(evolve, readmitted_panel, tournament, leaf),
        )

        judged_here = tournament + "\nThe promotion decision is taken here.\n"
        self.assertIn(
            "tournament-promotion",
            architecture_errors(evolve, generation, judged_here, leaf),
        )

        unresolved = evolve.replace(
            "judge --standard orch-code", "do --standard orch-code", 1
        )
        self.assertIn(
            "eligibility-unit",
            architecture_errors(unresolved, generation, tournament, leaf),
        )


class TestCanonicalAdvance(unittest.TestCase):
    def assert_rejected(self, payload=None, raw=None):
        result = run_advance(payload=payload, raw=raw)
        self.assertEqual(2, result.returncode)
        self.assertEqual(b"", result.stdout)
        self.assertTrue(result.stderr.startswith(b"search-plan: "))
        self.assertLessEqual(len(result.stderr), 512)

    def test_advance_is_the_only_subcommand_and_a_second_word_is_not_ignored(self):
        """`main`'s argv guard, which every other test walks straight past.

        Each argv below is handed a request the command would answer at
        exit 0, so the refusal is the guard's and not the request's: an
        argv this script does not define must not be read as `advance`
        with extra words, and a caller that passed nothing must not have
        its stdin consumed by a default.
        """

        request = generation_zero_request()
        for argv in ([], ["plan"], ["advance", "--force"], ["--help"], ["ADVANCE"]):
            with self.subTest(argv=argv):
                result = run_advance(payload=request, argv=argv)
                self.assertEqual(2, result.returncode)
                self.assertEqual(b"", result.stdout)
                self.assertEqual(b"search-plan: expected advance\n", result.stderr)

    def test_generation_zero_is_byte_stable_and_read_only(self):
        request = generation_zero_request()
        with tempfile.TemporaryDirectory() as directory:
            first = spawn_advance(request, cwd=directory)
            second = spawn_advance(reverse_object_keys(request), cwd=directory)
            self.assertEqual([], list(Path(directory).iterdir()))

        self.assertEqual(0, first.returncode, first.stderr.decode())
        self.assertEqual(b"", first.stderr)
        self.assertEqual(first.stdout, second.stdout)
        self.assertTrue(first.stdout.endswith(b"\n"))
        self.assertNotEqual(b"\n\n", first.stdout[-2:])

        response = json.loads(first.stdout)
        self.assertEqual("search-advance/v1", response["schema"])
        self.assertEqual("planned", response["status"])
        self.assertIsNone(response["input_projection_identity"])
        self.assertEqual([], response["missing_slot_identities"])
        self.assertEqual([], response["diagnostics"])

        projection = response["projection"]
        plan = response["plan"]
        self.assertEqual(projection["identity"], response["output_projection_identity"])
        self.assertEqual(
            projection["identity"],
            tagged_identity(
                "search-projection/v1",
                {key: value for key, value in projection.items() if key != "identity"},
            ),
        )
        self.assertEqual(
            plan["identity"],
            tagged_identity(
                "search-plan/v1",
                {key: value for key, value in plan.items() if key != "identity"},
            ),
        )
        self.assertEqual(0, projection["last_settled_generation"])
        self.assertEqual(plan, projection["last_plan"])
        self.assertEqual(["candidate:origin"], projection["archive"])
        self.assertEqual([request["settled"]["outcomes"][0]], projection["nodes"])
        self.assertEqual(["outcome:origin"], plan["basis_outcome_identities"])
        self.assertEqual(1, plan["generation"])

        self.assertEqual(1, len(plan["slots"]))
        slot = plan["slots"][0]
        self.assertEqual("reflect", slot["kind"])
        self.assertEqual(["candidate:origin"], slot["parent_identities"])
        self.assertEqual("dimension:quality", slot["focus_dimension_identity"])
        self.assertEqual([], slot["complementary_dimension_identities"])
        self.assertEqual({"runs": 1}, slot["reservation"])
        self.assertEqual(request["settled"]["outcomes"][0]["feedback"], slot["feedback"])
        self.assertEqual(
            slot["identity"],
            tagged_identity(
                "search-slot/v1",
                {key: value for key, value in slot.items() if key != "identity"},
            ),
        )

    def test_opaque_evaluation_identity_has_no_mode_branch(self):
        judged = generation_zero_request()
        benchmark = copy.deepcopy(judged)
        benchmark["policy"]["evaluation_identity"] = "evaluation:benchmark-fixture"
        benchmark["policy"]["identity"] = tagged_identity(
            "search-policy/v1",
            {
                key: value
                for key, value in benchmark["policy"].items()
                if key != "identity"
            },
        )
        benchmark["settled"]["outcomes"][0]["evaluation_identity"] = (
            "evaluation:benchmark-fixture"
        )

        judged_result = run_advance(judged)
        benchmark_result = run_advance(benchmark)
        self.assertEqual(0, judged_result.returncode, judged_result.stderr.decode())
        self.assertEqual(0, benchmark_result.returncode, benchmark_result.stderr.decode())
        judged_response = json.loads(judged_result.stdout)
        benchmark_response = json.loads(benchmark_result.stdout)
        self.assertEqual(judged_response["status"], benchmark_response["status"])
        self.assertEqual(
            [slot["kind"] for slot in judged_response["plan"]["slots"]],
            [slot["kind"] for slot in benchmark_response["plan"]["slots"]],
        )

        drift = copy.deepcopy(judged)
        drift["settled"]["outcomes"][0]["evaluation_identity"] = (
            "evaluation:benchmark-fixture"
        )
        self.assert_rejected(drift)

    def test_closed_schema_identity_numeric_and_reference_failures_exit_two(self):
        cases = []

        protected = generation_zero_request()
        protected["settled"]["outcomes"][0]["protected_locator"] = "secret:item"
        cases.append(protected)

        feedback = generation_zero_request()
        feedback["settled"]["outcomes"][0]["feedback"][0][
            "source_identity"
        ] = "source:held-back"
        cases.append(feedback)

        identity = generation_zero_request()
        identity["policy"]["identity"] = "sha256:" + "0" * 64
        cases.append(identity)

        numeric = generation_zero_request()
        numeric["policy"]["dimensions"][0]["resolution"] = "0.10"
        numeric["policy"]["identity"] = tagged_identity(
            "search-policy/v1",
            {key: value for key, value in numeric["policy"].items() if key != "identity"},
        )
        cases.append(numeric)

        reference = generation_zero_request()
        reference["settled"]["preferred_incumbent_identity"] = "candidate:absent"
        cases.append(reference)

        for case in cases:
            with self.subTest(case=cases.index(case)):
                self.assert_rejected(case)

        floating = generation_zero_request()
        floating["remaining_bound"]["runs"] = 1.0
        self.assert_rejected(floating)

        duplicate = canonical_bytes(generation_zero_request()).replace(
            b'"projection":null',
            b'"projection":null,"projection":null',
            1,
        )
        self.assert_rejected(raw=duplicate)

    def test_deep_json_recursion_is_invalid_input(self):
        # Spawned: 5000 levels is deep enough to exhaust the parser, and the
        # refusal is only a refusal if it costs the caller its own stack.
        raw = b'{"policy":' + b"[" * 5_000 + b"0" + b"]" * 5_000 + b"}"
        result = spawn_advance(raw=raw)
        self.assertEqual(2, result.returncode)
        self.assertEqual(b"", result.stdout)
        self.assertTrue(result.stderr.startswith(b"search-plan: "))
        self.assertLessEqual(len(result.stderr), 512)

    def test_public_request_identity_and_decimal_caps_are_exact(self):
        module = load_search_module()
        # The protocol states the three caps the module enforces, and the
        # numbers are read off the module rather than repeated here: a cap
        # changed in one place and not the other is what this half catches.
        protocol = normalized(read(SEARCH_PROTOCOL))
        for cap in (
            module.MAX_INPUT_BYTES,
            module.MAX_IDENTITY_CHARS,
            module.MAX_DECIMAL_CHARS,
        ):
            self.assertIn(f"at most {cap:,}", protocol)
            # The number is the claim: a protocol stating a neighbouring cap
            # would satisfy a check that only looked for a digit run.
            self.assertNotIn(f"at most {cap + 1:,}", protocol)

        at_request_cap = b"0" + b" " * (module.MAX_INPUT_BYTES - 1)
        self.assertEqual(0, module._load_request(at_request_cap))
        with self.assertRaises(module.ProtocolError):
            module._load_request(at_request_cap + b" ")

        identity_at_cap = generation_zero_request()
        identity_at_cap["policy"]["planner_revision"] = "x" * 256
        identity_at_cap["policy"]["identity"] = tagged_identity(
            "search-policy/v1",
            {
                key: value
                for key, value in identity_at_cap["policy"].items()
                if key != "identity"
            },
        )
        self.assertEqual(0, run_advance(identity_at_cap).returncode)
        identity_over_cap = copy.deepcopy(identity_at_cap)
        identity_over_cap["policy"]["planner_revision"] += "x"
        identity_over_cap["policy"]["identity"] = tagged_identity(
            "search-policy/v1",
            {
                key: value
                for key, value in identity_over_cap["policy"].items()
                if key != "identity"
            },
        )
        self.assert_rejected(identity_over_cap)

        decimal_at_cap = generation_zero_request()
        decimal_at_cap["policy"]["dimensions"][0]["resolution"] = "1" + "0" * 127
        decimal_at_cap["policy"]["identity"] = tagged_identity(
            "search-policy/v1",
            {
                key: value
                for key, value in decimal_at_cap["policy"].items()
                if key != "identity"
            },
        )
        self.assertEqual(0, run_advance(decimal_at_cap).returncode)
        decimal_over_cap = copy.deepcopy(decimal_at_cap)
        decimal_over_cap["policy"]["dimensions"][0]["resolution"] += "0"
        decimal_over_cap["policy"]["identity"] = tagged_identity(
            "search-policy/v1",
            {
                key: value
                for key, value in decimal_over_cap["policy"].items()
                if key != "identity"
            },
        )
        self.assert_rejected(decimal_over_cap)

    def test_rehashed_open_plans_must_be_current_lawful_policy_prefixes(self):
        request = two_dimension_request()
        initial_result = run_advance(request)
        self.assertEqual(0, initial_result.returncode, initial_result.stderr.decode())
        initial = json.loads(initial_result.stdout)

        cases = []
        dangling = copy.deepcopy(initial["projection"])
        dangling["last_plan"]["slots"][0]["parent_identities"] = ["candidate:missing"]
        rehash_open_plan_slot(dangling, 0)
        cases.append(dangling)

        reservation_drift = copy.deepcopy(initial["projection"])
        reservation_drift["last_plan"]["slots"][0]["reservation"]["runs"] = 0
        rehash_open_plan_slot(reservation_drift, 0)
        cases.append(reservation_drift)

        proposal_drift = copy.deepcopy(initial["projection"])
        proposal_drift["last_plan"]["slots"][0][
            "focus_dimension_identity"
        ] = "dimension:cost"
        rehash_open_plan_slot(proposal_drift, 0)
        cases.append(proposal_drift)

        unseen = copy.deepcopy(initial["projection"])
        unseen["seen_slot_identities"].remove(
            unseen["last_plan"]["slots"][0]["identity"]
        )
        unseen["identity"] = tagged_identity(
            "search-projection/v1",
            {key: value for key, value in unseen.items() if key != "identity"},
        )
        cases.append(unseen)

        for projection in cases:
            with self.subTest(case=cases.index(projection)):
                replay = settled_request(
                    request["policy"],
                    {"projection": projection},
                    [],
                    "candidate:origin",
                )
                self.assert_rejected(replay)

    def test_emitted_projection_replays_as_valid_pending_state(self):
        request = two_dimension_request()
        first = run_advance(request)
        self.assertEqual(0, first.returncode, first.stderr.decode())
        response = json.loads(first.stdout)
        replay = settled_request(
            request["policy"], response, [], "candidate:origin"
        )
        pending = run_advance(replay)
        self.assertEqual(0, pending.returncode, pending.stderr.decode())
        self.assertEqual("pending", json.loads(pending.stdout)["status"])
