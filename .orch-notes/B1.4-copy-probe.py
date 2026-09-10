"""Replay the copy-fidelity seam without editing the repository under test."""
import argparse
import hashlib
import json
from pathlib import Path
import py_compile
import shutil
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tests import validator_copy
from tests.test_validate_cases import validator_ownership

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--output", type=Path)
args = parser.parse_args()
relative = Path("example-workflows/recent-search/skills/research-acquire/tests/fixtures/cache/disk_backed_cache.py")
authored = (ROOT / relative).read_bytes()
original_roots = (validator_copy.ROOT, validator_ownership.ROOT)
observations = []
with tempfile.TemporaryDirectory(prefix="b14-copy-fidelity-") as temporary:
    scratch = Path(temporary)
    for scenario in ("authored", "generated-directory", "generated-file", "altered", "deleted"):
        source, destination = scratch / scenario / "source", scratch / scenario / "copy"
        fixture = source / relative
        fixture.parent.mkdir(parents=True)
        fixture.write_bytes(authored)
        ungraded = source / "tests/fixtures/root-only.txt"
        ungraded.parent.mkdir(parents=True)
        ungraded.write_text("root test corpus\n", encoding="utf-8")
        generated = None
        if scenario == "generated-directory":
            generated = fixture.parent / "__pycache__/disk_backed_cache.cpython-39.pyc"
        elif scenario == "generated-file":
            generated = fixture.with_suffix(".pyc")
        if generated is not None:
            generated.parent.mkdir(parents=True, exist_ok=True)
            py_compile.compile(str(fixture), cfile=str(generated), doraise=True)
        with mock.patch.object(validator_copy, "ROOT", source), mock.patch.object(validator_ownership, "ROOT", source):
            shutil.copytree(source, destination, ignore=validator_copy.source_copy_skips)
            copied_fixture = destination / relative
            preserved_before_mutation = copied_fixture.read_bytes() == authored
            if scenario == "altered":
                copied_fixture.write_bytes(authored + b"\n# altered control\n")
            elif scenario == "deleted":
                copied_fixture.unlink()
            case = validator_ownership.FrictionLocationSyncTest("test_the_copy_grades_what_the_tree_grades")
            clean = SimpleNamespace(returncode=0, stdout="")
            with mock.patch.object(case, "_assert_clean_first"), mock.patch.object(case, "_wrong_result_tree", return_value=destination), mock.patch.object(case, "_clean", clean), mock.patch.object(validator_ownership, "validate_the_real_tree", return_value=clean):
                result = unittest.TestResult()
                case.run(result)
            observations.append({
                "scenario": scenario, "test": case.id(), "tests_run": result.testsRun,
                "failures": len(result.failures), "errors": len(result.errors),
                "details": [detail for _, detail in result.failures + result.errors],
                "authored_fixture_preserved_before_mutation": preserved_before_mutation,
                "generated_source_present": generated is not None and generated.is_file(),
                "generated_copy_absent": generated is None or not (destination / generated.relative_to(source)).exists(),
                "root_corpus_omitted": not (destination / "tests/fixtures").exists(),
            })
restored = original_roots == (validator_copy.ROOT, validator_ownership.ROOT)
cleaned = not scratch.exists()
expected = [(0, 0), (0, 0), (0, 0), (1, 0), (0, 1)]
passed = all((row["failures"], row["errors"]) == counts for row, counts in zip(observations, expected))
passed = passed and all(row["authored_fixture_preserved_before_mutation"] and row["generated_copy_absent"] and row["root_corpus_omitted"] and row["tests_run"] == 1 for row in observations)
passed = passed and all(row["generated_source_present"] for row in observations[1:3])
passed = passed and "AssertionError" in "".join(observations[3]["details"])
passed = passed and "FileNotFoundError" in "".join(observations[4]["details"])
passed = passed and relative.name in "".join(observations[4]["details"]) and restored and cleaned
report = {
    "assigned_name": "B1.4", "dispatch_id": "B1.4:d1",
    "assignment_seal": "sha256:4e6322a841b9994f0e29b3c9abefdd35595c2ebf0279f81f147d6cc389cca8a8",
    "fixture": relative.as_posix(), "fixture_sha256": hashlib.sha256(authored).hexdigest(),
    "comparator_sha256": hashlib.sha256(Path(validator_ownership.__file__).read_bytes()).hexdigest(),
    "method": "Actual source-copy callback and actual fidelity test on scratch trees carrying real package fixture bytes; validation readings substituted only to isolate the fixture comparison.",
    "observations": observations, "patched_roots_restored": restored,
    "scratch_removed": cleaned, "passed": passed,
    "gaps": ["This probe does not execute validation or workflow prose; the affected module exercises real validation separately."],
}
serialized = json.dumps(report, indent=2) + "\n"
if args.output:
    args.output.write_text(serialized, encoding="utf-8")
print(serialized)
raise SystemExit(0 if passed else 1)
