"""Pool generation: anonymous members, ORDER.json, the private runtime copy, dev-pool normalization, store refusals."""
import contextlib
import io
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
BB = HERE.parents[1]
SCRIPTS = BB.parents[1] / "skills" / "benchmaker" / "scripts"
for path in (BB, SCRIPTS):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from metabench import cli, pool, registry, store  # noqa: E402
from metabench.members import cheaters, floors  # noqa: E402

TOY = registry.MetaTask("toy-sum", "toydomain", {"output": "output.json", "inputs": ["input.json"], "number_lines": False},
                        (("oracle", "floor:noop"),), domain_file=HERE.parent / "fixtures" / "toydomain.py")
REAL = ("schedule-nosolver", "logtriage-llm", "calendar-skill")
ID = re.compile(r"m[0-9a-f]{6}$")


def setUpModule():
    registry.register(TOY)


class PoolCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.store = store.Store(self.root / "store")

    def generate(self, meta_task="toy-sum", **options):
        pool_id, path = pool.generate(meta_task, self.store, **options)
        return pool_id, path, json.loads((path / "ORDER.json").read_text(encoding="utf-8"))


class AnonymityTests(PoolCase):
    def test_no_member_directory_or_file_reveals_behaviour(self):
        _, path, order = self.generate()
        words = set()
        for spec in order["members"].values():
            words |= {str(spec.get(k)).lower() for k in ("behavior", "name", "defect", "label") if spec.get(k)}
        words |= {"oracle", "defect", "ladder", "floor", "cheater", "heuristic", "noop", "tamper", "empty"}
        listing = list((path / "members").rglob("*"))
        self.assertTrue(listing)
        for item in listing:
            relative = item.relative_to(path).as_posix().lower()
            for word in words:
                self.assertNotIn(word, relative)
            if item.is_file():
                text = item.read_text(encoding="utf-8").lower()
                for word in ("oracle", "ladder", "cheater", "tamper", "noop"):
                    self.assertNotIn(word, text, item.name)

    def test_order_json_exists_once_and_only_in_the_store_pool(self):
        pool_id, path, _ = self.generate()
        found = list(self.root.rglob("ORDER.json"))
        self.assertEqual(found, [path / "ORDER.json"])
        for config in (path / "members").glob("*/member.json"):
            data = json.loads(config.read_text(encoding="utf-8"))
            self.assertEqual(set(data), {"id", "order", "runtime", "store"})
            self.assertEqual(Path(data["order"]), path / "ORDER.json")

    def test_ids_are_random_hex_and_match_directories(self):
        _, path, order = self.generate()
        names = sorted(p.name for p in (path / "members").iterdir())
        self.assertEqual(names, sorted(order["members"]))
        self.assertTrue(all(ID.match(name) for name in names))
        _, _, other = self.generate()
        self.assertFalse(set(order["members"]) & set(other["members"]))


