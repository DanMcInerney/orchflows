import sys
import tempfile
import types
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[1]))
sys.path.insert(0, str(HERE.parents[3] / "skills" / "benchmaker" / "scripts"))

from metabench import labeled  # noqa: E402


def entry(name: str, label: str, kind: str = "kind") -> dict:
    return {"files": {"out.json": name.encode()}, "label": label, "kind": kind}


def domain(items: dict, *, apply: bool = True):
    ns = types.SimpleNamespace(labeled=lambda instance: items[instance["id"]])
    if apply:
        ns.apply = lambda workspace, files: [Path(workspace, rel).write_bytes(data) for rel, data in files.items()]
    return ns


def grade(task: str, sub: str, accepted: bool, **extra) -> dict:
    return {"task": task, "submission": sub, "grading_status": "scored", "full_success": accepted, "credit": 1.0 if accepted else 0.0,
            "dimensions": {}, "critical_failures": [], "reason": "", **extra}


class BuildSubmissionsTests(unittest.TestCase):
    def test_writes_final_workspaces_and_returns_labels(self):
        items = {"a": [entry("a1", "valid"), entry("a2", "valid"), entry("a3", "invalid")], "b": [entry("b1", "suboptimal")], "d": []}
        recognized = {"a": {"id": "a"}, "b": {"id": "b"}, "c": None, "d": {"id": "d"}}
        with tempfile.TemporaryDirectory() as tmp:
            labels = labeled.build_submissions(domain(items), recognized, Path(tmp) / "subs")
            self.assertEqual(labels["uncovered"], ["c", "d"])
            self.assertEqual(sorted(labels["submissions"]), ["a", "b"])
            self.assertEqual(sorted(m["label"] for m in labels["submissions"]["a"].values()), ["invalid", "valid", "valid"])
            for task, subs in labels["submissions"].items():
                for sub, meta in subs.items():
                    path = Path(tmp, "subs", task, sub, "out.json")
                    self.assertTrue(path.is_file())
                    self.assertEqual(path.read_bytes()[:1], task.encode()[:1])
            self.assertFalse((Path(tmp) / "subs" / "c").exists())

    def test_nothing_in_the_tree_names_a_label(self):
        items = {"a": [entry("x", "valid", "offset-variant"), entry("y", "invalid", "defect:ignore")]}
        with tempfile.TemporaryDirectory() as tmp:
            labeled.build_submissions(domain(items), {"a": {"id": "a"}}, Path(tmp))
            names = [p.relative_to(tmp).as_posix() for p in Path(tmp).rglob("*")]
            self.assertEqual(len(names), 5)
            for name in names:
                for word in ("valid", "invalid", "defect", "offset", "label"):
                    self.assertNotIn(word, name)
            self.assertEqual({Path(n).name for n in names if "/" in n and n.count("/") == 2}, {"out.json"})

    def test_starts_from_the_public_workspace_and_works_without_apply(self):
        items = {"a": [entry("answer", "valid")]}
        with tempfile.TemporaryDirectory() as tmp:
            public = Path(tmp) / "env" / "a"
            public.mkdir(parents=True)
            (public / "input.json").write_text("{}")
            labels = labeled.build_submissions(domain(items, apply=False), {"a": {"id": "a"}}, Path(tmp) / "subs",
                                               workspaces={"a": public})
            (sub,) = labels["submissions"]["a"]
            self.assertEqual((Path(tmp) / "subs" / "a" / sub / "input.json").read_text(), "{}")
            self.assertEqual((Path(tmp) / "subs" / "a" / sub / "out.json").read_bytes(), b"answer")

    def test_unsafe_names_are_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            for rel in ("../out.json", "/abs.json", "C:\\abs.json", ""):
                items = {"a": [{"files": {rel: b"x"}, "label": "valid"}]}
                with self.assertRaises(ValueError):
                    labeled.build_submissions(domain(items), {"a": {"id": "a"}}, Path(tmp))
            with self.assertRaises(ValueError):
                labeled.build_submissions(domain({"a": []}), {"../a": {"id": "a"}}, Path(tmp))
            with self.assertRaises(ValueError):
                labeled.build_submissions(domain({"a": [{"files": {"x": "text"}, "label": "valid"}]}), {"a": {"id": "a"}}, Path(tmp))


