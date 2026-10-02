"""Reference-package assembly and `confirm` on a slice, with the toy domain and package-mini."""
import json
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

from metabench import confirm, pool, refpkg, registry, store  # noqa: E402

TOY = registry.MetaTask("toy-sum", "toydomain", {"output": "output.json", "inputs": ["input.json"], "number_lines": False},
                        (("oracle", "floor:noop"),), domain_file=HERE.parent / "fixtures" / "toydomain.py")


def setUpModule():
    registry.register(TOY)


def assemble_mini(destination: Path) -> Path:
    import shutil

    shutil.copytree(SK / "tests" / "fixtures" / "package-mini", destination)
    shutil.copytree(SK / "scripts" / "benchkit", destination / "benchkit", ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copyfile(SK / "scripts" / "run.py", destination / "run.py")
    return destination


def document(**members):
    return {"meta_task": "toy-sum", "exposure": "private", "members": members, "known_pairs": [], "contrasts": [],
            "aa_pairs": [], "unconfirmed": []}


def scripted(behavior, **fields):
    return {"kind": "scripted", "behavior": behavior, "origin": "synthetic", **fields}


class ReferencePackageTests(unittest.TestCase):
    def test_assemble_runs_the_generator_and_copies_the_kit(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            reference = tmp / "reference"
            reference.mkdir()
            (reference / "generate.py").write_text(
                "import argparse, shutil\nfrom pathlib import Path\np = argparse.ArgumentParser()\n"
                "p.add_argument('--instances'); p.add_argument('--out')\na = p.parse_args()\n"
                f"shutil.copytree({str(SK / 'tests' / 'fixtures' / 'package-mini')!r}, a.out)\n"
                "Path(a.out, 'instances.txt').write_text(a.instances)\n", encoding="utf-8")
            registry.register(registry.MetaTask("toy-ref", "toydomain", TOY.io, domain_file=TOY.domain_file, reference=reference))
            out = refpkg.assemble("toy-ref", tmp / "pkg")
            self.assertEqual((out / "instances.txt").read_text(encoding="utf-8"), "offline")
            self.assertEqual((out / "run.py").read_bytes(), (store.KIT / "run.py").read_bytes())
            self.assertTrue((out / "benchkit" / "cli.py").is_file())
            self.assertFalse(list(out.rglob("__pycache__")))
            done = subprocess.run([sys.executable, "run.py", "smoke", "--agent", "@reference", "--output", str(tmp / "o")], cwd=out,
                                  capture_output=True, text=True)
            self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
            public = refpkg.assemble("toy-ref", tmp / "pkg2", instances="public", store_root=tmp / "store")
            self.assertEqual((public / "instances.txt").read_text(encoding="utf-8"), str(tmp / "store" / "material" / "toy-ref" / "public"))
            with self.assertRaises(refpkg.RefpkgError):
                refpkg.assemble("toy-ref", tmp / "pkg")           # not empty
            registry.register(registry.MetaTask("toy-none", "toydomain", TOY.io, domain_file=TOY.domain_file, reference=tmp / "missing"))
            with self.assertRaisesRegex(refpkg.RefpkgError, "no generator"):
                refpkg.assemble("toy-none", tmp / "pkg3")

    def test_a_failing_generator_is_reported_with_its_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            reference = Path(tmp) / "reference"
            reference.mkdir()
            (reference / "generate.py").write_text("raise SystemExit('boom: no instances')\n", encoding="utf-8")
            registry.register(registry.MetaTask("toy-bad", "toydomain", TOY.io, domain_file=TOY.domain_file, reference=reference))
            with self.assertRaisesRegex(refpkg.RefpkgError, "boom: no instances"):
                refpkg.assemble("toy-bad", Path(tmp) / "pkg")

    def test_slice_build_needs_held_out_material(self):
        with tempfile.TemporaryDirectory() as tmp, self.assertRaisesRegex(refpkg.RefpkgError, "material fetch"):
            refpkg.build_slice("toy-sum", store.Store(Path(tmp) / "store"))


class ConfirmTests(unittest.TestCase):
    def checked(self, scores):
        return {member: {f"t{i}": [{"label": label, "recognized": True, "reasons": []}] for i, label in enumerate(labels)}
                for member, labels in scores.items()}

    def test_a_clear_gap_confirms_and_a_tie_does_not(self):
        checked = self.checked({"hi": ["valid"] * 6, "lo": ["invalid"] * 6, "same": ["valid"] * 6})
        win = confirm.compare(checked, "hi", "lo")
        self.assertLess(win["p_greater"], 0.05)
        self.assertTrue(confirm._wins(win))
        self.assertFalse(confirm._wins(confirm.compare(checked, "hi", "same")))
        self.assertTrue(confirm._loses(confirm.compare(checked, "lo", "hi")))

    def test_suboptimal_earns_half_credit_and_unrecognized_none(self):
        checked = self.checked({"m": ["valid", "suboptimal", "invalid"]})
        checked["m"]["t3"] = [{"label": None, "recognized": False, "reasons": []}]
        scores = confirm.task_scores(checked, "m")
        self.assertEqual([scores[f"t{i}"]["mean_credit"] for i in range(4)], [1.0, 0.5, 0.0, 0.0])
        self.assertEqual(confirm.exercised(checked, "m"), 2 / 3)

    def test_twin_is_the_unmodified_member_of_the_same_model(self):
        order = {"members": {"a": {"kind": "llm", "model": "m", "effort": "low", "mode": "single-call", "harness_defect": None},
                             "b": {"kind": "llm", "model": "m", "effort": "low", "mode": "single-call", "harness_defect": "last_chars:10"},
                             "c": {"kind": "llm", "model": "x", "effort": "low", "mode": "single-call", "harness_defect": None}}}
        self.assertEqual(confirm.twin(order, "b"), "a")

    def test_confirm_runs_the_pool_on_the_slice_and_writes_confirmations(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            st = store.Store(tmp / "store")
            slice_package = assemble_mini(st.slice("toy-sum", "s1") / "package")
            order = document(oracle=scripted("oracle"), defect=scripted("defect", defect="off_by_one"), noop={"kind": "scripted", "behavior": "floor", "name": "noop"})
            order["known_pairs"] = [{"higher": "oracle", "lower": "noop", "basis": "construction"}]
            order["unconfirmed"] = [{"higher": "oracle", "lower": "defect", "basis": "hypothesis"}]
            pool_id, pool_dir = pool.assemble(TOY, pool.normalize(order, "toy-sum"), st)
            result = confirm.confirm("toy-sum", st.root, pool_id=pool_id, jobs=3, out_root=tmp / "out")
            self.assertEqual((result["slice"], result["members_run"], result["llm"]), ("s1", 3, False))
            self.assertTrue(slice_package.is_dir())
            written = json.loads((pool_dir / "confirmations.json").read_text(encoding="utf-8"))
            self.assertEqual(written["pairs"][0]["outcome"], "unconfirmed")   # two tasks cannot reach p < 0.05
            updated = pool.read_order(st, "toy-sum", pool_id)
            self.assertEqual(len(updated["known_pairs"]), 1)
            self.assertEqual(len(updated["unconfirmed"]), 1)


if __name__ == "__main__":
    unittest.main()
