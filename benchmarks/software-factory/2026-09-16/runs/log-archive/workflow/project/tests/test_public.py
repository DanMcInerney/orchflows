import json
from pathlib import Path
import tempfile
import unittest

from log_archive import search_logs


class PublicContract(unittest.TestCase):
    def test_tokens_filters_order_and_pagination(self):
        path = Path(__file__).resolve().parents[1] / "sample.ndjson"
        result = search_logs(path, "GATEWAY timeout", service="gateway")
        self.assertEqual(result["total"], 1)
        self.assertEqual(result["items"][0]["id"], "r2")
        result = search_logs(path, limit=1, offset=1)
        self.assertEqual(result["total"], 3)
        self.assertEqual(result["items"][0]["id"], "r2")
        self.assertEqual(search_logs(path, "gate")["total"], 0)

    def test_append_and_validation(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "archive.ndjson"
            path.write_text("", encoding="utf-8")
            self.assertEqual(search_logs(path)["total"], 0)
            item = dict(id="a", timestamp="2026-07-01T00:00:00.000Z",
                        service="api", level="INFO", message="ready")
            with path.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(item) + "\n")
            self.assertEqual(search_logs(path)["items"], [item])
            with self.assertRaises(TypeError):
                search_logs(path, limit=True)
            with self.assertRaises(ValueError):
                search_logs(path, since="yesterday")


if __name__ == "__main__":
    unittest.main()
