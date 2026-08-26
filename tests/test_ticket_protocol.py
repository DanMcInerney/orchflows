"""Regression oracles for the sole sealed ticket protocol."""

from __future__ import annotations

import json
import hashlib
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from installer import packages, planning
from scripts.tickets_format import _parse_frontmatter
from scripts.tickets_reissue import _cited_context


ROOT = Path(__file__).resolve().parent.parent
TICKETS = ROOT / "scripts" / "tickets.py"
REQUIRED_EXECUTORS = {
    "orch-decompose", "orch-draft", "orch-edit", "orch-critique",
    "orch-repair", "orch-verify", "orch-integrate",
}


class TicketRun:
    def __init__(self, state: Path):
        self.state = state

    def call(self, *args):
        env = dict(os.environ, ORCHFLOWS_STATE_HOME=str(self.state))
        done = subprocess.run(
            [sys.executable, str(TICKETS), *args], cwd=ROOT, env=env,
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        payload = json.loads(done.stdout)
        if done.returncode or "error" in payload:
            raise AssertionError(f"{args}: {done.returncode}: {payload}")
        return payload

    def new(self, run: str, ticket_id: str, executor: str):
        return self.call(
            "new", run, ticket_id, "--executor", executor,
            "--objective", f"Exercise {executor} through the sealed protocol.",
            "--criterion", "the packet names the exact executor | oracle: packet JSON | oracle_class: deterministic | provenance: pre-existing",
            "--isolation", "none",
        )

    def seal(self, run: str, root_id: str):
        stamped = self.call("stamp-generation", run, root_id)
        validated = self.call("draft-validate", run, root_id)
        cut = validated["draft_validation"]["cut_generation"]
        sealed = self.call("seal", run, root_id, "--cut-generation", cut)
        return stamped, validated, sealed

    def ticket(self, run: str, ticket_id: str):
        return (self.state / "tickets" / run / f"{ticket_id}.md").read_text(encoding="utf-8")


class EndToEndProtocolTest(unittest.TestCase):
    def test_fresh_direct_root_reaches_packet_with_its_exact_executor(self):
        with tempfile.TemporaryDirectory() as raw:
            lane = TicketRun(Path(raw))
            lane.new("direct", "root", "orch-verify")
            stamped, validated, sealed = lane.seal("direct", "root")
            self.assertRegex(stamped["stamp_generation"]["root_generation"], r"^root:root:1:sha256:[0-9a-f]{64}$")
            self.assertRegex(validated["draft_validation"]["cut_generation"], r"^cut:root:1:sha256:[0-9a-f]{64}$")
            self.assertEqual("sealed", sealed["assignment_seal"]["state"])
            lane.call("ready", "--run", "direct")
            lane.call("claim", "direct", "root", "--by", "protocol-test")
            packet = lane.call("packet", "direct", "root", "--reply-to", "root-test")
            self.assertEqual("orch-verify", packet["packet"]["executor"])
            self.assertRegex(packet["packet"]["admission"], r"^plain-artifact:sha256:[0-9a-f]{64}$")

    def test_decomposed_root_and_member_use_the_same_generation_model(self):
        with tempfile.TemporaryDirectory() as raw:
            lane = TicketRun(Path(raw))
            lane.new("decomposed", "root", "orch-decompose")
            lane.new("decomposed", "root.01", "orch-verify")
            lane.seal("decomposed", "root")
            root = _parse_frontmatter(lane.ticket("decomposed", "root"))
            member = _parse_frontmatter(lane.ticket("decomposed", "root.01"))
            self.assertEqual(root["root_generation"], member["root_generation"])
            self.assertEqual(root["cut_generation"], member["cut_generation"])
            self.assertNotEqual(root["assignment_seal"], member["assignment_seal"])

    def test_fresh_fix_template_is_sealed_before_it_is_written(self):
        with tempfile.TemporaryDirectory() as raw:
            lane = TicketRun(Path(raw))
            made = lane.call(
                "instantiate", str(ROOT / "compositions" / "fix"),
                "--run", "fix-template", "--set", "failure=observed",
                "--set", "workspace=C:/fixture",
            )
            generation = made["instantiate"]["generation"]
            self.assertEqual("00-reproduce", generation["root_id"])
            self.assertRegex(generation["root_generation"], r"^root:00-reproduce:1:sha256:[0-9a-f]{64}$")
            for ticket_id in made["instantiate"]["ids"]:
                data = _parse_frontmatter(lane.ticket("fix-template", ticket_id))
                self.assertEqual("pending", data["admission"])
                self.assertRegex(data["root_generation"], r"^root:")
                self.assertRegex(data["cut_generation"], r"^cut:")
                self.assertRegex(data["assignment_seal"], r"^sha256:[0-9a-f]{64}$")

    def test_successor_digest_is_context_only(self):
        body = "---\nid: prior\n---\n\n## Result\n\nresult bytes\n\n## Context\n\n- state: accepted identity abc.\n\n## Handoff\n\nhandoff bytes\n"
        digest, refusal = _cited_context(body, "prior-run", "prior")
        self.assertIsNone(refusal)
        self.assertEqual(hashlib.sha256(b"- state: accepted identity abc.").hexdigest(), digest)


class RegistryClosureTest(unittest.TestCase):
    def test_every_emitted_executor_has_an_exact_role_matched_codex_skill(self):
        surfaces = [ROOT / "templates" / "host-block.md", ROOT / "skills" / "engines" / "orch-frontier" / "SKILL.md"]
        surfaces.extend((ROOT / "packs").glob("orch-*/SKILL.md"))
        surfaces.extend((ROOT / "compositions").glob("*/*.md"))
        emitted = set()
        for path in surfaces:
            emitted.update(re.findall(r"\borch-[a-z0-9-]+\b", path.read_text(encoding="utf-8")))

        canonical = {}
        for skill_md in packages.discover_packages():
            frontmatter, _ = packages.split_frontmatter(skill_md.read_text(encoding="utf-8"))
            canonical[packages.frontmatter_field(frontmatter, "name")] = (
                packages.frontmatter_field(frontmatter, "role"), skill_md,
            )
        emitted = {name for name in emitted if name in canonical}
        self.assertTrue(REQUIRED_EXECUTORS <= emitted)

        with tempfile.TemporaryDirectory() as raw, mock.patch.object(Path, "home", return_value=Path(raw)), mock.patch.object(planning, "detect_hosts", return_value=(False, True)):
            plan = planning._build_user_plan(script_name_discoverer=lambda _root: [])
        adapters = {path.parent.name: body for path, body in plan.codex_skills}
        self.assertEqual(set(canonical), set(adapters) - {directory.name for directory, _, _ in packages.discover_templates()})
        profiles = packages.load_role_profiles()
        for name in sorted(emitted):
            role, skill_md = canonical[name]
            body = adapters[name]
            self.assertIn(str(plan.lib_home / skill_md.relative_to(ROOT)), body)
            if role in ("planner", "worker"):
                binding = profiles[f"orch-{role}"]["codex"]
                self.assertIn(f"requires the matching role `orch-{role}`", body)
                self.assertIn(f"agent_type `{binding['agent_type']}`", body)


class LiveSurfaceCensusTest(unittest.TestCase):
    def test_ticket_surfaces_have_no_protocol_brand_or_compatibility_branch(self):
        paths = [ROOT / "contracts" / "work-item.md", ROOT / "rules" / "topology.md", ROOT / "TICKETS.md"]
        paths.extend((ROOT / "scripts").glob("tickets*.py"))
        paths.extend((ROOT / "skills").glob("**/SKILL.md"))
        paths.extend((ROOT / "packs").glob("**/*.md"))
        forbidden = tuple("v" + str(number) + ":" for number in range(3))
        forbidden += ("ADMISSION_" + "V2", "is_" + "v1", "is_" + "v2", "co" + "hort")
        findings = []
        for path in paths:
            text = path.read_text(encoding="utf-8")
            for token in forbidden:
                if token in text:
                    findings.append(f"{path.relative_to(ROOT)}: {token}")
        self.assertEqual([], findings)
        self.assertIn("words-v1", (ROOT / "contracts" / "work-item.md").read_text(encoding="utf-8"))
        self.assertIn("search-policy/v1", (ROOT / "docs" / "search-plan-protocol.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
