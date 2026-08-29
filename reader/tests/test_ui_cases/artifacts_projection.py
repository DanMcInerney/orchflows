"""Contained artifact inventory and content projection contracts."""

from reader.tests.test_ui_cases._web import *  # noqa: F401,F403

import base64
import hashlib

import reader.scripts.ui_artifacts_projection as artifacts


NOT_FOUND = {"error": {"code": "not_found", "message": "resource not found"}}
INTERNAL_ERROR = {
    "error": {"code": "internal_error", "message": "projection failed"}
}


def _artifact_id(identity: dict) -> str:
    encoded = json.dumps(
        identity, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    digest = base64.urlsafe_b64encode(hashlib.sha256(encoded).digest())
    return "art_" + digest.decode("ascii").rstrip("=")


def _result(ticket: Path, value: str):
    text = ticket.read_text(encoding="utf-8")
    marker = "## Result\n\n"
    if marker in text:
        ticket.write_text(text.replace(marker, marker + value + "\n", 1), encoding="utf-8")
        return
    with ticket.open("a", encoding="utf-8") as handle:
        handle.write("\n## Result\n\n{0}\n".format(value))


class ArtifactsProjectionTest(unittest.TestCase):
    def test_inventory_and_content_enforce_canonical_containment_and_http_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            root = make_sink(tmp)
            outside = tmp / "outside-secret.md"
            outside.write_text("outside-artifact-content", encoding="utf-8")
            artifact = root / "results" / "run-gamma" / "G1" / "result.md"
            artifact.parent.mkdir(parents=True)
            artifact.write_text(
                "safe result\n{0}\nC:\\private\\secret.txt\n/private/secret.txt\n".format(
                    root.resolve()
                ),
                encoding="utf-8",
            )
            raw = artifact.read_bytes()
            identity = {
                "kind": "artifact",
                "locator": "sink:results/run-gamma/G1/result.md",
                "sha256": hashlib.sha256(raw).hexdigest(),
            }
            opaque_id = _artifact_id(identity)
            _result(
                root / "tickets" / "run-gamma" / "G1.md",
                "result: "
                + json.dumps(identity, sort_keys=True, separators=(",", ":")),
            )
            _result(
                root / "tickets" / "run-gamma" / "G2.md",
                "the result is in the workspace output directory",
            )
            escaped = dict(
                identity,
                locator="sink:../outside-secret.md",
                sha256=hashlib.sha256(outside.read_bytes()).hexdigest(),
            )
            _result(
                root / "tickets" / "run-gamma" / "G3.md",
                "result: "
                + json.dumps(escaped, sort_keys=True, separators=(",", ":")),
            )
            run_state = root / "runs" / "run-gamma"
            run_state.mkdir(parents=True)
            (run_state / "run.json").write_text(
                json.dumps(
                    {"project": str(outside), "workspace": str(outside.parent)}
                ),
                encoding="utf-8",
            )
            before = snapshot(root)

            status, inventory = artifacts.project_artifact_inventory(
                root, "run-gamma", "G1"
            )
            missing_status, missing = artifacts.project_artifact_inventory(
                root, "run-gamma", "G2"
            )
            escaped_status, escaped_inventory = artifacts.project_artifact_inventory(
                root, "run-gamma", "G3"
            )
            content_status, content = artifacts.project_artifact(
                root, "run-gamma", "G1", opaque_id
            )

            self.assertEqual(200, status)
            self.assertEqual(
                {"schema", "run", "ticket", "state", "artifacts"}, set(inventory)
            )
            self.assertEqual("available", inventory["state"])
            self.assertEqual(
                [{"id": opaque_id, "state": "available"}], inventory["artifacts"]
            )
            self.assertRegex(opaque_id, r"\Aart_[A-Za-z0-9_-]{43}\Z")
            self.assertNotIn("sink:", json.dumps(inventory, sort_keys=True))
            self.assertEqual((200, "unavailable", []), (missing_status, missing["state"], missing["artifacts"]))
            self.assertEqual(
                (200, "unavailable", []),
                (escaped_status, escaped_inventory["state"], escaped_inventory["artifacts"]),
            )
            self.assertEqual(200, content_status)
            self.assertEqual(
                {"schema", "id", "text", "sha256", "redacted"}, set(content)
            )
            self.assertEqual(opaque_id, content["id"])
            self.assertTrue(content["redacted"])
            self.assertIn("safe result", content["text"])
            self.assertIn("[redacted-host-path]", content["text"])
            self.assertNotIn(str(root.resolve()), content["text"])
            self.assertNotIn("C:\\private", content["text"])
            self.assertNotIn("/private/secret", content["text"])
            self.assertNotIn("outside-artifact-content", json.dumps((inventory, content)))
            self.assertEqual(
                hashlib.sha256(content["text"].encode("utf-8")).hexdigest(),
                content["sha256"],
            )

            inventory_route = "/api/v1/runs/run-gamma/tickets/G1/artifacts"
            content_route = inventory_route + "/" + opaque_id
            with serving(root) as server:
                for route in (inventory_route, content_route):
                    get_response = fetch(server, route)
                    head_response = request(server, route, method="HEAD")
                    self.assertEqual(200, get_response[0], route)
                    self.assertEqual(200, head_response[0], route)
                    self.assertTrue(get_response[2], route)
                    self.assertEqual("", head_response[2], route)
                    self.assertEqual(
                        get_response[1].get("ETag"), head_response[1].get("ETag"), route
                    )
                    self.assertEqual(
                        get_response[1].get("Content-Length"),
                        head_response[1].get("Content-Length"),
                        route,
                    )
                    self.assertEqual(
                        "application/json; charset=utf-8",
                        get_response[1].get("Content-Type"),
                        route,
                    )
                    repeated = fetch(
                        server,
                        route,
                        {"If-None-Match": get_response[1].get("ETag")},
                    )
                    self.assertEqual((304, ""), (repeated[0], repeated[2]), route)

                for route in (
                    inventory_route + "/art_invalid",
                    inventory_route + "/%2e%2e",
                    "/api/v1/runs/%2e%2e/tickets/G1/artifacts",
                    "/api/v1/runs/run-gamma/tickets/%2e%2e/artifacts",
                ):
                    response = fetch(server, route)
                    self.assertEqual(404, response[0], route)
                    self.assertEqual(NOT_FOUND, json.loads(response[2]), route)
                    self.assertIsNone(response[1].get("ETag"), route)
                    self.assertNotIn("outside", response[2], route)

            self.assertEqual(before, snapshot(root))


if __name__ == "__main__":
    unittest.main()
