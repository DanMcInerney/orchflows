"""Session discovery, activity evidence, and graph-layout regressions."""

import unittest
from unittest.mock import patch

from reader.scripts import ui_discovery, ui_layout, ui_sessions
from reader.tests.test_ui_cases import _base as fixture
from reader.tests.test_ui_cases._transcript_support import TranscriptCase


class TestActivityState(TranscriptCase):
    """Activity is derived only from Agent calls and matching results."""

    def read(self, session=fixture.TITLED_SESSION):
        found = ui_discovery.find_session(self.transcripts, session)
        self.assertIsNotNone(found, session)
        return ui_sessions.read_session(found)

    def states(self, session=fixture.TITLED_SESSION):
        return {agent["id"]: agent["state"] for agent in self.read(session)["agents"]}

    def test_matching_agent_result_is_finished_and_unanswered_call_running(self):
        states = self.states()
        self.assertEqual(ui_sessions.ACTIVITY_FINISHED, states[fixture.RETURNED_AGENT])
        self.assertEqual(ui_sessions.ACTIVITY_RUNNING, states[fixture.CALLED_AGENT])
        self.assertEqual(ui_sessions.ACTIVITY_UNKNOWN, states[fixture.UNEVIDENCED_AGENT])

    def test_non_agent_tool_calls_do_not_mark_a_subagent_finished(self):
        found = ui_discovery.find_session(self.transcripts, fixture.TITLED_SESSION)
        summary = ui_sessions.cached_transcript(found["path"], found["identity"])
        self.assertEqual({"toolu_alpha_01", "toolu_alpha_02"}, summary["agent_calls"])
        self.assertEqual({"toolu_alpha_01"}, summary["agent_returns"])

    def test_missing_result_does_not_default_to_finished(self):
        self.own_fixture()
        path = self.transcripts / fixture.ALPHA_PROJECT / (fixture.TITLED_SESSION + ".jsonl")
        original = path.read_text(encoding="utf-8")
        path.write_text(
            "".join(line for line in original.splitlines(True) if "tool_result" not in line),
            encoding="utf-8",
        )
        states = self.states()
        self.assertNotIn(ui_sessions.ACTIVITY_FINISHED, states.values())
        self.assertEqual(ui_sessions.ACTIVITY_RUNNING, states[fixture.RETURNED_AGENT])

    def test_agent_file_stat_failure_has_no_epoch_fallback(self):
        found = ui_discovery.find_session(self.transcripts, fixture.TITLED_SESSION)
        session_path = found["path"]
        real = ui_sessions._stat_identity

        def refuse_subagents(path):
            return None if "subagents" in path.parts else real(path)

        with patch.object(ui_sessions, "_stat_identity", refuse_subagents):
            agents = ui_sessions.read_agents(session_path)
        unknown = next(item for item in agents if item["id"] == fixture.UNEVIDENCED_AGENT)
        self.assertIsNone(unknown["modified"])

    def test_every_activity_state_has_a_declared_presentation(self):
        for state in ui_sessions.ACTIVITY_STATES:
            presentation = ui_sessions.activity_presentation(state)
            self.assertEqual(state, presentation.word)
            self.assertTrue(presentation.glyph)
            self.assertIn(presentation.hue, ui_sessions.HUE_TOKENS)


class TestSessionLayout(TranscriptCase):
    """Session topology uses the canonical layout owner, not HTML glue."""

    def read(self, session=fixture.TITLED_SESSION):
        found = ui_discovery.find_session(self.transcripts, session)
        return ui_sessions.read_session(found)

    def test_graph_contains_orchestrator_and_each_subagent(self):
        agents = self.read()["agents"]
        nodes, edges, inferred = ui_layout.session_graph(agents)
        self.assertIn(ui_sessions.ORCHESTRATOR_NODE, nodes)
        self.assertEqual(1 + len(agents), len(nodes))
        self.assertEqual(len(agents), len(edges))
        self.assertTrue(all(target in nodes for _source, target in edges))
        self.assertTrue(all(edge in edges for edge in inferred))

    def test_depth_one_agents_attach_to_orchestrator(self):
        agents = self.read()["agents"]
        nodes, edges, _inferred = ui_layout.session_graph(agents)
        self.assertTrue(nodes)
        for agent in agents:
            if agent["depth"] == 1:
                self.assertIn((ui_sessions.ORCHESTRATOR_NODE, agent["id"]), edges)

    def test_recorded_parent_attaches_to_known_subagent(self):
        agents = self.read(fixture.TRUNCATED_SESSION)["agents"]
        child = next(agent for agent in agents if agent["id"] == fixture.CHILD_AGENT)
        self.assertEqual(fixture.PARENT_AGENT, ui_layout._agent_parent(child, ui_layout.agent_ids(agents)))