class ScoreLabelsTests(unittest.TestCase):
    LABELS = {"submissions": {
        "a": {"a1": {"label": "valid", "kind": "canonical"}, "a2": {"label": "valid", "kind": "offset-variant"},
              "a3": {"label": "invalid", "kind": "defect"}},
        "b": {"b1": {"label": "valid", "kind": "canonical"}, "b2": {"label": "suboptimal", "kind": "later"},
              "b3": {"label": "lenient", "kind": "valid-lenient"}}},
        "uncovered": ["c", "d"]}

    def rows(self):
        return [grade("a", "a1", True), grade("a", "a2", False), grade("a", "a3", True),
                grade("b", "b1", True), grade("b", "b2", False), grade("b", "b3", True)]

    def test_hand_computed_rates(self):
        result = labeled.score_labels(self.rows(), self.LABELS)
        # positives a1 a2 b1: two accepted. negatives a3 b2: one rejected. b3 is left out.
        self.assertEqual((result["positives"], result["negatives"], result["ignored"]), (3, 2, 1))
        self.assertAlmostEqual(result["tpr"], 2 / 3)
        self.assertAlmostEqual(result["tnr"], 1 / 2)
        self.assertEqual([(r["task"], r["submission"], r["kind"]) for r in result["false_rejects"]], [("a", "a2", "offset-variant")])
        self.assertEqual([(r["task"], r["submission"], r["kind"]) for r in result["false_accepts"]], [("a", "a3", "defect")])
        self.assertEqual((result["tasks_covered"], result["tasks_total"]), (2, 4))
        self.assertAlmostEqual(result["oracle_coverage"], 0.5)
        self.assertEqual(result["uncovered"], ["c", "d"])
        low, high = result["tpr_ci90"]
        self.assertTrue(low < 2 / 3 < high)

    def test_perfect_verifier(self):
        rows = [grade("a", "a1", True), grade("a", "a2", True), grade("a", "a3", False), grade("b", "b1", True), grade("b", "b2", False)]
        result = labeled.score_labels(rows, self.LABELS)
        self.assertEqual((result["tpr"], result["tnr"]), (1.0, 1.0))
        self.assertEqual((result["false_rejects"], result["false_accepts"]), ([], []))

    def test_missing_and_unscored_grades_are_not_acceptances(self):
        rows = [grade("a", "a1", True), {"task": "a", "submission": "a2", "grading_status": "indeterminate", "reason": "verifier crashed"},
                grade("a", "a3", False), grade("b", "b2", False)]
        result = labeled.score_labels(rows, self.LABELS)
        self.assertEqual(sorted((r["submission"], r["reason"]) for r in result["false_rejects"]),
                         [("a2", "indeterminate: verifier crashed"), ("b1", "no grade row")])
        self.assertEqual(sorted(r["submission"] for r in result["ungraded"]), ["a2", "b1", "b3"])
        self.assertAlmostEqual(result["tpr"], 1 / 3)
        self.assertEqual(result["tnr"], 1.0)

    def test_critical_failure_with_full_success_is_not_accepted(self):
        rows = [grade("a", "a3", True, critical_failures=["clobbered"])]
        result = labeled.score_labels(rows, self.LABELS)
        self.assertEqual([r["submission"] for r in result["false_accepts"]], [])
        self.assertEqual(result["tnr"], 1.0)

    def test_critical_failure_alone_rejects_a_valid_output(self):
        rows = [grade("a", "a1", False, critical_failures=["clobbered"])]
        result = labeled.score_labels(rows, self.LABELS)
        self.assertIn("a1", [r["submission"] for r in result["false_rejects"]])

    def test_no_labelled_submissions_is_not_computed(self):
        result = labeled.score_labels([], {"submissions": {}, "uncovered": ["a"]})
        self.assertIs(result["computed"], False)
        self.assertEqual(result["uncovered"], ["a"])

    def test_empty_class_gives_no_rate(self):
        labels = {"submissions": {"a": {"a1": {"label": "valid", "kind": "k"}}}, "uncovered": []}
        result = labeled.score_labels([grade("a", "a1", True)], labels)
        self.assertEqual(result["tpr"], 1.0)
        self.assertIsNone(result["tnr"])
        self.assertIsNone(result["tnr_ci90"])


if __name__ == "__main__":
    unittest.main()