class OrderTests(PoolCase):
    def test_order_maps_ids_to_behaviours_and_pairs_use_ids(self):
        _, _, order = self.generate()
        by_label = {spec["label"]: m for m, spec in order["members"].items()}
        for label in ("oracle", "defect:off_by_one", "defect:drop_last", "heuristic:first_number", "ladder:0.15", "ladder:0.4",
                      "ladder:0.7", "ladder:0.4-b", "floor:noop", "floor:empty", "floor:echo_input"):
            self.assertIn(label, by_label)
        for name in cheaters.NAMES:
            self.assertIn(f"cheater:{name}", by_label)
        ids = set(order["members"])
        for pair in [*order["known_pairs"], *order["contrasts"]]:
            self.assertTrue({pair["higher"], pair["lower"]} <= ids)
        known = {(p["higher"], p["lower"]) for p in order["known_pairs"]}
        self.assertIn((by_label["oracle"], by_label["defect:off_by_one"]), known)
        self.assertIn((by_label["ladder:0.15"], by_label["ladder:0.4"]), known)
        self.assertIn((by_label["ladder:0.7"], by_label["cheater:tamper"]), known)
        self.assertEqual(order["aa_pairs"], [[by_label["ladder:0.4"], by_label["ladder:0.4-b"]]])
        self.assertEqual([(c["higher"], c["lower"]) for c in order["contrasts"]], [(by_label["oracle"], by_label["floor:noop"])])
        self.assertEqual((order["meta_task"], order["domain"], order["killable"], order["unconfirmed"]), ("toy-sum", "toydomain", {}, []))

    def test_ladders_carry_q_and_the_aa_copy_shares_it(self):
        _, _, order = self.generate()
        ladders = {s["label"]: s["q"] for s in order["members"].values() if s["behavior"] == "ladder"}
        self.assertEqual(ladders, {"ladder:0.15": 0.15, "ladder:0.4": 0.4, "ladder:0.7": 0.7, "ladder:0.4-b": 0.4})

    def test_real_domains_compose_every_defect_and_heuristic_and_keep_diagnostics_out_of_pairs(self):
        for meta_task in REAL:
            with self.subTest(meta_task):
                domain = registry.load_domain(registry.get(meta_task))
                _, _, order = self.generate(meta_task)
                labels = {s["label"]: m for m, s in order["members"].items()}
                for name in domain.DEFECTS:
                    self.assertIn(f"defect:{name}", labels)
                for name in domain.HEURISTICS:
                    self.assertTrue(f"heuristic:{name}" in labels or f"floor:{name}" in labels, name)
                lower = {p["lower"] for p in order["known_pairs"]}
                for name in getattr(domain, "DIAGNOSTIC", ()):
                    self.assertIn(f"defect:{name}", labels)
                    self.assertNotIn(labels[f"defect:{name}"], lower)
                self.assertTrue(order["contrasts"])
                self.assertTrue(all(c["must_resolve"] for c in order["contrasts"]))

    def test_private_operators_join_the_pool(self):
        private = self.store.private_members()
        private.mkdir(parents=True)
        (private / "extra.py").write_text(
            "DEFECTS = {'double_it': lambda instance, rng: {'output.json': b'{\"sum\": 0}'}}\n", encoding="utf-8")
        (private / "other.py").write_text("META_TASKS = ['elsewhere']\nDEFECTS = {'x': lambda i, r: {}}\n", encoding="utf-8")
        _, _, order = self.generate()
        privates = [s for s in order["members"].values() if s["kind"] == "private"]
        self.assertEqual([(s["module"], s["behavior"], s["source"]) for s in privates], [("private_members/extra.py", "double_it", "DEFECTS")])
        member = next(m for m, s in order["members"].items() if s["kind"] == "private")
        self.assertIn(member, {p["lower"] for p in order["known_pairs"]})

    def test_llm_members_only_with_include_llm(self):
        _, _, plain = self.generate()
        self.assertFalse([s for s in plain["members"].values() if s["kind"] == "llm"])
        _, _, order = self.generate(include_llm=True)
        llm = {s["label"]: s for s in order["members"].values() if s["kind"] == "llm"}
        self.assertEqual(sorted(llm), ["haiku-low", "haiku-low-b", "sonnet-low"])
        self.assertEqual(llm["haiku-low"]["io"], TOY.io)
        self.assertEqual(len(order["unconfirmed"]), 1)
        self.assertEqual(len(order["aa_pairs"]), 2)
        self.assertEqual(pool.members_of(order, llm=False), sorted(m for m, s in order["members"].items() if s["kind"] != "llm"))

    def test_real_llm_pools_name_valid_harness_defects_and_copy_skills(self):
        from metabench.members import llm

        for meta_task in REAL:
            with self.subTest(meta_task):
                _, path, order = self.generate(meta_task, include_llm=True)
                members = [s for s in order["members"].values() if s["kind"] == "llm"]
                self.assertGreaterEqual(len(members), 4)
                for spec in members:
                    llm.defect_of(spec)
                    self.assertIn("io", spec)
                self.assertTrue(order["unconfirmed"])
        _, path, order = self.generate("calendar-skill", include_llm=True)
        specs = {s["label"]: s for s in order["members"].values() if s["kind"] == "llm"}
        skill, hidden = Path(specs["haiku-skill"]["skill"]), specs["haiku-hidden-skill"]
        self.assertTrue((skill / ".claude-plugin" / "plugin.json").is_file())
        self.assertEqual(hidden["skill"], specs["haiku-skill"]["skill"])
        harmful = Path(specs["haiku-harmful-skill"]["harness_defect"].partition(":")[2])
        self.assertNotEqual((harmful / "skills" / "booking-rules" / "SKILL.md").read_text(encoding="utf-8"),
                            (skill / "skills" / "booking-rules" / "SKILL.md").read_text(encoding="utf-8"))
        self.assertTrue(str(skill).startswith(str(path)))


