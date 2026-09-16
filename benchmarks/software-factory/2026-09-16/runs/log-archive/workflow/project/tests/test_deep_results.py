"""Deep, valid JSON extras survive both entry points with caller ownership."""

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import baseline_reference
from log_archive import search_logs


ROOT = Path(__file__).resolve().parents[1]


def nested_record(depth, mixed):
    record = dict(id="nested", service="api", level="INFO", message="ready",
                  timestamp="2026-01-01T00:00:00.000Z")
    wrappers = [("{\"next\":", "}") if mixed and index % 2 else ("[", "]")
                for index in range(depth)]
    extra = ("".join(opening for opening, _ in wrappers)
             + '{"leaf":[1,{"value":"original"}]}'
             + "".join(closing for _, closing in reversed(wrappers)))
    return json.dumps(record)[:-1] + ',"extra":' + extra + "}\n"


def leaf(record, depth, mixed):
    value = record["extra"]
    for index in range(depth):
        value = value["next"] if mixed and index % 2 else value[0]
    return value["leaf"]


class DeepResultTests(unittest.TestCase):
    def test_deep_api_results_preserve_mutable_leaves_and_ownership(self):
        with tempfile.TemporaryDirectory() as directory:
            for depth in (550, 800):
                for mixed in (False, True):
                    with self.subTest(depth=depth, mixed=mixed):
                        path = Path(directory) / f"{depth}-{mixed}.ndjson"
                        path.write_text(nested_record(depth, mixed) * 2, encoding="utf-8")
                        expected = baseline_reference.search_logs(path)
                        actual = search_logs(path)
                        self.assertEqual(actual["total"], expected["total"])
                        self.assertEqual(actual["total"], 2)
                        self.assertEqual(len(actual["items"]), 2)
                        # Walk iteratively so the assertion itself does not impose
                        # a smaller nesting limit on otherwise valid JSON values.
                        self.assertEqual(leaf(actual["items"][0], depth, mixed),
                                         leaf(expected["items"][0], depth, mixed))
                        owned = leaf(actual["items"][0], depth, mixed)
                        owned[1]["value"] = "changed"
                        owned.append("added")
                        self.assertEqual(leaf(actual["items"][1], depth, mixed),
                                         [1, {"value": "original"}])
                        again = search_logs(path)
                        for item in again["items"]:
                            self.assertEqual(leaf(item, depth, mixed),
                                             [1, {"value": "original"}])

    def test_deep_cli_returns_complete_json(self):
        with tempfile.TemporaryDirectory() as directory:
            for depth in (550, 800):
                for mixed in (False, True):
                    with self.subTest(depth=depth, mixed=mixed):
                        path = Path(directory) / f"{depth}-{mixed}.ndjson"
                        path.write_text(nested_record(depth, mixed), encoding="utf-8")
                        result = subprocess.run(
                            [sys.executable, "-B", str(ROOT / "log_archive.py"),
                             "--file", str(path)], capture_output=True, text=True,
                            timeout=15, check=False)
                        self.assertEqual(result.returncode, 0, result.stderr)
                        self.assertEqual(result.stderr, "")
                        answer = json.loads(result.stdout)
                        self.assertEqual(answer["total"], 1)
                        self.assertEqual(len(answer["items"]), 1)
                        self.assertEqual(leaf(answer["items"][0], depth, mixed),
                                         [1, {"value": "original"}])


if __name__ == "__main__":
    unittest.main()
