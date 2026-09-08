"""Installer regression cases grouped by behavioral seam."""

from __future__ import annotations

from ..support import *  # noqa: F403


class TestPartialApplyAfterRmtree(unittest.TestCase):
    """A failure during staged copying preserves the complete old library."""

    def test_crash_mid_copy_leaves_lib_home_partially_repopulated_and_no_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "project"
            project.mkdir()

            src_a = root / "a.md"
            src_b = root / "b.md"
            src_c = root / "c.md"
            src_a.write_text("new a\n", encoding="utf-8")
            src_b.write_text("new b\n", encoding="utf-8")
            src_c.write_text("new c\n", encoding="utf-8")

            lib_home = project / ".orchflows" / "lib"
            lib_home.mkdir(parents=True)
            (project / ".orchflows" / "state" / "tickets").mkdir(parents=True)
            (lib_home / "old.md").write_text("stale\n", encoding="utf-8")

            receipt_path = project / ".orchflows" / "receipt.json"
            receipt_path.write_text('{"pre-existing": true}\n', encoding="utf-8")
            receipt_before = receipt_path.read_bytes()

            dest_a = lib_home / "a.md"
            dest_b = lib_home / "b.md"
            dest_c = lib_home / "c.md"

            plan = install.Plan(
                lib_home=lib_home,
                scope_home=project / ".orchflows",
                bin_dir=project / ".orch" / "bin",
                receipt_path=receipt_path,
                lib_copies=[(src_a, dest_a), (src_b, dest_b), (src_c, dest_c)],
            )

            real_copy2 = shutil.copy2

            def flaky_copy2(src, dest, *args, **kwargs):
                if Path(src) == src_b:
                    raise RuntimeError("simulated crash during copy")
                return real_copy2(src, dest, *args, **kwargs)

            with patch.object(install.shutil, "copy2", side_effect=flaky_copy2):
                with self.assertRaisesRegex(RuntimeError, "simulated crash"):
                    install.apply_plan(plan, accepted_source=install.resolve_source_commit())

            self.assertEqual("stale\n", (lib_home / "old.md").read_text(encoding="utf-8"))
            self.assertFalse(dest_a.exists())
            self.assertFalse(dest_b.exists())
            self.assertFalse(dest_c.exists())
            # apply_plan aborted before reaching the receipt write.
            self.assertEqual(receipt_before, receipt_path.read_bytes())