class RuntimeTests(PoolCase):
    def test_runtime_copy_is_private_and_importable_without_the_repository(self):
        pool_id, path, _ = self.generate()
        runtime = self.store.runtime(pool_id)
        for relative in ("metabench/members/shim.py", "metabench/members/llm.py", "metabench/builders.py",
                         "metabench/transcripts.py", "metabench/domains/toydomain.py", "metabench/domains/scheduling.py",
                         "benchkit/launch.py", "benchkit/__init__.py"):
            self.assertTrue((runtime / relative).is_file(), relative)
        self.assertFalse(list(runtime.rglob("ORDER.json")))
        code = ("import sys; sys.path.insert(0, sys.argv[1]); import metabench.members.shim as s, metabench.members.llm, "
                "benchkit.launch, metabench.domains.toydomain, metabench.domains.calendar; print(s.__file__)")
        done = subprocess.run([sys.executable, "-c", code, str(runtime)], cwd=self.root, capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertTrue(Path(done.stdout.strip()).is_relative_to(runtime))

    def test_launcher_is_the_only_code_in_a_member_directory(self):
        _, path, order = self.generate()
        member = next(iter(order["members"]))
        self.assertEqual(sorted(p.name for p in (path / "members" / member).iterdir()), ["member.json", "run_agent.py"])


class DevPoolTests(PoolCase):
    def test_the_three_dev_pools_share_one_shape(self):
        docs = {mt: json.loads((registry.get(mt).meta_dir / "dev-pool.json").read_text(encoding="utf-8")) for mt in REAL}
        self.assertEqual(len({tuple(sorted(doc)) for doc in docs.values()}), 1)
        for mt, doc in docs.items():
            normal = pool.normalize(doc, mt)
            self.assertEqual(normal["exposure"], "exposed")
            self.assertEqual(sorted(normal), sorted(["meta_task", "exposure", "use", *pool.POOL_KEYS]))
            self.assertTrue(normal["aa_pairs"])

    def test_dev_pools_generate_with_anonymous_members(self):
        for mt in REAL:
            with self.subTest(mt):
                document = pool.load_dev(registry.get(mt))
                _, path, order = self.generate(mt, dev=True)
                self.assertEqual(len(order["members"]), len(document["members"]))
                self.assertEqual(order["exposure"], "exposed")
                self.assertTrue(all(ID.match(m) for m in order["members"]))
                self.assertFalse([p for p in (path / "members").rglob("*") if "oracle" in p.name or "ladder" in p.name])

    def test_normalize_accepts_exposure_and_rejects_unknown_members(self):
        doc = {"meta_task": "toy-sum", "exposure": "private", "members": {"a": {"kind": "scripted"}}, "known_pairs": []}
        self.assertEqual(pool.normalize(doc)["exposure"], "private")
        self.assertEqual(pool.normalize({**doc, "label": "exposed", "exposure": None})["exposure"], "exposed")
        with self.assertRaisesRegex(ValueError, "unknown member 'b'"):
            pool.normalize({**doc, "known_pairs": [{"higher": "a", "lower": "b"}]})
        with self.assertRaisesRegex(ValueError, "not 'other'"):
            pool.normalize(doc, "other")
        with self.assertRaisesRegex(ValueError, "no members"):
            pool.normalize({"meta_task": "toy-sum"})


class GenericMemberTests(unittest.TestCase):
    def test_floor_and_cheater_names(self):
        self.assertEqual(floors.GENERIC, ("noop", "empty", "echo_input"))
        self.assertEqual(set(cheaters.NAMES), set(cheaters.BEHAVIORS))
        with tempfile.TemporaryDirectory() as tmp, self.assertRaises(ValueError):
            floors.run("mystery", Path(tmp), "", {})


class StoreTests(unittest.TestCase):
    def test_store_inside_the_repository_is_refused_and_not_created(self):
        inside = store.REPO / "example-workflows" / "benchmaker" / "x-store-should-not-exist"
        with self.assertRaises(store.StoreError):
            store.resolve(inside)
        self.assertFalse(inside.exists())

    def test_store_and_out_root_or_work_root_must_not_contain_each_other(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            with self.assertRaises(store.StoreError):
                store.resolve(tmp / "out" / "store", out_root=tmp / "out")
            with self.assertRaises(store.StoreError):
                store.resolve(tmp / "work" / "meta", work_root=tmp / "work")
            with self.assertRaises(store.StoreError):
                store.resolve(tmp / "store", out_root=tmp / "store" / "out")
            self.assertEqual(store.resolve(tmp / "store", out_root=tmp / "out", work_root=tmp / "work"), (tmp / "store").resolve())

    def test_default_store_follows_the_environment_variable(self):
        self.assertEqual(store.default_store({"METABENCH_STORE": "somewhere"}), Path("somewhere"))
        self.assertEqual(store.default_store({}), Path.home() / ".bmk-eval" / "meta")

    def test_cli_refuses_a_store_in_the_repository(self):
        inside = store.REPO / "x-store-should-not-exist"
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            code = cli.main(["pool", "generate", "--meta-task", "schedule-nosolver", "--store", str(inside)])
        self.assertEqual(code, cli.REFUSED)
        self.assertIn("must not contain each other", err.getvalue())
        self.assertFalse(inside.exists())

    def test_json_files_are_strict_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            store.write_json(Path(tmp) / "a.json", {"x": float("nan"), "y": [float("inf"), 1.5]})
            self.assertEqual(json.loads((Path(tmp) / "a.json").read_text(encoding="utf-8")), {"x": None, "y": [None, 1.5]})


if __name__ == "__main__":
    unittest.main()
