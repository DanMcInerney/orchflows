"""How each native child was launched: fresh, inherited parent history, or unknown. Synthetic records only."""

from contextlib import closing
import importlib.util
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("native_logs_launch", ROOT / "scripts/native_logs.py")
logs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(logs)


def transcript(path, records):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r) + "\n" for r in records), encoding="utf-8")


def response(kind, **fields):
    return {"type": "response_item", "payload": {"type": kind, **fields}}


def exec_call(call_id, code):
    return response("custom_tool_call", name="exec", call_id=call_id, input=code)


def exec_done(call_id):
    return response("custom_tool_call_output", call_id=call_id, output=[{"type": "input_text", "text": "done"}])


def spawned(*children):
    return {"type": "event_msg", "payload": {"type": "item_completed", "item": {
        "type": "CollabAgentToolCall", "id": "exec-event", "tool": "spawn_agent", "status": "completed",
        "receiver_thread_ids": list(children)}}}


def v1(code, child):
    return [exec_call("call-" + child, code), spawned(child), exec_done("call-" + child)]


def claude(role, *blocks, **fields):
    return {"type": role, "message": {"content": list(blocks)}, **fields}


class LaunchContextTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="orchflows-native-launch-")
        self.addCleanup(temporary.cleanup)
        self.home = Path(temporary.name).resolve()
        with closing(sqlite3.connect(self.home / "state_5.sqlite")) as db:
            db.execute("CREATE TABLE threads (id TEXT, rollout_path TEXT, cwd TEXT, title TEXT, created_at INTEGER, updated_at INTEGER)")
            db.execute("CREATE TABLE thread_spawn_edges (parent_thread_id TEXT, child_thread_id TEXT)")
            db.commit()

    def codex(self, identifier, records, parent=None, **meta):
        path = self.home / "sessions" / (identifier + ".jsonl")
        header = {"id": identifier, **({"parent_thread_id": parent} if parent else {}), **meta}
        transcript(path, [{"type": "session_meta", "payload": header}] + records)
        with closing(sqlite3.connect(self.home / "state_5.sqlite")) as db:
            db.execute("INSERT INTO threads VALUES (?,?,?,?,?,?)", (identifier, str(path), "/project", identifier, 0, 0))
            if parent:
                db.execute("INSERT INTO thread_spawn_edges VALUES (?,?)", (parent, identifier))
            db.commit()

    def launches(self, host, root, **kwargs):
        agents = logs.inspect(host, root, self.home, **kwargs)["agents"]
        return {a["id"]: a for a in agents}

    def test_codex_v1_fork_context_from_exec_code_and_child_record(self):
        self.codex("root", [
            *v1('await tools.multi_agent_v1__spawn_agent({message:"Say fork_context: true", fork_context:false})', "fresh"),
            *v1('const r = await tools.multi_agent_v1__spawn_agent({\n  fork_context: true, // full history\n  message: `review ${x}`})', "forked"),
            *v1('await tools.multi_agent_v1__spawn_agent({message:"no fork argument"})', "default"),
            exec_call("both", 'await Promise.all([tools.multi_agent_v1__spawn_agent({message:"a", fork_context:true}), '
                              'tools.multi_agent_v1__spawn_agent({message:"b", fork_context:false})])'),
            spawned("mixed"), exec_done("both"),
            exec_call("one", "await tools.multi_agent_v1__spawn_agent({fork_context:false})"),
            exec_call("two", "await tools.multi_agent_v1__spawn_agent({fork_context:false})"),
            spawned("overlap"), exec_done("one"), exec_done("two")])
        for child in ("fresh", "default", "mixed"):
            self.codex(child, [], parent="root", multi_agent_version="v1")
        for child in ("forked", "overlap"):
            self.codex(child, [], parent="root", multi_agent_version="v1", forked_from_id="root",
                       subagent_history_start_ordinal=9)
        agents = self.launches("codex", "root")
        self.assertEqual({k: a.get("launch_context") for k, a in agents.items()},
                         {"root": None, "fresh": "fresh", "forked": "inherited", "default": "fresh",
                          "mixed": "unknown", "overlap": "inherited"})
        record, call = agents["forked"]["launch_evidence"]
        self.assertEqual((record["forked_from_id"], record["history_start_ordinal"], record["indicates"]), ("root", 9, "inherited"))
        self.assertEqual((call["api"], call["tool"], call["call_id"], call["arguments"], call["indicates"]),
                         ("codex-v1", "exec", "call-forked", [{"fork_context": True}], "inherited"))
        self.assertEqual(agents["mixed"]["launch_evidence"][1]["arguments"], [{"fork_context": True}, {"fork_context": False}])
        overlap = agents["overlap"]["launch_evidence"][1]
        self.assertIsNone(overlap["indicates"])
        self.assertIn("2 exec calls were open", overlap["detail"])
        self.assertEqual((agents["root"]["spawn_count"], agents["root"]["unlinked_spawns"]), (5, []))

    def test_codex_v1_arguments_only_count_in_the_spawn_object(self):
        cases = {
            "tools.multi_agent_v1__spawn_agent({items:[{type:'text', fork_context:true}], fork_context:false})": "fresh",
            "/* fork_context:true */ tools.multi_agent_v1__spawn_agent({message})": "fresh",
            "messages.map(m => tools.multi_agent_v1__spawn_agent({message: m, fork_context: true}))": "inherited",
            "tools.multi_agent_v1__spawn_agent({...base, message})": "unknown",
            "tools.multi_agent_v1__spawn_agent({message, fork_context: forkIt})": "unknown",
            "tools.multi_agent_v1__spawn_agent(args)": "unknown",
            "tools.exec_command({cmd: 'spawn nothing'})": "unknown",
        }
        records = [r for index, code in enumerate(cases) for r in v1(code, f"child-{index}")]
        self.codex("root", records)
        for index in range(len(cases)):
            self.codex(f"child-{index}", [], parent="root", multi_agent_version="v1")
        agents = self.launches("codex", "root")
        self.assertEqual([agents[f"child-{i}"]["launch_context"] for i in range(len(cases))], list(cases.values()))

    def test_codex_v2_fork_turns_linked_by_task_path(self):
        def spawn(call, output, **arguments):
            return [response("function_call", name="spawn_agent", namespace="collaboration", call_id=call,
                             arguments=json.dumps({"message": "gAAAAencrypted", **arguments})),
                    response("function_call_output", call_id=call, output=output)]
        self.codex("root", [*spawn("s1", '{"task_name":"/root/review"}', task_name="review", fork_turns="none"),
                            *spawn("s2", '{"task_name":"/root/full"}', task_name="full", fork_turns="all"),
                            *spawn("s3", '{"task_name":"/root/implicit"}', task_name="implicit"),
                            *spawn("s4", "spawn failed", task_name="lost", fork_turns="2")])
        for child in ("review", "full", "implicit", "lost"):
            self.codex(child, [], parent="root", multi_agent_version="v2", agent_path="/root/" + child)
        agents = self.launches("codex", "root")
        self.assertEqual({k: agents[k]["launch_context"] for k in ("review", "full", "implicit", "lost")},
                         {"review": "fresh", "full": "inherited", "implicit": "inherited", "lost": "unknown"})
        self.assertEqual(agents["review"]["launch_evidence"][1]["arguments"], [{"fork_turns": "none"}])
        self.assertEqual(agents["implicit"]["launch_evidence"][1]["arguments"], [{}])
        unlinked = agents["root"]["unlinked_spawns"]
        self.assertEqual([(u["call_id"], u["indicates"]) for u in unlinked], [("s4", "inherited")])
        self.assertNotIn("gAAAAencrypted", json.dumps(agents))

    def test_claude_fork_subagent_type_is_inherited(self):
        session = self.home / "projects/project/session.jsonl"
        def agent(call, name="Agent", **arguments):
            return claude("assistant", {"type": "tool_use", "id": call, "name": name, "input": {"prompt": "work", **arguments}})
        def launched(call, child):
            return claude("user", {"type": "tool_result", "tool_use_id": call, "content": "launched"},
                          toolUseResult={"status": "async_launched", "agentId": child})
        transcript(session, [agent("t1", subagent_type="fork"), launched("t1", "forkchild"),
                             agent("t2", subagent_type="general-purpose"), launched("t2", "worker"),
                             agent("t3", name="Task"), agent("t4", subagent_type="fork")])
        children = {"forkchild": {"agentType": "fork"}, "worker": {"agentType": "general-purpose"},
                    "implicit": {"toolUseId": "t3"}, "orphan": None}
        for child, meta in children.items():
            path = session.with_suffix("") / "subagents" / f"agent-{child}.jsonl"
            transcript(path, [claude("user", {"type": "text", "text": "work"})])
            if meta is not None:
                path.with_suffix(".meta.json").write_text(json.dumps(meta), encoding="utf-8")
        agents = self.launches("claude", "session")
        self.assertEqual({k: agents[k]["launch_context"] for k in children},
                         {"forkchild": "inherited", "worker": "fresh", "implicit": "fresh", "orphan": "unknown"})
        record, call = agents["forkchild"]["launch_evidence"]
        self.assertEqual((record["agent_type"], call["arguments"], call["line"]), ("fork", [{"subagent_type": "fork"}], 1))
        self.assertEqual(agents["implicit"]["launch_evidence"][1]["arguments"], [{"subagent_type": "omitted"}])
        self.assertEqual([(u["call_id"], u["indicates"]) for u in agents["session"]["unlinked_spawns"]], [("t4", "inherited")])

    def test_child_on_later_page_keeps_parent_spawn_evidence_and_nothing_is_written(self):
        self.codex("root", v1("await tools.multi_agent_v1__spawn_agent({fork_context:true, message:'m'})", "child"))
        self.codex("child", [], parent="root", multi_agent_version="v1")
        before = {p: p.read_bytes() for p in self.home.rglob("*") if p.is_file()}
        first = logs.inspect("codex", "root", self.home, limit=1)
        child = logs.inspect("codex", "root", self.home, limit=1, after=first["next_cursor"])["agents"][0]
        self.assertEqual((child["id"], child["launch_context"]), ("child", "inherited"))
        self.assertEqual(child["launch_evidence"][1]["call_id"], "call-child")
        self.assertEqual(before, {p: p.read_bytes() for p in self.home.rglob("*") if p.is_file()})


if __name__ == "__main__":
    unittest.main()
