"""Stable opaque identities for exact workflow topology."""

from __future__ import annotations

import base64
import hashlib
import re
import unittest

from reader.scripts import ui_workflows_identity as identity


class WorkflowIdentityTests(unittest.TestCase):
    def test_node_id_builders_preserve_the_canonical_owner_names(self):
        self.assertEqual("workflow:evolve", identity.workflow_node_id("evolve"))
        self.assertEqual(
            "work:evolve/02-campaign",
            identity.work_node_id("evolve", "02-campaign"),
        )
        self.assertEqual("skill:orch-slice", identity.skill_node_id("orch-slice"))
        self.assertEqual(
            "script:bin/tickets.py",
            identity.script_node_id(r"bin\tickets.py"),
        )

    def test_installed_paths_are_normalized_once_and_must_stay_relative(self):
        self.assertEqual(
            "lib/skills/workflows/orch-outline/SKILL.md",
            identity.normalize_installed_path(
                r"lib\skills\workflows\.\orch-outline\SKILL.md"
            ),
        )
        for path in ("", ".", "../bin/tickets.py", "lib/../bin/tickets.py", "/bin/x.py", r"C:\bin\x.py"):
            with self.subTest(path=path):
                with self.assertRaises(identity.WorkflowIdentityError):
                    identity.normalize_installed_path(path)

    def test_edge_components_are_percent_encoded_and_url_safe(self):
        edge_id = identity.edge_id(
            "dependency",
            "work:evolve/00-eval",
            "work:evolve/01 eligibility",
        )

        self.assertEqual(
            "edge:dependency:work%3Aevolve%2F00-eval:work%3Aevolve%2F01%20eligibility",
            edge_id,
        )
        self.assertNotIn("/", edge_id)
        self.assertEqual(edge_id, identity.edge_id(
            "dependency", "work:evolve/00-eval", "work:evolve/01 eligibility"
        ))

    def test_source_ids_are_unpadded_base64url_hashes_of_normalized_paths(self):
        path = "lib/example-workflows/evolve/02-campaign.md"
        expected = base64.urlsafe_b64encode(
            hashlib.sha256(path.encode("utf-8")).digest()
        ).decode("ascii").rstrip("=")

        source_id = identity.source_id(r"lib\example-workflows\evolve\02-campaign.md")

        self.assertEqual("src_" + expected, source_id)
        self.assertIsNotNone(re.fullmatch(r"src_[A-Za-z0-9_-]{43}", source_id))


if __name__ == "__main__":
    unittest.main()
