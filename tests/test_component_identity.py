"""Failability proof for benchmarks/benchmaker/tools/component_identity.py.

Every test builds a synthetic package in a tempdir. Nothing here reads
``benchmarks/benchmaker/``: the live manifest's directory components are
knowingly divergent until the redesign's re-seal lands, so a test that
read them would encode that divergence as the expected answer.

A clean fixture must ``--verify`` at exit 0. Each other test mutates
exactly one thing and proves the tool reports it — a checker that never
fires is worthless, and this one exists precisely because the manifest
could not detect a ``cases/`` edit.
"""

from __future__ import annotations

import contextlib
import hashlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TOOL_DIR = REPO_ROOT / "benchmarks" / "benchmaker" / "tools"
if str(TOOL_DIR) not in sys.path:
    sys.path.insert(0, str(TOOL_DIR))

import component_identity as ci  # noqa: E402


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # write_bytes, not write_text: the newline= kwarg is 3.10+ and the
    # digests are over exact LF bytes on every platform.
    path.write_bytes(text.encode("utf-8"))


def build_package(root: Path) -> dict:
    """A minimal package whose manifest already binds to its tree."""
    write(root / "evaluation-design.md", "# design\n")
    write(root / "scoring.md", "# scoring\n")
    write(root / "tools" / "validate_cases.py", "print('runner')\n")
    write(root / "cases" / "cs-one" / "case.toml", 'id = "cs-one"\n')
    write(root / "cases" / "cs-two" / "case.toml", 'id = "cs-two"\n')
    write(root / "provenance" / "provenance.md", "# provenance\n")
    write(root / "qualification" / "index.md", "# verdicts\n")
    manifest = {
        "benchmark_identity": "sha256:pending",
        "evaluation_design": {"identity": "", "locator": "evaluation-design.md"},
        "runnable_cases": {"identity": "", "locator": "cases/"},
        "runner": {"identity": "", "locator": "tools/validate_cases.py"},
        "scoring": {"identity": "", "locator": "scoring.md"},
        "provenance": {"identity": "", "locator": "provenance/"},
        "qualification": {"identity": "", "locator": "qualification/"},
        "protected_evidence": {
            "candidate_inaccessible_check": None,
            "identity": {"files": {"held.json": "sha256:" + "0" * 64}},
            "locator": "BENCH_PROTECTED_DIR",
            "release_policy": "never to candidate or builder contexts",
            "visibility": "qualification and scoring contexts only",
        },
        "gaps": [],
    }
    (root / "manifest.json").write_bytes(ci.manifest_bytes(manifest))
    run(root, "--write")
    return read_manifest(root)


def read_manifest(root: Path) -> dict:
    return json.loads((root / "manifest.json").read_text(encoding="utf-8"))


def run(root: Path, mode: str) -> tuple[int, str]:
    stream = io.StringIO()
    with contextlib.redirect_stdout(stream):
        code = ci.main(["--set-root", str(root), mode])
    return code, stream.getvalue()


class ComponentIdentityTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name) / "pkg"
        self.root.mkdir()
        self.manifest = build_package(self.root)

    def tearDown(self):
        self._tmp.cleanup()

    def reseal_manifest(self, manifest: dict) -> None:
        (self.root / "manifest.json").write_bytes(ci.manifest_bytes(manifest))

    # --- the clean fixture ------------------------------------------------

    def test_written_package_verifies(self):
        code, out = run(self.root, "--verify")
        self.assertEqual(0, code, out)
        self.assertIn("manifest bound to tree", out)

    def test_write_is_idempotent(self):
        before = (self.root / "manifest.json").read_bytes()
        run(self.root, "--write")
        self.assertEqual(before, (self.root / "manifest.json").read_bytes())

    def test_identity_is_the_documented_recipe(self):
        # A file component is the sha256 of its bytes.
        design = self.root / "evaluation-design.md"
        self.assertEqual(
            "sha256:" + hashlib.sha256(design.read_bytes()).hexdigest(),
            self.manifest["evaluation_design"]["identity"],
        )
        # A directory component is the sha256 of its component lock.
        lines = []
        for relative in ("cs-one/case.toml", "cs-two/case.toml"):
            digest = hashlib.sha256(
                (self.root / "cases" / relative).read_bytes()
            ).hexdigest()
            lines.append("%s  %s\n" % (digest, relative))
        payload = "".join(lines).encode("ascii")
        self.assertEqual(
            "sha256:" + hashlib.sha256(payload).hexdigest(),
            self.manifest["runnable_cases"]["identity"],
        )

    def test_benchmark_identity_covers_the_payload(self):
        self.assertEqual(
            "sha256:"
            + hashlib.sha256(ci.canonical_payload(self.manifest)).hexdigest(),
            self.manifest["benchmark_identity"],
        )

    # --- the hole this tool exists to close -------------------------------

    def test_edited_case_file_is_detected(self):
        write(self.root / "cases" / "cs-one" / "case.toml", 'id = "cs-one-edited"\n')
        code, out = run(self.root, "--verify")
        self.assertEqual(1, code, out)
        self.assertIn("ERROR component: runnable_cases", out)

    def test_added_case_file_is_detected(self):
        write(self.root / "cases" / "cs-three" / "case.toml", 'id = "cs-three"\n')
        code, out = run(self.root, "--verify")
        self.assertEqual(1, code, out)
        self.assertIn("ERROR component: runnable_cases", out)

    def test_removed_case_file_is_detected(self):
        (self.root / "cases" / "cs-two" / "case.toml").unlink()
        code, out = run(self.root, "--verify")
        self.assertEqual(1, code, out)
        self.assertIn("ERROR component: runnable_cases", out)

    def test_renamed_case_file_is_detected(self):
        # Same bytes, different path: a content-only digest would miss it.
        source = self.root / "cases" / "cs-two" / "case.toml"
        write(self.root / "cases" / "cs-two" / "renamed.toml", source.read_text())
        source.unlink()
        code, out = run(self.root, "--verify")
        self.assertEqual(1, code, out)
        self.assertIn("ERROR component: runnable_cases", out)

    def test_swapped_case_contents_are_detected(self):
        # Both files keep their bytes; only the pairing changes.
        write(self.root / "cases" / "cs-one" / "case.toml", 'id = "cs-two"\n')
        write(self.root / "cases" / "cs-two" / "case.toml", 'id = "cs-one"\n')
        code, out = run(self.root, "--verify")
        self.assertEqual(1, code, out)
        self.assertIn("ERROR component: runnable_cases", out)

    def test_edited_file_component_is_detected(self):
        write(self.root / "scoring.md", "# scoring, revised\n")
        code, out = run(self.root, "--verify")
        self.assertEqual(1, code, out)
        self.assertIn("ERROR component: scoring", out)

    def test_edited_provenance_is_detected(self):
        write(self.root / "provenance" / "provenance.md", "# provenance, revised\n")
        code, out = run(self.root, "--verify")
        self.assertEqual(1, code, out)
        self.assertIn("ERROR component: provenance", out)

    def test_edited_qualification_is_detected(self):
        write(self.root / "qualification" / "index.md", "# verdicts, revised\n")
        code, out = run(self.root, "--verify")
        self.assertEqual(1, code, out)
        self.assertIn("ERROR component: qualification", out)

    # --- manifest-side drift ---------------------------------------------

    def test_forged_component_identity_is_detected(self):
        manifest = read_manifest(self.root)
        manifest["runnable_cases"]["identity"] = "sha256:" + "1" * 64
        manifest["benchmark_identity"] = "sha256:" + hashlib.sha256(
            ci.canonical_payload(manifest)
        ).hexdigest()
        self.reseal_manifest(manifest)
        code, out = run(self.root, "--verify")
        self.assertEqual(1, code, out)
        self.assertIn("ERROR component: runnable_cases", out)

    def test_stale_benchmark_identity_is_detected(self):
        manifest = read_manifest(self.root)
        manifest["gaps"] = ["a gap added without re-deriving the identity"]
        self.reseal_manifest(manifest)
        code, out = run(self.root, "--verify")
        self.assertEqual(1, code, out)
        self.assertIn("ERROR component: benchmark_identity", out)

    def test_write_repairs_both_layers(self):
        write(self.root / "cases" / "cs-one" / "case.toml", 'id = "cs-one-edited"\n')
        self.assertEqual(1, run(self.root, "--verify")[0])
        code, out = run(self.root, "--write")
        self.assertEqual(0, code, out)
        self.assertEqual(0, run(self.root, "--verify")[0])
        self.assertNotEqual(
            self.manifest["benchmark_identity"],
            read_manifest(self.root)["benchmark_identity"],
        )

    # --- exemptions and error paths ---------------------------------------

    def test_protected_evidence_is_named_exempt_not_silently_skipped(self):
        code, out = run(self.root, "--verify")
        self.assertEqual(0, code, out)
        self.assertIn("exempt protected_evidence", out)

    def test_write_leaves_protected_evidence_untouched(self):
        before = self.manifest["protected_evidence"]
        run(self.root, "--write")
        self.assertEqual(before, read_manifest(self.root)["protected_evidence"])

    def test_unresolvable_locator_is_an_error(self):
        manifest = read_manifest(self.root)
        manifest["scoring"]["locator"] = "no-such-file.md"
        self.reseal_manifest(manifest)
        code, out = run(self.root, "--verify")
        self.assertEqual(1, code, out)
        self.assertIn("neither a file nor a directory", out)

    def test_empty_locator_is_an_error(self):
        manifest = read_manifest(self.root)
        manifest["scoring"]["locator"] = "   "
        self.reseal_manifest(manifest)
        code, out = run(self.root, "--verify")
        self.assertEqual(1, code, out)
        self.assertIn("no usable locator", out)

    def test_missing_manifest_is_an_error(self):
        (self.root / "manifest.json").unlink()
        code, out = run(self.root, "--verify")
        self.assertEqual(1, code, out)
        self.assertIn("no manifest.json", out)

    def test_malformed_manifest_is_an_error(self):
        (self.root / "manifest.json").write_text("{not json", encoding="utf-8")
        code, out = run(self.root, "--verify")
        self.assertEqual(1, code, out)
        self.assertIn("not valid JSON", out)

    def test_dotted_and_cache_paths_are_out_of_scope(self):
        # Mirrors seal_set.py's exclusions, so the two recipes agree.
        write(self.root / "cases" / "__pycache__" / "x.pyc", "junk\n")
        write(self.root / "cases" / ".notes" / "scratch.md", "scratch\n")
        code, out = run(self.root, "--verify")
        self.assertEqual(0, code, out)


if __name__ == "__main__":
    unittest.main()
