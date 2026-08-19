"""Private runtime lifecycle and project-environment boundaries."""

from __future__ import annotations

from ..support import *  # noqa: F403


class RuntimeVenvTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name).resolve()
        self.home = self.root / "home"
        self.home.mkdir()
        self.project_runtime = self.root / "project" / ".venv"

    def test_user_install_uses_private_runtime_when_project_venv_is_active(self):
        install.venv.EnvBuilder(with_pip=False).create(self.project_runtime)
        project_python = install.private_runtime_python(self.project_runtime)
        program = "\n".join(
            (
                "from pathlib import Path",
                "from unittest.mock import patch",
                "import importlib.util, sys",
                f"spec = importlib.util.spec_from_file_location('installer_under_test', {str(install.REPO_ROOT / 'install.py')!r})",
                "installer = importlib.util.module_from_spec(spec)",
                "sys.modules[spec.name] = installer",
                "spec.loader.exec_module(installer)",
                f"with patch.object(installer.Path, 'home', return_value=Path({str(self.home)!r})), patch.object(installer, 'detect_hosts', return_value=(False, True)):",
                "    raise SystemExit(installer.main(['--user', '--yes']))",
            )
        )
        completed = subprocess.run(
            [str(project_python), "-c", program],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=dict(os.environ, VIRTUAL_ENV=str(self.project_runtime)),
        )
        self.assertEqual(0, completed.returncode, completed.stdout + completed.stderr)

        runtime_home = self.home / ".orchflows" / "runtime"
        runtime_python = install.private_runtime_python(runtime_home)
        rendered = (self.home / ".codex" / "AGENTS.md").read_text(encoding="utf-8")
        self.assertTrue(runtime_python.is_file())
        self.assertIn(str(runtime_python), rendered)
        self.assertNotEqual(project_python.resolve(), runtime_python.resolve())
        self.assertNotIn(str(self.project_runtime), rendered)

    def test_user_install_reuses_healthy_private_runtime(self):
        with patch.object(install.Path, "home", return_value=self.home), mock_host_clis("codex"):
            install.apply_plan(install.build_plan("user", None))
            marker = install.private_runtime_home() / "reuse-marker"
            marker.write_text("keep", encoding="utf-8")
            install.apply_plan(install.build_plan("user", None))
        self.assertEqual("keep", marker.read_text(encoding="utf-8"))

    def test_user_install_repairs_an_unhealthy_private_runtime(self):
        with patch.object(install.Path, "home", return_value=self.home), mock_host_clis("codex"):
            install.apply_plan(install.build_plan("user", None))
            runtime_home = install.private_runtime_home()
            marker = runtime_home / "unhealthy-marker"
            marker.write_text("remove me", encoding="utf-8")
            metadata = install._runtime_metadata()
            metadata["requirements_sha256"] = "0" * 64
            (runtime_home / install.RUNTIME_METADATA_FILENAME).write_text(
                json.dumps(metadata) + "\n", encoding="utf-8"
            )
            install.apply_plan(install.build_plan("user", None))
        self.assertFalse(marker.exists())
        self.assertTrue(install.private_runtime_is_healthy(runtime_home))

    def test_dry_run_has_no_runtime_or_filesystem_effects(self):
        output = io.StringIO()
        with patch.object(install.Path, "home", return_value=self.home), mock_host_clis(
            "codex"
        ), redirect_stdout(output):
            result = install.main(["--user", "--dry-run"])
        self.assertEqual(0, result)
        self.assertIn(
            f"private runtime: create {self.home / '.orchflows' / 'runtime'}",
            output.getvalue(),
        )
        self.assertEqual([], list(self.home.iterdir()))

    def test_project_install_does_not_create_a_runtime(self):
        project = self.root / "project"
        project.mkdir()
        output = io.StringIO()
        with patch.object(install.Path, "home", return_value=self.home), mock_host_clis("codex"):
            install.apply_plan(install.build_plan("user", None))
            marker = install.private_runtime_home() / "project-reuse-marker"
            marker.write_text("keep", encoding="utf-8")
        with patch.object(install.Path, "home", return_value=self.home), redirect_stdout(output):
            plan = install.build_plan("project", project)
            install.print_plan(plan)
            install.apply_plan(plan)
        self.assertIn("private runtime: reuse required", output.getvalue())
        self.assertEqual("keep", marker.read_text(encoding="utf-8"))
        self.assertFalse((project / ".orchflows" / "runtime").exists())

    def test_project_install_refuses_before_writing_without_a_user_runtime(self):
        project = self.root / "project"
        project.mkdir()
        with patch.object(install.Path, "home", return_value=self.home):
            plan = install.build_plan("project", project)
            with self.assertRaisesRegex(RuntimeError, "run install.py --user first"):
                install.apply_plan(plan)
        self.assertFalse((project / "CLAUDE.md").exists())
        self.assertFalse((project / "AGENTS.md").exists())
        self.assertFalse((project / ".orchflows").exists())

    def test_failed_repair_preserves_the_previous_runtime(self):
        with patch.object(install.Path, "home", return_value=self.home), mock_host_clis("codex"):
            install.apply_plan(install.build_plan("user", None))
            runtime_home = install.private_runtime_home()
            old_python = install.private_runtime_python(runtime_home)
            marker = runtime_home / "old-generation"
            marker.write_text("keep", encoding="utf-8")
            metadata = install._runtime_metadata()
            metadata["requirements_sha256"] = "0" * 64
            (runtime_home / install.RUNTIME_METADATA_FILENAME).write_text(
                json.dumps(metadata) + "\n", encoding="utf-8"
            )
            with patch.object(
                install, "_build_private_runtime", side_effect=RuntimeError("build failed")
            ):
                with self.assertRaisesRegex(RuntimeError, "build failed"):
                    install.apply_plan(install.build_plan("user", None))
        self.assertTrue(old_python.is_file())
        self.assertEqual("keep", marker.read_text(encoding="utf-8"))

    def test_unowned_runtime_is_refused_and_preserved(self):
        runtime_home = self.home / ".orchflows" / "runtime"
        runtime_home.mkdir(parents=True)
        marker = runtime_home / "not-ours"
        marker.write_text("keep", encoding="utf-8")
        with patch.object(install.Path, "home", return_value=self.home), mock_host_clis("codex"):
            with self.assertRaisesRegex(RuntimeError, "unowned private runtime"):
                install.apply_plan(install.build_plan("user", None))
        self.assertEqual("keep", marker.read_text(encoding="utf-8"))

    def test_rendered_friction_command_executes_from_a_spaced_home(self):
        spaced_home = self.root / "home with spaces"
        spaced_home.mkdir()
        with patch.object(install.Path, "home", return_value=spaced_home), mock_host_clis("codex"):
            install.apply_plan(install.build_plan("user", None))
        rendered = (spaced_home / ".codex" / "AGENTS.md").read_text(encoding="utf-8")
        shell = "PowerShell" if os.name == "nt" else "POSIX"
        command = next(
            line.strip().split(":", 1)[1].strip()
            for line in rendered.splitlines()
            if line.strip().startswith(f"{shell}:")
        )
        command = command.replace("<what happened>", "spaced home")
        command = command.replace("<what was expected or missing>", "runnable command")
        if os.name == "nt":
            completed = subprocess.run(
                ["powershell", "-NoProfile", "-Command", command],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
        else:
            completed = subprocess.run(
                ["/bin/sh", "-c", command],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
        self.assertEqual(0, completed.returncode, completed.stderr)
        self.assertEqual("friction logged", completed.stdout.strip())

    def test_dry_run_reports_create_reuse_and_repair(self):
        with patch.object(install.Path, "home", return_value=self.home), mock_host_clis("codex"):
            self.assertEqual("create", install.build_plan("user", None).runtime_action)
            install.apply_plan(install.build_plan("user", None))
            self.assertEqual("reuse", install.build_plan("user", None).runtime_action)
            metadata = install._runtime_metadata()
            metadata["requirements_sha256"] = "0" * 64
            (install.private_runtime_home() / install.RUNTIME_METADATA_FILENAME).write_text(
                json.dumps(metadata) + "\n", encoding="utf-8"
            )
            self.assertEqual("repair", install.build_plan("user", None).runtime_action)

    def test_failed_first_install_leaves_runtime_discoverable_to_uninstall(self):
        with patch.object(install.Path, "home", return_value=self.home), mock_host_clis("codex"):
            plan = install.build_plan("user", None)
            real_create = install._create_private_runtime

            def create_then_fail():
                real_create()
                raise RuntimeError("later install step failed")

            with patch.object(install, "_create_private_runtime", side_effect=create_then_fail):
                with self.assertRaisesRegex(RuntimeError, "later install step failed"):
                    install.apply_plan(plan)
            receipt = json.loads(plan.receipt_path.read_text(encoding="utf-8"))
            report = install.run_uninstall("user", None, dry_run=True)
            runtime_home = install.private_runtime_home()
        self.assertTrue(receipt["install_in_progress"])
        self.assertEqual(str(runtime_home), receipt["runtime"]["home"])
        manual = {entry["path"]: entry["action"] for entry in report["manual_actions"]}
        self.assertIn("retained", manual[str(runtime_home)])

    def test_update_and_uninstall_follow_the_private_runtime_policy(self):
        with patch.object(install.Path, "home", return_value=self.home), mock_host_clis("codex"):
            first = install.apply_plan(install.build_plan("user", None))
            runtime_home = install.private_runtime_home()
            second = install.apply_plan(install.build_plan("user", None))
            report = install.run_uninstall("user", None, dry_run=False)
        self.assertEqual(first["runtime"], second["runtime"])
        self.assertEqual(str(runtime_home), second["runtime"]["home"])
        manual = {entry["path"]: entry["action"] for entry in report["manual_actions"]}
        self.assertIn("retained", manual[str(runtime_home)])
        self.assertTrue(install.private_runtime_is_healthy(runtime_home))

    def test_dependency_contract_is_empty_documented_and_project_safe(self):
        declared = [
            line.strip()
            for line in install.RUNTIME_REQUIREMENTS.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
        self.assertEqual([], declared)
        self.assertIn("dependencies = []", (install.REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        self.assertNotIn("Stdlib-only", install.__doc__ or "")
        self.assertIn("requirements-runtime.txt", (install.REPO_ROOT / "ARCHITECTURE.md").read_text(encoding="utf-8"))
        self.assertIn("requirements-runtime.txt", (install.REPO_ROOT / "README.md").read_text(encoding="utf-8"))

    def test_dependency_install_ignores_project_and_pip_location_overrides(self):
        contaminated = {
            "PIP_PREFIX": "project-prefix",
            "PIP_TARGET": "project-target",
            "PIP_USER": "1",
            "PYTHONHOME": "project-python-home",
            "PYTHONPATH": "project-python-path",
            "VIRTUAL_ENV": "project-venv",
        }
        with patch.dict(os.environ, contaminated, clear=False):
            environment = install._dependency_environment()
        for name in contaminated:
            if name == "VIRTUAL_ENV":
                self.assertEqual("project-venv", environment[name])
            else:
                self.assertNotEqual(contaminated[name], environment.get(name))
