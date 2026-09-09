"""Outside production seam checks for the 3D browser-game package."""
import hashlib
import json
import os
import queue
import shutil
import subprocess
import tempfile
import threading
import time
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import urlopen


# This test resolves its repository-owned fixture and package paths from the
# checkout root; the climb belongs to this test owner, not a wildcard exemption.
ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "example-workflows" / "3d-browser-game"
SCRIPTS = PACKAGE / "scripts"
NODE = shutil.which("node") or "node"


def node_script(script, args, cwd, timeout=30):
    return subprocess.run([NODE, str(SCRIPTS / script), *[str(item) for item in args]], cwd=cwd, capture_output=True, text=True, encoding="utf-8", timeout=timeout)


class OutsideProductionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "target-game"
        self.root.mkdir()
        self.git(["init", "-q"])
        self.git(["config", "user.email", "outside@example.invalid"])
        self.git(["config", "user.name", "Outside Probe"])
        (self.root / "package.json").write_text('{"private":true}\n', encoding="utf-8")
        self.git(["add", "package.json"])
        self.git(["commit", "-qm", "fixture"])

    def tearDown(self):
        self.temp.cleanup()

    def git(self, args):
        return subprocess.run(["git", *args], cwd=self.root, check=True, capture_output=True, text=True, encoding="utf-8")

    def commit(self):
        return self.git(["rev-parse", "HEAD"]).stdout.strip()

    def config(self, build_script, output_dir="dist"):
        return {
            "build": {"command": [NODE, str(build_script)], "output_dir": output_dir},
            "server": {"output_dir": output_dir, "ready_path": "/", "host": "127.0.0.1", "port": 0},
            "harness": {
                "commands": [
                    {"type": "observe"}, {"type": "key", "key": "ArrowRight", "action": "down"},
                    {"type": "observe"}, {"type": "stop"},
                ],
                "capture_dir": ".outside/captures", "session_out": ".outside/session.json",
            },
        }

    def write_script(self, name, source):
        path = self.root / name
        path.write_text(source, encoding="utf-8")
        return path

    def write_config(self, config):
        path = self.root / "outside-config.json"
        path.write_text(json.dumps(config), encoding="utf-8")
        return path

    def build(self, config, expected=None):
        config_path = self.write_config(config)
        expected = expected or self.commit()
        return node_script("outside_build.mjs", ["--config", config_path, "--workspace", self.root, "--artifact-commit", "git:" + expected], self.root)

    def test_package_helper_command_is_fixed_to_package_node_and_script(self):
        expression = "import * as m from './example-workflows/3d-browser-game/scripts/outside_probe.mjs'; console.log(JSON.stringify(m.packageOwnedCommand('build',['--config','target.json'])));"
        result = subprocess.run([NODE, "--input-type=module", "-e", expression], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=30)
        self.assertEqual(0, result.returncode, result.stderr)
        command = json.loads(result.stdout)
        self.assertEqual(Path(os.path.realpath(NODE)), Path(os.path.realpath(command[0])))
        self.assertEqual(SCRIPTS / "outside_build.mjs", Path(command[1]))
        self.assertEqual(["--config", "target.json"], command[2:])

    def test_package_command_rejects_caller_selected_helper(self):
        expression = "import * as m from './example-workflows/3d-browser-game/scripts/outside_probe.mjs'; try { m.packageOwnedCommand('node',['-e','process.exit(9)']); process.exit(9); } catch (error) { console.log(JSON.stringify({code:error.code,pointer:error.pointer})); }"
        result = subprocess.run([NODE, "--input-type=module", "-e", expression], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=30)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual({"code": "invalid-input", "pointer": "/outside_probe/helper"}, json.loads(result.stdout))

    def test_build_hashes_actual_output_and_binds_source_tree(self):
        script = self.write_script("build.mjs", "import {mkdir,writeFile} from 'node:fs/promises'; await mkdir('dist',{recursive:true}); await writeFile('dist/index.html','built-'+Date.now());")
        result = self.build(self.config(script))
        self.assertEqual(0, result.returncode, result.stderr + result.stdout)
        value = json.loads(result.stdout)
        self.assertEqual("built", value["status"])
        self.assertEqual("git:" + self.commit(), value["artifact_commit"])
        self.assertEqual("dist", value["output"]["path"])
        self.assertEqual(1, value["output"]["file_count"])
        self.assertRegex(value["output"]["files"][0]["sha256"], r"^sha256:[0-9a-f]{64}$")
        self.assertRegex(value["output"]["sha256"], r"^sha256:[0-9a-f]{64}$")
        self.assertRegex(value["source"]["tree"], r"^git:[0-9a-f]{40}$")

    def test_failed_build_removes_previous_output(self):
        stale = self.root / "dist" / "stale.html"
        stale.parent.mkdir()
        stale.write_text("stale", encoding="utf-8")
        script = self.write_script("fail.mjs", "process.exitCode=17;")
        result = self.build(self.config(script))
        self.assertNotEqual(0, result.returncode)
        self.assertFalse(self.root.joinpath("dist").exists())
        self.assertIn("production build exited", result.stderr)

    def test_build_rejects_head_drift_and_removes_new_output(self):
        script = self.write_script("drift.mjs", "import {mkdir,writeFile} from 'node:fs/promises'; import {spawnSync} from 'node:child_process'; await mkdir('dist',{recursive:true}); await writeFile('dist/index.html','drift'); spawnSync('git',['commit','--allow-empty','-m','drift'],{stdio:'ignore'});")
        expected = self.commit()
        result = self.build(self.config(script), expected=expected)
        self.assertNotEqual(0, result.returncode)
        self.assertFalse(self.root.joinpath("dist").exists())
        self.assertIn("joined commit changed during production build", result.stderr)

    def test_build_timeout_removes_partial_output(self):
        script = self.write_script("slow.mjs", "import {mkdir,writeFile} from 'node:fs/promises'; await mkdir('dist',{recursive:true}); await writeFile('dist/index.html','partial'); await new Promise(resolve => setTimeout(resolve,10000));")
        config = self.config(script)
        config["build"]["timeout_ms"] = 100
        result = self.build(config)
        self.assertNotEqual(0, result.returncode)
        self.assertFalse(self.root.joinpath("dist").exists())
        self.assertIn("production build exceeded", result.stderr)

    def test_build_refuses_git_metadata_and_tracked_source_output(self):
        git_config = self.config(self.write_script("noop.mjs", ""), output_dir=".git")
        git_result = self.build(git_config)
        self.assertNotEqual(0, git_result.returncode)
        self.assertTrue(self.root.joinpath(".git").is_dir())
        source_config = self.config(self.write_script("noop-source.mjs", ""), output_dir="package.json")
        source_result = self.build(source_config)
        self.assertNotEqual(0, source_result.returncode)
        self.assertIn("overlaps tracked source", source_result.stderr)
        self.assertTrue(self.root.joinpath("package.json").is_file())

    def directory_alias(self, target, alias):
        # Junctions need no Windows symlink privilege; POSIX uses a symlink.
        result = subprocess.run([NODE, "--input-type=module", "-e",
            "import {symlinkSync} from 'node:fs'; symlinkSync(process.argv[1],process.argv[2],process.platform === 'win32' ? 'junction' : 'dir');",
            str(target), str(alias)], capture_output=True, text=True, encoding="utf-8", timeout=10)
        self.assertEqual(0, result.returncode, result.stderr)
        return alias

    def test_static_server_reports_actual_bind_and_only_serves_output(self):
        script = self.write_script("build.mjs", "import {mkdir,writeFile} from 'node:fs/promises'; await mkdir('dist',{recursive:true}); await writeFile('dist/index.html','hello outside');")
        built = self.build(self.config(script))
        self.assertEqual(0, built.returncode, built.stderr)
        build_result = json.loads(built.stdout)
        config_path = self.write_config(self.config(script))
        workspace = self.directory_alias(self.root, Path(self.temp.name) / "workspace-alias")
        command = [NODE, str(SCRIPTS / "outside_server.mjs"), "--config", config_path, "--workspace", workspace, "--artifact-commit", "git:" + self.commit(), "--output-sha256", build_result["output"]["sha256"]]
        process = subprocess.Popen(command, cwd=PACKAGE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8")
        first_line = queue.Queue()
        threading.Thread(target=lambda: first_line.put(process.stdout.readline()), daemon=True).start()
        try:
            line = first_line.get(timeout=10)
            ready = json.loads(line)
            self.assertEqual("ready", ready["status"], ready)
            self.assertEqual("dist", ready["output"]["path"])
            self.assertEqual(build_result["output"]["sha256"], ready["output"]["sha256"])
            with urlopen(ready["address"]["url"], timeout=5) as response:
                self.assertEqual(200, response.status)
                self.assertEqual(b"hello outside", response.read())
            self.directory_alias(self.root, self.root / "dist" / "escape")
            for path in ("/../package.json", "/%2e%2e%2fpackage.json", "/escape/package.json"):
                with self.subTest(path=path):
                    with self.assertRaises(HTTPError) as rejected:
                        urlopen(ready["address"]["url"].rstrip("/") + path, timeout=5)
                    self.assertIn(rejected.exception.code, (400, 404, 500))
        finally:
            process.terminate()
            process.communicate(timeout=10)
        self.assertIsNotNone(process.returncode)

    def test_static_server_rejects_stale_output_hash_before_bind(self):
        script = self.write_script("build.mjs", "import {mkdir,writeFile} from 'node:fs/promises'; await mkdir('dist',{recursive:true}); await writeFile('dist/index.html','fresh');")
        built = self.build(self.config(script))
        self.assertEqual(0, built.returncode, built.stderr)
        config_path = self.write_config(self.config(script))
        workspace = self.directory_alias(self.root, Path(self.temp.name) / "workspace-alias")
        command = [NODE, str(SCRIPTS / "outside_server.mjs"), "--config", config_path, "--workspace", workspace, "--artifact-commit", "git:" + self.commit(), "--output-sha256", "sha256:" + "0" * 64]
        result = subprocess.run(command, cwd=PACKAGE, capture_output=True, text=True, encoding="utf-8", timeout=30)
        self.assertNotEqual(0, result.returncode)
        self.assertIn("server output hash differs", result.stderr)
        self.assertNotIn('"status":"ready"', result.stdout)
        outside = Path(self.temp.name) / "outside"
        outside.mkdir()
        (outside / "index.html").write_text("must not serve", encoding="utf-8")
        self.directory_alias(outside, self.root / "escaped-output")
        for output in ("../outside", "escaped-output"):
            with self.subTest(output=output):
                config = self.config(script)
                config["server"]["output_dir"] = output
                self.write_config(config)
                rejected = subprocess.run(command, cwd=PACKAGE, capture_output=True, text=True, encoding="utf-8", timeout=30)
                self.assertEqual(2, rejected.returncode, rejected.stderr)
                self.assertEqual("/server/output_dir", json.loads(rejected.stdout)["error"]["pointer"])
                self.assertIn("path escapes root", rejected.stderr)


    def test_run_timeout_kills_and_observes_a_package_child(self):
        expression = "import {run} from './example-workflows/3d-browser-game/scripts/outside_probe.mjs'; try { await run([process.execPath,'-e','setTimeout(()=>{},10000)'],process.cwd(),100); process.exit(9); } catch (error) { console.log(JSON.stringify({code:error.code,pointer:error.pointer})); }"
        result = subprocess.run([NODE, "--input-type=module", "-e", expression], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=30)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual({"code": "timeout-process-loss", "pointer": "/probe/timeout_ms"}, json.loads(result.stdout))

    def test_harness_capability_failure_returns_without_a_session(self):
        config = self.config(self.write_script("build.mjs", ""))
        config.update({"artifact_commit": "git:" + self.commit(), "server": {**config["server"], "external": True, "cwd": str(self.root), "url": "http://127.0.0.1:9/"}, "capture_dir": str(self.root / ".outside" / "captures"), "session_out": str(self.root / ".outside" / "session.json"), "browser": {"package": "module-that-is-not-installed", "headless": False}})
        config_path = self.write_config(config)
        result = node_script("outside_harness.mjs", ["--config", config_path], PACKAGE, timeout=30)
        self.assertNotEqual(0, result.returncode)
        self.assertIn("Playwright is unavailable", result.stderr)
        self.assertFalse((self.root / ".outside" / "session.json").exists())

    def test_outside_config_rejects_missing_capture_and_nonordinary_scenario(self):
        expression = "import * as m from './example-workflows/3d-browser-game/scripts/outside_probe.mjs'; const c={build:{command:['node','build.mjs'],output_dir:'dist'},server:{output_dir:'dist',ready_path:'/'},harness:{commands:[{type:'observe'},{type:'stop'}],capture_dir:'.outside/c',session_out:'.outside/s.json'}}; try { m.validateConfig(c); process.exit(9); } catch (error) { console.log(JSON.stringify({code:error.code,pointer:error.pointer})); }"
        result = subprocess.run([NODE, "--input-type=module", "-e", expression], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=30)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual("/outside_probe/config/harness/commands", json.loads(result.stdout)["pointer"])

    def test_outside_registration_validates_inline_config_and_result_schema(self):
        expression = "import * as m from './example-workflows/3d-browser-game/scripts/validate_evidence.mjs'; const config={build:{command:['node','build.mjs'],output_dir:'dist'},server:{output_dir:'dist',ready_path:'/'},harness:{commands:[{type:'observe'},{type:'key',key:'w',action:'down'},{type:'observe'},{type:'stop'}],capture_dir:'.outside/c',session_out:'.outside/s.json'}}; const result={status:'observed',artifact_commit:'git:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',joined_commit:'git:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',build:{},server:{},harness:{},captures:{},cleanup:{}}; console.log(JSON.stringify(await m.validateOutsideProbeRegistration({config,result})));"
        result = subprocess.run([NODE, "--input-type=module", "-e", expression], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=30)
        self.assertEqual(0, result.returncode, result.stderr)
        value = json.loads(result.stdout)
        self.assertEqual("observed", value["result"]["status"])
        self.assertIsNone(value["config_path"])


if __name__ == "__main__":
    unittest.main()
