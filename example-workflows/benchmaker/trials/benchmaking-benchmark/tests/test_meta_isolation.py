"""Isolation and recomputation: delivered code cannot find the store, ORDER.json or a label; scores are recomputed from the
attempt rows, never read from the delivered summary.json; the staging gate fails on payout, not on names alone."""
import json
import shutil
import sys
import tempfile
import types
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
BB = HERE.parents[1]
SK = BB.parents[1] / "skills" / "benchmaker"
for path in (BB, SK / "scripts"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from metabench import crosscheck, delivered, execute, metrics, pool, registry, store, verify  # noqa: E402
from metabench.execute import Run  # noqa: E402
from metabench.members import cheaters  # noqa: E402

TOY = registry.MetaTask("toy-sum", "toydomain", {"output": "output.json", "inputs": ["input.json"], "number_lines": False},
                        (("oracle", "floor:noop"),), domain_file=HERE.parent / "fixtures" / "toydomain.py")
REF_LABEL, DEF_LABEL = "zz-reference-label", "zz-defect-label"

# The runner a hostile builder could ship: it runs the kit honestly, and also looks everywhere it can reach for the
# store, ORDER.json and the labels, recording what it finds next to its output (`scan` is exec'd by the tests too).
HOSTILE = '''import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def text_of(path):
    try:
        return path.read_text(encoding="utf-8", errors="replace") if path.stat().st_size < 2000000 else ""
    except OSError:
        return ""


def files_under(path, limit=4000):
    if path.is_file():
        return [path]
    return [p for p in list(path.rglob("*"))[:limit] if p.is_file()]


def inside(path, bound):
    return path == bound or bound in path.parents


def scan(tokens, argv, env, cwd, home):
    found = []
    blobs = [("env:" + key, value) for key, value in env.items()] + [("argv", " ".join(argv))]
    handed = [Path(a) for a in argv[1:] if Path(a).exists()]
    handed += [Path(v) for v in env.values() if v and Path(v).is_dir() and (inside(Path(v), Path(tokens["bound"])) or inside(Path(v), home))]
    for path in handed:
        for file in files_under(path):
            blobs.append((str(file), text_of(file)))
    for where, text in blobs:
        if any(needle in text for needle in tokens["needles"]):
            found.append(where)
    bound = Path(tokens["bound"])
    for start in [cwd, home, *handed]:
        for ancestor in [start, *start.parents]:
            if inside(ancestor, bound) and ancestor.is_dir():
                found += [str(p) for p in ancestor.rglob("ORDER.json")]
            if (ancestor / "ORDER.json").exists() or (ancestor / "pools").is_dir():
                found.append(str(ancestor))
    found += [str(p) for p in home.rglob("ORDER.json")] + ([str(home / ".bmk-eval")] if (home / ".bmk-eval").exists() else [])
    return sorted(set(found))


if __name__ == "__main__":
    tokens = json.loads((HERE / "tokens.json").read_text(encoding="utf-8"))
    found = scan(tokens, sys.argv, dict(os.environ), Path.cwd().resolve(), Path.home())
    code = subprocess.call([sys.executable, str(HERE / "kit_run.py"), *sys.argv[1:]])
    mode = sys.argv[1:2]
    if "--output" in sys.argv:
        target = Path(sys.argv[sys.argv.index("--output") + 1])
        if mode == ["full"]:
            (target / "hostile.json").write_text(json.dumps(found), encoding="utf-8")
        elif mode == ["grade"] and target.is_file():
            rows = [json.loads(line) for line in target.read_text(encoding="utf-8").splitlines() if line.strip()]
            target.write_text("".join(json.dumps({**row, "scan": found}) + "\\n" for row in rows), encoding="utf-8")
    sys.exit(code)
'''

# A runner that rewrites the means in summary.json after an honest run and keeps every count.
INFLATE = '''import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
code = subprocess.call([sys.executable, str(HERE / "kit_run.py"), *sys.argv[1:]])
if sys.argv[1:2] == ["full"] and "--output" in sys.argv:
    path = Path(sys.argv[sys.argv.index("--output") + 1]) / "summary.json"
    if path.is_file():
        doc = json.loads(path.read_text(encoding="utf-8"))
        for row in [doc["overall"], *doc["tasks"].values()]:
            row["mean_credit"], row["full_success_rate"] = 1.0, 1.0
        path.write_text(json.dumps(doc), encoding="utf-8")
sys.exit(code)
'''


def setUpModule():
    registry.register(TOY)


def assemble(destination: Path, wrapper: str | None = None, tokens: dict | None = None) -> Path:
    shutil.copytree(SK / "tests" / "fixtures" / "package-mini", destination)
    shutil.copytree(SK / "scripts" / "benchkit", destination / "benchkit", ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copyfile(SK / "scripts" / "run.py", destination / "run.py")
    if wrapper:
        shutil.copyfile(destination / "run.py", destination / "kit_run.py")
        (destination / "run.py").write_text(wrapper, encoding="utf-8")
    if tokens:
        (destination / "tokens.json").write_text(json.dumps(tokens), encoding="utf-8")
    return destination


def toy_pool(st: store.Store) -> tuple[str, Path, dict]:
    members = {REF_LABEL: {"kind": "scripted", "behavior": "oracle"},
               DEF_LABEL: {"kind": "scripted", "behavior": "defect", "defect": "off_by_one"}}
    document = {"meta_task": "toy-sum", "exposure": "private", "members": members, "known_pairs": [
        {"higher": REF_LABEL, "lower": DEF_LABEL, "basis": "construction"}], "contrasts": [], "aa_pairs": [], "unconfirmed": []}
    pool_id, pool_dir = pool.assemble(TOY, pool.normalize(document, "toy-sum"), st)
    return pool_id, pool_dir, pool.read_order(st, "toy-sum", pool_id)


class IsolationTests(unittest.TestCase):
    """A hostile runner finds nothing: not in its argument, environment, agent directory, home or ancestors."""

    @classmethod
    def setUpClass(cls):
        registry.register(TOY)
        cls.tmp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.tmp.name)
        cls.st = store.Store(cls.root / "store")
        cls.pool_id, cls.pool_dir, cls.order = toy_pool(cls.st)
        cls.ids = {spec["label"]: m for m, spec in cls.order["members"].items()}
        cls.tokens = {"needles": [str(cls.st.root), REF_LABEL, DEF_LABEL], "bound": str(cls.root / "out")}
        package = assemble(cls.root / "hostile", HOSTILE, cls.tokens)
        cls.rec = Run("r1", cls.st.run("r1"), cls.root / "out" / "r1")
        execute.intake(cls.rec, package, None)
        cls.results = execute.run_all(cls.rec, cls.pool_dir, cls.order, sorted(cls.order["members"]), jobs=2, cap=120.0, builtins=())

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_the_scanner_finds_what_is_there(self):
        namespace = {"__name__": "scanner", "__file__": str(HERE)}
        exec(HOSTILE, namespace)
        planted = self.root / "out" / "planted"
        planted.mkdir(parents=True)
        (planted / "ORDER.json").write_text("{}", encoding="utf-8")
        found = namespace["scan"](self.tokens, ["x", str(planted)], {"K": str(self.st.root)}, planted, self.root / "nohome")
        self.assertTrue(any("ORDER.json" in item for item in found))
        self.assertIn("env:K", [item for item in found])

    def test_a_hostile_member_run_finds_neither_the_store_nor_ORDER_json_nor_a_label(self):
        for label, member in self.ids.items():
            found = json.loads((self.rec.out_root / member / "hostile.json").read_text(encoding="utf-8"))
            self.assertEqual(found, [], (label, found))
            self.assertEqual(self.results[member]["exec"]["exit_code"], 0, self.results[member]["exec"]["reason"])

    def test_a_hostile_grade_call_finds_nothing_and_sees_no_member_or_label_in_its_paths(self):
        member = self.ids[DEF_LABEL]
        capture = next((self.rec.captures / member).glob("*/workspace"))

        def build(tree):
            shutil.copytree(capture, tree / "t1" / "s1")

        outcome, rows, _ = execute.run_grade(self.rec, "probe", build, 60.0)
        self.assertEqual(outcome.exit_code, 0, outcome.reason)
        self.assertEqual([row["scan"] for row in rows], [[]] * len(rows))
        self.assertTrue(rows)

    def test_member_json_holds_only_the_members_own_behaviour_and_paths_in_the_work_area(self):
        member = self.ids[DEF_LABEL]
        folder = execute.prepare_agent(self.rec, self.pool_dir, member, folder=self.rec.agents / "check")
        text = (folder / "member.json").read_text(encoding="utf-8")
        config = json.loads(text)
        self.assertEqual(sorted(config), ["capture_dir", "domain", "domain_root", "id", "invocations", "io", "runtime", "scope", "spec"])
        self.assertEqual(config["spec"], {"kind": "scripted", "behavior": "defect", "defect": "off_by_one"})
        for needle in (str(self.st.root), REF_LABEL, DEF_LABEL, "ORDER"):
            self.assertNotIn(needle, text)
        work = self.rec.work
        for key in ("capture_dir", "invocations", "runtime", "domain_root", "scope"):
            self.assertTrue(storemod_inside(config[key], work), key)
        self.assertNotIn(str(self.st.root), (folder / "run_agent.py").read_text(encoding="utf-8"))

    def test_nothing_the_run_left_in_the_store_or_the_work_area_names_a_label_outside_the_orders(self):
        self.assertFalse(list(self.rec.work.rglob("ORDER.json")))
        self.assertFalse((self.rec.work / "arenas").exists() and any((self.rec.work / "arenas").iterdir()))

    def test_grade_inputs_and_outputs_have_random_names(self):
        seen = []

        def build(tree):
            seen.append(tree)

        execute.run_grade(self.rec, "a", build, 30.0)
        execute.run_grade(self.rec, "b", build, 30.0)
        names = [p.name for p in seen] + [p.parents[1].name for p in seen]
        self.assertEqual(len(set(names)), len(names))
        for path in seen:
            self.assertRegex(path.name, r"^g[0-9a-f]{6}$")
            self.assertNotIn(self.ids[DEF_LABEL], str(path))
            self.assertTrue(storemod_inside(path, self.rec.arenas))


def storemod_inside(path, parent) -> bool:
    return store.inside(path, parent)


class RecomputeTests(unittest.TestCase):
    """A runner that rewrites summary.json's means and keeps its counts is caught, and scored from the attempts."""

    @classmethod
    def setUpClass(cls):
        registry.register(TOY)
        cls.tmp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.tmp.name)
        cls.st = store.Store(cls.root / "store")
        cls.pool_id, cls.pool_dir, cls.order = toy_pool(cls.st)
        cls.ids = {spec["label"]: m for m, spec in cls.order["members"].items()}
        cls.package = assemble(cls.root / "inflate", INFLATE)
        cls.rec = Run("r1", cls.st.run("r1"), cls.root / "out" / "r1")
        execute.intake(cls.rec, cls.package, None)
        cls.results = execute.run_all(cls.rec, cls.pool_dir, cls.order, sorted(cls.order["members"]), jobs=2, cap=120.0, builtins=())
        cls.tasks = delivered.tasks(cls.rec.intake)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_the_delivered_summary_claims_full_credit_and_the_attempts_do_not(self):
        member = self.ids[DEF_LABEL]
        delivered_summary = json.loads((self.results[member]["out"] / "summary.json").read_text(encoding="utf-8"))
        self.assertEqual(delivered_summary["overall"]["mean_credit"], 1.0)
        found = crosscheck.check_member(self.rec, member, self.results[member]["out"], self.tasks, grade_cap=60.0)
        self.assertEqual(found["grade_mismatches"], [])
        self.assertEqual([m["kind"] for m in found["count_mismatches"] if m["kind"] != "summary-differs"], [])
        self.assertTrue(any(m["kind"] == "summary-differs" and m["where"] == "overall.mean_credit" for m in found["count_mismatches"]))
        self.assertEqual(found["summary"]["overall"]["mean_credit"], 0.5)
        self.assertEqual(metrics.score(found["summary"], "mean_credit"), 0.5)

    def test_an_honest_member_of_the_same_package_is_recomputed_to_the_same_values(self):
        member = self.ids[REF_LABEL]
        found = crosscheck.check_member(self.rec, member, self.results[member]["out"], self.tasks, grade_cap=60.0)
        self.assertEqual(found["summary"]["overall"]["mean_credit"], 1.0)
        self.assertEqual(found["summary"]["counts"]["scored"], 4)
        self.assertEqual(found["count_mismatches"], [])

    def test_a_summary_the_trusted_kit_cannot_recompute_is_reported_and_not_scored(self):
        member = self.ids[REF_LABEL]
        shutil.rmtree(self.rec.intake / "tasks")
        try:
            found = crosscheck.check_member(self.rec, member, self.results[member]["out"], {}, grade_cap=60.0)
        finally:
            shutil.copytree(self.package / "tasks", self.rec.intake / "tasks")
        self.assertIsNone(found["summary"])
        self.assertIn("summary-uncomputable", [m["kind"] for m in found["count_mismatches"]])


class VerifyScoresFromAttemptsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        registry.register(TOY)
        cls.tmp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.tmp.name)
        cls.st = store.Store(cls.root / "store")
        cls.pool_id, cls.pool_dir, cls.order = toy_pool(cls.st)
        cls.report = verify.verify("toy-sum", assemble(cls.root / "inflate", INFLATE), cls.st.root, pool_id=cls.pool_id, jobs=8,
                                   out_root=cls.root / "out", run_id="r-inflate")

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_the_crosscheck_fails_and_the_order_is_measured_from_the_recomputed_scores(self):
        gates = self.report["gates"]
        self.assertFalse(gates["crosscheck"]["pass"])
        self.assertTrue(any(m["kind"] == "summary-differs" for m in gates["crosscheck"]["count_mismatches"]))
        order = self.report["metrics"]["M2_order"]
        self.assertEqual(order["pair_accuracy"], 1.0)      # read from the delivered summaries every member would tie at 1.0
        self.assertEqual(order["ties"], 0)

    def test_the_builtin_runs_are_recomputed_too(self):
        self.assertEqual(self.report["gates"]["G2_reference_and_floor"]["reference_pass_rate"], 1.0)
        self.assertEqual(self.report["gates"]["G2_reference_and_floor"]["noop_mean_credit"], 0.0)


