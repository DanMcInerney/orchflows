"""Routing summary and CLI regression cases."""

from ._support import *

class TestRoutingSummary(unittest.TestCase):
    @staticmethod
    def _record(adapter_set, expected, observed, repeat=1):
        return {
            "adapter_set": adapter_set,
            "case": f"{expected}-{observed}-{repeat}",
            "repeat": repeat,
            "expected": expected,
            "observed": observed,
            "match": expected == observed,
        }

    def test_the_summary_counts_matches_misroutes_and_unrouted_per_set(self):
        records = [
            self._record("all", "ticket", "ticket"),
            self._record("all", "ticket", "fix"),
            self._record("all", "answer", "answer"),
            self._record("all", "named:evolve", "unrouted"),
            self._record("four", "ticket", "ticket"),
            self._record("four", "named:evolve", "named:evolve"),
        ]
        summary = routing_live.summarize(records)

        self.assertEqual(4, summary["all"]["n"])
        self.assertEqual(2, summary["all"]["matched"])
        self.assertEqual(0.5, summary["all"]["misroute_rate"])
        self.assertEqual(1, summary["all"]["unrouted"])
        self.assertEqual(2, summary["four"]["n"])
        self.assertEqual(0.0, summary["four"]["misroute_rate"])
        self.assertEqual(0, summary["four"]["unrouted"])

    def test_an_error_leaves_the_misroute_rate_and_never_enters_it(self):
        """A session that failed before it could route is neither a route nor
        a misroute. Counting it as one made the rate a measure of how often
        the CLI was reachable."""

        records = [
            self._record("all", "ticket", "ticket"),
            self._record("all", "answer", "answer"),
            self._record("all", "fix", "ticket"),
            self._record("all", "named:evolve", "error"),
        ]
        summary = routing_live.summarize(records)["all"]
        self.assertEqual(4, summary["n"])
        self.assertEqual(1, summary["errors"])
        # one misroute over the three sessions that ran
        self.assertEqual(round(1 / 3, 4), summary["misroute_rate"])

    def test_a_set_that_only_errored_reports_no_rate_rather_than_a_perfect_one(self):
        summary = routing_live.summarize(
            [self._record("four", "ticket", "error")]
        )["four"]
        self.assertEqual(1, summary["errors"])
        self.assertEqual(0.0, summary["misroute_rate"])

    def test_the_summary_records_the_spend_and_the_budget(self):
        records = [
            dict(self._record("all", "ticket", "ticket"), cost_usd=0.02),
            dict(self._record("all", "fix", "fix"), cost_usd=0.03),
        ]
        summary = routing_live.summarize(records, max_budget_usd=0.04)["all"]
        self.assertEqual(0.05, summary["cost_usd"])
        self.assertEqual(0.04, summary["max_budget_usd"])
        self.assertTrue(summary["budget_stopped"])

    def test_the_by_class_breakdown_buckets_by_the_expected_class(self):
        records = [
            self._record("all", "named:evolve", "named:evolve"),
            self._record("all", "named:renovate", "ticket"),
            self._record("all", "fix", "fix"),
        ]
        by_class = routing_live.summarize(records)["all"]["by_class"]
        self.assertEqual({"named", "fix"}, set(by_class))
        self.assertEqual(2, by_class["named"]["n"])
        self.assertEqual(1, by_class["named"]["matched"])
        self.assertEqual(0.5, by_class["named"]["misroute_rate"])
        self.assertEqual(0.0, by_class["fix"]["misroute_rate"])

    def test_an_empty_record_set_summarizes_to_nothing_rather_than_dividing_by_zero(self):
        self.assertEqual({}, routing_live.summarize([]))

    def test_the_table_names_every_set_and_its_rate(self):
        summary = routing_live.summarize(
            [self._record("all", "ticket", "fix"), self._record("four", "ticket", "ticket")]
        )
        table = routing_live.format_table(summary)
        self.assertIn("all", table)
        self.assertIn("four", table)
        self.assertIn("1.0", table)


class TestRoutingBenchMain(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.out = self.tmp / "bench.json"

    def tearDown(self):
        self._tmp.cleanup()

    def _main(self, argv, records):
        with mock.patch.object(routing_live, "_claude_command", return_value=["claude"]), \
                mock.patch.object(routing_live, "run_benchmark", return_value=records) as run, \
                contextlib.redirect_stdout(io.StringIO()) as printed:
            code = routing_live.main(argv)
        return code, printed.getvalue(), run

    def test_it_measures_and_exits_zero_even_when_everything_misroutes(self):
        records = [
            {
                "adapter_set": "four",
                "case": "t1",
                "repeat": 1,
                "expected": "ticket",
                "observed": "unrouted",
                "match": False,
            }
        ]
        code, printed, _ = self._main(["--adapters", "four", "--out", str(self.out)], records)
        self.assertEqual(0, code)
        self.assertIn("four", printed)

    def test_the_written_json_carries_the_records_and_the_summary(self):
        records = [
            {
                "adapter_set": "all",
                "case": "a1",
                "repeat": 1,
                "expected": "answer",
                "observed": "answer",
                "match": True,
            }
        ]
        self._main(["--adapters", "all", "--out", str(self.out)], records)
        payload = json.loads(self.out.read_text(encoding="utf-8"))
        self.assertEqual(records, payload["records"])
        self.assertEqual(1, payload["summary"]["all"]["n"])
        self.assertEqual(0.0, payload["summary"]["all"]["misroute_rate"])
        # Written as bytes: this host's default text write would emit CRLF.
        self.assertNotIn(b"\r\n", self.out.read_bytes())

    def test_both_is_the_default_and_names_the_two_sets(self):
        _, _, run = self._main(["--out", str(self.out)], [])
        self.assertEqual(("all", "four"), run.call_args.kwargs["adapter_sets"])

    def test_the_repeat_and_turn_bounds_reach_the_run(self):
        _, _, run = self._main(
            ["--adapters", "four", "--repeat", "3", "--max-turns", "5", "--out", str(self.out)],
            [],
        )
        self.assertEqual(3, run.call_args.kwargs["repeat"])
        self.assertEqual(5, run.call_args.kwargs["max_turns"])
        self.assertEqual(("four",), run.call_args.kwargs["adapter_sets"])

    def test_the_budget_flag_reaches_the_run_and_the_written_payload(self):
        code, _, run = self._main(
            ["--adapters", "four", "--max-budget-usd", "1.50", "--out", str(self.out)], [],
        )
        self.assertEqual(0, code)
        self.assertEqual(1.50, run.call_args.kwargs["max_budget_usd"])
        payload = json.loads(self.out.read_text(encoding="utf-8"))
        self.assertEqual(1.50, payload["max_budget_usd"])

    def test_no_budget_is_the_default(self):
        _, _, run = self._main(["--out", str(self.out)], [])
        self.assertIsNone(run.call_args.kwargs["max_budget_usd"])

    def test_it_loads_the_shipped_case_set_by_default(self):
        _, _, run = self._main(["--out", str(self.out)], [])
        shipped = json.loads(ROUTING_CASES.read_text(encoding="utf-8"))
        self.assertEqual(
            [case["id"] for case in shipped],
            [case["id"] for case in run.call_args.kwargs["cases"]],
        )
