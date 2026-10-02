"""The executor and `verify` end to end on package-mini with the toy domain."""
import contextlib
import io
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
BB = HERE.parents[1]
SK = BB.parents[1] / "skills" / "benchmaker"
for path in (BB, SK / "scripts"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from metabench import cli, execute, metrics, pool, registry, store, verify  # noqa: E402
from metabench.execute import Run  # noqa: E402

TOY = registry.MetaTask("toy-sum", "toydomain", {"output": "output.json", "inputs": ["input.json"], "number_lines": False},
                        (("oracle", "floor:noop"),), domain_file=HERE.parent / "fixtures" / "toydomain.py")
PROMPT = "Add the numbers in `input.json` and write `{\"sum\": <total>}` to `output.json`. Example output: {\"sum\": 6}\n"


def setUpModule():
    registry.register(TOY)


def assemble_mini(destination: Path) -> Path:
    shutil.copytree(SK / "tests" / "fixtures" / "package-mini", destination)
    shutil.copytree(SK / "scripts" / "benchkit", destination / "benchkit", ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copyfile(SK / "scripts" / "run.py", destination / "run.py")
    return destination


def document(**members):
    return {"meta_task": "toy-sum", "exposure": "private", "members": members, "known_pairs": [], "contrasts": [],
            "aa_pairs": [], "unconfirmed": []}


def scripted(behavior, **fields):
    return {"kind": "scripted", "behavior": behavior, "origin": "synthetic", **fields}


class ExecutorTests(unittest.TestCase):
    def test_environment_is_an_allow_list_without_claude_variables(self):
        base = {"PATH": "p", "SystemRoot": "C:\\Windows", "TEMP": "x", "CLAUDECODE": "1", "CLAUDE_CODE_EFFORT_LEVEL": "high",
                "ANTHROPIC_API_KEY": "k", "GITHUB_TOKEN": "t", "HOME": "h", "Path": "p2"}
        env = execute.clean_env(Path("T"), base=base)
        self.assertEqual({k.upper() for k in env}, {"PATH", "SYSTEMROOT", "HOME", "TEMP", "TMP", "PYTHONDONTWRITEBYTECODE"})
        self.assertEqual((env["TEMP"], env["TMP"]), ("T", "T"))
        llm = execute.clean_env(Path("T"), base=base, llm=True)
        self.assertEqual(llm["ANTHROPIC_API_KEY"], "k")
        self.assertNotIn("CLAUDECODE", llm)
        self.assertNotIn("GITHUB_TOKEN", llm)

    def test_cap_is_the_suite_deadline_plus_slack(self):
        with tempfile.TemporaryDirectory() as tmp:
            package = Path(tmp)
            self.assertEqual(execute.cap_seconds(package), execute.DEFAULT_CAP)
            (package / "suite.json").write_text('{"deadline_seconds": 120}', encoding="utf-8")
            self.assertEqual(execute.cap_seconds(package), 120 + execute.SLACK_SECONDS)
            self.assertEqual(execute.cap_seconds(package, 7), 7.0)

    def test_intake_refuses_a_directory_that_is_not_a_package(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = Run("r", Path(tmp) / "run", Path(tmp) / "out")
            with self.assertRaises(ValueError):
                execute.intake(run, Path(tmp), None)

    def test_intake_keeps_a_pristine_copy_and_flags_reference_files_but_not_the_kit(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            package = assemble_mini(tmp / "pkg")
            reference = tmp / "ref"
            (reference / "sources").mkdir(parents=True)
            shutil.copyfile(package / "tasks" / "t01" / "tests" / "verify.py", reference / "sources" / "verify_template.py")
            shutil.copyfile(package / "run.py", reference / "run.py")
            (reference / "sources" / "other.txt").write_text("different", encoding="utf-8")
            run = Run("r", tmp / "run", tmp / "out")
            copied = execute.intake(run, package, reference)
            self.assertEqual(sorted(copied), ["tasks/t01/tests/verify.py", "tasks/t02/tests/verify.py"])
            self.assertTrue((run.intake / "run.py").is_file() and (run.package / "benchkit").is_dir())
            self.assertEqual((run.intake / "suite.json").read_bytes(), (package / "suite.json").read_bytes())

    def test_a_runner_that_hangs_is_killed_at_the_cap_and_recorded(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            package = tmp / "pkg"
            package.mkdir()
            (package / "suite.json").write_text("{}", encoding="utf-8")
            (package / "run.py").write_text("import time\ntime.sleep(60)\n", encoding="utf-8")
            run = Run("r", tmp / "run", tmp / "out")
            execute.intake(run, package, None)
            for folder in (run.agents, run.invocations, run.captures):
                folder.mkdir(parents=True)
            member_dir = tmp / "pool" / "members" / "m000001"
            member_dir.mkdir(parents=True)
            (member_dir / "member.json").write_text("{}", encoding="utf-8")
            result = execute.run_member(run, tmp / "pool", "m000001", {"kind": "scripted"}, 1.0)
            self.assertEqual(result["exec"]["status"], "timeout")
            self.assertFalse(result["exec"]["schema_valid"])
            self.assertIsNone(result["run"]["summary"])
            gates = metrics.gates({"preflight": {"exit_code": 0}, "members": {"m000001": result["exec"]}}, None, None, None, None)
            self.assertFalse(gates["G1_executability"]["pass"])
            self.assertGreater(gates["G1_executability"]["infrastructure_error_share"], 0)


class VerifyEndToEndTests(unittest.TestCase):
    """One `verify` of the assembled package-mini against the toy pool (with LLM members present but not run)."""

    @classmethod
    def setUpClass(cls):
        registry.register(TOY)
        cls.tmp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.tmp.name)
        cls.package = assemble_mini(cls.root / "package-mini")
        cls.store = store.Store(cls.root / "store")
        cls.pool_id, cls.pool_dir = pool.generate("toy-sum", cls.store, include_llm=True)
        cls.order = pool.read_order(cls.store, "toy-sum", cls.pool_id)
        cls.report = verify.verify("toy-sum", cls.package, cls.store.root, pool_id=cls.pool_id, jobs=8, out_root=cls.root / "out",
                                   run_id="r-test")
        cls.run_dir = cls.store.run("r-test")
        cls.ledger = cls.root / "out" / "r-test.work" / "ledger"

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_every_gate_passes_and_the_report_files_exist(self):
        gates = self.report["gates"]
        self.assertTrue(metrics.gates_pass(gates), json.dumps(gates, indent=1)[:2000])
        self.assertEqual(self.report["gates"]["staging"]["cheater_findings"], [])
        on_disk = json.loads((self.run_dir / "report.json").read_text(encoding="utf-8"))
        self.assertEqual(on_disk["gates"].keys(), gates.keys())
        self.assertEqual((on_disk["meta_task"], on_disk["pool"], on_disk["arm"]), ("toy-sum", self.pool_id, "reference"))
        text = (self.run_dir / "report.md").read_text(encoding="utf-8")
        self.assertLess(text.index("## Gates"), text.index("## Metrics"))
        self.assertNotIn("FAIL", text.split("## Metrics")[0])

    def test_every_scripted_member_and_both_builtins_ran_and_llm_members_did_not(self):
        scripted_ids = [m for m, s in self.order["members"].items() if s["kind"] != "llm"]
        llm_ids = [m for m, s in self.order["members"].items() if s["kind"] == "llm"]
        self.assertEqual(self.report["gates"]["G1_executability"]["member_runs"], len(scripted_ids) + 2)
        for member in scripted_ids:
            self.assertTrue((self.root / "out" / "r-test" / member / "summary.json").is_file(), member)
            self.assertTrue((self.ledger / "invocations" / f"{member}.jsonl").is_file(), member)
        for member in llm_ids:
            self.assertFalse((self.root / "out" / "r-test" / member).exists())
            self.assertFalse((self.ledger / "invocations" / f"{member}.jsonl").exists())
        for name in ("reference", "noop"):
            self.assertTrue((self.root / "out" / "r-test" / name / "summary.json").is_file())

    def test_delivered_code_ran_outside_the_store_and_left_nothing_there(self):
        self.assertFalse((self.run_dir / "packages").exists())
        self.assertFalse(list(self.run_dir.rglob("attempts.jsonl")))
        self.assertFalse((self.root / "out" / "r-test.work" / "arenas").exists())
        self.assertTrue((self.run_dir / "intake" / "run.py").is_file())
        self.assertEqual(list(self.root.rglob("ORDER.json")), [self.pool_dir / "ORDER.json"])

    def test_the_crosscheck_regraded_every_captured_attempt_and_both_builtins(self):
        cross = self.report["gates"]["crosscheck"]
        self.assertTrue(cross["pass"])
        self.assertEqual(cross["regraded"], 4 * (2 + len([m for m, s in self.order["members"].items() if s["kind"] != "llm"])))

    def test_the_verifier_check_and_ordering_are_measured(self):
        m = self.report["metrics"]
        self.assertEqual((m["M6_verifier"]["tpr"], m["M6_verifier"]["tnr"]), (1.0, 1.0))
        self.assertEqual(m["M6_verifier"]["oracle_coverage"], 1.0)
        self.assertGreater(m["M2_order"]["pairs"], 0)
        self.assertEqual(m["M2_order"]["contradicted"], [])
        self.assertEqual(m["M1_cheaters"]["hackable_tasks"], [])
        self.assertEqual(m["M3_kill"]["killable"], 2)           # both toy defects are wrong on both tasks
        self.assertEqual(self.report["metrics"]["M9_claims"]["contradicted"], [])

    def test_equivalent_defects_leave_the_kill_rate_and_move_their_pairs_to_unconfirmed(self):
        by_label = {s["label"]: m for m, s in self.order["members"].items()}
        order = verify.prune(self.order, set(self.order["members"]),
                             {by_label["defect:off_by_one"]: {"basis": "checker", "confirmed": False}})
        lower = {p["lower"] for p in order["known_pairs"]}
        self.assertNotIn(by_label["defect:off_by_one"], lower)
        self.assertIn(by_label["defect:off_by_one"], {p["lower"] for p in order["unconfirmed"]})
        self.assertIn(by_label["defect:drop_last"], lower)

    def test_the_command_line_help_and_plan_work_and_launch_nothing(self):
        done = subprocess.run([sys.executable, "-m", "metabench", "--help"], cwd=BB, capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stderr)
        for word in ("material", "pool", "slice", "confirm", "verify", "refpkg", "selfcheck", "build", "report"):
            self.assertIn(word, done.stdout)
        work = self.root / "no-work-root"
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = cli.main(["build", "--arm", "plain", "--meta-task", "schedule-nosolver", "--model", "claude-sonnet-5-5", "--effort", "low",
                             "--budget", "small", "--plan", "--store", str(self.root / "store"), "--work-root", str(work)])
        self.assertEqual(code, 0)
        self.assertIn("nothing is launched", out.getvalue())
        self.assertFalse(work.exists())

    def test_the_report_command_tabulates_runs(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(cli.main(["report", "--runs", "r-test", "--store", str(self.root / "store")]), 0)
        self.assertIn("| r-test | reference | reference | pass |", out.getvalue())


if __name__ == "__main__":
    unittest.main()