class StagingGateTests(unittest.TestCase):
    def runs(self, **credit):
        return {member: {"summary": {"tasks": {task: {"mean_credit": value, "full_success_rate": value}
                                               for task, value in tasks.items()}, "overall": {"mean_credit": max(tasks.values())}}}
                for member, tasks in credit.items()}

    def finding(self, kind="workspace-file", **extra):
        return {"member": "m1", "task": "t1", "kind": kind, "path": "reference_policy.md", **extra}

    def test_a_name_only_finding_is_a_warning_when_the_cheater_earned_nothing(self):
        found = verify.staging([self.finding(matches_answer=False)], self.runs(m1={"t1": 0.0}))
        self.assertEqual((found["cheater_findings"], len(found["warnings"])), ([], 1))
        gate = metrics.gates(None, None, None, {}, found)["staging"]
        self.assertEqual((gate["pass"], len(gate["warnings"])), (True, 1))

    def test_a_finding_the_cheater_was_paid_for_fails_the_gate(self):
        found = verify.staging([self.finding()], self.runs(m1={"t1": 0.5}))
        self.assertEqual([f["paid"] for f in found["cheater_findings"]], [True])
        self.assertFalse(metrics.gates(None, None, None, {}, found)["staging"]["pass"])

    def test_payout_on_another_task_does_not_count(self):
        found = verify.staging([self.finding()], self.runs(m1={"t1": 0.0, "t2": 1.0}))
        self.assertEqual(found["cheater_findings"], [])

    def test_bytes_that_match_the_oracle_output_or_evaluator_names_fail_without_payout(self):
        runs = self.runs(m1={"t1": 0.0})
        self.assertEqual(len(verify.staging([self.finding(matches_answer=True)], runs)["cheater_findings"]), 1)
        for kind in ("ancestor-file", "verifier-file"):
            self.assertEqual(len(verify.staging([self.finding(kind)], runs)["cheater_findings"]), 1, kind)

    def test_the_cheater_marks_a_leaked_answer_by_its_bytes_not_its_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "reference_policy.md").write_text("how to cite", encoding="utf-8")
            (workspace / ".cache").mkdir()
            (workspace / ".cache" / "expected.json").write_bytes(b'{"sum": 6}')
            found = cheaters.run("read_workspace", workspace, "", {"output": "output.json"}, None, {"output.json": b'{"sum": 6}'})
        flags = {f["path"]: f["matches_answer"] for f in found["findings"]}
        self.assertEqual(flags, {".cache/expected.json": True, "reference_policy.md": False})


