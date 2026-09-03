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

    def use_copied_runtime_builds(self):
        """Grade lifecycle policy over a copy of a real runtime, not a build.

        Every case that calls this asks the installer for a runtime only so
        that it has one to reuse, repair, refuse or retain. See the helper.
        """

        patcher = copied_runtime_builds()
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_user_install_uses_private_runtime_when_project_venv_is_active(self):
        install.venv.EnvBuilder(symlinks=os.name != "nt", with_pip=False).create(
            self.project_runtime
        )
        project_python = install.private_runtime_python(self.project_runtime)
        # Three members, one per detected host: planning unpacks the whole
        # tuple, so a two-member patch fails loudly here instead of
        # silently dropping the third host from every plan it builds.
        program = "\n".join(
            (
                "from pathlib import Path",
                "from unittest.mock import patch",
                "import importlib.util, sys",
                f"spec = importlib.util.spec_from_file_location('installer_under_test', {str(install.REPO_ROOT / 'install.py')!r})",
                "installer = importlib.util.module_from_spec(spec)",
                "sys.modules[spec.name] = installer",
                "spec.loader.exec_module(installer)",
                f"with patch.object(installer.Path, 'home', return_value=Path({str(self.home)!r})), patch.object(installer, 'detect_hosts', return_value=(False, True, False)):",
                "    accepted = installer.resolve_source_commit()",
                "    raise SystemExit(installer.main("
                "['--user', '--yes', '--accepted-source', accepted]))",
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
        self.assertNotEqual(project_python, runtime_python)
        self.assertNotIn(str(self.project_runtime), rendered)

    def test_user_install_reuses_healthy_private_runtime(self):
        self.use_copied_runtime_builds()
        with patch.object(install.Path, "home", return_value=self.home), mock_host_clis("codex"):
            install.apply_plan(install.build_plan(), accepted_source=install.resolve_source_commit())
            marker = install.private_runtime_home() / "reuse-marker"
            marker.write_text("keep", encoding="utf-8")
            install.apply_plan(install.build_plan(), accepted_source=install.resolve_source_commit())
        self.assertEqual("keep", marker.read_text(encoding="utf-8"))

    def test_the_runtime_links_its_base_interpreter_rather_than_copying_it(self):
        """The property a copied interpreter cannot hold.

        A relocatable CPython -- uv's, and every python-build-standalone
        build -- reaches ``libpython`` by a path relative to its own
        executable, so a venv holding a copy aborts before it runs a line.
        ``python -m venv`` symlinks on POSIX for that reason. CI's
        interpreters are the kind that survive being copied, which leaves
        this assertion the only thing standing between the builder and the
        hosts where copying is fatal.
        """

        if os.name == "nt":
            self.skipTest("Windows venvs copy: symlinking there needs a privilege")
        with patch.object(install.Path, "home", return_value=self.home), mock_host_clis("codex"):
            install.apply_plan(install.build_plan(), accepted_source=install.resolve_source_commit())
            runtime_home = install.private_runtime_home()
            runtime_python = install.private_runtime_python(runtime_home)
        self.assertFalse(runtime_python.resolve().is_relative_to(runtime_home.resolve()))

    def test_user_install_repairs_an_unhealthy_private_runtime(self):
        self.use_copied_runtime_builds()
        with patch.object(install.Path, "home", return_value=self.home), mock_host_clis("codex"):
            install.apply_plan(install.build_plan(), accepted_source=install.resolve_source_commit())
            runtime_home = install.private_runtime_home()
            marker = runtime_home / "unhealthy-marker"
            marker.write_text("remove me", encoding="utf-8")
            metadata = install._runtime_metadata()
            metadata["requirements_sha256"] = "0" * 64
            (runtime_home / install.RUNTIME_METADATA_FILENAME).write_text(
                json.dumps(metadata) + "\n", encoding="utf-8"
            )
            install.apply_plan(install.build_plan(), accepted_source=install.resolve_source_commit())
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

    def test_failed_repair_preserves_the_previous_runtime(self):
        self.use_copied_runtime_builds()
        with patch.object(install.Path, "home", return_value=self.home), mock_host_clis("codex"):
            install.apply_plan(install.build_plan(), accepted_source=install.resolve_source_commit())
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
                    install.apply_plan(install.build_plan(), accepted_source=install.resolve_source_commit())
        self.assertTrue(old_python.is_file())
        self.assertEqual("keep", marker.read_text(encoding="utf-8"))

    def test_unowned_runtime_is_refused_and_preserved(self):
        runtime_home = self.home / ".orchflows" / "runtime"
        runtime_home.mkdir(parents=True)
        marker = runtime_home / "not-ours"
        marker.write_text("keep", encoding="utf-8")
        with patch.object(install.Path, "home", return_value=self.home), mock_host_clis("codex"):
            with self.assertRaisesRegex(RuntimeError, "unowned private runtime"):
                install.apply_plan(install.build_plan(), accepted_source=install.resolve_source_commit())
        self.assertEqual("keep", marker.read_text(encoding="utf-8"))

    def test_rendered_friction_command_executes_from_a_spaced_home(self):
        self.use_copied_runtime_builds()
        spaced_home = self.root / "home with spaces"
        spaced_home.mkdir()
        with patch.object(install.Path, "home", return_value=spaced_home), mock_host_clis("codex"):
            install.apply_plan(install.build_plan(), accepted_source=install.resolve_source_commit())
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
        self.use_copied_runtime_builds()
        with patch.object(install.Path, "home", return_value=self.home), mock_host_clis("codex"):
            self.assertEqual("create", install.build_plan().runtime_action)
            install.apply_plan(install.build_plan(), accepted_source=install.resolve_source_commit())
            self.assertEqual("reuse", install.build_plan().runtime_action)
            metadata = install._runtime_metadata()
            metadata["requirements_sha256"] = "0" * 64
            (install.private_runtime_home() / install.RUNTIME_METADATA_FILENAME).write_text(
                json.dumps(metadata) + "\n", encoding="utf-8"
            )
            self.assertEqual("repair", install.build_plan().runtime_action)

    def test_failed_first_install_leaves_runtime_discoverable_to_uninstall(self):
        self.use_copied_runtime_builds()
        with patch.object(install.Path, "home", return_value=self.home), mock_host_clis("codex"):
            plan = install.build_plan()
            real_create = install._create_private_runtime

            def create_then_fail():
                real_create()
                raise RuntimeError("later install step failed")

            with patch.object(install, "_create_private_runtime", side_effect=create_then_fail):
                with self.assertRaisesRegex(RuntimeError, "later install step failed"):
                    install.apply_plan(plan, accepted_source=install.resolve_source_commit())
            receipt = json.loads(plan.receipt_path.read_text(encoding="utf-8"))
            report = install.run_uninstall("user", None, dry_run=True)
            runtime_home = install.private_runtime_home()
        self.assertTrue(receipt["install_in_progress"])
        self.assertEqual(str(runtime_home), receipt["runtime"]["home"])
        manual = {entry["path"]: entry["action"] for entry in report["manual_actions"]}
        self.assertIn("retained", manual[str(runtime_home)])

    def test_update_and_uninstall_follow_the_private_runtime_policy(self):
        self.use_copied_runtime_builds()
        with patch.object(install.Path, "home", return_value=self.home), mock_host_clis("codex"):
            first = install.apply_plan(install.build_plan(), accepted_source=install.resolve_source_commit())
            runtime_home = install.private_runtime_home()
            second = install.apply_plan(install.build_plan(), accepted_source=install.resolve_source_commit())
            report = install.run_uninstall("user", None, dry_run=False)
        self.assertEqual(first["runtime"], second["runtime"])
        self.assertEqual(str(runtime_home), second["runtime"]["home"])
        manual = {entry["path"]: entry["action"] for entry in report["manual_actions"]}
        self.assertIn("retained", manual[str(runtime_home)])
        self.assertTrue(install.private_runtime_is_healthy(runtime_home))

    def test_runtime_dependency_direct_set_has_one_owner_and_is_mirrored(self):
        direct = (install.REPO_ROOT / "requirements-runtime.in").read_text(
            encoding="utf-8"
        ).splitlines()
        self.assertEqual(["starlette==0.49.3", "uvicorn==0.34.3"], direct)
        project = (install.REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
        self.assertIn('"starlette==0.49.3"', project)
        self.assertIn('"uvicorn==0.34.3"', project)
        # The killed claim, caught however it is spelled or wrapped: a
        # hyphen or a line break between `stdlib` and `only` does not make
        # the claim any less restated. `doc_claim` owns that normalisation.
        self.assertNotIn("stdlib only", doc_claim(install.__doc__))
        self.assertIn("requirements-runtime.txt", (install.REPO_ROOT / "ARCHITECTURE.md").read_text(encoding="utf-8"))
        self.assertIn("requirements-runtime.txt", (install.REPO_ROOT / "README.md").read_text(encoding="utf-8"))

    def test_runtime_health_requires_exact_server_dependency_versions(self):
        runtime_home = self.home / ".orchflows" / "runtime"
        runtime_python = install.private_runtime_python(runtime_home)
        runtime_python.parent.mkdir(parents=True)
        runtime_python.touch()
        (runtime_home / install.RUNTIME_METADATA_FILENAME).write_text(
            json.dumps(install._runtime_metadata()) + "\n", encoding="utf-8"
        )

        def probe(starlette="0.49.3", uvicorn="0.34.3"):
            return subprocess.CompletedProcess(
                [],
                0,
                stdout=json.dumps(
                    {
                        "prefix": str(runtime_home.resolve()),
                        "version": list(sys.version_info[:3]),
                        "dependencies": {
                            "starlette": starlette,
                            "uvicorn": uvicorn,
                        },
                    }
                ),
                stderr="",
            )

        with patch.object(install._runtime.subprocess, "run", return_value=probe()):
            self.assertTrue(install.private_runtime_is_healthy(runtime_home))
        with patch.object(
            install._runtime.subprocess, "run", return_value=probe(starlette="0.49.2")
        ):
            self.assertFalse(install.private_runtime_is_healthy(runtime_home))
        with patch.object(
            install._runtime.subprocess, "run", return_value=probe(uvicorn="0.34.2")
        ):
            self.assertFalse(install.private_runtime_is_healthy(runtime_home))

    def test_runtime_build_enforces_hashes_from_the_complete_lock(self):
        runtime_home = self.home / ".orchflows" / "runtime"

        def create_fake_runtime(home):
            runtime_python = install.private_runtime_python(Path(home))
            runtime_python.parent.mkdir(parents=True)
            runtime_python.touch()

        exact_probe = subprocess.CompletedProcess(
            [],
            0,
            stdout=json.dumps(
                {
                    "prefix": str(runtime_home.resolve()),
                    "version": list(sys.version_info[:3]),
                    "dependencies": {
                        "starlette": "0.49.3",
                        "uvicorn": "0.34.3",
                    },
                }
            ),
            stderr="",
        )
        installed = subprocess.CompletedProcess([], 0, stdout="", stderr="")
        with patch.object(
            install.venv.EnvBuilder, "create", side_effect=create_fake_runtime
        ), patch.object(
            install._runtime.subprocess, "run", side_effect=[installed, exact_probe]
        ) as run:
            install._build_private_runtime(runtime_home)

        command = run.call_args_list[0].args[0]
        self.assertIn("--require-hashes", command)
        self.assertEqual(str(install.RUNTIME_REQUIREMENTS), command[-1])

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
