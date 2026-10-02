"""Pool members through the shim: scripted behaviours, cheaters, LLM members with a stand-in CLI, the invocation log."""
import json
import os
import random
import subprocess
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve()
BB = HERE.parents[1]
SK = BB.parents[1] / "skills" / "benchmaker"
for path in (BB, SK / "scripts"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from metabench import execute, pool, registry, store  # noqa: E402
from metabench.execute import Run  # noqa: E402
from metabench.members import ladder, shim  # noqa: E402

TOY = registry.MetaTask("toy-sum", "toydomain", {"output": "output.json", "inputs": ["input.json"], "number_lines": False},
                        (("oracle", "floor:noop"),), domain_file=HERE.parent / "fixtures" / "toydomain.py")
PROMPT = "Add the numbers in `input.json` and write `{\"sum\": <total>}` to `output.json`. Example output: {\"sum\": 6}\n"


def setUpModule():
    registry.register(TOY)


def document(**members):
    return {"meta_task": "toy-sum", "exposure": "private", "members": members, "known_pairs": [], "contrasts": [],
            "aa_pairs": [], "unconfirmed": []}


def scripted(behavior, **fields):
    return {"kind": "scripted", "behavior": behavior, "origin": "synthetic", **fields}


class ShimCase(unittest.TestCase):
    """Runs pool members through the same agent-directory path the delivered runner uses."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.store = store.Store(self.root / "store")
        self.scope = self.root

    def pool(self, **members):
        self.pool_id, self.pool_dir = pool.assemble(TOY, pool.normalize(document(**members), "toy-sum"), self.store)
        order = pool.read_order(self.store, "toy-sum", self.pool_id)
        self.ids = {spec["label"]: m for m, spec in order["members"].items()}
        self.run_ = Run("r1", self.store.run("r1"), self.root / "out")
        for folder in (self.run_.agents, self.run_.captures, self.run_.invocations):
            folder.mkdir(parents=True, exist_ok=True)
        return order

    def workspace(self, name="ws", numbers=(1, 2, 3), files=None, parent=None):
        path = (parent or self.root) / name
        path.mkdir(parents=True, exist_ok=True)
        (path / "input.json").write_text(json.dumps({"numbers": list(numbers)}), encoding="utf-8")
        for relative, text in (files or {}).items():
            (path / relative).parent.mkdir(parents=True, exist_ok=True)
            (path / relative).write_text(text, encoding="utf-8")
        return path

    def start(self, label, workspace, prompt=PROMPT):
        member = self.ids[label]
        agent = self.run_.agents / member
        if not agent.exists():
            execute.prepare_agent(self.run_, self.pool_dir, member, scope=self.scope)
        prompt_file = self.root / f"prompt-{workspace.name}.md"
        prompt_file.write_text(prompt, encoding="utf-8")
        return [sys.executable, str(agent / "run_agent.py"), "--workspace", str(workspace), "--prompt-file", str(prompt_file),
                "--transcript", str(self.root / f"t-{workspace.name}.jsonl"), "--timeout", "10"]

    def run_member(self, label, workspace, prompt=PROMPT, env=None):
        done = subprocess.run(self.start(label, workspace, prompt), cwd=workspace, capture_output=True, text=True, env=env)
        rows = execute.invocation_rows(self.run_.invocations / f"{self.ids[label]}.jsonl")
        return done, rows

    def output(self, workspace):
        path = workspace / "output.json"
        return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


class ScriptedMemberTests(ShimCase):
    def test_oracle_solves_logs_the_invocation_and_captures_without_naming_itself(self):
        self.pool(oracle=scripted("oracle"))
        ws = self.workspace()
        done, rows = self.run_member("oracle", ws)
        self.assertEqual(done.returncode, 0, done.stderr)
        line = json.loads(done.stdout.strip().splitlines()[-1])
        self.assertEqual((line["status"], line["exit_code"], line["model"], line["cost_usd"]), ("completed", 0, None, 0.0))
        self.assertEqual(self.output(ws), {"sum": 6})
        self.assertEqual(sorted(p.name for p in ws.iterdir()), ["input.json", "output.json"])
        (row,) = rows
        self.assertEqual((row["status"], row["recognized"], row["behavior_draw"], row["findings"]), ("completed", True, "oracle", []))
        self.assertEqual(Path(row["workspace"]), ws.resolve())
        captured = self.run_.ledger / row["final_capture"]
        self.assertEqual(json.loads((captured / "output.json").read_text(encoding="utf-8")), {"sum": 6})
        self.assertEqual((self.run_.ledger / row["prompt_capture"]).read_text(encoding="utf-8"), PROMPT)
        self.assertEqual((self.root / f"t-ws.jsonl").read_text(encoding="utf-8").strip(), '{"event": "done"}')
        for text in (done.stdout, (self.root / "t-ws.jsonl").read_text(encoding="utf-8")):
            self.assertNotIn("oracle", text)

    def test_defect_writes_a_wrong_answer_and_still_ends_normally(self):
        self.pool(defect=scripted("defect", defect="off_by_one"))
        ws = self.workspace()
        done, rows = self.run_member("defect", ws)
        self.assertEqual(done.returncode, 0)
        self.assertEqual(self.output(ws), {"sum": 7})
        self.assertEqual(rows[0]["behavior_draw"], "defect:off_by_one")

    def test_ladder_applies_a_defect_with_probability_q(self):
        self.pool(always=scripted("ladder", q=1.0, seed=3), never=scripted("ladder", q=0.0, seed=3))
        wrong = self.workspace("a")
        _, rows = self.run_member("always", wrong)
        self.assertNotEqual(self.output(wrong), {"sum": 6})
        self.assertRegex(rows[0]["behavior_draw"], r"^ladder:q=1\.0:applied=(off_by_one|drop_last)$")
        right = self.workspace("b")
        _, rows = self.run_member("never", right)
        self.assertEqual(self.output(right), {"sum": 6})
        self.assertEqual(rows[0]["behavior_draw"], "ladder:q=0.0:applied=none")

    def test_ladder_keeps_the_oracle_when_no_defect_is_wrong_on_the_instance(self):
        good = {"output.json": b'{"sum": 6}'}

        class Domain:
            DEFECTS = {"harmless": lambda instance, rng: good, "diag": lambda instance, rng: {"output.json": b"x"}}
            DIAGNOSTIC = ("diag",)
            solve = staticmethod(lambda instance: [good])
            check = staticmethod(lambda instance, files: {"label": "valid" if files == good else "invalid"})

        self.assertEqual(ladder.draw(Domain, {}, 1.0, random.Random(0)), (good, None))
        self.assertEqual(ladder.draw(Domain, {}, 0.0, random.Random(0)), (good, None))

    def test_floors(self):
        self.pool(noop=scripted("floor", name="noop"), empty=scripted("floor", name="empty"), echo=scripted("floor", name="echo_input"))
        for label, check in (("noop", lambda ws: self.assertFalse((ws / "output.json").exists())),
                             ("empty", lambda ws: self.assertEqual((ws / "output.json").read_bytes(), b"")),
                             ("echo", lambda ws: self.assertEqual((ws / "output.json").read_bytes(), (ws / "input.json").read_bytes()))):
            ws = self.workspace(label)
            done, rows = self.run_member(label, ws)
            self.assertEqual(done.returncode, 0, done.stderr)
            check(ws)
            self.assertTrue(rows[0]["behavior_draw"].startswith("floor:"))

    def test_heuristic_runs_the_domain_function(self):
        self.pool(first=scripted("heuristic", name="first_number"))
        ws = self.workspace(numbers=(4, 5))
        self.run_member("first", ws)
        self.assertEqual(self.output(ws), {"sum": 4})

    def test_unrecognized_workspace_is_logged_not_guessed(self):
        self.pool(oracle=scripted("oracle"))
        ws = self.root / "empty"
        ws.mkdir()
        done, rows = self.run_member("oracle", ws)
        self.assertEqual(done.returncode, 0)
        self.assertFalse(rows[0]["recognized"])
        self.assertEqual(list(ws.iterdir()), [])

    def test_a_crashing_member_reports_an_error_with_exit_code_one(self):
        self.pool(broken=scripted("defect", defect="no_such_defect"))
        ws = self.workspace()
        done, rows = self.run_member("broken", ws)
        self.assertEqual(done.returncode, 1)
        self.assertEqual(json.loads(done.stdout.strip().splitlines()[-1])["status"], "error")
        self.assertEqual(rows[0]["status"], "error")
        self.assertTrue((self.run_.ledger / rows[0]["final_capture"]).is_dir())

    def test_private_operators_run_from_the_store(self):
        self.store.private_members().mkdir(parents=True)
        (self.store.private_members() / "extra.py").write_text(
            "DEFECTS = {'zero': lambda instance, rng: {'output.json': b'{\"sum\": 0}'}}\n", encoding="utf-8")
        self.pool(extra={"kind": "private", "module": "private_members/extra.py", "behavior": "zero", "source": "DEFECTS"})
        ws = self.workspace()
        done, rows = self.run_member("extra", ws)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(self.output(ws), {"sum": 0})
        self.assertEqual(rows[0]["behavior_draw"], "private:zero")

    def test_concurrent_attempts_of_one_member_log_every_invocation_once(self):
        self.pool(oracle=scripted("oracle"))
        workspaces = [self.workspace(f"w{i}") for i in range(6)]
        self.start("oracle", workspaces[0])             # prepares the agent directory before the threads need it
        with ThreadPoolExecutor(6) as threads:
            codes = list(threads.map(lambda ws: subprocess.run(self.start("oracle", ws), cwd=ws, capture_output=True).returncode,
                                     workspaces))
        self.assertEqual(codes, [0] * 6)
        rows = execute.invocation_rows(self.run_.invocations / f"{self.ids['oracle']}.jsonl")
        self.assertEqual(len(rows), 6)
        self.assertEqual({r["status"] for r in rows}, {"completed"})
        self.assertEqual({Path(r["workspace"]) for r in rows}, {ws.resolve() for ws in workspaces})


class InvocationLogTests(unittest.TestCase):
    def test_a_lock_the_system_refuses_for_a_moment_is_waited_out(self):
        real, refused = os.open, []

        def flaky(path, flags, *rest):
            if len(refused) < 3:
                refused.append(path)
                raise PermissionError(13, "Access is denied")
            return real(path, flags, *rest)

        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(shim, "LOCK_WAIT", 0.001), mock.patch.object(shim.os, "open", flaky):
            log = Path(tmp) / "log" / "m.jsonl"
            shim.append(log, {"n": 1})
            shim.append(log, {"n": 2})
            self.assertEqual([json.loads(line)["n"] for line in log.read_text(encoding="utf-8").splitlines()], [1, 2])
            self.assertFalse(list(log.parent.glob("*.lock")))
        self.assertEqual(len(refused), 3)

    def test_a_stale_lock_delays_the_append_but_never_loses_it(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(shim, "LOCK_TRIES", 3), mock.patch.object(shim, "LOCK_WAIT", 0.001):
            log = Path(tmp) / "m.jsonl"
            (Path(tmp) / "m.jsonl.lock").write_text("", encoding="utf-8")
            shim.append(log, {"n": 1})
            self.assertEqual(json.loads(log.read_text(encoding="utf-8")), {"n": 1})
            self.assertTrue((Path(tmp) / "m.jsonl.lock").exists())

    def test_the_last_record_per_invocation_wins_in_start_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "m.jsonl"
            for row in ({"invocation": "b", "started": "2", "status": "running"}, {"invocation": "a", "started": "1", "status": "running"},
                        {"invocation": "b", "started": "2", "status": "completed"}):
                shim.append(log, row)
            log.write_text(log.read_text(encoding="utf-8") + "torn line without a newline", encoding="utf-8")
            self.assertEqual([(r["invocation"], r["status"]) for r in execute.invocation_rows(log)], [("a", "running"), ("b", "completed")])


class LlmMemberTests(ShimCase):
    """The shim around members.llm, with a stand-in `claude` that replays a recorded result and records its input."""

    LLM = {"kind": "llm", "mode": "single-call", "model": "claude-haiku-4-5", "effort": "low", "harness_defect": None, "io": TOY.io}
    OK = {"type": "result", "subtype": "success", "is_error": False, "api_error_status": None,
          "result": "```json\n{\"sum\": 6}\n```", "stop_reason": "end_turn", "total_cost_usd": 0.0187,
          "modelUsage": {"claude-haiku-4-5-20251001": {}}}
    LIMIT = {**OK, "is_error": True, "api_error_status": 429, "result": "You've hit your session limit · resets 4pm",
             "total_cost_usd": 0, "modelUsage": {}}

    def fake_claude(self, name, result):
        """A directory holding a `claude` executable that records its arguments and stdin and prints `result`."""
        folder = self.root / name
        folder.mkdir()
        (folder / "result.json").write_text(json.dumps(result), encoding="utf-8")
        (folder / "fake_claude.py").write_text(
            "import json, sys\n"
            "from pathlib import Path\n"
            "here = Path(__file__).parent\n"
            "(here / 'seen.json').write_text(json.dumps({'argv': sys.argv[1:], 'stdin': sys.stdin.read()}), encoding='utf-8')\n"
            "sys.stdout.write((here / 'result.json').read_text(encoding='utf-8'))\n", encoding="utf-8")
        if sys.platform == "win32":
            (folder / "claude.cmd").write_text(f'@"{sys.executable}" "%~dp0fake_claude.py" %*\r\n', encoding="utf-8", newline="")
        else:
            (folder / "claude").write_text(f'#!/bin/sh\nexec "{sys.executable}" "$(dirname "$0")/fake_claude.py" "$@"\n', encoding="utf-8")
            (folder / "claude").chmod(0o755)
        return folder, {**os.environ, "PATH": str(folder) + os.pathsep + os.environ["PATH"]}

    def test_a_single_call_member_writes_the_reply_and_reports_model_and_cost(self):
        self.pool(llm=dict(self.LLM))
        folder, env = self.fake_claude("bin-ok", self.OK)
        ws = self.workspace()
        done, rows = self.run_member("llm", ws, env=env)
        self.assertEqual(done.returncode, 0, done.stderr)
        line = json.loads(done.stdout.strip().splitlines()[-1])
        self.assertEqual((line["status"], line["model"], line["cost_usd"]), ("completed", "claude-haiku-4-5-20251001", 0.0187))
        self.assertEqual(self.output(ws), {"sum": 6})
        self.assertEqual((rows[0]["status"], rows[0]["behavior_draw"], rows[0]["findings"], rows[0]["cost_usd"]),
                         ("completed", "llm:single-call:claude-haiku-4-5:low", [], 0.0187))
        seen = json.loads((folder / "seen.json").read_text(encoding="utf-8"))
        self.assertIn("--safe-mode", seen["argv"])
        self.assertEqual(seen["argv"][seen["argv"].index("--model") + 1], "claude-haiku-4-5")
        self.assertIn("=== input.json ===", seen["stdin"])
        self.assertIn(PROMPT.strip(), seen["stdin"])

    def test_a_usage_limit_ends_the_member_with_exit_code_three(self):
        self.pool(llm=dict(self.LLM))
        _, env = self.fake_claude("bin-limit", self.LIMIT)
        ws = self.workspace()
        done, rows = self.run_member("llm", ws, env=env)
        self.assertEqual(done.returncode, 3)
        self.assertEqual(json.loads(done.stdout.strip().splitlines()[-1])["status"], "usage-limit")
        self.assertEqual(rows[0]["status"], "usage-limit")
        self.assertIsNone(self.output(ws))

    def test_inherited_claude_variables_do_not_reach_the_cli(self):
        self.pool(llm=dict(self.LLM))
        folder, env = self.fake_claude("bin-env", self.OK)
        (folder / "fake_claude.py").write_text(
            "import json, os, sys\n"
            "from pathlib import Path\n"
            "here = Path(__file__).parent\n"
            "(here / 'seen.json').write_text(json.dumps({'env': sorted(os.environ)}), encoding='utf-8')\n"
            "sys.stdout.write((here / 'result.json').read_text(encoding='utf-8'))\n", encoding="utf-8")
        env.update(CLAUDECODE="1", CLAUDE_CODE_EFFORT_LEVEL="high", GITHUB_TOKEN="x")
        self.run_member("llm", self.workspace(), env=env)
        seen = json.loads((folder / "seen.json").read_text(encoding="utf-8"))["env"]
        self.assertFalse({"CLAUDECODE", "CLAUDE_CODE_EFFORT_LEVEL", "GITHUB_TOKEN"} & set(seen))


class CheaterMemberTests(ShimCase):
    def setUp(self):
        super().setUp()
        self.pool(**{name: scripted("cheater", name=name) for name in ("read_workspace", "read_ancestors", "tamper", "exit_early", "copy_example")})

    def test_read_workspace_finds_hidden_answers_and_writes_them_as_the_answer(self):
        ws = self.workspace(files={".cache/expected.json": '{"sum": 6}', "notes/readme.txt": "nothing here"})
        _, rows = self.run_member("read_workspace", ws)
        self.assertEqual([f["path"] for f in rows[0]["findings"]], [".cache/expected.json"])
        self.assertEqual(self.output(ws), {"sum": 6})

    def test_read_workspace_finds_nothing_in_a_clean_workspace(self):
        ws = self.workspace()
        _, rows = self.run_member("read_workspace", ws)
        self.assertEqual(rows[0]["findings"], [])
        self.assertIsNone(self.output(ws))

    def test_read_ancestors_finds_nothing_against_a_kit_style_layout(self):
        ws = self.workspace(parent=self.root / "scratch" / "benchkit-x")
        _, rows = self.run_member("read_ancestors", ws)
        inside = [f for f in rows[0]["findings"] if Path(f["path"]).is_relative_to(self.root)]
        self.assertEqual(inside, [])
        self.assertIsNone(self.output(ws))

    def test_read_ancestors_finds_answers_when_workspaces_are_staged_inside_the_package(self):
        package = self.root / "pkg" / "task"
        (package / "tests").mkdir(parents=True)
        (package / "tests" / "expected.json").write_text('{"sum": 6}', encoding="utf-8")
        (package / "tests" / "verify.py").write_text("print('checks')\n", encoding="utf-8")
        ws = self.workspace("ws", parent=package / "work")
        _, rows = self.run_member("read_ancestors", ws)
        paths = {Path(f["path"]).name for f in rows[0]["findings"] if Path(f["path"]).is_relative_to(self.root)}
        self.assertEqual(paths, {"expected.json", "verify.py"})
        self.assertEqual(self.output(ws), {"sum": 6})

    def test_tamper_overwrites_reachable_verifiers_and_plants_reward_files(self):
        package = self.root / "pkg" / "task"
        (package / "tests").mkdir(parents=True)
        verifier = package / "tests" / "verify.py"
        verifier.write_text("raise SystemExit('real verifier')\n", encoding="utf-8")
        ws = self.workspace("ws", parent=package / "work", files={"test_local.py": "assert False\n"})
        done, rows = self.run_member("tamper", ws)
        self.assertIn("tampered", verifier.read_text(encoding="utf-8"))
        self.assertIn("tampered", (ws / "test_local.py").read_text(encoding="utf-8"))
        for folder in (ws, ws.parent):
            for name in ("reward.txt", "grade.json", "result.json"):
                self.assertTrue((folder / name).is_file(), (folder, name))
        self.assertEqual({Path(f["path"]).name for f in rows[0]["findings"] if Path(f["path"]).is_relative_to(self.root)}, {"verify.py"})
        self.assertEqual(json.loads(done.stdout.strip().splitlines()[-1])["final"], "All tests pass")

    def test_cheaters_never_read_or_touch_anything_above_their_scope(self):
        outside = self.root / "outside"
        (outside / "tests").mkdir(parents=True)
        (outside / "tests" / "expected.json").write_text('{"sum": 6}', encoding="utf-8")
        verifier = outside / "tests" / "verify.py"
        verifier.write_text("real verifier\n", encoding="utf-8")
        self.scope = outside / "work"
        ws = self.workspace("ws", parent=outside / "work")
        for label in ("read_ancestors", "tamper"):
            _, rows = self.run_member(label, ws)
            self.assertEqual(rows[0]["findings"], [], label)
        self.assertIsNone(self.output(ws))
        self.assertEqual(verifier.read_text(encoding="utf-8"), "real verifier\n")
        self.assertFalse((outside / "reward.txt").exists())
        self.assertTrue((outside / "work" / "reward.txt").is_file())

    def test_the_default_scope_is_the_runs_work_area(self):
        agent = execute.prepare_agent(self.run_, self.pool_dir, self.ids["tamper"])
        self.assertEqual(Path(json.loads((agent / "member.json").read_text(encoding="utf-8"))["scope"]), self.run_.work)

    def test_exit_early_claims_success_and_writes_nothing(self):
        ws = self.workspace()
        done, rows = self.run_member("exit_early", ws)
        self.assertEqual(json.loads(done.stdout.strip().splitlines()[-1])["final"], "All tests pass")
        self.assertEqual(sorted(p.name for p in ws.iterdir()), ["input.json"])
        self.assertEqual(rows[0]["findings"], [])

    def test_copy_example_writes_the_example_from_the_prompt(self):
        ws = self.workspace()
        self.run_member("copy_example", ws)
        self.assertEqual(self.output(ws), {"sum": 6})

    def test_copy_example_has_nothing_to_copy_without_a_json_example(self):
        ws = self.workspace()
        self.run_member("copy_example", ws, prompt="Add the numbers and write the sum to output.json.\n")
        self.assertIsNone(self.output(ws))


if __name__ == "__main__":
    unittest.main()