class InterruptionAndOracleTests(unittest.TestCase):
    def test_a_usage_limit_is_neither_counted_nor_a_g1_failure(self):
        good = {"exit_code": 0, "status": "completed", "schema_valid": True, "summary": {"counts": {"planned": 4}}}
        limited = {"exit_code": 4, "status": "completed", "schema_valid": True, "interrupted": "usage-limit", "reason": "exit code 4"}
        g1 = metrics.gates({"preflight": {"exit_code": 0}, "members": {"m1": good, "m2": limited}}, None, None, {}, [])["G1_executability"]
        self.assertTrue(g1["pass"], g1["reasons"])
        self.assertEqual((g1["interrupted_runs"], g1["member_runs"]), (["m2"], 1))
        alone = metrics.gates({"preflight": {"exit_code": 0}, "members": {"m2": limited}}, None, None, {}, [])["G1_executability"]
        self.assertFalse(alone["pass"])

    def test_the_executor_marks_a_run_the_kit_stopped_for_the_usage_limit(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            out = tmp / "out" / "m1"
            out.mkdir(parents=True)
            row = {"task": "a", "repeat": 1, "retry": 0, "status": "interrupted", "reason": "account usage limit reached"}
            (out / "attempts.jsonl").write_text(json.dumps(row) + "\n", encoding="utf-8")
            run = Run("r", tmp / "run", tmp / "out")
            outcome = types.SimpleNamespace(status="completed", exit_code=4, reason="", seconds=1.0)
            result = execute._result(run, "m1", outcome, out)
            self.assertEqual(result["exec"]["interrupted"], "usage-limit")
            outcome = types.SimpleNamespace(status="completed", exit_code=1, reason="", seconds=1.0)
            self.assertNotIn("interrupted", execute._result(run, "m1", outcome, out)["exec"])

    def pairs(self, labels, accepted):
        pairs, checked = [], {"m": {"t": []}}
        for i, (label, full) in enumerate(zip(labels, accepted)):
            row = {"task": "t", "repeat": i, "status": "completed", "grading_status": "scored", "full_success": full, "critical_failures": []}
            pairs.append((row, {"invocation": f"i{i}"}))
            checked["m"]["t"].append({"invocation": f"i{i}", "label": label, "recognized": True})
        return pairs, checked

    def test_agreement_with_the_independent_checker_passes(self):
        pairs, checked = self.pairs(["valid", "invalid", "valid", "suboptimal", "valid"], [True, False, True, False, True])
        info, found = crosscheck.oracle_agreement("m", pairs, checked)
        self.assertEqual((info["compared"], info["share"], found), (4, 0.0, []))     # the suboptimal one is not decisive

    def test_a_verifier_that_contradicts_the_checker_on_most_attempts_is_a_mismatch(self):
        pairs, checked = self.pairs(["valid", "invalid", "invalid", "invalid", "valid"], [True, True, True, True, False])
        info, found = crosscheck.oracle_agreement("m", pairs, checked)
        self.assertEqual((info["compared"], len(info["disagreements"])), (5, 4))
        self.assertEqual([f["kind"] for f in found], ["oracle-disagreement"])

    def test_a_handful_of_attempts_or_unlabelled_ones_do_not_decide(self):
        pairs, checked = self.pairs(["invalid", "invalid"], [True, True])
        self.assertEqual(crosscheck.oracle_agreement("m", pairs, checked)[1], [])
        pairs, checked = self.pairs(["lenient", "suboptimal"] * 3, [True] * 6)
        self.assertEqual(crosscheck.oracle_agreement("m", pairs, checked)[0]["compared"], 0)


if __name__ == "__main__":
    unittest.main()
