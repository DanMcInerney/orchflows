"""Collision-seam migrate-state regression cases."""
from __future__ import annotations

from .common import MigrationCase, lines_of, write


class TestMigrationCollision(MigrationCase):
    """Run ownership and record-content collisions keep the first claimant."""

    def test_a_run_two_projects_claim_is_refused_and_the_rest_migrates(self):
        shared = "20260301T000000Z-shared"
        first = self.source_root("epsilon", origin="git@github.com:acme/epsilon.git")
        second = self.source_root("zeta", origin="git@github.com:acme/zeta.git")
        for root in (first, second):
            write(root / "runs" / shared / "worklog.md", f"# from {root.parent.name}\n")
            write(root / "tickets" / shared / "01-x.md", f"from {root.parent.name}\n")
        write(first / "runs" / "20260301T000000Z-own" / "worklog.md", "# mine\n")

        report = self.migrate(first, second)

        self.assertEqual([entry["run"] for entry in report["collisions"]], [shared])
        claimants = sorted(claim["project"] for claim in report["collisions"][0]["claims"])
        self.assertEqual(claimants, ["git@github.com:acme/epsilon",
                                     "git@github.com:acme/zeta"])
        self.assertFalse((self.sink / "runs" / shared).exists())
        self.assertFalse((self.sink / "tickets" / shared).exists())
        self.assertTrue((self.sink / "runs" / "20260301T000000Z-own" / "worklog.md").is_file())
        for source in report["sources"]:
            self.assertIn(shared, source["runs"]["skipped_collision"])
            self.assertIn(shared, source["tickets"]["skipped_collision"])

    def test_two_workspaces_of_one_project_are_not_a_collision(self):
        shared = "20260301T000000Z-shared"
        origin = "git@github.com:acme/eta.git"
        first = self.source_root("eta", origin=origin)
        second = self.source_root("eta-clone", origin=origin)
        for root, body in ((first, "# one\n"), (second, "# one\n")):
            write(root / "runs" / shared / "worklog.md", body)

        report = self.migrate(first, second)

        self.assertEqual(report["collisions"], [])
        self.assertTrue((self.sink / "runs" / shared / "worklog.md").is_file())
        self.assertEqual(lines_of(self.sink / "runs" / shared / "worklog.md"), ["# one"])
        self.assertEqual(report["sources"][1]["runs"]["existing"], 1)
        for source in report["sources"]:
            self.assertEqual(source["differing"], [])

    def test_two_workspaces_disagreeing_on_one_record_keep_the_first(self):
        shared = "20260301T000000Z-shared"
        origin = "git@github.com:acme/theta.git"
        first = self.source_root("theta", origin=origin)
        second = self.source_root("theta-clone", origin=origin)
        write(first / "runs" / shared / "worklog.md", "# from theta\n")
        write(second / "runs" / shared / "worklog.md", "# from theta-clone\n")

        report = self.migrate(first, second)

        landed = self.sink / "runs" / shared / "worklog.md"
        self.assertTrue(landed.is_file(), f"{landed} never reached the sink")
        self.assertEqual(lines_of(landed), ["# from theta"])
        self.assertEqual(report["errors"], [])
        self.assertEqual(report["sources"][0]["differing"], [])
        conflict = report["sources"][1]["differing"]
        self.assertEqual(len(conflict), 1, conflict)
        self.assertEqual(conflict[0]["source"],
                         str(second / "runs" / shared / "worklog.md"))
        self.assertEqual(conflict[0]["dest"], str(landed))
        self.assertEqual(conflict[0].get("claimed_by"),
                         str(first / "runs" / shared / "worklog.md"))
        self.assertEqual(lines_of(second / "runs" / shared / "worklog.md"),
                         ["# from theta-clone"])
