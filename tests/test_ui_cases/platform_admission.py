"""Build, notice, and generated-source admission regressions."""

import hashlib
import json

from tests.test_ui_cases._base import *  # noqa: F401,F403
from tools import check_source_sizes as sizes
from tools import ui_frontend as frontend


class TestPlatformAdmission(unittest.TestCase):
    def test_every_browser_remote_load_delimiter_is_rejected(self):
        probes = (
            b"fetch(`https://example.test/a`)",
            b"import(`https://example.test/a.js`)",
            b"new Worker(`https://example.test/w.js`)",
            b"body{background:url(//example.test/a.png)}",
        )
        self.assertTrue(all(frontend.REMOTE_ASSET.search(probe) for probe in probes))

    def test_python_notice_source_and_artifact_are_both_admission_inputs(self):
        good = {"anyio": ("4.12.1", "[PyPI](https://pypi.org/project/anyio/4.12.1/)", "MIT", "P: anyio/")}
        frontend._assert_notice_inventory({"anyio": "4.12.1"}, good, {"anyio": "MIT"}, "Python")
        for index in (1, 3):
            bad = {"anyio": tuple("missing" if position == index else value for position, value in enumerate(good["anyio"]))}
            with self.assertRaisesRegex(RuntimeError, "notice (source|artifact) mismatch"):
                frontend._assert_notice_inventory({"anyio": "4.12.1"}, bad, {"anyio": "MIT"}, "Python")

    def test_generated_exemption_requires_a_contained_matching_hash(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            asset = root / "web" / "dist" / "assets" / "worker.js"
            manifest = root / sizes.GENERATED_SOURCE_MANIFESTS[0]
            asset.parent.mkdir(parents=True)
            manifest.parent.mkdir(parents=True)
            asset.write_text("generated\n", encoding="utf-8")
            digest = hashlib.sha256(asset.read_bytes()).hexdigest()
            manifest.write_text(json.dumps({"assets/worker.js": digest, "../../evil.py": digest}), encoding="utf-8")
            self.assertEqual({asset.resolve()}, sizes.generated_source_files(root))
            asset.write_text("authored mutation\n", encoding="utf-8")
            self.assertEqual(set(), sizes.generated_source_files(root))
